"""KANConvNet — IoV intrusion-detection classifier (FedIoV §3.4).

Computational flow (paper eqs 16–19):

    z0 = Preprocess(x)                                       # done in DataLoader
    z1 = W1 · F(z0) + b1                                     # FourierKANLinear
    z2 = σ_Kolmogorov(z1)                                    # KolmogorovActivation
    z3, z4, z5 = ReLU + Linear stack                         # hidden refinement
    z6 = W5 · σ_Kolmogorov(z5) + b5                          # KAN head
    ŷ  = softmax(z6)                                         # classifier

When ``use_conv_backbone=True`` (default) the model first runs a small
``KANConv1d`` stack over the time-windowed signal (B, C, T) → global pool →
flat feature vector → the KAN head above. This realises the
"convolutional backbone" the paper references and keeps the architecture
applicable to both windowed CAN frames and flat telemetry vectors.

Input shapes accepted:
    (B, F)        — flat feature vector (skips the conv backbone)
    (B, F, W)     — windowed sequence (uses the conv backbone)
"""
from __future__ import annotations

from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from .kan_conv import KANConv1d
from .kan_layers import FourierKANLinear, KolmogorovActivation


class KANConvNet(nn.Module):
    """Lightweight Kolmogorov–Arnold convolutional classifier.

    Args:
        in_features:     F — input feature dimension.
        n_classes:       number of output classes.
        layer_size:      width of the KAN/MLP head (Table 4 "Layer Size").
        dropout:         dropout rate (Table 4).
        fourier_modes:   K for the Fourier-basis KAN layers.
        conv_channels:   (C1, C2) for the two-stage KAN conv backbone.
        kernel_size:     conv kernel length.
        use_conv_backbone: if False, expect (B, F) input only.
    """

    def __init__(
        self,
        in_features: int = 46,
        n_classes: int = 4,
        layer_size: int = 128,
        dropout: float = 0.2,
        fourier_modes: int = 8,
        conv_channels: Tuple[int, int] = (32, 64),
        kernel_size: int = 5,
        use_conv_backbone: bool = True,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.n_classes = n_classes
        self.use_conv_backbone = use_conv_backbone

        # ── KAN convolutional backbone (eq. 16 applied per time step) ──
        if use_conv_backbone:
            c1, c2 = conv_channels
            self.conv1 = KANConv1d(in_features, c1, kernel_size, n_modes=fourier_modes)
            self.bn1 = nn.BatchNorm1d(c1)
            self.conv2 = KANConv1d(c1, c2, kernel_size, n_modes=fourier_modes)
            self.bn2 = nn.BatchNorm1d(c2)
            self.pool = nn.AdaptiveAvgPool1d(1)            # global temporal pool
            head_in = c2
        else:
            self.conv1 = self.bn1 = self.conv2 = self.bn2 = self.pool = None
            head_in = in_features

        # ── KAN head: eq. (16) → (17) → (18) → (19) ──
        # z1 = W1 · F(z0) + b1
        self.kan_in = FourierKANLinear(head_in, layer_size, n_modes=fourier_modes)
        # σ_Kolmogorov
        self.act1 = KolmogorovActivation(layer_size)
        # Hidden refinement (z3, z4, z5) — three Linear+ReLU blocks
        self.hidden = nn.Sequential(
            nn.Linear(layer_size, layer_size), nn.ReLU(inplace=True), nn.Dropout(dropout),
            nn.Linear(layer_size, layer_size), nn.ReLU(inplace=True), nn.Dropout(dropout),
            nn.Linear(layer_size, layer_size), nn.ReLU(inplace=True),
        )
        # Final σ_Kolmogorov before the readout (eq. 18)
        self.act2 = KolmogorovActivation(layer_size)
        # Readout: z6 = W5 · σ_K(z5) + b5
        self.head = nn.Linear(layer_size, n_classes)

        self.dropout = nn.Dropout(dropout)
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, a=5 ** 0.5)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def _backbone(self, x: torch.Tensor) -> torch.Tensor:
        """(B, F, W) -> (B, head_in)."""
        x = self.conv1(x)
        x = self.bn1(x)
        x = F.relu(x, inplace=True)
        x = self.conv2(x)
        x = self.bn2(x)
        x = F.relu(x, inplace=True)
        x = self.pool(x).squeeze(-1)        # (B, C2)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns class logits (B, n_classes)."""
        if x.dim() == 3:
            if not self.use_conv_backbone:
                raise ValueError("Got 3-D input but conv backbone is disabled.")
            if x.size(1) != self.in_features:
                raise ValueError(
                    f"Expected C={self.in_features}; got {x.size(1)}"
                )
            z0 = self._backbone(x)                            # (B, C2)
        elif x.dim() == 2:
            if x.size(1) != self.in_features:
                raise ValueError(
                    f"Expected F={self.in_features}; got {x.size(1)}"
                )
            z0 = x
        else:
            raise ValueError(f"Expected (B,F) or (B,F,W); got {tuple(x.shape)}")

        # KAN head — eqs 16–19
        z1 = self.kan_in(z0)            # W1 · F(z0) + b1
        z2 = self.act1(z1)              # σ_Kolmogorov
        z5 = self.hidden(self.dropout(z2))
        z5_act = self.act2(z5)          # σ_Kolmogorov(z5)
        z6 = self.head(z5_act)          # W5 · σ_K(z5) + b5
        return z6                        # logits — softmax happens in CE loss

    @torch.no_grad()
    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """Argmax over class logits — eq. (19) `ŷ = SGD(z6)` at inference."""
        return self.forward(x).argmax(dim=-1)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

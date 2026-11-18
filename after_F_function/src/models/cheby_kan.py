"""Chebyshev Kolmogorov-Arnold Network (ChebyKAN) Architecture.

Basis Functions: Orthogonal Chebyshev polynomials of the first kind:
    T_0(x) = 1
    T_1(x) = x
    T_k(x) = 2x * T_{k-1}(x) - T_{k-2}(x)
Input stability: x_norm = tanh(x) in [-1, 1].
"""
from __future__ import annotations

import math
from typing import Dict, Any, List
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class ChebyshevKANLinear(nn.Module):
    """Linear KAN layer using Chebyshev orthogonal polynomials."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        degree: int = 4,
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.degree = degree

        # Chebyshev weights: (out_features, in_features, degree + 1)
        self.cheby_weight = nn.Parameter(torch.empty(out_features, in_features, degree + 1))
        # Base linear weights: (out_features, in_features)
        self.base_weight = nn.Parameter(torch.empty(out_features, in_features))

        if bias:
            self.bias = nn.Parameter(torch.empty(out_features))
        else:
            self.register_parameter("bias", None)

        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.kaiming_uniform_(self.base_weight, a=math.sqrt(5))
        nn.init.normal_(self.cheby_weight, mean=0.0, std=1.0 / (self.in_features * (self.degree + 1)))
        if self.bias is not None:
            bound = 1 / math.sqrt(self.in_features) if self.in_features > 0 else 0
            nn.init.uniform_(self.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Normalize input to [-1, 1] via tanh for Chebyshev polynomial domain
        x_norm = torch.tanh(x)

        # Recursive Chebyshev polynomial computation
        cheby_basis = [torch.ones_like(x_norm)]
        if self.degree >= 1:
            cheby_basis.append(x_norm)

        for _ in range(2, self.degree + 1):
            cheby_basis.append(2.0 * x_norm * cheby_basis[-1] - cheby_basis[-2])

        # Shape: (batch_size, in_features, degree + 1)
        cheby_basis = torch.stack(cheby_basis, dim=-1)

        base_out = F.linear(x_norm, self.base_weight)
        cheby_out = torch.einsum("bid,oid->bo", cheby_basis, self.cheby_weight)

        out = base_out + cheby_out
        if self.bias is not None:
            out = out + self.bias
        return out


class ChebyshevKAN(nn.Module):
    """Deep ChebyKAN network with LayerNorm and Dropout."""

    def __init__(
        self,
        in_features: int = 46,
        n_classes: int = 5,
        hidden_dim: int = 64,
        num_layers: int = 2,
        degree: int = 4,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.n_classes = n_classes
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.degree = degree

        layers: List[nn.Module] = []
        # Layer 1: Input -> hidden_dim
        layers.append(ChebyshevKANLinear(in_features, hidden_dim, degree=degree))
        layers.append(nn.LayerNorm(hidden_dim))
        layers.append(nn.Dropout(dropout))

        # Hidden layers
        for _ in range(num_layers - 1):
            layers.append(ChebyshevKANLinear(hidden_dim, hidden_dim, degree=degree))
            layers.append(nn.LayerNorm(hidden_dim))
            layers.append(nn.Dropout(dropout))

        # Output layer
        layers.append(ChebyshevKANLinear(hidden_dim, n_classes, degree=degree))

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def flatten_parameters(self) -> np.ndarray:
        """Flatten all trainable parameters into a single 1D numpy array (float64)."""
        vecs = [p.detach().cpu().numpy().ravel() for p in self.parameters() if p.requires_grad]
        return np.concatenate(vecs).astype(np.float64)

    def load_flat_parameters(self, flat: np.ndarray) -> None:
        """Load 1D parameter array back into PyTorch model parameters."""
        flat = np.asarray(flat, dtype=np.float64)
        offset = 0
        for p in self.parameters():
            if not p.requires_grad:
                continue
            numel = p.numel()
            chunk = flat[offset:offset + numel].reshape(p.shape)
            p.data.copy_(torch.from_numpy(chunk).to(p.device, dtype=p.dtype))
            offset += numel

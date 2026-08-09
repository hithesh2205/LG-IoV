"""MamKANformer full model.

.. warning::

   **ARCHIVED — Month 3 branch, not used by any live code path.**

   Superseded by ``models/cheby_kan.ChebyshevKAN`` in Month 4. The reason is
   parameter count, which is the cost driver under homomorphic encryption:
   MamKANformer has ~609,000 parameters against ChebyKAN's 44,164, i.e. 14x the
   ciphertexts, 14x the V2X bandwidth and 14x the aggregation time.

   Nothing in ``train_federated.py``, ``federated/`` or ``config.yaml`` reads
   this module. It is retained as a reference for the Month-3 design study and
   is deliberately frozen. Do not extend it — it also predates the Month-5 data
   fixes (defects D1/D2), so anything trained with it would be invalid.

Combines per-modality input projection heads, a sequence fusion block,
a stack of MamKANformer blocks, and the post-block KAN layers (including the FHE hook).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .mamkanformer_block import MamKANformerBlock
from .kan_sublayer import BSplineKANLinear


class MamKANformer(nn.Module):
    """The unified MamKANformer network for centralized baseline IoV IDS.
    
    Accepts (B, 46) input and maps to (B, n_classes).
    """

    def __init__(
        self,
        dataset: str,
        n_classes: int,
        hidden_dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        layer_size: int = 128,
        grid_size: int = 5,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.dataset = dataset
        self.n_classes = n_classes
        self.hidden_dim = hidden_dim
        self.layer_size = layer_size

        # Define modality slices and projection heads depending on the dataset
        self._setup_modalities()

        # Define projection heads
        self.proj_heads = nn.ModuleList([
            nn.Linear(size, hidden_dim) for size in self.modality_sizes
        ])

        # Stack of MamKANformerBlocks
        self.blocks = nn.ModuleList([
            MamKANformerBlock(
                d_model=hidden_dim,
                num_heads=num_heads,
                grid_size=grid_size,
                dropout=dropout,
            )
            for _ in range(num_layers)
        ])

        # Normalization layer after blocks
        self.ln_post = nn.LayerNorm(hidden_dim)

        # Post-block KAN Layers (derived from the right side of the diagram)
        # KAN Layer 1: nonlinear mapping from hidden_dim to layer_size
        self.kan_layer1 = BSplineKANLinear(
            in_features=hidden_dim,
            out_features=layer_size,
            grid_size=grid_size,
        )

        # KAN Layer 2: Sensitive Layer -> Encrypted with FHE during aggregation
        # [FHE-HOOK] adaptive encryption layer inserts here
        self.kan_layer2 = BSplineKANLinear(
            in_features=layer_size,
            out_features=layer_size,
            grid_size=grid_size,
        )

        # KAN Layer 3: final nonlinear mapping
        self.kan_layer3 = BSplineKANLinear(
            in_features=layer_size,
            out_features=layer_size,
            grid_size=grid_size,
        )

        # Readout classification head (Softmax applied in CrossEntropyLoss)
        self.classifier = nn.Linear(layer_size, n_classes)
        self.dropout = nn.Dropout(dropout)

    def _setup_modalities(self) -> None:
        """Define feature slice indices for different dataset modalities."""
        if self.dataset in ("can_vtc", "car_hack"):
            # 1. Payload: 18 features (indices 0..15, 44, 45)
            # 2. DLC: 2 features (indices 16, 17)
            # 3. CAN ID: 26 features (indices 18..43)
            self.modality_indices = [
                [i for i in range(16)] + [44, 45],
                [16, 17],
                [i for i in range(18, 44)],
            ]
        elif self.dataset == "cicids":
            # 1. Packet Lengths/Sizes (14 features)
            # 2. Durations and IATs (19 features)
            # 3. Header lengths and rates (6 features)
            # 4. Flags and ratios (7 features)
            self.modality_indices = [
                list(range(0, 14)),
                list(range(14, 33)),
                list(range(33, 39)),
                list(range(39, 46)),
            ]
        elif self.dataset == "veremi":
            # 1. Kinematic means (18 features)
            # 2. Kinematic stds (18 features)
            # 3. Speed magnitude (2 features)
            # 4. Acceleration magnitude (2 features)
            # 5. Spread and headings (6 features)
            self.modality_indices = [
                list(range(0, 18)),
                list(range(18, 36)),
                [36, 37],
                [38, 39],
                list(range(40, 46)),
            ]
        else:
            # Fallback: divide features into 4 equal splits
            self.modality_indices = [
                list(range(0, 12)),
                list(range(12, 24)),
                list(range(24, 35)),
                list(range(35, 46)),
            ]
            
        self.modality_sizes = [len(indices) for indices in self.modality_indices]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the full MamKANformer model.
        
        Args:
            x: input tensor of shape (B, 46)
            
        Returns:
            logits: output tensor of shape (B, n_classes)
        """
        # Shape trace: B, 46
        B = x.size(0)

        # [1] Input Modality Projection
        projected_modalities = []
        for i, indices in enumerate(self.modality_indices):
            # Extract features belonging to this modality
            x_mod = x[:, indices]  # (B, mod_size)
            # Project to hidden_dim
            proj_out = self.proj_heads[i](x_mod)  # (B, hidden_dim)
            projected_modalities.append(proj_out)

        # [2] Sequence Fusion Module
        # Stack projected modalities along the sequence dimension: (B, Num_Modalities, hidden_dim)
        x_seq = torch.stack(projected_modalities, dim=1)

        # [3] MamKANformer Blocks Trunk
        for block in self.blocks:
            x_seq = block(x_seq)  # (B, Num_Modalities, hidden_dim)

        # Apply final sequence norm
        x_seq = self.ln_post(x_seq)

        # [4] Temporal/Modality Pooling
        # Average pool across modality sequence dimension
        x_pool = x_seq.mean(dim=1)  # (B, hidden_dim)

        # [5] Post-block KAN Layers (incorporating the FHE encrypted layer)
        z1 = self.kan_layer1(x_pool)  # (B, layer_size)
        z1 = self.dropout(F.relu(z1))

        # [FHE-HOOK] adaptive encryption layer inserts here
        z2 = self.kan_layer2(z1)  # (B, layer_size)
        z2 = self.dropout(F.relu(z2))

        z3 = self.kan_layer3(z2)  # (B, layer_size)
        z3 = self.dropout(F.relu(z3))

        # [6] Classification Head
        logits = self.classifier(z3)  # (B, n_classes)
        return logits

    def num_parameters(self) -> int:
        """Return the number of learnable parameters in the model."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

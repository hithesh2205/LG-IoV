"""MamKANformer block coupling Mamba, Self-Attention, and KAN.
"""
from __future__ import annotations

import torch
import torch.nn as nn

from .mamba_sublayer import MambaSublayer
from .attention_sublayer import MultiHeadSelfAttention
from .kan_sublayer import BSplineKANLinear


class MamKANformerBlock(nn.Module):
    """A single MamKANformer block.
    
    Couples Mamba, Multi-Head Self-Attention, and B-spline KAN layers.
    Follows pre-normalization design with residual connections.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 4,
        grid_size: int = 5,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.mamba = MambaSublayer(d_model=d_model)

        self.ln2 = nn.LayerNorm(d_model)
        self.attention = MultiHeadSelfAttention(d_model=d_model, num_heads=num_heads, dropout=dropout)

        self.ln3 = nn.LayerNorm(d_model)
        self.kan = BSplineKANLinear(
            in_features=d_model,
            out_features=d_model,
            grid_size=grid_size,
        )

        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        """Forward pass of the MamKANformer block.
        
        Args:
            x: input tensor of shape (B, T, D)
            mask: optional attention mask of shape (B, H, T, T)
            
        Returns:
            output tensor of shape (B, T, D)
        """
        # [1] Mamba SSM sub-layer
        # Input shape: (B, T, D) -> LN -> Mamba -> Residual -> (B, T, D)
        x = x + self.dropout(self.mamba(self.ln1(x)))

        # [2] Multi-Head Self-Attention sub-layer
        # Input shape: (B, T, D) -> LN -> Attention -> Residual -> (B, T, D)
        x = x + self.dropout(self.attention(self.ln2(x), mask=mask))

        # [3] KAN sub-layer
        # Reshape to (B * T, D) for the BSplineKANLinear layer, then restore shape
        B, T, D = x.shape
        x_norm = self.ln3(x)
        x_flat = x_norm.view(-1, D)
        
        kan_out_flat = self.kan(x_flat)
        kan_out = kan_out_flat.view(B, T, D)
        
        x = x + self.dropout(kan_out)
        
        return x

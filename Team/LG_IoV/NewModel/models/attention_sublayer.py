"""Multi-Head Self-Attention sub-layer implemented in PyTorch.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiHeadSelfAttention(nn.Module):
    """Multi-Head Self-Attention Layer.
    
    Accepts input shape (B, T, D) and returns (B, T, D).
    Matches paper §3.4 temporal dependency modeling context.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        assert d_model % num_heads == 0, f"d_model ({d_model}) must be divisible by num_heads ({num_heads})"
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        # Key, Query, Value projections
        self.q_proj = nn.Linear(d_model, d_model, bias=True)
        self.k_proj = nn.Linear(d_model, d_model, bias=True)
        self.v_proj = nn.Linear(d_model, d_model, bias=True)

        # Output projection
        self.out_proj = nn.Linear(d_model, d_model, bias=True)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        """Forward pass of the Multi-Head Self-Attention.
        
        Args:
            x: input tensor of shape (B, T, D)
            mask: optional attention mask of shape (B, 1, T, T) or (B, T, T)
            
        Returns:
            output tensor of shape (B, T, D)
        """
        B, T, D = x.shape

        # [1] Project to Queries, Keys, and Values
        # (B, T, D) -> (B, T, H, d_k) -> (B, H, T, d_k)
        q = self.q_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)

        # [2] Scaled dot-product attention
        # scores: (B, H, T, T)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)

        if mask is not None:
            # Mask should broadcast to (B, H, T, T)
            scores = scores.masked_fill(mask == 0, -1e9)

        # Softmax weights along sequence key dimension
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # [3] Multiply weights by Values
        # context: (B, H, T, d_k)
        context = torch.matmul(attn_weights, v)

        # [4] Concatenate heads and project output
        # (B, H, T, d_k) -> (B, T, H, d_k) -> (B, T, D)
        context = context.transpose(1, 2).contiguous().view(B, T, D)
        out = self.out_proj(context)
        return out

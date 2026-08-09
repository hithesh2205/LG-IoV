"""B-spline Kolmogorov-Arnold Network (KAN) linear layer implemented in pure PyTorch.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class BSplineKANLinear(nn.Module):
    """Cubic B-spline KAN linear layer.
    
    Replaces standard linear weights with learnable 1D B-spline curves on edges.
    Matches paper §3.4 KAN nonlinear mapping.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        grid_size: int = 5,
        spline_order: int = 3,
        scale_base: float = 1.0,
        scale_spline: float = 1.0,
        grid_range: tuple[float, float] = (-3.0, 3.0),
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.grid_size = grid_size
        self.spline_order = spline_order
        self.scale_base = scale_base
        self.scale_spline = scale_spline
        
        # Number of spline control points/coefficients per edge
        self.num_coefs = grid_size + spline_order

        # 1. Base weights: standard linear layer representation
        self.base_weight = nn.Parameter(torch.randn(out_features, in_features))
        
        # 2. Spline weights/coefficients: (out_features, in_features, num_coefs)
        self.spline_weight = nn.Parameter(torch.randn(out_features, in_features, self.num_coefs))

        # 3. Bias term
        if bias:
            self.bias = nn.Parameter(torch.zeros(out_features))
        else:
            self.register_parameter("bias", None)

        # 4. Initialize grid of knots
        # Uniform grid in [grid_range[0], grid_range[1]] extended by spline_order on both sides
        h = (grid_range[1] - grid_range[0]) / grid_size
        grid = torch.linspace(
            grid_range[0] - spline_order * h,
            grid_range[1] + spline_order * h,
            grid_size + 2 * spline_order + 1,
            dtype=torch.float32,
        )
        # Register grid as a buffer (shape: in_features, grid_size + 2 * spline_order + 1)
        self.register_buffer("grid", grid.unsqueeze(0).repeat(in_features, 1))

        self.reset_parameters()

    def reset_parameters(self) -> None:
        """Initialize weights using Kaiming scaling to prevent gradient explosion/vanishing."""
        # Base weight initialization
        nn.init.kaiming_uniform_(self.base_weight, a=math.sqrt(5) if hasattr(math, "sqrt") else 2.236)
        with torch.no_grad():
            self.base_weight.mul_(self.scale_base)
            
            # Spline weight initialization
            # Standard initialization scales coefficients to be small
            nn.init.normal_(self.spline_weight, mean=0.0, std=self.scale_spline / (self.in_features * self.num_coefs))

    def evaluate_bsplines(self, x: torch.Tensor) -> torch.Tensor:
        """Evaluate input on the B-spline basis using Cox-de Boor recursion.
        
        Args:
            x: (B, in_features)
            
        Returns:
            bases: (B, in_features, num_coefs)
        """
        # x shape: (B, in_features) -> (B, in_features, 1)
        x_unsqueezed = x.unsqueeze(-1)
        # grid shape: (in_features, G + 2 * k + 1) -> (1, in_features, G + 2 * k + 1)
        grid = self.grid.unsqueeze(0)
        
        # Base case p=0 (Indicator functions over intervals)
        bases = ((x_unsqueezed >= grid[..., :-1]) & (x_unsqueezed < grid[..., 1:])).to(x.dtype)
        
        # Cox-de Boor recursion for p=1..spline_order
        for p in range(1, self.spline_order + 1):
            t_i = grid[..., :-p-1]
            t_ip = grid[..., p:-1]
            t_i1 = grid[..., 1:-p]
            t_ip1 = grid[..., p+1:]
            
            denom1 = t_ip - t_i
            denom2 = t_ip1 - t_i1
            
            # Avoid division by zero
            denom1 = torch.where(denom1 == 0, 1.0, denom1)
            denom2 = torch.where(denom2 == 0, 1.0, denom2)
            
            w1 = (x_unsqueezed - t_i) / denom1
            w2 = (t_ip1 - x_unsqueezed) / denom2
            
            bases = w1 * bases[..., :-1] + w2 * bases[..., 1:]
            
        return bases

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the B-spline KAN layer.
        
        Args:
            x: input tensor of shape (B, in_features)
            
        Returns:
            output tensor of shape (B, out_features)
        """
        # [1] Base linear mapping (w_b * x)
        base_output = F.linear(x, self.base_weight)  # (B, out_features)

        # [2] Spline mapping (w_s * spline_basis(x))
        # splines shape: (B, in_features, num_coefs)
        splines = self.evaluate_bsplines(x)
        
        # contract along the input and coefficient dimensions to get (B, out_features)
        spline_output = torch.einsum("bik,oik->bo", splines, self.spline_weight)

        # [3] Final output compilation
        output = base_output + spline_output
        if self.bias is not None:
            output = output + self.bias
            
        return output

    def extra_repr(self) -> str:
        return f"in_features={self.in_features}, out_features={self.out_features}, grid_size={self.grid_size}"

"""Chebyshev Polynomial KAN (ChebyKAN) Neural Network implementation.

Replaces B-spline basis functions with Chebyshev polynomials of the first kind.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class ChebyshevKANLinear(nn.Module):
    """Linear KAN layer using Chebyshev polynomials of the first kind as basis functions.
    
    Evaluates recursively: T_0(x) = 1, T_1(x) = x, T_n(x) = 2x * T_{n-1}(x) - T_{n-2}(x)
    """

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
        # Base weights for parallel linear mapping: (out_features, in_features)
        self.base_weight = nn.Parameter(torch.empty(out_features, in_features))
        
        if bias:
            self.bias = nn.Parameter(torch.empty(out_features))
        else:
            self.register_parameter("bias", None)

        self.reset_parameters()

    def reset_parameters(self) -> None:
        # Initialize base weight using standard Kaiming initialization
        nn.init.kaiming_uniform_(self.base_weight, a=math.sqrt(5))
        
        # Initialize Chebyshev weights with standard normal scaled by feature dimensions
        nn.init.normal_(self.cheby_weight, mean=0.0, std=1.0 / (self.in_features * (self.degree + 1)))
        
        if self.bias is not None:
            # Standard uniform bias initialization
            bound = 1 / math.sqrt(self.in_features) if self.in_features > 0 else 0
            nn.init.uniform_(self.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Normalize input to [-1, 1] via tanh to ensure numerical stability of Chebyshev polynomials
        x_norm = torch.tanh(x)

        # Compute Chebyshev polynomials recursively
        # T_0(x) = 1
        # T_1(x) = x
        # T_k(x) = 2x * T_{k-1}(x) - T_{k-2}(x)
        cheby_basis = [torch.ones_like(x_norm)]
        if self.degree >= 1:
            cheby_basis.append(x_norm)
            
        for k in range(2, self.degree + 1):
            cheby_basis.append(2.0 * x_norm * cheby_basis[-1] - cheby_basis[-2])
            
        # Shape: (batch_size, in_features, degree + 1)
        cheby_basis = torch.stack(cheby_basis, dim=-1)

        # Compute base projection: (batch_size, out_features)
        base_out = F.linear(x_norm, self.base_weight)

        # Compute Chebyshev projection via Einstein summation contract
        cheby_out = torch.einsum("bid,oid->bo", cheby_basis, self.cheby_weight)

        out = base_out + cheby_out
        if self.bias is not None:
            out = out + self.bias
        return out


class ChebyshevKAN(nn.Module):
    """Pure Chebyshev KAN Neural Network replacing the MamKANformer trunk."""

    def __init__(
        self,
        dataset: str,
        n_classes: int,
        hidden_dim: int,
        num_layers: int,
        degree: int = 4,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.dataset = dataset
        self.n_classes = n_classes
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.degree = degree

        layers = []
        # Input layer: 46 features mapped to hidden_dim
        layers.append(ChebyshevKANLinear(46, hidden_dim, degree=degree))
        layers.append(nn.LayerNorm(hidden_dim))
        layers.append(nn.Dropout(dropout))

        # Stacking hidden layers
        for _ in range(num_layers - 1):
            layers.append(ChebyshevKANLinear(hidden_dim, hidden_dim, degree=degree))
            layers.append(nn.LayerNorm(hidden_dim))
            layers.append(nn.Dropout(dropout))

        # Output layer mapping hidden_dim to classes
        layers.append(ChebyshevKANLinear(hidden_dim, n_classes, degree=degree))

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input shape: (B, 46)
        return self.network(x)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

"""Mamba SSM (Selective State Space Model) sub-layer implemented in pure PyTorch.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class MambaSublayer(nn.Module):
    """Mamba SSM Block (Selective State Space Model).
    
    Accepts input shape (B, T, D) and returns (B, T, D).
    Matches paper §3.4 temporal dependency modeling using selective scan.
    """

    def __init__(
        self,
        d_model: int,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        self.d_conv = d_conv
        self.expand = expand
        self.d_inner = int(self.expand * self.d_model)

        # Input projections
        self.in_proj = nn.Linear(self.d_model, self.d_inner * 2, bias=False)

        # Causal 1D Convolution along the temporal/sequence dimension
        self.conv1d = nn.Conv1d(
            in_channels=self.d_inner,
            out_channels=self.d_inner,
            kernel_size=d_conv,
            bias=True,
            padding=d_conv - 1,
            groups=self.d_inner,
        )

        # Selective Parameter Projections (B, C, Delta)
        self.x_proj = nn.Linear(self.d_inner, self.d_state * 2 + self.d_inner, bias=False)
        
        # Delta parameter projection (Softplus bias init)
        self.dt_proj = nn.Linear(self.d_inner, self.d_inner, bias=True)
        
        # Initialize dt_proj bias to softplus(dt_bias) around 0.1
        dt_init_std = 0.08
        dt_init_value = 0.1
        # Inverse softplus: log(exp(0.1) - 1)
        dt_bias_init = math.log(math.exp(dt_init_value) - 1.0)
        nn.init.constant_(self.dt_proj.bias, dt_bias_init)

        # SSM S4D matrix A: learnable parameter (d_inner, d_state)
        # S4D initialization: A = -log(arange(1, d_state+1))
        # Keep A negative for stability: exp(A) < 1
        A_init = torch.arange(1, self.d_state + 1, dtype=torch.float32).repeat(self.d_inner, 1)
        self.A_log = nn.Parameter(torch.log(A_init))

        # SSM parameter D (skip connection/feedforward term)
        self.D = nn.Parameter(torch.ones(self.d_inner))

        # Output projection
        self.out_proj = nn.Linear(self.d_inner, self.d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the Mamba SSM block.
        
        Args:
            x: input tensor of shape (B, T, D)
            
        Returns:
            output tensor of shape (B, T, D)
        """
        # B: batch size, T: sequence length, D: feature dimension
        B, T, D = x.shape
        
        # [1] Input projection -> split into branches
        # (B, T, 2 * d_inner)
        xz = self.in_proj(x)
        x_branch, z_branch = xz.chunk(2, dim=-1)

        # [2] Apply 1D Convolution over sequence dimension
        # Conv1d expects (B, C, T)
        x_conv = x_branch.transpose(1, 2)  # (B, d_inner, T)
        # Pad left to maintain causality
        x_conv = self.conv1d(x_conv)[:, :, :T]  # (B, d_inner, T)
        x_conv = x_conv.transpose(1, 2)  # (B, T, d_inner)
        
        # Apply SiLU activation
        x_active = F.silu(x_conv)  # (B, T, d_inner)

        # [3] Parameter projections for Selective Scan
        # Projects to: Delta (B, T, d_inner), B (B, T, d_state), C (B, T, d_state)
        x_params = self.x_proj(x_active)  # (B, T, d_inner + 2 * d_state)
        dt, B_s, C_s = torch.split(x_params, [self.d_inner, self.d_state, self.d_state], dim=-1)

        # Discretize dt via dt_proj and softplus
        dt = F.softplus(self.dt_proj(dt))  # (B, T, d_inner)

        # Retrieve matrix A (strictly negative)
        A = -torch.exp(self.A_log)  # (d_inner, d_state)

        # [4] Selective Scan Recurrence (Discretization & Scan)
        # h_t = A_d * h_{t-1} + B_d * x_t
        # A_d = exp(dt_t * A)
        # B_d = dt_t * B_t
        # y_t = C_t * h_t + D * x_t
        h = torch.zeros(B, self.d_inner, self.d_state, device=x.device)
        ys = []

        for t in range(T):
            dt_t = dt[:, t, :].unsqueeze(-1)  # (B, d_inner, 1)
            x_t = x_active[:, t, :].unsqueeze(-1)  # (B, d_inner, 1)
            B_t = B_s[:, t, :].unsqueeze(1)  # (B, 1, d_state)
            C_t = C_s[:, t, :].unsqueeze(-1)  # (B, d_state, 1)

            # Discretize A and B
            # A: (d_inner, d_state) -> broadcast with dt_t -> (B, d_inner, d_state)
            A_d = torch.exp(dt_t * A.unsqueeze(0))
            # B_d = dt_t * B_t -> (B, d_inner, d_state)
            B_d = dt_t * B_t

            # Update state h_t: (B, d_inner, d_state)
            h = A_d * h + B_d * x_t

            # Compute selective scan output y_t: (B, d_inner)
            y_t = torch.matmul(h, C_t).squeeze(-1)  # (B, d_inner)
            ys.append(y_t)

        y = torch.stack(ys, dim=1)  # (B, T, d_inner)

        # [5] Skip connection with D parameter
        y = y + x_active * self.D.unsqueeze(0).unsqueeze(0)

        # [6] Multiplicative Gating with z branch
        z_gate = F.silu(z_branch)
        y_gated = y * z_gate

        # [7] Project back to d_model
        out = self.out_proj(y_gated)  # (B, T, D)
        return out

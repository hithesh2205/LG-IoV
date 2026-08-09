"""1D KAN-flavoured convolution for the KANConvNet backbone.

A conventional 1D conv does:   y[c_out, t] = b + Σ_{c_in, k} W[c_out, c_in, k] · x[c_in, t+k]

A KAN-style conv replaces the per-edge linear weight ``W[c_out, c_in, k]``
with a learnable nonlinear activation φ on each edge. Following the paper
we realise φ with a Fourier basis (same parameterisation as
``FourierKANLinear``):

    φ_{c_out, c_in, k}(x) = Σ_{m=1..M} [ a · sin(m x) + b · cos(m x) ]

so the layer keeps the spatial-locality / weight-sharing of a conv but
gains learnable per-edge nonlinearities. Implementation uses ``F.unfold``
to lay the receptive field out as a flat vector, then reuses a single
``FourierKANLinear`` mapping (in_channels · kernel_size) -> out_channels.
This keeps memory / FLOPs O(in*out*K*M*T) — practical for the CAN-bus
windows (T <= 64) the paper targets.
"""
from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from .kan_layers import FourierKANLinear


class KANConv1d(nn.Module):
    """KAN-style 1-D convolution.

    Args:
        in_channels:  C_in
        out_channels: C_out
        kernel_size:  receptive-field length (odd → "same" padding).
        stride:       temporal stride.
        n_modes:      Fourier modes per edge (passed to FourierKANLinear).
        padding:      either an int or ``"same"`` (default).
        bias:         whether to learn a bias on each output channel.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        stride: int = 1,
        n_modes: int = 8,
        padding: "int | str" = "same",
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride
        if padding == "same":
            if stride != 1:
                raise ValueError("padding='same' requires stride=1")
            padding = kernel_size // 2
        self.padding = int(padding)

        # Single KAN-linear shared across all temporal positions —
        # this is what gives the layer its weight-sharing convolutional
        # behaviour. Input dim = C_in * K, output dim = C_out.
        self.kan = FourierKANLinear(
            in_features=in_channels * kernel_size,
            out_features=out_channels,
            n_modes=n_modes,
            bias=bias,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Args: x (B, C_in, T). Returns (B, C_out, T_out)."""
        if x.dim() != 3:
            raise ValueError(f"KANConv1d expects (B, C, T); got {tuple(x.shape)}")
        b, c, t = x.shape
        if c != self.in_channels:
            raise ValueError(f"expected C_in={self.in_channels}; got {c}")

        # F.unfold expects 4-D input, so add a trailing W=1.
        # Resulting cols: (B, C_in*K, T_out).
        x4 = x.unsqueeze(-1)
        cols = F.unfold(
            x4,
            kernel_size=(self.kernel_size, 1),
            stride=(self.stride, 1),
            padding=(self.padding, 0),
        )                                                # (B, C_in*K, T_out)
        t_out = cols.size(-1)
        # Move time to batch so we can hit the shared KAN linear once.
        cols = cols.transpose(1, 2).reshape(b * t_out, -1)  # (B*T_out, C_in*K)
        out = self.kan(cols)                                # (B*T_out, C_out)
        out = out.view(b, t_out, self.out_channels).transpose(1, 2).contiguous()
        return out  # (B, C_out, T_out)

    def extra_repr(self) -> str:
        return (f"in_channels={self.in_channels}, out_channels={self.out_channels},"
                f" kernel_size={self.kernel_size}, stride={self.stride},"
                f" padding={self.padding}")

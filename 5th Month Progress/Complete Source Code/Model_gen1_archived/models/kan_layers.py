"""Core Kolmogorov–Arnold building blocks for KANConvNet.

Two pieces correspond directly to paper §3.4 (Heidari et al., FedIoV 2026):

* ``FourierKANLinear``  — implements
      z1 = W1 · F(z0) + b1        (eq. 16)
  i.e. a per-edge Fourier basis (the "Fourier-based encoding" the paper
  mentions) summed to produce each output unit. This is the KAN
  reformulation that puts learnable nonlinear activations on edges
  instead of nodes.

* ``KolmogorovActivation`` — implements σ_Kolmogorov (eqs. 17, 18) as a
  smooth gated composition of tanh and SiLU with per-channel learnable
  parameters. It stays interpretable (Kolmogorov–Arnold representation
  theorem: any continuous multivariate function is a composition of
  continuous univariate functions plus addition), differentiable, and
  cheap enough for in-vehicle inference.

Both layers are batched (B, *).
"""
from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class FourierKANLinear(nn.Module):
    """KAN linear layer with a Fourier basis on every (in, out) edge.

    For each input scalar x_i and output unit j, the edge activation is
        phi_{ij}(x) = sum_{k=1}^{K} [ a_{ijk} sin(k x) + b_{ijk} cos(k x) ]
    and the output is
        y_j = bias_j + sum_i phi_{ij}(x_i).

    This is the "linear transformation coupled with a Fourier-based
    encoding" used to realise eq. (16) of the FedIoV paper.

    The implementation is fully vectorised (no Python loops over i or j)
    and uses ``einsum`` so it stays fast under autograd.

    Args:
        in_features:  size of the input feature dimension.
        out_features: size of the output feature dimension.
        n_modes:      K, number of Fourier basis pairs per edge.
        scale:        std of the Gaussian init for the Fourier coefficients.
        bias:         whether to learn an additive output bias.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        n_modes: int = 8,
        scale: float = 0.1,
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.n_modes = n_modes

        # Frequencies 1..K (registered as buffer so they move with .to()).
        freqs = torch.arange(1, n_modes + 1, dtype=torch.float32)
        self.register_buffer("freqs", freqs)

        # Fourier coefficients: (out, in, K) for sine and cosine.
        self.coeff_sin = nn.Parameter(
            torch.randn(out_features, in_features, n_modes) * scale / math.sqrt(n_modes)
        )
        self.coeff_cos = nn.Parameter(
            torch.randn(out_features, in_features, n_modes) * scale / math.sqrt(n_modes)
        )

        if bias:
            self.bias = nn.Parameter(torch.zeros(out_features))
        else:
            self.register_parameter("bias", None)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Args:  x of shape (B, in_features). Returns (B, out_features)."""
        if x.dim() != 2 or x.size(-1) != self.in_features:
            raise ValueError(
                f"FourierKANLinear expects (B, {self.in_features}); got {tuple(x.shape)}"
            )
        # (B, in, K) — broadcast x_i against each frequency.
        phase = x.unsqueeze(-1) * self.freqs  # (B, in, K)
        sin_t = torch.sin(phase)
        cos_t = torch.cos(phase)
        # Edge activations summed over in and over K -> (B, out)
        out = torch.einsum("bik,oik->bo", sin_t, self.coeff_sin) + \
              torch.einsum("bik,oik->bo", cos_t, self.coeff_cos)
        if self.bias is not None:
            out = out + self.bias
        return out

    def extra_repr(self) -> str:
        return (f"in_features={self.in_features}, out_features={self.out_features},"
                f" n_modes={self.n_modes}")


class KolmogorovActivation(nn.Module):
    """Per-channel, learnable Kolmogorov-inspired nonlinearity.

    σ_K(x) = α · tanh(β · x) + γ · SiLU(δ · x) + ε

    Each parameter is a length-``num_features`` vector so different
    channels can specialise. With α=1, β=1, γ=0, ε=0 it collapses to plain
    tanh, so initialisation starts in a well-behaved regime.

    Operates on either (B, C) or (B, C, T) tensors — the broadcast handles
    both via ``reshape``.
    """

    def __init__(self, num_features: int) -> None:
        super().__init__()
        self.num_features = num_features
        self.alpha = nn.Parameter(torch.ones(num_features))
        self.beta = nn.Parameter(torch.ones(num_features))
        self.gamma = nn.Parameter(torch.zeros(num_features))
        self.delta = nn.Parameter(torch.ones(num_features))
        self.bias = nn.Parameter(torch.zeros(num_features))

    def _broadcast(self, p: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        # x is either (B, C) or (B, C, T). Reshape p to broadcast over T.
        if x.dim() == 2:
            return p.view(1, -1)
        if x.dim() == 3:
            return p.view(1, -1, 1)
        raise ValueError(
            f"KolmogorovActivation supports rank-2 or rank-3 inputs; got {x.dim()}"
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.size(1) != self.num_features:
            raise ValueError(
                f"KolmogorovActivation expects C={self.num_features}; got {x.size(1)}"
            )
        a = self._broadcast(self.alpha, x)
        b = self._broadcast(self.beta, x)
        g = self._broadcast(self.gamma, x)
        d = self._broadcast(self.delta, x)
        e = self._broadcast(self.bias, x)
        return a * torch.tanh(b * x) + g * F.silu(d * x) + e

    def extra_repr(self) -> str:
        return f"num_features={self.num_features}"

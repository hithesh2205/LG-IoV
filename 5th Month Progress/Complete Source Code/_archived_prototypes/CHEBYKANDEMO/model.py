"""
model.py — Pure Chebyshev KAN (Kolmogorov-Arnold Network) for IoV Intrusion Detection.

Architecture
============
ChebyKANLayer:
    Learnable Chebyshev polynomial expansions on every edge, plus a base
    linear transform and bias.  Forward path:
        1. tanh normalisation → [-1, 1]
        2. Chebyshev recurrence T_0 … T_{degree-1}
        3. einsum contraction with chebyshev_weights
        4. base linear + bias

ChebyKAN:
    Three stacked ChebyKANLayers (46→64→64→n_classes) with LayerNorm and
    Dropout between the hidden layers.

All feature vectors are **exactly 46 dimensions**.  An assertion fires if
the default configuration does not yield 44 164 trainable parameters.
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_INPUT_DIM: int = 46
_EXPECTED_PARAMS_DEFAULT: int = 44_164


# ═══════════════════════════════════════════════════════════════════════════
# ChebyKANLayer
# ═══════════════════════════════════════════════════════════════════════════
class ChebyKANLayer(nn.Module):
    """Single Chebyshev-KAN layer.

    For every (input, output) edge the layer maintains a learnable weight
    vector of length ``degree`` that is contracted with the Chebyshev
    polynomial expansion of the (tanh-normalised) input.  A conventional
    linear (base) weight and bias are added on top.

    Parameters
    ----------
    in_features : int
        Number of input features.
    out_features : int
        Number of output features.
    degree : int, default 5
        Number of Chebyshev polynomials (T_0 … T_{degree-1}).
    """

    def __init__(self, in_features: int, out_features: int, degree: int = 5) -> None:
        super().__init__()
        logger.debug(
            "ChebyKANLayer.__init__: in=%d, out=%d, degree=%d",
            in_features,
            out_features,
            degree,
        )

        self.in_features: int = in_features
        self.out_features: int = out_features
        self.degree: int = degree

        # --- learnable parameters -------------------------------------------
        self.chebyshev_weights: nn.Parameter = nn.Parameter(
            torch.empty(out_features, in_features, degree)
        )
        self.base_weight: nn.Parameter = nn.Parameter(
            torch.empty(out_features, in_features)
        )
        self.bias: nn.Parameter = nn.Parameter(torch.zeros(out_features))

        # --- initialisation --------------------------------------------------
        nn.init.kaiming_uniform_(self.chebyshev_weights, a=math.sqrt(5))
        nn.init.xavier_uniform_(self.base_weight)
        # bias is already zero-initialised

        logger.debug(
            "ChebyKANLayer params — cheby: %s, base: %s, bias: %s",
            list(self.chebyshev_weights.shape),
            list(self.base_weight.shape),
            list(self.bias.shape),
        )

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(batch, in_features)``.

        Returns
        -------
        torch.Tensor
            Shape ``(batch, out_features)``.
        """
        assert x.ndim == 2, f"Expected 2-D input (batch, features), got shape {x.shape}"
        assert x.size(1) == self.in_features, (
            f"Feature dim mismatch: expected {self.in_features}, got {x.size(1)}"
        )

        # 1. Normalise to [-1, 1] via tanh ------------------------------------
        x_norm: torch.Tensor = torch.tanh(x)  # (batch, in_features)

        # 2. Chebyshev recurrence T_0 … T_{degree-1} -------------------------
        cheby_polys: List[torch.Tensor] = []

        if self.degree >= 1:
            t0: torch.Tensor = torch.ones_like(x_norm)  # T_0 = 1
            cheby_polys.append(t0)

        if self.degree >= 2:
            t1: torch.Tensor = x_norm  # T_1 = x
            cheby_polys.append(t1)

        for n in range(2, self.degree):
            t_next: torch.Tensor = 2.0 * x_norm * cheby_polys[n - 1] - cheby_polys[n - 2]
            cheby_polys.append(t_next)

        # 3. Stack → (batch, in_features, degree) -----------------------------
        cheby_stack: torch.Tensor = torch.stack(cheby_polys, dim=-1)  # (B, I, D)
        assert cheby_stack.shape == (x.size(0), self.in_features, self.degree), (
            f"Chebyshev stack shape mismatch: {cheby_stack.shape}"
        )

        # 4. Contract with chebyshev_weights via einsum -----------------------
        #    cheby_stack : (B, I, D)
        #    chebyshev_weights : (O, I, D)
        #    result : (B, O)
        cheby_out: torch.Tensor = torch.einsum(
            "bid,oid->bo", cheby_stack, self.chebyshev_weights
        )

        # 5. Base linear transform --------------------------------------------
        base_out: torch.Tensor = F.linear(x_norm, self.base_weight)  # (B, O)

        # 6. Add bias ---------------------------------------------------------
        output: torch.Tensor = cheby_out + base_out + self.bias

        return output

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def param_counts(self) -> Tuple[int, int, int, int]:
        """Return (cheby_count, base_count, bias_count, total)."""
        cheby_count: int = self.out_features * self.in_features * self.degree
        base_count: int = self.out_features * self.in_features
        bias_count: int = self.out_features
        total: int = cheby_count + base_count + bias_count
        return cheby_count, base_count, bias_count, total

    def extra_repr(self) -> str:
        """Pretty-print for ``print(model)``."""
        return (
            f"in_features={self.in_features}, out_features={self.out_features}, "
            f"degree={self.degree}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# ChebyKAN (full model)
# ═══════════════════════════════════════════════════════════════════════════
class ChebyKAN(nn.Module):
    """Three-layer Chebyshev-KAN classifier for IoV intrusion detection.

    Default topology (4-class, 46-feature CAN-VTC):
        input_norm → layer1(46→64) → norm1 → drop1
                   → layer2(64→64) → norm2 → drop2
                   → output(64→4)

    Parameters
    ----------
    in_features : int, default 46
        Input feature dimension (must be 46 for CAN-VTC).
    hidden_dim : int, default 64
        Width of both hidden layers.
    n_classes : int, default 4
        Number of output classes.
    degree : int, default 5
        Chebyshev polynomial degree for every ChebyKANLayer.
    dropout : float, default 0.2
        Dropout probability between hidden layers.
    """

    def __init__(
        self,
        in_features: int = _INPUT_DIM,
        hidden_dim: int = 64,
        n_classes: int = 4,
        degree: int = 5,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        logger.info(
            "ChebyKAN.__init__: in=%d, hidden=%d, classes=%d, degree=%d, dropout=%.2f",
            in_features,
            hidden_dim,
            n_classes,
            degree,
            dropout,
        )

        assert in_features == _INPUT_DIM, (
            f"All feature vectors must be exactly {_INPUT_DIM} dimensions, "
            f"got in_features={in_features}"
        )

        self.in_features: int = in_features
        self.hidden_dim: int = hidden_dim
        self.n_classes: int = n_classes
        self.degree: int = degree

        # --- Defensive input normalisation (redundant with preprocessing) ----
        # Implemented as a tanh activation applied at the very start.
        # Stored as an attribute so the intent is explicit in `print(model)`.
        self.input_norm: nn.Tanh = nn.Tanh()

        # --- ChebyKAN layers -------------------------------------------------
        self.layer1: ChebyKANLayer = ChebyKANLayer(in_features, hidden_dim, degree)
        self.norm1: nn.LayerNorm = nn.LayerNorm(hidden_dim)
        self.drop1: nn.Dropout = nn.Dropout(dropout)

        self.layer2: ChebyKANLayer = ChebyKANLayer(hidden_dim, hidden_dim, degree)
        self.norm2: nn.LayerNorm = nn.LayerNorm(hidden_dim)
        self.drop2: nn.Dropout = nn.Dropout(dropout)

        self.output: ChebyKANLayer = ChebyKANLayer(hidden_dim, n_classes, degree)

        # --- Parameter-count verification & pretty-print ---------------------
        total_params: int = self._print_param_table()

        if (
            n_classes == 4
            and in_features == _INPUT_DIM
            and hidden_dim == 64
            and degree == 5
        ):
            assert total_params == _EXPECTED_PARAMS_DEFAULT, (
                f"Parameter count mismatch: expected {_EXPECTED_PARAMS_DEFAULT}, "
                f"got {total_params}"
            )

        logger.info("ChebyKAN initialised — %d trainable parameters", total_params)

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the full ChebyKAN.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(batch, 46)``.

        Returns
        -------
        torch.Tensor
            Raw logits of shape ``(batch, n_classes)``.
        """
        assert x.ndim == 2, f"Expected 2-D input, got shape {x.shape}"
        assert x.size(1) == self.in_features, (
            f"Feature dim must be {self.in_features}, got {x.size(1)}"
        )

        # Defensive normalisation — values should already be in [-1, 1] from
        # preprocessing, but tanh is a no-op on well-scaled data.
        h: torch.Tensor = self.input_norm(x)

        h = self.layer1(h)
        h = self.norm1(h)
        h = self.drop1(h)

        h = self.layer2(h)
        h = self.norm2(h)
        h = self.drop2(h)

        logits: torch.Tensor = self.output(h)
        return logits

    # ------------------------------------------------------------------
    # State-dict loading with strict=False support
    # ------------------------------------------------------------------
    def load_state_dict_flexible(
        self,
        state_dict: dict,
        strict: bool = False,
    ) -> torch.nn.modules.module._IncompatibleKeys:
        """Load a state dict with ``strict=False`` by default.

        This is intentional: when bootstrapping a pre-trained model onto a
        dataset with a **different number of classes**, the ``output`` layer
        weights will have a shape mismatch.  Using ``strict=False`` silently
        skips those keys, allowing the rest of the model to benefit from
        transfer learning while the output layer trains from scratch.

        Parameters
        ----------
        state_dict : dict
            The state dictionary to load.
        strict : bool, default False
            If ``False``, mismatched / missing keys are tolerated.

        Returns
        -------
        torch.nn.modules.module._IncompatibleKeys
            Named tuple with ``missing_keys`` and ``unexpected_keys``.
        """
        logger.info(
            "load_state_dict_flexible called with strict=%s (%d keys in state_dict)",
            strict,
            len(state_dict),
        )
        result = super().load_state_dict(state_dict, strict=strict)
        if result.missing_keys:
            logger.warning("Missing keys: %s", result.missing_keys)
        if result.unexpected_keys:
            logger.warning("Unexpected keys: %s", result.unexpected_keys)
        return result

    # ------------------------------------------------------------------
    # Parameter table (rich)
    # ------------------------------------------------------------------
    def _print_param_table(self) -> int:
        """Build and print a rich table summarising per-layer parameter counts.

        Returns
        -------
        int
            Total number of trainable parameters.
        """
        console: Console = Console()
        table: Table = Table(
            title="ChebyKAN Parameter Breakdown",
            show_lines=True,
        )
        table.add_column("Layer", style="bold cyan", min_width=14)
        table.add_column("Cheby W", justify="right", min_width=10)
        table.add_column("Base W", justify="right", min_width=10)
        table.add_column("Bias", justify="right", min_width=6)
        table.add_column("Total", justify="right", style="bold green", min_width=8)

        running_total: int = 0

        # Helper for ChebyKANLayer rows
        kan_layers: List[Tuple[str, ChebyKANLayer]] = [
            ("layer1", self.layer1),
            ("layer2", self.layer2),
            ("output", self.output),
        ]
        for name, layer in kan_layers:
            cheby_c, base_c, bias_c, subtotal = layer.param_counts()
            table.add_row(
                name,
                f"{cheby_c:,}",
                f"{base_c:,}",
                f"{bias_c:,}",
                f"{subtotal:,}",
            )
            running_total += subtotal

        # LayerNorm rows (weight + bias = 2 * normalised_shape)
        norm_layers: List[Tuple[str, nn.LayerNorm]] = [
            ("norm1", self.norm1),
            ("norm2", self.norm2),
        ]
        for name, norm in norm_layers:
            norm_params: int = sum(p.numel() for p in norm.parameters())
            table.add_row(name, "—", "—", "—", f"{norm_params:,}")
            running_total += norm_params

        # Footer
        table.add_section()
        table.add_row("TOTAL", "", "", "", f"{running_total:,}")

        console.print(table)
        return running_total

    def extra_repr(self) -> str:
        """Pretty-print for ``print(model)``."""
        return (
            f"in_features={self.in_features}, hidden_dim={self.hidden_dim}, "
            f"n_classes={self.n_classes}, degree={self.degree}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Quick self-test
# ═══════════════════════════════════════════════════════════════════════════
def _self_test() -> None:
    """Run a minimal smoke test to verify shapes and parameter counts."""
    logger.info("Running ChebyKAN self-test …")

    model: ChebyKAN = ChebyKAN(
        in_features=46,
        hidden_dim=64,
        n_classes=4,
        degree=5,
        dropout=0.2,
    )

    batch_size: int = 8
    x: torch.Tensor = torch.randn(batch_size, 46)

    # Ensure input values are in plausible range after scaling
    x = torch.clamp(x, -1.0, 1.0)

    logits: torch.Tensor = model(x)
    assert logits.shape == (batch_size, 4), (
        f"Output shape mismatch: expected ({batch_size}, 4), got {logits.shape}"
    )

    # Verify total parameter count via PyTorch's own accounting
    pytorch_total: int = sum(p.numel() for p in model.parameters())
    assert pytorch_total == _EXPECTED_PARAMS_DEFAULT, (
        f"PyTorch param count {pytorch_total} ≠ expected {_EXPECTED_PARAMS_DEFAULT}"
    )

    # Test load_state_dict_flexible with strict=False
    state: dict = model.state_dict()
    model2: ChebyKAN = ChebyKAN(in_features=46, hidden_dim=64, n_classes=4, degree=5)
    result = model2.load_state_dict_flexible(state, strict=False)
    assert len(result.missing_keys) == 0, f"Unexpected missing keys: {result.missing_keys}"
    assert len(result.unexpected_keys) == 0, f"Unexpected extra keys: {result.unexpected_keys}"

    logger.info("✓ Self-test passed — output shape %s, params %d", logits.shape, pytorch_total)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
    _self_test()

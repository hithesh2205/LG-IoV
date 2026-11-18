"""Automated Tests for ChebyKAN Architecture, Forward Pass, and Gradient Updates."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn

TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.models.cheby_kan import ChebyshevKAN, ChebyshevKANLinear


def test_cheby_linear_layer() -> None:
    print("\n[test] ChebyshevKANLinear layer forward pass")
    layer = ChebyshevKANLinear(in_features=46, out_features=64, degree=4)
    x = torch.randn(8, 46)
    out = layer(x)
    assert out.shape == (8, 64), f"Expected shape (8, 64), got {out.shape}"
    assert torch.all(torch.isfinite(out)), "Output activations must be finite"
    print("  PASS  ChebyshevKANLinear produces finite outputs of correct dimension")


def test_full_chebykan_network() -> None:
    print("\n[test] Full ChebyshevKAN forward pass & parameter count")
    model = ChebyshevKAN(in_features=46, n_classes=5, hidden_dim=64, num_layers=2, degree=4, dropout=0.2)
    x = torch.randn(16, 46)
    logits = model(x)
    assert logits.shape == (16, 5), f"Expected shape (16, 5), got {logits.shape}"
    n_params = model.num_parameters()
    print(f"  PASS  ChebyshevKAN forward pass verified (Total parameters: {n_params:,})")


def test_gradient_step_and_flattening() -> None:
    print("\n[test] Gradient computation, parameter update, and flattening roundtrip")
    model = ChebyshevKAN(in_features=46, n_classes=5, hidden_dim=64, num_layers=2, degree=4)
    flat_orig = model.flatten_parameters()

    # Forward + Backward
    x = torch.randn(4, 46)
    y = torch.tensor([0, 1, 2, 3])
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)

    optimizer.zero_grad()
    loss = criterion(model(x), y)
    loss.backward()

    # Ensure all gradients are finite
    for name, p in model.named_parameters():
        if p.requires_grad:
            assert p.grad is not None, f"Gradient missing for {name}"
            assert torch.all(torch.isfinite(p.grad)), f"Infinite gradient in {name}"

    optimizer.step()
    flat_updated = model.flatten_parameters()

    # Verify parameters updated
    diff = np.max(np.abs(flat_updated - flat_orig))
    assert diff > 0.0, "Model parameters should change after optimizer step"
    print(f"  PASS  Gradients are finite and parameters updated (max parameter diff: {diff:.4e})")

    # Verify reloading
    model.load_flat_parameters(flat_orig)
    flat_reloaded = model.flatten_parameters()
    np.testing.assert_allclose(flat_orig, flat_reloaded, atol=1e-12)
    print("  PASS  Parameter flattening and reloading is bitwise lossless")


def main() -> None:
    test_cheby_linear_layer()
    test_full_chebykan_network()
    test_gradient_step_and_flattening()
    print("\nAll ChebyKAN model tests PASSED successfully!")


if __name__ == "__main__":
    main()

"""Automated Tests for the F Aggregation Function Mathematical Formulation."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.crypto.ckks_vector import PlaintextVector
from src.federated.rsu_server import RSUServer


def test_f_function_mathematical_truth() -> None:
    print("\n[test] F aggregation mathematical equivalence with ground truth")
    model_kwargs = {"in_features": 46, "n_classes": 5, "hidden_dim": 64, "num_layers": 2, "degree": 4}
    server = RSUServer(model_kwargs=model_kwargs, backend="none")
    dim = server.model.num_parameters()

    rng = np.random.default_rng(2025)
    # 4 clients with unequal sample counts
    sample_counts = [350, 1200, 2500, 5000]
    updates = [rng.normal(0, 0.05, size=dim) for _ in sample_counts]

    packages = [
        {"client_id": i, "update": PlaintextVector(up), "n_k": n}
        for i, (up, n) in enumerate(zip(updates, sample_counts))
    ]

    initial_w = server.broadcast_global_model()
    diag = server.aggregate_and_update(packages)
    updated_w = server.broadcast_global_model()

    # Analytical ground truth: sum(n_k * v_k) / sum(n_k)
    N_true = sum(sample_counts)
    expected_delta = np.sum([n * v for n, v in zip(sample_counts, updates)], axis=0) / N_true
    expected_w = initial_w + expected_delta

    assert diag["N"] == N_true, f"N mismatch: {diag['N']} vs {N_true}"
    np.testing.assert_allclose(updated_w, expected_w, atol=1e-12)
    print("  PASS  F function matches analytical sample-weighted average to machine precision")


def test_single_client_aggregation() -> None:
    print("\n[test] F function with a single client")
    model_kwargs = {"in_features": 46, "n_classes": 5, "hidden_dim": 64, "num_layers": 2, "degree": 4}
    server = RSUServer(model_kwargs=model_kwargs, backend="none")
    dim = server.model.num_parameters()

    single_update = np.ones(dim, dtype=np.float64) * 0.05
    n_k = 1500
    initial_w = server.broadcast_global_model()

    diag = server.aggregate_and_update([{"client_id": 0, "update": PlaintextVector(single_update), "n_k": n_k}])
    updated_w = server.broadcast_global_model()

    assert diag["N"] == n_k
    np.testing.assert_allclose(updated_w, initial_w + single_update, atol=1e-12)
    print("  PASS  Single client update correctly yields Delta w_1")


def test_zero_records_and_empty_handling() -> None:
    print("\n[test] Safe handling of N=0 and empty packages")
    model_kwargs = {"in_features": 46, "n_classes": 5, "hidden_dim": 64, "num_layers": 2, "degree": 4}
    server = RSUServer(model_kwargs=model_kwargs, backend="none")
    initial_w = server.broadcast_global_model()

    # Empty packages
    res_empty = server.aggregate_and_update([])
    assert res_empty["status"] == "skipped_empty"
    np.testing.assert_array_equal(server.broadcast_global_model(), initial_w)
    print("  PASS  Empty client packages safely preserves global model")

    # N = 0 packages
    res_zero = server.aggregate_and_update([{"client_id": 0, "update": PlaintextVector(np.zeros(10)), "n_k": 0}])
    assert res_zero["status"] == "skipped_zero_records"
    np.testing.assert_array_equal(server.broadcast_global_model(), initial_w)
    print("  PASS  N=0 client packages safely preserves global model")


def main() -> None:
    test_f_function_mathematical_truth()
    test_single_client_aggregation()
    test_zero_records_and_empty_handling()
    print("\nAll F aggregation function tests PASSED successfully!")


if __name__ == "__main__":
    main()

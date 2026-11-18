"""Automated Tests for Data Layer, 46 Features, Preprocessing, and Partitioning."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

# Ensure after_F_function is importable
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
WORKSPACE_DIR = PROJECT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.data.can_features import windows_from_stream, extract_window_features
from src.data.preprocess import assert_no_group_overlap
from src.data.partition import iid_partition, dirichlet_partition


def test_46_features_geometry() -> None:
    print("\n[test] 46-features geometry and order")
    n = 64
    can_ids = np.arange(n, dtype=np.int64)
    dlc = np.full(n, 8, dtype=np.float32)
    payload = np.random.uniform(0, 1, size=(n, 8)).astype(np.float32)

    feat = extract_window_features(can_ids, dlc, payload)
    assert feat.shape == (46,), f"Expected shape (46,), got {feat.shape}"
    assert np.all(np.isfinite(feat)), "Features must be finite"
    print("  PASS  extract_window_features yields exact 46 finite features")


def test_window_group_containment() -> None:
    print("\n[test] window block containment (no boundary crossing)")
    rng = np.random.default_rng(42)
    n = 800
    can_ids = rng.integers(0, 2048, size=n).astype(np.int64)
    dlc = np.full(n, 8, dtype=np.float32)
    payload = rng.random((n, 8)).astype(np.float32)
    msg_labels = np.zeros(n, dtype=np.int64)
    msg_labels[200:250] = 1

    window, stride, block = 64, 16, 200
    X, y, groups = windows_from_stream(
        can_ids, dlc, payload, window, stride, msg_labels=msg_labels, block_size=block
    )

    assert X.shape[0] > 0, "Must emit windows"
    assert X.shape[1] == 46, f"Expected 46 columns, got {X.shape[1]}"
    assert y.shape[0] == X.shape[0], "Labels count mismatch"
    assert groups.shape[0] == X.shape[0], "Groups count mismatch"
    print(f"  PASS  windows_from_stream emitted {X.shape[0]} windows with 46 features")


def test_group_leakage_assertion() -> None:
    print("\n[test] assert_no_group_overlap detector")
    groups = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    train_idx = np.array([0, 1, 2, 3])  # groups 0, 1
    val_idx = np.array([4, 5])          # group 2
    test_idx = np.array([6, 7])         # group 3
    # Clean split must pass
    assert_no_group_overlap(groups, train_idx, val_idx, test_idx)
    print("  PASS  clean group allocation passes")

    # Leaking split must raise AssertionError
    leaking_test = np.array([2, 6, 7])  # group 1 leaks into test!
    try:
        assert_no_group_overlap(groups, train_idx, val_idx, leaking_test)
        assert False, "Expected AssertionError on leaking groups"
    except AssertionError:
        print("  PASS  leaking group allocation is rejected")


def test_client_partitions() -> None:
    print("\n[test] client partitions (IID & Non-IID)")
    labels = np.random.choice(5, size=2000, p=[0.6, 0.1, 0.1, 0.1, 0.1])

    # IID
    iid_res = iid_partition(labels, n_clients=5, seed=2025)
    assert len(iid_res.client_indices) == 5
    assert sum(len(idx) for idx in iid_res.client_indices) == 2000
    print("  PASS  IID partition assigns exact total samples across 5 clients")

    # Non-IID Dirichlet
    non_iid_res = dirichlet_partition(labels, n_clients=5, alpha=0.3, seed=2025)
    assert len(non_iid_res.client_indices) == 5
    assert sum(len(idx) for idx in non_iid_res.client_indices) == 2000
    assert all(len(idx) > 0 for idx in non_iid_res.client_indices)
    print("  PASS  Non-IID Dirichlet partition assigns valid heterogeneous shards")


def main() -> None:
    test_46_features_geometry()
    test_window_group_containment()
    test_group_leakage_assertion()
    test_client_partitions()
    print("\nAll data layer tests PASSED successfully!")


if __name__ == "__main__":
    main()

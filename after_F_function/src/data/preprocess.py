"""Preprocessing pipeline for IoV IDS datasets.

Enforces:
1. Group-aware train/val/test splitting (70/15/15) without boundary crossing.
2. Quantile clipping (fitted on train only).
3. Z-score scaling (fitted on train only).
4. Class weight computation for dataset imbalance.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import numpy as np

from .car_hack import load_features_labels as load_car_hack


def assert_no_group_overlap(
    groups: np.ndarray,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
) -> None:
    """Fail loudly if any block id appears in more than one split."""
    g_train = set(np.unique(groups[train_idx]).tolist())
    g_val = set(np.unique(groups[val_idx]).tolist())
    g_test = set(np.unique(groups[test_idx]).tolist())

    for a_name, a, b_name, b in (
        ("train", g_train, "val", g_val),
        ("train", g_train, "test", g_test),
        ("val", g_val, "test", g_test),
    ):
        shared = a & b
        if shared:
            raise AssertionError(
                f"Group leakage detected: {len(shared)} block(s) appear in both "
                f"{a_name} and {b_name}."
            )


class PreprocessingPipeline:
    """Fits, transforms, and manages dataset preprocessing parameters."""

    def __init__(
        self,
        clip_low: float = 0.005,
        clip_high: float = 0.995,
        val_split: float = 0.15,
        test_split: float = 0.15,
        seed: int = 2025,
    ) -> None:
        self.clip_low = clip_low
        self.clip_high = clip_high
        self.val_split = val_split
        self.test_split = test_split
        self.seed = seed

        self.clip_min: Optional[np.ndarray] = None
        self.clip_max: Optional[np.ndarray] = None
        self.mean: Optional[np.ndarray] = None
        self.std: Optional[np.ndarray] = None
        self.class_weights: Optional[np.ndarray] = None
        self.classes: Optional[Tuple[str, ...]] = None

    def fit_transform(
        self,
        name: str,
        data_root: Path,
        window: int = 64,
        stride: int = 16,
        max_rows_per_class: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Load data, perform group-aware split, fit parameters on train, and scale."""
        if name == "car_hack":
            # Data directory: data_root / Car_hack_pro / Car_hack_pro
            car_dir = data_root / "Car_hack_pro" / "Car_hack_pro"
            if not car_dir.exists():
                car_dir = data_root / "Car_hack_pro"
            X, y, classes, groups = load_car_hack(car_dir, window, stride, max_rows_per_class)
        else:
            raise ValueError(f"Dataset {name} not supported in baseline experiment.")

        if X.shape[0] == 0:
            raise RuntimeError(f"No samples loaded for {name}")
        if X.shape[1] != 46:
            raise RuntimeError(f"Expected 46 features, got {X.shape[1]}")

        self.classes = classes

        # Group-aware split
        train_idx, val_idx, test_idx = self._grouped_split(y, groups)
        assert_no_group_overlap(groups, train_idx, val_idx, test_idx)

        # Quantile clipping fitted on train only
        self.clip_min = np.quantile(X[train_idx], self.clip_low, axis=0)
        self.clip_max = np.quantile(X[train_idx], self.clip_high, axis=0)
        X_clipped = np.clip(X, self.clip_min, self.clip_max)

        # Z-score scaling fitted on train only
        self.mean = X_clipped[train_idx].mean(axis=0)
        self.std = X_clipped[train_idx].std(axis=0) + 1e-6
        X_scaled = (X_clipped - self.mean) / self.std

        # Class weights for loss weighting
        cls_counts = np.bincount(y[train_idx], minlength=len(classes)).astype(np.float32)
        cls_counts_clipped = np.clip(cls_counts, 1.0, None)
        self.class_weights = cls_counts.sum() / (len(classes) * cls_counts_clipped)
        self.class_weights[cls_counts == 0] = 1.0

        return {
            "X_train": X_scaled[train_idx],
            "y_train": y[train_idx],
            "X_val": X_scaled[val_idx],
            "y_val": y[val_idx],
            "X_test": X_scaled[test_idx],
            "y_test": y[test_idx],
            "train_idx": train_idx,
            "val_idx": val_idx,
            "test_idx": test_idx,
            "classes": classes,
        }

    def _grouped_split(
        self, y: np.ndarray, groups: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.seed)
        unique_groups = np.unique(groups)

        dominant: Dict[int, int] = {}
        for g in unique_groups:
            labels_in_g = y[groups == g]
            counts = np.bincount(labels_in_g)
            dominant[int(g)] = int(counts.argmax())

        train_g: list = []
        val_g: list = []
        test_g: list = []

        for c in sorted(set(dominant.values())):
            gs = np.array([g for g in unique_groups if dominant[int(g)] == c])
            rng.shuffle(gs)
            n = len(gs)
            n_test = int(round(n * self.test_split))
            n_val = int(round(n * self.val_split))
            if n >= 3:
                n_test = max(1, n_test)
                n_val = max(1, n_val)
            test_g.extend(gs[:n_test].tolist())
            val_g.extend(gs[n_test:n_test + n_val].tolist())
            train_g.extend(gs[n_test + n_val:].tolist())

        train_set = set(train_g)
        val_set = set(val_g)
        test_set = set(test_g)

        idx = np.arange(len(groups))
        train_idx = idx[np.isin(groups, list(train_set))]
        val_idx = idx[np.isin(groups, list(val_set))]
        test_idx = idx[np.isin(groups, list(test_set))]

        rng.shuffle(train_idx)
        rng.shuffle(val_idx)
        rng.shuffle(test_idx)

        return train_idx, val_idx, test_idx

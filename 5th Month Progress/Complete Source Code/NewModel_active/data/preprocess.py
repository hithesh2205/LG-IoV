"""Preprocessing pipeline for FedIoV datasets.

Performs:
1. **Group-aware** train/val/test splitting (70/15/15).
2. Percentile clipping (fitted on train only).
3. Z-score scaling (fitted on train only).
4. Class weight computation for imbalance.
5. Saving of all preprocessing artifacts.

Splitting (revised Month 5 — defect D2)
---------------------------------------
The previous splitter shuffled *individual windows* and cut 70/15/15. Because
the CAN adapters emit windows with 75 % overlap (window 64, stride 16),
consecutive windows share 48 of their 64 messages — so a uniformly random split
placed near-duplicates on both sides of the train/test boundary and the reported
test accuracy measured memorisation, not generalisation.

Every adapter now returns a ``groups`` array of contiguous **block** ids, and no
window ever crosses a block boundary (enforced in ``can_features.windows_from_stream``).
This splitter assigns **whole blocks** to exactly one split, so two overlapping
windows are always on the same side. Stratification is preserved approximately
by bucketing blocks on their dominant class before allocating.

``assert_no_group_overlap`` verifies the invariant and is called on every split.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np

from .can_vtc_dataset import load_features_labels as load_can_vtc
from .car_hack_dataset import load_features_labels as load_car_hack
from .cicids_dataset import load_features_labels as load_cicids
from .veremi_dataset import load_features_labels as load_veremi

DATASETS = ("can_vtc", "car_hack", "cicids", "veremi")


def assert_no_group_overlap(
    groups: np.ndarray,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
) -> None:
    """Fail loudly if any block id appears in more than one split.

    This is the machine-checkable form of the D2 fix: if it holds, no pair of
    overlapping windows can straddle the train/test boundary.
    """
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
                f"Group leakage: {len(shared)} block(s) appear in both "
                f"{a_name} and {b_name} (e.g. {sorted(shared)[:5]}). "
                "Overlapping windows would span the split boundary."
            )


class PreprocessingPipeline:
    """Fits, transforms, and saves dataset preprocessing parameters."""

    def __init__(
        self,
        clip_low: float = 0.005,
        clip_high: float = 0.995,
        val_split: float = 0.15,
        test_split: float = 0.15,
        seed: int = 2025,
    ):
        self.clip_low = clip_low
        self.clip_high = clip_high
        self.val_split = val_split
        self.test_split = test_split
        self.seed = seed

        # Fitted parameters
        self.clip_min: Optional[np.ndarray] = None
        self.clip_max: Optional[np.ndarray] = None
        self.mean: Optional[np.ndarray] = None
        self.std: Optional[np.ndarray] = None
        self.class_weights: Optional[np.ndarray] = None
        self.classes: Optional[Tuple[str, ...]] = None

    def fit_transform(
        self, name: str, data_root: Path, window: int = 64, stride: int = 16,
        max_rows_per_class: Optional[int] = None, cicids_multi_class: bool = False
    ) -> Dict[str, Any]:
        """Load raw data, perform stratified split, fit scaler on train, and transform all."""
        print(f"[preprocess] Loading raw data for '{name}' from {data_root}")
        
        # 1. Load raw data — every adapter returns (X, y, classes, groups)
        if name == "can_vtc":
            X, y, classes, groups = load_can_vtc(data_root / "Can_vtc_pro", window, stride, max_rows_per_class)
        elif name == "car_hack":
            X, y, classes, groups = load_car_hack(data_root / "Car_hack_pro" / "Car_hack_pro", window, stride, max_rows_per_class)
        elif name == "cicids":
            X, y, classes, groups = load_cicids(data_root / "CICIDS_pro" / "CICIDS_pro", max_rows_per_class, cicids_multi_class)
        elif name == "veremi":
            X, y, classes, groups = load_veremi(data_root / "VeReMi_pro", window, stride, max_rows_per_class, cicids_multi_class)
        else:
            raise ValueError(f"Unknown dataset: {name}")

        if X.shape[0] == 0:
            raise RuntimeError(f"No samples loaded for {name}")
        if X.shape[1] != 46:
            raise RuntimeError(f"Expected 46 features, got {X.shape[1]}")
        if groups.shape[0] != X.shape[0]:
            raise RuntimeError(
                f"groups length {groups.shape[0]} != n_samples {X.shape[0]}")

        self.classes = classes

        # 2. Group-aware train/val/test split (no window can span the boundary)
        train_idx, val_idx, test_idx = self._grouped_split(y, groups)
        assert_no_group_overlap(groups, train_idx, val_idx, test_idx)

        # 3. Fit Percentile clipping on train only
        self.clip_min = np.quantile(X[train_idx], self.clip_low, axis=0)
        self.clip_max = np.quantile(X[train_idx], self.clip_high, axis=0)

        # Apply clipping
        X_clipped = np.clip(X, self.clip_min, self.clip_max)

        # 4. Fit Z-score on train only
        self.mean = X_clipped[train_idx].mean(axis=0)
        self.std = X_clipped[train_idx].std(axis=0) + 1e-6

        # Apply scaling
        X_scaled = (X_clipped - self.mean) / self.std

        # 5. Compute class weights based on train set only to handle imbalance
        cls_counts = np.bincount(y[train_idx], minlength=len(classes)).astype(np.float32)
        # Avoid division by zero
        cls_counts_clipped = np.clip(cls_counts, 1.0, None)
        self.class_weights = cls_counts.sum() / (len(classes) * cls_counts_clipped)
        # For classes with 0 samples, set weight to 1.0
        self.class_weights[cls_counts == 0] = 1.0

        # Warn if any split lost a class entirely. This happens when a row cap
        # truncates a capture before its injection window begins, and it makes
        # accuracy/ROC-AUC meaningless — so it must never pass silently.
        for split_name, idx in (("train", train_idx), ("val", val_idx), ("test", test_idx)):
            present = set(np.unique(y[idx]).tolist())
            missing = set(range(len(classes))) - present
            if missing:
                print(f"[preprocess] WARNING: {split_name} split is missing "
                      f"class(es) {sorted(missing)} "
                      f"({[classes[m] for m in sorted(missing)]}). "
                      f"Metrics over this split are not comparable. If a row cap "
                      f"is in use, raise it — the capture's injections may start "
                      f"beyond the cap.")

        print(f"[preprocess] {name} split sizes: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")
        print(f"[preprocess] Classes: {classes}")
        print(f"[preprocess] Class counts (train): {cls_counts.tolist()}")
        print(f"[preprocess] Class weights: {self.class_weights.tolist()}")

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
        }

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Apply the fitted clipping and scaling parameters to new inputs."""
        if self.mean is None or self.std is None or self.clip_min is None or self.clip_max is None:
            raise ValueError("Pipeline must be fitted before transforming.")
        X_clipped = np.clip(X, self.clip_min, self.clip_max)
        return (X_clipped - self.mean) / self.std

    def _grouped_split(
        self, y: np.ndarray, groups: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Assign whole contiguous blocks to train/val/test.

        Blocks are bucketed by their dominant class so the split stays
        approximately stratified, then allocated 70/15/15 *by block*. Because a
        block is never split, two overlapping windows always land together.
        """
        rng = np.random.default_rng(self.seed)
        unique_groups = np.unique(groups)

        # Dominant class of each block.
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
            # With very few blocks in a class, guarantee train gets at least one.
            if n >= 3:
                n_test = max(1, n_test)
                n_val = max(1, n_val)
                if n_test + n_val >= n:
                    n_test, n_val = 1, 1
            test_g.append(gs[:n_test])
            val_g.append(gs[n_test:n_test + n_val])
            train_g.append(gs[n_test + n_val:])

        train_groups = set(np.concatenate(train_g).tolist()) if train_g else set()
        val_groups = set(np.concatenate(val_g).tolist()) if val_g else set()
        test_groups = set(np.concatenate(test_g).tolist()) if test_g else set()

        gl = groups.tolist()
        train_idx = np.array([i for i, g in enumerate(gl) if g in train_groups], dtype=np.int64)
        val_idx = np.array([i for i, g in enumerate(gl) if g in val_groups], dtype=np.int64)
        test_idx = np.array([i for i, g in enumerate(gl) if g in test_groups], dtype=np.int64)

        # Shuffle *within* each split — order affects batching, not leakage.
        rng.shuffle(train_idx)
        rng.shuffle(val_idx)
        rng.shuffle(test_idx)

        print(f"[preprocess] blocks: total={len(unique_groups):,} "
              f"train={len(train_groups):,} val={len(val_groups):,} "
              f"test={len(test_groups):,}")
        return train_idx, val_idx, test_idx

    def save(self, path: Path) -> None:
        """Save the pipeline configuration and parameters as a pickle file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "clip_low": self.clip_low,
            "clip_high": self.clip_high,
            "val_split": self.val_split,
            "test_split": self.test_split,
            "seed": self.seed,
            "clip_min": self.clip_min,
            "clip_max": self.clip_max,
            "mean": self.mean,
            "std": self.std,
            "class_weights": self.class_weights,
            "classes": self.classes,
        }
        with open(path, "wb") as f:
            pickle.dump(artifacts, f)
        print(f"[preprocess] Saved pipeline artifacts to {path}")

    @classmethod
    def load(cls, path: Path) -> PreprocessingPipeline:
        """Load a saved pipeline artifact from a pickle file."""
        with open(path, "rb") as f:
            artifacts = pickle.load(f)
        pipe = cls(
            clip_low=artifacts["clip_low"],
            clip_high=artifacts["clip_high"],
            val_split=artifacts["val_split"],
            test_split=artifacts["test_split"],
            seed=artifacts["seed"],
        )
        pipe.clip_min = artifacts["clip_min"]
        pipe.clip_max = artifacts["clip_max"]
        pipe.mean = artifacts["mean"]
        pipe.std = artifacts["std"]
        pipe.class_weights = artifacts["class_weights"]
        pipe.classes = artifacts["classes"]
        print(f"[preprocess] Loaded pipeline artifacts from {path}")
        return pipe

"""Unified dataset builder.

One entry point — ``build_datasets(name, ...)`` — that:

1. Dispatches to the right per-dataset adapter (CAN-VTC, Car-Hacking, CICIDS-2017).
2. Applies the same preprocessing (percentile clipping + z-score) the paper
   describes in §5.2, fitted on the **train split only**.
3. Returns three ``CanFeatureDataset`` objects with identical (N, 46)
   shape so the KANConvNet training loop is dataset-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset

from . import can_vtc_dataset, car_hack_dataset, cicids_dataset, veremi_dataset


# ── Public dataset names + their disk paths ──────────────────────────────

DATASETS: Tuple[str, ...] = ("can_vtc", "car_hack", "cicids", "veremi")

# Anchored under <project root>/Preprocessed_Dataset (see config.DATA_ROOT).
_SUBPATHS = {
    "can_vtc":  ("Can_vtc_pro",),
    "car_hack": ("Car_hack_pro", "Car_hack_pro"),
    "cicids":   ("CICIDS_pro", "CICIDS_pro"),
    "veremi":   ("VeReMi_pro",),
}


@dataclass
class SplitResult:
    train: "CanFeatureDataset"
    val:   "CanFeatureDataset"
    test:  "CanFeatureDataset"
    classes: Tuple[str, ...]
    feature_mean: np.ndarray
    feature_std:  np.ndarray


class CanFeatureDataset(Dataset):
    """Memory-light wrapper around a (N, 46) tensor + (N,) labels."""

    def __init__(self, features: np.ndarray, labels: np.ndarray) -> None:
        if features.shape[0] != labels.shape[0]:
            raise ValueError("features and labels rows mismatch")
        self.features = torch.from_numpy(features.astype(np.float32))
        self.labels = torch.from_numpy(labels.astype(np.int64))

    def __len__(self) -> int:
        return self.features.size(0)

    def __getitem__(self, idx: int):
        return self.features[idx], self.labels[idx]


# ─────────────────────────────────────────────────────────────────────────


def _resolve_root(data_root: Path, name: str) -> Path:
    """Resolve `<data_root>/<sub..>` per dataset; falls back to data_root if
    it already points at a leaf directory containing the files."""
    sub = _SUBPATHS[name]
    candidate = data_root.joinpath(*sub)
    if candidate.is_dir():
        return candidate
    # Backward-compat: caller may pass the leaf directly.
    return data_root


def _load_raw(
    name: str, data_root: Path, window: int, stride: int,
    max_rows_per_class: Optional[int],
    cicids_multi_class: bool,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...]]:
    if name == "can_vtc":
        return can_vtc_dataset.load_features_labels(
            _resolve_root(data_root, name), window, stride, max_rows_per_class,
        )
    if name == "car_hack":
        return car_hack_dataset.load_features_labels(
            _resolve_root(data_root, name), window, stride, max_rows_per_class,
        )
    if name == "cicids":
        return cicids_dataset.load_features_labels(
            _resolve_root(data_root, name),
            max_rows_per_file=max_rows_per_class,
            multi_class=cicids_multi_class,
        )
    if name == "veremi":
        return veremi_dataset.load_features_labels(
            _resolve_root(data_root, name),
            window=window, stride=stride,
            max_rows_per_class=max_rows_per_class,
            multi_class=cicids_multi_class,   # reuse the same flag
        )
    raise ValueError(f"unknown dataset: {name!r}; expected one of {DATASETS}")


def _stratified_split(
    y: np.ndarray, val_split: float, test_split: float, seed: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    train_idx, val_idx, test_idx = [], [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        rng.shuffle(idx)
        n = len(idx)
        n_test = int(round(n * test_split))
        n_val = int(round(n * val_split))
        test_idx.append(idx[:n_test])
        val_idx.append(idx[n_test:n_test + n_val])
        train_idx.append(idx[n_test + n_val:])
    train_idx = np.concatenate(train_idx)
    val_idx = np.concatenate(val_idx)
    test_idx = np.concatenate(test_idx)
    rng.shuffle(train_idx); rng.shuffle(val_idx); rng.shuffle(test_idx)
    return train_idx, val_idx, test_idx


def build_datasets(
    name: str,
    data_root: Path,
    window: int = 64,
    stride: int = 16,
    val_split: float = 0.15,
    test_split: float = 0.15,
    seed: int = 2025,
    max_rows_per_class: Optional[int] = None,
    clip_low: float = 0.005,
    clip_high: float = 0.995,
    cicids_multi_class: bool = False,
) -> SplitResult:
    """End-to-end loader. Returns train/val/test datasets ready for DataLoader."""
    print(f"\n[data] building {name!r} from {data_root}")
    X, y, classes = _load_raw(name, data_root, window, stride,
                              max_rows_per_class, cicids_multi_class)
    if X.shape[0] == 0:
        raise RuntimeError(f"No samples produced for {name!r}.")
    if X.shape[1] != 46:
        raise RuntimeError(
            f"Expected 46 features per row, got {X.shape[1]} — "
            f"the adapter for {name!r} is misconfigured."
        )

    train_idx, val_idx, test_idx = _stratified_split(
        y, val_split, test_split, seed
    )

    # Percentile clip on train, applied to all splits.
    lo = np.quantile(X[train_idx], clip_low, axis=0)
    hi = np.quantile(X[train_idx], clip_high, axis=0)
    X = np.clip(X, lo, hi)

    # z-score on train.
    mean = X[train_idx].mean(axis=0)
    std = X[train_idx].std(axis=0) + 1e-6
    X = (X - mean) / std

    print(f"[data] total={X.shape[0]} train={len(train_idx)} "
          f"val={len(val_idx)} test={len(test_idx)} classes={classes}")
    return SplitResult(
        train=CanFeatureDataset(X[train_idx], y[train_idx]),
        val=CanFeatureDataset(X[val_idx],   y[val_idx]),
        test=CanFeatureDataset(X[test_idx], y[test_idx]),
        classes=classes,
        feature_mean=mean.astype(np.float32),
        feature_std=std.astype(np.float32),
    )

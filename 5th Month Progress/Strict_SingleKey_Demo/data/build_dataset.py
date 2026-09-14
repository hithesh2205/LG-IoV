"""Unified dataset builder — thin convenience wrapper.

One entry point — ``build_datasets(name, ...)`` — that returns ready-to-use
train/val/test ``CanFeatureDataset`` objects.

Consolidation note (Month 5, defect D7)
---------------------------------------
This module previously carried its **own** copy of the loading, splitting and
scaling logic, including a second ``_stratified_split`` that shuffled individual
windows. That duplicate was the leaky splitter described in defect D2, and it
silently diverged from ``preprocess.PreprocessingPipeline``.

There is now exactly one implementation. ``build_datasets`` delegates to
``PreprocessingPipeline.fit_transform``, which performs the group-aware split
and the fit-on-train-only clipping and scaling. ``CanFeatureDataset`` is
re-exported from ``data.loader`` so there is also only one definition of it.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from .loader import CanFeatureDataset
from .preprocess import DATASETS, PreprocessingPipeline

__all__ = ["CanFeatureDataset", "SplitResult", "build_datasets", "DATASETS"]


@dataclass
class SplitResult:
    train: CanFeatureDataset
    val:   CanFeatureDataset
    test:  CanFeatureDataset
    classes: Tuple[str, ...]
    feature_mean: np.ndarray
    feature_std:  np.ndarray
    class_weights: np.ndarray


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
    """End-to-end loader. Returns train/val/test datasets ready for DataLoader.

    ``data_root`` must be the directory that *contains* the per-dataset folders
    (``Can_vtc_pro``, ``Car_hack_pro``, ``CICIDS_pro``, ``VeReMi_pro``); the
    pipeline resolves the per-dataset subpath itself.
    """
    if name not in DATASETS:
        raise ValueError(f"unknown dataset: {name!r}; expected one of {DATASETS}")

    print(f"\n[data] building {name!r} from {data_root}")
    pipeline = PreprocessingPipeline(
        clip_low=clip_low,
        clip_high=clip_high,
        val_split=val_split,
        test_split=test_split,
        seed=seed,
    )
    split = pipeline.fit_transform(
        name, data_root,
        window=window, stride=stride,
        max_rows_per_class=max_rows_per_class,
        cicids_multi_class=cicids_multi_class,
    )

    print(f"[data] total={split['X_train'].shape[0] + split['X_val'].shape[0] + split['X_test'].shape[0]} "
          f"train={split['X_train'].shape[0]} val={split['X_val'].shape[0]} "
          f"test={split['X_test'].shape[0]} classes={pipeline.classes}")

    return SplitResult(
        train=CanFeatureDataset(split["X_train"], split["y_train"]),
        val=CanFeatureDataset(split["X_val"], split["y_val"]),
        test=CanFeatureDataset(split["X_test"], split["y_test"]),
        classes=pipeline.classes,
        feature_mean=pipeline.mean.astype(np.float32),
        feature_std=pipeline.std.astype(np.float32),
        class_weights=pipeline.class_weights.astype(np.float32),
    )

"""Shared timeless 46-feature extractor for CAN-style datasets.

After the timestamp-removal cleanup, both ``Can_vtc_pro`` and ``Car_hack_pro``
provide CAN message streams without time deltas. The 46-dim feature vector
used as KANConvNet input (paper §3.4) is therefore re-defined to use
**timeless** descriptors of each W-message window:

    slots 0..7   payload byte means b0..b7        (normalised /255)
    slots 8..15  payload byte stds  b0..b7
    slots 16     DLC mean
    slots 17     DLC std
    slots 18     unique CAN-ID ratio  (count(unique IDs) / W)
    slots 19     dominant-ID frequency
    slots 20..43 CAN-ID histogram over 24 hash buckets
    slots 44     mean Shannon entropy over the W payload byte distributions
    slots 45     non-zero payload byte ratio

Total = 8 + 8 + 2 + 2 + 24 + 2 = 46  ✓
"""
from __future__ import annotations

from typing import List

import numpy as np


N_ID_BUCKETS = 24


def extract_window_features(
    can_ids: np.ndarray,        # (W,) int64
    dlc: np.ndarray,             # (W,) float32
    payload: np.ndarray,         # (W, 8) float32 in [0,1]  (NaN-safe)
) -> np.ndarray:
    """Return a 46-dim feature vector for one window."""
    feat = np.empty(46, dtype=np.float32)

    # payload byte mean / std
    feat[0:8] = payload.mean(axis=0)
    feat[8:16] = payload.std(axis=0)

    # DLC mean / std
    feat[16] = dlc.mean()
    feat[17] = dlc.std()

    # unique-ID ratio + dominant-ID frequency
    uniq, counts = np.unique(can_ids, return_counts=True)
    feat[18] = float(len(uniq)) / max(len(can_ids), 1)
    feat[19] = float(counts.max()) / max(len(can_ids), 1)

    # CAN-ID histogram over hashed buckets
    buckets = np.zeros(N_ID_BUCKETS, dtype=np.float32)
    np.add.at(buckets, can_ids % N_ID_BUCKETS, 1.0)
    buckets /= max(buckets.sum(), 1.0)
    feat[20:20 + N_ID_BUCKETS] = buckets

    # Mean Shannon entropy across the eight byte positions.
    ent = 0.0
    for b in range(8):
        # Each byte slot — discretise [0,1] back to 0..255 then count.
        vals = (payload[:, b] * 255.0).astype(np.int32)
        _, c = np.unique(vals, return_counts=True)
        p = c.astype(np.float64) / c.sum()
        ent += float(-(p * np.log2(p + 1e-12)).sum())
    feat[44] = ent / 8.0

    # Fraction of non-zero payload bytes in the window.
    feat[45] = float((payload > 0).mean())

    return feat


def windows_from_stream(
    can_ids: np.ndarray,
    dlc: np.ndarray,
    payload: np.ndarray,
    window: int,
    stride: int,
) -> np.ndarray:
    """Slide W-length windows; return (N, 46) feature matrix."""
    n = len(can_ids)
    rows: List[np.ndarray] = []
    for start in range(0, n - window + 1, stride):
        end = start + window
        rows.append(extract_window_features(
            can_ids[start:end], dlc[start:end], payload[start:end]
        ))
    if not rows:
        return np.zeros((0, 46), dtype=np.float32)
    return np.stack(rows, axis=0)

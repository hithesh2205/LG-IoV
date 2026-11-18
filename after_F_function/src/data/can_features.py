"""Shared 46-feature extractor for CAN-style datasets.

Preserves the exact timeless feature representation from the original codebase:
    slots 0..7   payload byte means b0..b7        (normalised /255)
    slots 8..15  payload byte stds  b0..b7
    slots 16     DLC mean
    slots 17     DLC std
    slots 18     unique CAN-ID ratio  (count(unique IDs) / W)
    slots 19     dominant-ID frequency
    slots 20..43 CAN-ID histogram over 24 hash buckets
    slots 44     mean Shannon entropy over the W payload byte distributions
    slots 45     non-zero payload byte ratio
Total = 8 + 8 + 2 + 2 + 24 + 2 = 46 features.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np

N_ID_BUCKETS = 24
DEFAULT_BLOCK_SIZE = 6400


def n_blocks_for(n_messages: int, block_size: int = DEFAULT_BLOCK_SIZE) -> int:
    """Return number of contiguous blocks spanning n_messages."""
    if n_messages <= 0:
        return 0
    return max(1, int(np.ceil(n_messages / block_size)))



def extract_window_features(
    can_ids: np.ndarray,
    dlc: np.ndarray,
    payload: np.ndarray,
) -> np.ndarray:
    """Return a 46-dim feature vector for one window."""
    feat = np.empty(46, dtype=np.float32)

    # 0..7: payload byte mean
    feat[0:8] = payload.mean(axis=0)
    # 8..15: payload byte std
    feat[8:16] = payload.std(axis=0)

    # 16, 17: DLC mean / std
    feat[16] = float(dlc.mean())
    feat[17] = float(dlc.std())

    # 18, 19: unique-ID ratio + dominant-ID frequency
    uniq, counts = np.unique(can_ids, return_counts=True)
    feat[18] = float(len(uniq)) / max(len(can_ids), 1)
    feat[19] = float(counts.max()) / max(len(can_ids), 1)

    # 20..43: CAN-ID histogram over 24 hashed buckets
    buckets = np.zeros(N_ID_BUCKETS, dtype=np.float32)
    np.add.at(buckets, can_ids % N_ID_BUCKETS, 1.0)
    buckets /= max(buckets.sum(), 1.0)
    feat[20:20 + N_ID_BUCKETS] = buckets

    # 44: Mean Shannon entropy across the eight byte positions
    ent = 0.0
    for b in range(8):
        vals = (payload[:, b] * 255.0).astype(np.int32)
        _, c = np.unique(vals, return_counts=True)
        p = c.astype(np.float64) / c.sum()
        ent += float(-(p * np.log2(p + 1e-12)).sum())
    feat[44] = ent / 8.0

    # 45: Fraction of non-zero payload bytes in the window
    feat[45] = float((payload > 0).mean())

    return feat


def windows_from_stream(
    can_ids: np.ndarray,
    dlc: np.ndarray,
    payload: np.ndarray,
    window: int = 64,
    stride: int = 16,
    msg_labels: Optional[np.ndarray] = None,
    block_size: int = DEFAULT_BLOCK_SIZE,
    group_offset: int = 0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Slide W-length windows inside contiguous blocks.
    
    Returns (X (M, 46), y (M,), groups (M,))
    """
    n = len(can_ids)
    if n < window:
        return (np.zeros((0, 46), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.int64))

    rows: List[np.ndarray] = []
    labels: List[int] = []
    groups: List[int] = []

    n_blocks = max(1, int(np.ceil(n / block_size)))
    for b in range(n_blocks):
        b_start = b * block_size
        b_end = min(n, b_start + block_size)
        if b_end - b_start < window:
            continue
        for start in range(b_start, b_end - window + 1, stride):
            end = start + window
            rows.append(extract_window_features(
                can_ids[start:end], dlc[start:end], payload[start:end]
            ))
            if msg_labels is None:
                labels.append(0)
            else:
                labels.append(int(msg_labels[start:end].max()))
            groups.append(group_offset + b)

    if not rows:
        return (np.zeros((0, 46), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.int64))

    return (np.stack(rows, axis=0),
            np.asarray(labels, dtype=np.int64),
            np.asarray(groups, dtype=np.int64))

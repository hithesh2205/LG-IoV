"""Shared timeless 46-feature extractor for CAN-style datasets.

After the timestamp-removal cleanup, both ``Can_vtc_pro`` and ``Car_hack_pro``
provide CAN message streams without time deltas. The 46-dim feature vector
used as classifier input is therefore defined over **timeless** descriptors of
each W-message window:

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

Windowing contract (revised Month 5, defects D1/D2)
---------------------------------------------------
``windows_from_stream`` now returns ``(X, y, groups)`` rather than ``X`` alone:

* ``y``      — per-window label derived from **per-message ground truth**, not
  from the source filename. A window is labelled with the attack class if it
  contains at least one injected message, otherwise normal (class 0).
* ``groups`` — a contiguous *block* id. Windows are emitted only when they lie
  fully inside one block, so no window ever straddles a block boundary. The
  splitter in ``preprocess.py`` then assigns whole blocks to train/val/test,
  which makes it impossible for two overlapping windows to land on opposite
  sides of the split.

Both changes are required for the reported metrics to mean anything; see
``Documentation/05_defects.md`` (D1, D2).
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np


N_ID_BUCKETS = 24

#: Default contiguous block length, in messages. Windows never cross a block
#: boundary, and whole blocks are assigned to a single split.
DEFAULT_BLOCK_SIZE = 6400


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
    msg_labels: Optional[np.ndarray] = None,
    block_size: int = DEFAULT_BLOCK_SIZE,
    group_offset: int = 0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Slide W-length windows inside contiguous blocks.

    Args:
        can_ids, dlc, payload: the parsed message stream.
        window, stride: sliding-window geometry.
        msg_labels: optional (N,) int array of **per-message** class labels,
            0 = normal, >0 = an attack class. When ``None`` every window is
            labelled 0 and the caller is responsible for assigning labels.
        block_size: contiguous block length in messages. Windows are emitted
            only when fully contained in one block.
        group_offset: added to every emitted block id, so callers can keep the
            block ids of different source files disjoint.

    Returns:
        ``(X (M,46) float32, y (M,) int64, groups (M,) int64)``
    """
    n = len(can_ids)
    if n < window:
        return (np.zeros((0, 46), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.int64))

    if block_size < window:
        raise ValueError(f"block_size ({block_size}) must be >= window ({window})")

    rows: List[np.ndarray] = []
    labels: List[int] = []
    groups: List[int] = []

    n_blocks = max(1, int(np.ceil(n / block_size)))
    for b in range(n_blocks):
        b_start = b * block_size
        b_end = min(n, b_start + block_size)
        if b_end - b_start < window:
            continue  # tail too short to hold a full window
        # Emit only windows fully inside [b_start, b_end) — no boundary crossing.
        for start in range(b_start, b_end - window + 1, stride):
            end = start + window
            rows.append(extract_window_features(
                can_ids[start:end], dlc[start:end], payload[start:end]
            ))
            if msg_labels is None:
                labels.append(0)
            else:
                # A window is an attack window if it contains ANY injected
                # message. Each capture carries a single attack class, so the
                # max over the window recovers that class.
                labels.append(int(msg_labels[start:end].max()))
            groups.append(b + group_offset)

    if not rows:
        return (np.zeros((0, 46), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.int64))

    return (np.stack(rows, axis=0),
            np.asarray(labels, dtype=np.int64),
            np.asarray(groups, dtype=np.int64))


def n_blocks_for(n_messages: int, block_size: int = DEFAULT_BLOCK_SIZE) -> int:
    """Number of block ids a stream of ``n_messages`` will consume."""
    return max(1, int(np.ceil(n_messages / block_size)))


def report_window_purity(name: str, y: np.ndarray, injection_rate: float) -> str:
    """Warn when a capture's injection density saturates every window.

    A window is labelled "attack" if it holds *any* injected message. When the
    injection rate is high relative to the window length, essentially every
    window becomes an attack window and the capture separates perfectly from a
    clean capture — the label is then correct per-message but still coincides
    with the source file, so the task degenerates into flood detection rather
    than intrusion detection.

    This is a property of the *attack*, not a labelling bug, but it must be
    visible in the run log so nobody reads a near-perfect score as evidence of
    generalisation.

    Returns a short status string: ``"mixed"``, ``"saturated"`` or ``"clean"``.
    """
    if len(y) == 0:
        return "empty"
    atk = float((y > 0).mean())
    if atk >= 0.99:
        print(f"[{name}] NOTE: injection rate {injection_rate:.1%} saturates the "
              f"window ({atk:.1%} of windows are attack). This capture "
              f"separates trivially from a clean capture — treat high accuracy "
              f"here as flood detection, not generalisation.")
        return "saturated"
    if atk <= 0.01:
        return "clean"
    return "mixed"

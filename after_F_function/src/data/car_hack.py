"""Car-Hacking dataset loader (HCRL) with per-message ground-truth labelling."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

from .can_features import (
    DEFAULT_BLOCK_SIZE,
    n_blocks_for,
    windows_from_stream,
)

CLASSES: Tuple[str, ...] = (
    "normal", "DoS", "Fuzzy", "RPM", "gear",
)

FILE_TO_ATTACK_CLASS = {
    "cleaned_normal_run_data.csv": 0,
    "cleaned_DoS_dataset.csv":     1,
    "cleaned_Fuzzy_dataset.csv":   2,
    "cleaned_RPM_dataset.csv":     3,
    "cleaned_gear_dataset.csv":    4,
}

_LOG_RE = re.compile(
    r"^\s*ID:\s*([0-9a-fA-F]+)\s+\S+\s+DLC:\s*(\d+)\s*(.*?)\s*$"
)


def _hex_to_int(tok: str) -> int:
    try:
        return int(tok, 16)
    except ValueError:
        return 0


def _parse_flat_csv(
    path: Path, max_rows: Optional[int], attack_class: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    ids: List[int] = []
    dlcs: List[int] = []
    payloads: List[List[float]] = []
    labels: List[int] = []
    n_malformed = 0

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if max_rows is not None and i >= max_rows:
                break
            parts = line.strip().split(",")
            if len(parts) < 3:
                n_malformed += 1
                continue

            flag = parts[-1].strip().upper()
            if flag == "T":
                label = attack_class
            elif flag == "R":
                label = 0
            else:
                n_malformed += 1
                continue

            ids.append(_hex_to_int(parts[0]))
            try:
                dlcs.append(int(parts[1]))
            except ValueError:
                dlcs.append(0)

            byte_tokens = parts[2:-1][:8]
            row = [_hex_to_int(t) / 255.0 for t in byte_tokens]
            row.extend([0.0] * (8 - len(row)))
            payloads.append(row[:8])
            labels.append(label)

    if not ids:
        return (np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, 8), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                n_malformed)

    return (np.asarray(ids, dtype=np.int64),
            np.asarray(dlcs, dtype=np.float32),
            np.asarray(payloads, dtype=np.float32),
            np.asarray(labels, dtype=np.int64),
            n_malformed)


def _parse_log(
    path: Path, max_rows: Optional[int],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    ids: List[int] = []
    dlcs: List[int] = []
    payloads: List[List[float]] = []
    n_malformed = 0

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if max_rows is not None and i >= max_rows:
                break
            m = _LOG_RE.match(line)
            if not m:
                n_malformed += 1
                continue
            ids.append(int(m.group(1), 16))
            dlcs.append(int(m.group(2)))
            tokens = m.group(3).split()
            row = [_hex_to_int(t) / 255.0 for t in tokens[:8]]
            row.extend([0.0] * (8 - len(row)))
            payloads.append(row[:8])

    if not ids:
        return (np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, 8), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                n_malformed)

    return (np.asarray(ids, dtype=np.int64),
            np.asarray(dlcs, dtype=np.float32),
            np.asarray(payloads, dtype=np.float32),
            np.zeros(len(ids), dtype=np.int64),
            n_malformed)


def load_features_labels(
    root: Path,
    window: int = 64,
    stride: int = 16,
    max_rows_per_class: Optional[int] = None,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...], np.ndarray]:
    """Return (X (N, 46), y (N,), classes, groups (N,))."""
    feat_blocks: List[np.ndarray] = []
    label_blocks: List[np.ndarray] = []
    group_blocks: List[np.ndarray] = []
    group_offset = 0

    for fname, attack_class in FILE_TO_ATTACK_CLASS.items():
        path = root / fname
        if not path.exists():
            continue

        if fname == "cleaned_normal_run_data.csv":
            can_ids, dlc, payload, msg_labels, n_bad = _parse_log(path, max_rows_per_class)
        else:
            can_ids, dlc, payload, msg_labels, n_bad = _parse_flat_csv(path, max_rows_per_class, attack_class)

        if len(can_ids) == 0:
            continue

        X, y, g = windows_from_stream(
            can_ids, dlc, payload, window, stride,
            msg_labels=msg_labels, block_size=block_size,
            group_offset=group_offset,
        )
        group_offset += n_blocks_for(len(can_ids), block_size)

        feat_blocks.append(X)
        label_blocks.append(y)
        group_blocks.append(g)

    if not feat_blocks:
        raise RuntimeError(f"No Car-Hacking files found under {root}")

    return (np.concatenate(feat_blocks, axis=0),
            np.concatenate(label_blocks, axis=0),
            CLASSES,
            np.concatenate(group_blocks, axis=0))

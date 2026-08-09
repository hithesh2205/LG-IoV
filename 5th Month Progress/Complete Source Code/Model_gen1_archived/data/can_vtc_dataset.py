"""IEEE VTC-CAN dataset adapter.

After timestamp removal, each line is::

    ID: <hex>    000    DLC: <int>    <up to 8 hex bytes>

Class label is inferred from the source filename:
    Attack_free   -> 0
    DoS_attack    -> 1
    Fuzzy_attack  -> 2
    Impersonation_attack -> 3
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from .can_features import windows_from_stream


CLASSES: Tuple[str, ...] = (
    "Attack_free", "DoS_attack", "Fuzzy_attack", "Impersonation_attack",
)

# Cleaned line: "ID: 0220    000    DLC: 8    29 c5 26 55 6a 67 02 5d"
_LINE_RE = re.compile(
    r"^\s*ID:\s*([0-9a-fA-F]+)\s+\S+\s+DLC:\s*(\d+)\s*(.*?)\s*$"
)


def _parse_can_log(path: Path, max_rows: Optional[int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stream-parse → (can_ids, dlc, payload(N,8))."""
    ids: List[int] = []
    dlcs: List[int] = []
    payloads: List[List[float]] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if max_rows is not None and i >= max_rows:
                break
            m = _LINE_RE.match(line)
            if not m:
                continue
            ids.append(int(m.group(1), 16))
            dlcs.append(int(m.group(2)))
            tokens = m.group(3).split()
            row = [int(tok, 16) / 255.0 for tok in tokens[:8]]
            row.extend([0.0] * (8 - len(row)))
            payloads.append(row)
    if not ids:
        return (np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, 8), dtype=np.float32))
    return (np.asarray(ids, dtype=np.int64),
            np.asarray(dlcs, dtype=np.float32),
            np.asarray(payloads, dtype=np.float32))


def load_features_labels(
    root: Path,
    window: int,
    stride: int,
    max_rows_per_class: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...]]:
    """Return (X (N,46), y (N,), classes)."""
    feat_blocks, label_blocks = [], []
    for idx, cls in enumerate(CLASSES):
        path = root / f"cleaned_{cls}_dataset.csv"
        if not path.exists():
            print(f"[can_vtc] WARN missing {path.name}")
            continue
        can_ids, dlc, payload = _parse_can_log(path, max_rows_per_class)
        X = windows_from_stream(can_ids, dlc, payload, window, stride)
        y = np.full(X.shape[0], idx, dtype=np.int64)
        print(f"[can_vtc] {cls}: {X.shape[0]} windows")
        feat_blocks.append(X)
        label_blocks.append(y)
    if not feat_blocks:
        raise RuntimeError(f"No CAN-VTC files found under {root}")
    return (np.concatenate(feat_blocks, axis=0),
            np.concatenate(label_blocks, axis=0),
            CLASSES)

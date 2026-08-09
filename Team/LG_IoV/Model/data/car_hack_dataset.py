"""Car-Hacking dataset adapter (HCRL).

After cleanup, the directory contains:

    cleaned_DoS_dataset.csv      flat CSV  id_hex,dlc,b0,..b7,R/T
    cleaned_Fuzzy_dataset.csv    flat CSV
    cleaned_RPM_dataset.csv      flat CSV
    cleaned_gear_dataset.csv     flat CSV
    cleaned_normal_run_data.csv  HCRL log  "ID: <hex>  000  DLC: <n>  <bytes>"

Class label is inferred from the source file (multi-class IDS):
    normal_run -> 0
    DoS        -> 1
    Fuzzy      -> 2
    RPM        -> 3
    gear       -> 4

The flat CSV's R/T flag (R=regular, T=injected attack) is dropped — it is
attack-row-level information; we operate at the window level and use the
file label.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from .can_features import windows_from_stream


CLASSES: Tuple[str, ...] = (
    "normal_run", "DoS", "Fuzzy", "RPM", "gear",
)

# Maps filename suffix → class index.
FILE_TO_LABEL = {
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


def _parse_flat_csv(path: Path, max_rows: Optional[int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Flat CSV: id_hex, dlc, b0..b7 (hex), R/T."""
    ids: List[int] = []
    dlcs: List[int] = []
    payloads: List[List[float]] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if max_rows is not None and i >= max_rows:
                break
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            ids.append(_hex_to_int(parts[0]))
            try:
                dlcs.append(int(parts[1]))
            except ValueError:
                dlcs.append(0)
            # Up to 8 payload byte tokens — the trailing R/T flag is dropped.
            byte_tokens = parts[2:10]
            row = [_hex_to_int(t) / 255.0 for t in byte_tokens]
            row.extend([0.0] * (8 - len(row)))
            payloads.append(row[:8])
    if not ids:
        return (np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, 8), dtype=np.float32))
    return (np.asarray(ids, dtype=np.int64),
            np.asarray(dlcs, dtype=np.float32),
            np.asarray(payloads, dtype=np.float32))


def _parse_log(path: Path, max_rows: Optional[int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ids: List[int] = []
    dlcs: List[int] = []
    payloads: List[List[float]] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if max_rows is not None and i >= max_rows:
                break
            m = _LOG_RE.match(line)
            if not m:
                continue
            ids.append(int(m.group(1), 16))
            dlcs.append(int(m.group(2)))
            tokens = m.group(3).split()
            row = [_hex_to_int(t) / 255.0 for t in tokens[:8]]
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
    feat_blocks, label_blocks = [], []
    for fname, label in FILE_TO_LABEL.items():
        path = root / fname
        if not path.exists():
            print(f"[car_hack] WARN missing {path.name}")
            continue
        parser = _parse_log if fname == "cleaned_normal_run_data.csv" else _parse_flat_csv
        can_ids, dlc, payload = parser(path, max_rows_per_class)
        X = windows_from_stream(can_ids, dlc, payload, window, stride)
        y = np.full(X.shape[0], label, dtype=np.int64)
        print(f"[car_hack] {CLASSES[label]}: {X.shape[0]} windows")
        feat_blocks.append(X)
        label_blocks.append(y)
    if not feat_blocks:
        raise RuntimeError(f"No Car-Hacking files found under {root}")
    return (np.concatenate(feat_blocks, axis=0),
            np.concatenate(label_blocks, axis=0),
            CLASSES)

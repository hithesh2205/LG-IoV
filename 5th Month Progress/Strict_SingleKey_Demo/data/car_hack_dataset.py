"""Car-Hacking dataset adapter (HCRL) — per-message ground-truth labelling.

Directory contents after cleanup::

    cleaned_DoS_dataset.csv      flat CSV  id_hex,dlc,b0,..b7,R/T
    cleaned_Fuzzy_dataset.csv    flat CSV
    cleaned_RPM_dataset.csv      flat CSV
    cleaned_gear_dataset.csv     flat CSV
    cleaned_normal_run_data.csv  HCRL log  "ID: <hex>  000  DLC: <n>  <bytes>"

Labelling (revised Month 5 — defect D1)
---------------------------------------
The four attack captures carry the HCRL ``R``/``T`` flag in field 11:

    R = regular (normal) message
    T = injected (attack) message

Earlier versions of this adapter **discarded** that flag and labelled every
window by its source filename. That turned the task into "which capture file is
this?" rather than "is there an intrusion in this window?", and was the direct
cause of the implausible headline accuracies.

This version uses the flag as the ground truth:

* a message is labelled with the file's attack class iff its flag is ``T``;
* a window is labelled with the attack class iff it contains **at least one**
  injected message, otherwise normal (class 0).

Consequence: attack captures now contribute *both* normal and attack windows,
which is the realistic setting — an IDS must find a burst of injected frames
inside otherwise ordinary traffic.

``cleaned_normal_run_data.csv`` has no flag column because every message in it
is normal by construction; it is labelled 0 throughout.

Malformed rows (a trailing field that is neither ``R`` nor ``T``) are counted
and dropped rather than silently coerced into a class.
"""
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

#: Maps filename → the attack class index injected in that capture.
#: ``cleaned_normal_run_data.csv`` contains no injections at all.
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
    """Flat CSV: ``id_hex, dlc, b0..b7 (hex), R/T``.

    Returns ``(can_ids, dlc, payload, msg_labels, n_malformed)`` where
    ``msg_labels[i]`` is ``attack_class`` for injected rows and 0 otherwise.
    """
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
                # Neither R nor T — a truncated/corrupt row. Drop it instead of
                # letting an unknown flag become a silent third class.
                n_malformed += 1
                continue

            ids.append(_hex_to_int(parts[0]))
            try:
                dlcs.append(int(parts[1]))
            except ValueError:
                dlcs.append(0)
            # Payload bytes sit between the DLC and the trailing flag.
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
    """HCRL log format — used only by the all-normal capture."""
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
            payloads.append(row)

    if not ids:
        return (np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, 8), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                n_malformed)

    return (np.asarray(ids, dtype=np.int64),
            np.asarray(dlcs, dtype=np.float32),
            np.asarray(payloads, dtype=np.float32),
            np.zeros(len(ids), dtype=np.int64),   # every message is normal
            n_malformed)


def load_features_labels(
    root: Path,
    window: int,
    stride: int,
    max_rows_per_class: Optional[int] = None,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...], np.ndarray]:
    """Return ``(X (N,46), y (N,), classes, groups (N,))``."""
    feat_blocks: List[np.ndarray] = []
    label_blocks: List[np.ndarray] = []
    group_blocks: List[np.ndarray] = []
    group_offset = 0

    for fname, attack_class in FILE_TO_ATTACK_CLASS.items():
        path = root / fname
        if not path.exists():
            print(f"[car_hack] WARN missing {path.name}")
            continue

        if fname == "cleaned_normal_run_data.csv":
            can_ids, dlc, payload, msg_labels, n_bad = _parse_log(
                path, max_rows_per_class)
        else:
            can_ids, dlc, payload, msg_labels, n_bad = _parse_flat_csv(
                path, max_rows_per_class, attack_class)

        if len(can_ids) == 0:
            print(f"[car_hack] WARN {fname}: no parsable messages")
            continue

        X, y, g = windows_from_stream(
            can_ids, dlc, payload, window, stride,
            msg_labels=msg_labels, block_size=block_size,
            group_offset=group_offset,
        )
        group_offset += n_blocks_for(len(can_ids), block_size)

        n_inj = int((msg_labels > 0).sum())
        n_atk_win = int((y > 0).sum())
        print(f"[car_hack] {fname}: msgs={len(can_ids):,} "
              f"injected={n_inj:,} ({100 * n_inj / len(can_ids):.1f}%) "
              f"malformed_dropped={n_bad:,} → windows={X.shape[0]:,} "
              f"(attack={n_atk_win:,}, normal={X.shape[0] - n_atk_win:,})")

        feat_blocks.append(X)
        label_blocks.append(y)
        group_blocks.append(g)

    if not feat_blocks:
        raise RuntimeError(f"No Car-Hacking files found under {root}")

    return (np.concatenate(feat_blocks, axis=0),
            np.concatenate(label_blocks, axis=0),
            CLASSES,
            np.concatenate(group_blocks, axis=0))

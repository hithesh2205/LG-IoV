"""IEEE VTC-CAN dataset adapter — signature-derived per-message labelling.

After timestamp removal each line is::

    ID: <hex>    000    DLC: <int>    <up to 8 hex bytes>

There is **no** per-message label column in the cleaned captures, so ground
truth has to be recovered from the injection signature itself.

What is and is not recoverable (measured, Month 5)
--------------------------------------------------
Message-ID census over the four captures (first 3M messages each), comparing
each attack capture's ID set against the 45 IDs seen in the attack-free capture:

    capture           unique IDs absent from attack-free    share of traffic
    DoS               1  (0x000)                            51.1 %
    Fuzzy             0                                      0.0 %
    Impersonation     0                                      0.0 %

* **DoS** floods CAN ID ``0x000`` — the highest-priority identifier — with
  all-zero payloads. ``0x000`` never occurs in the attack-free capture and
  accounts for 51.1 % of the DoS capture. This is the textbook CAN
  denial-of-service signature and gives an exact per-message label.

* **Fuzzy** and **Impersonation** inject on *legitimate* CAN IDs (zero novel
  IDs). Their injected messages are therefore indistinguishable from normal
  traffic on ID alone. They could only be labelled by a payload-anomaly
  heuristic — i.e. by running a detector to manufacture the labels a detector
  is then trained on, which is circular and scientifically worthless.

Decision
--------
CAN-VTC is loaded by default as a **2-class, per-message-labelled** problem:

    0 = normal      1 = DoS injection

The Fuzzy and Impersonation captures are **excluded by default**. Including
them would require reverting to filename labels, which is exactly defect D1.
Pass ``include_unlabelled_captures=True`` to fall back to the old file-level
behaviour — provided only to reproduce pre-Month-5 numbers, never for reporting.

To restore the full 4-class problem the raw IEEE VTC-CAN dataset must be
re-acquired with its injection ground truth intact. This is tracked as an open
item in ``Documentation/09_current_status.md``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from .can_features import (
    DEFAULT_BLOCK_SIZE,
    n_blocks_for,
    report_window_purity,
    windows_from_stream,
)


#: Default 2-class problem with recoverable per-message ground truth.
CLASSES: Tuple[str, ...] = ("normal", "DoS")

#: Legacy 4-class filename-derived labels (defect D1 — reproduction only).
LEGACY_CLASSES: Tuple[str, ...] = (
    "Attack_free", "DoS_attack", "Fuzzy_attack", "Impersonation_attack",
)

#: CAN ID used by the DoS flood. Absent from the attack-free capture.
DOS_INJECTION_ID = 0x000

# Cleaned line: "ID: 0220    000    DLC: 8    29 c5 26 55 6a 67 02 5d"
_LINE_RE = re.compile(
    r"^\s*ID:\s*([0-9a-fA-F]+)\s+\S+\s+DLC:\s*(\d+)\s*(.*?)\s*$"
)


def _parse_can_log(
    path: Path, max_rows: Optional[int],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stream-parse → ``(can_ids, dlc, payload(N,8))``."""
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
            row = []
            for tok in tokens[:8]:
                try:
                    row.append(int(tok, 16) / 255.0)
                except ValueError:
                    row.append(0.0)
            row.extend([0.0] * (8 - len(row)))
            payloads.append(row)
    if not ids:
        return (np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, 8), dtype=np.float32))
    return (np.asarray(ids, dtype=np.int64),
            np.asarray(dlcs, dtype=np.float32),
            np.asarray(payloads, dtype=np.float32))


def _load_labelled(
    root: Path, window: int, stride: int,
    max_rows_per_class: Optional[int], block_size: int,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...], np.ndarray]:
    """Default path: normal vs DoS with exact per-message labels."""
    sources = [
        ("cleaned_Attack_free_dataset.csv", False),
        ("cleaned_DoS_attack_dataset.csv",  True),
    ]

    feat_blocks: List[np.ndarray] = []
    label_blocks: List[np.ndarray] = []
    group_blocks: List[np.ndarray] = []
    group_offset = 0

    for fname, has_injection in sources:
        path = root / fname
        if not path.exists():
            print(f"[can_vtc] WARN missing {path.name}")
            continue

        can_ids, dlc, payload = _parse_can_log(path, max_rows_per_class)
        if len(can_ids) == 0:
            print(f"[can_vtc] WARN {fname}: no parsable messages")
            continue

        if has_injection:
            msg_labels = (can_ids == DOS_INJECTION_ID).astype(np.int64)
        else:
            msg_labels = np.zeros(len(can_ids), dtype=np.int64)

        X, y, g = windows_from_stream(
            can_ids, dlc, payload, window, stride,
            msg_labels=msg_labels, block_size=block_size,
            group_offset=group_offset,
        )
        group_offset += n_blocks_for(len(can_ids), block_size)

        n_inj = int(msg_labels.sum())
        n_atk_win = int((y > 0).sum())
        rate = n_inj / len(can_ids)
        print(f"[can_vtc] {fname}: msgs={len(can_ids):,} "
              f"injected={n_inj:,} ({100 * rate:.1f}%) "
              f"→ windows={X.shape[0]:,} "
              f"(attack={n_atk_win:,}, normal={X.shape[0] - n_atk_win:,})")
        if has_injection:
            report_window_purity("can_vtc", y, rate)

        feat_blocks.append(X)
        label_blocks.append(y)
        group_blocks.append(g)

    if not feat_blocks:
        raise RuntimeError(f"No CAN-VTC files found under {root}")

    return (np.concatenate(feat_blocks, axis=0),
            np.concatenate(label_blocks, axis=0),
            CLASSES,
            np.concatenate(group_blocks, axis=0))


def _load_legacy_file_labels(
    root: Path, window: int, stride: int,
    max_rows_per_class: Optional[int], block_size: int,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...], np.ndarray]:
    """Reproduction-only path: the pre-Month-5 filename labelling (defect D1)."""
    print("[can_vtc] *** WARNING: filename-derived labels (defect D1). "
          "Results from this path measure capture-session identification, "
          "NOT intrusion detection. Do not report them. ***")

    feat_blocks: List[np.ndarray] = []
    label_blocks: List[np.ndarray] = []
    group_blocks: List[np.ndarray] = []
    group_offset = 0

    for idx, cls in enumerate(LEGACY_CLASSES):
        path = root / f"cleaned_{cls}_dataset.csv"
        if not path.exists():
            print(f"[can_vtc] WARN missing {path.name}")
            continue
        can_ids, dlc, payload = _parse_can_log(path, max_rows_per_class)
        if len(can_ids) == 0:
            continue
        msg_labels = np.full(len(can_ids), idx, dtype=np.int64)
        X, y, g = windows_from_stream(
            can_ids, dlc, payload, window, stride,
            msg_labels=msg_labels, block_size=block_size,
            group_offset=group_offset,
        )
        group_offset += n_blocks_for(len(can_ids), block_size)
        print(f"[can_vtc] {cls}: {X.shape[0]:,} windows")
        feat_blocks.append(X)
        label_blocks.append(y)
        group_blocks.append(g)

    if not feat_blocks:
        raise RuntimeError(f"No CAN-VTC files found under {root}")

    return (np.concatenate(feat_blocks, axis=0),
            np.concatenate(label_blocks, axis=0),
            LEGACY_CLASSES,
            np.concatenate(group_blocks, axis=0))


def load_features_labels(
    root: Path,
    window: int,
    stride: int,
    max_rows_per_class: Optional[int] = None,
    block_size: int = DEFAULT_BLOCK_SIZE,
    include_unlabelled_captures: bool = False,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...], np.ndarray]:
    """Return ``(X (N,46), y (N,), classes, groups (N,))``.

    Args:
        include_unlabelled_captures: when True, reverts to the legacy 4-class
            filename labelling. Reproduction only — see module docstring.
    """
    if include_unlabelled_captures:
        return _load_legacy_file_labels(
            root, window, stride, max_rows_per_class, block_size)
    return _load_labelled(
        root, window, stride, max_rows_per_class, block_size)

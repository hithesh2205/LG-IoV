"""VeReMi dataset adapter.

VeReMi is a vehicular-network misbehaviour dataset of per-beacon kinematic
observations. After cleanup (Unnamed: 0 / any node-ID / RSSI removed), each
row carries 18 kinematic columns:

    type, rcvTime,
    pos_0, pos_1,           pos_noise_0, pos_noise_1,
    spd_0, spd_1,           spd_noise_0, spd_noise_1,
    acl_0, acl_1,           acl_noise_0, acl_noise_1,
    hed_0, hed_1,           hed_noise_0, hed_noise_1

plus labels:  attack (binary), attack_type (string).

To match the unified 46-feature contract of KANConvNet, we slide a length-W
window over the rows and produce summary statistics per window:

    slots  0..17  mean of each of the 18 kinematic columns
    slots 18..35  std  of each of the 18 kinematic columns
    slots 36..37  speed magnitude mean / std       sqrt(spd_0**2 + spd_1**2)
    slots 38..39  acceleration magnitude mean / std
    slots 40..41  position spread x / y            (max - min)
    slot  42      mean heading magnitude           sqrt(hed_0**2 + hed_1**2)
    slot  43      rcvTime delta mean
    slot  44      rcvTime delta std
    slot  45      fraction of rows with type == 3  (position broadcast)

Total = 18 + 18 + 10 = 46 ✓

Because the cleaned CSV is ~7 GB, we stream with ``pandas.read_csv``
chunksize. Windows are extracted within each chunk (slight loss at chunk
boundaries is negligible at W=64).
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


KINEMATIC_COLS: Tuple[str, ...] = (
    "type", "rcvTime",
    "pos_0", "pos_1", "pos_noise_0", "pos_noise_1",
    "spd_0", "spd_1", "spd_noise_0", "spd_noise_1",
    "acl_0", "acl_1", "acl_noise_0", "acl_noise_1",
    "hed_0", "hed_1", "hed_noise_0", "hed_noise_1",
)
assert len(KINEMATIC_COLS) == 18

LABEL_BIN_COL = "attack"
LABEL_MULTI_COL = "attack_type"


def _extract_windows(
    df: pd.DataFrame,
    window: int,
    stride: int,
    multi_class: bool,
    label_index: dict,
) -> Tuple[np.ndarray, np.ndarray]:
    """Slide W-windows over a chunk -> (N, 46), (N,) labels."""
    if len(df) < window:
        return np.zeros((0, 46), dtype=np.float32), np.zeros(0, dtype=np.int64)

    K = df[list(KINEMATIC_COLS)].to_numpy(dtype=np.float32)
    rcv = df["rcvTime"].to_numpy(dtype=np.float64)
    spd_x = df["spd_0"].to_numpy(dtype=np.float32)
    spd_y = df["spd_1"].to_numpy(dtype=np.float32)
    acl_x = df["acl_0"].to_numpy(dtype=np.float32)
    acl_y = df["acl_1"].to_numpy(dtype=np.float32)
    pos_x = df["pos_0"].to_numpy(dtype=np.float32)
    pos_y = df["pos_1"].to_numpy(dtype=np.float32)
    hed_x = df["hed_0"].to_numpy(dtype=np.float32)
    hed_y = df["hed_1"].to_numpy(dtype=np.float32)
    typ   = df["type"].to_numpy(dtype=np.int64)
    if multi_class:
        att = df[LABEL_MULTI_COL].astype(str).to_numpy()
    else:
        att = df[LABEL_BIN_COL].to_numpy(dtype=np.int64)

    rows: List[np.ndarray] = []
    labels: List[int] = []
    n = len(df)
    for start in range(0, n - window + 1, stride):
        end = start + window
        w_K = K[start:end]
        feat = np.empty(46, dtype=np.float32)
        feat[0:18] = w_K.mean(axis=0)
        feat[18:36] = w_K.std(axis=0)

        spd_mag = np.sqrt(spd_x[start:end] ** 2 + spd_y[start:end] ** 2)
        acl_mag = np.sqrt(acl_x[start:end] ** 2 + acl_y[start:end] ** 2)
        feat[36] = spd_mag.mean(); feat[37] = spd_mag.std()
        feat[38] = acl_mag.mean(); feat[39] = acl_mag.std()
        feat[40] = float(pos_x[start:end].max() - pos_x[start:end].min())
        feat[41] = float(pos_y[start:end].max() - pos_y[start:end].min())
        feat[42] = float(np.sqrt(hed_x[start:end] ** 2 + hed_y[start:end] ** 2).mean())

        rcv_d = np.diff(rcv[start:end])
        feat[43] = float(rcv_d.mean()) if len(rcv_d) else 0.0
        feat[44] = float(rcv_d.std())  if len(rcv_d) else 0.0
        feat[45] = float((typ[start:end] == 3).mean())

        rows.append(feat)

        if multi_class:
            vals, counts = np.unique(att[start:end], return_counts=True)
            dom = vals[counts.argmax()]
            if dom not in label_index:
                label_index[dom] = len(label_index)
            labels.append(label_index[dom])
        else:
            # Majority vote on attack flag.
            labels.append(int(att[start:end].mean() >= 0.5))

    if not rows:
        return np.zeros((0, 46), dtype=np.float32), np.zeros(0, dtype=np.int64)
    return np.stack(rows, axis=0), np.asarray(labels, dtype=np.int64)


def load_features_labels(
    root: Path,
    window: int = 64,
    stride: int = 16,
    max_rows_per_class: Optional[int] = None,
    multi_class: bool = False,
    chunksize: int = 1_000_000,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...]]:
    """Stream-read the cleaned VeReMi CSV → (X (N,46), y (N,), classes)."""
    csv_path = root / "cleaned_Veremi_final_dataset.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"missing {csv_path}")

    feat_blocks: List[np.ndarray] = []
    label_blocks: List[np.ndarray] = []
    label_index: dict = {}                      # multi-class label → int
    total_rows = 0
    cap = (max_rows_per_class * 5) if max_rows_per_class else None
    # ``max_rows_per_class`` is per-class for the CAN/CarHack adapters;
    # for VeReMi we use it as a soft row cap so smoke tests stay fast.

    print(f"[veremi] streaming {csv_path.name} (chunk={chunksize})")
    needed = list(KINEMATIC_COLS) + [LABEL_BIN_COL, LABEL_MULTI_COL]
    for chunk in pd.read_csv(csv_path, chunksize=chunksize,
                             usecols=needed, low_memory=False):
        chunk = chunk.dropna()
        Xc, yc = _extract_windows(chunk, window, stride, multi_class, label_index)
        if Xc.shape[0]:
            feat_blocks.append(Xc); label_blocks.append(yc)
        total_rows += len(chunk)
        if total_rows % (chunksize * 5) == 0 or (cap and total_rows >= cap):
            print(f"[veremi]   processed rows={total_rows:,}  windows={sum(b.shape[0] for b in feat_blocks):,}")
        if cap is not None and total_rows >= cap:
            break

    if not feat_blocks:
        raise RuntimeError("No VeReMi windows produced — check the CSV.")
    X = np.concatenate(feat_blocks, axis=0)
    y = np.concatenate(label_blocks, axis=0)

    if multi_class:
        classes = tuple(sorted(label_index, key=label_index.get))
    else:
        classes = ("BENIGN", "ATTACK")
    print(f"[veremi] windows={X.shape[0]:,}  classes={classes}")
    return X, y, classes

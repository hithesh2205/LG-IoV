"""CICIDS-2017 dataset adapter.

Each row in ``CICIDS_pro/CICIDS_pro/cleaned_*.csv`` is already a flow-level
feature vector (78 numeric columns + 1 label column after Destination Port
was removed). To match KANConvNet's 46-input contract we **select 46
columns** that are stable across all eight files and span the major
feature families (durations, packet counts, lengths, IATs, header sizes,
flag counts, rate stats). Any rows containing inf/NaN are dropped.

Labels — the CICIDS-2017 ``Label`` column has many values
(BENIGN, DDoS, PortScan, FTP-Patator, etc.). We expose two modes:

* ``multi_class=True``  → integer label per unique attack family.
* ``multi_class=False`` → binary {0=BENIGN, 1=attack}  (default).

Each row is already an independent flow record with its own label, so this
adapter has never suffered the window-overlap leakage of the CAN adapters
(defect D2). It still emits ``groups`` — contiguous row blocks, kept disjoint
across source files — so that the group-aware splitter in ``preprocess.py``
treats every dataset identically, and so that flows captured back-to-back in
one session cannot straddle the train/test boundary.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# 46 columns selected from the 78 cleaned-CICIDS features.
SELECTED_COLUMNS_46: Tuple[str, ...] = (
    " Flow Duration",
    " Total Fwd Packets",
    " Total Backward Packets",
    "Total Length of Fwd Packets",
    " Total Length of Bwd Packets",
    " Fwd Packet Length Max",
    " Fwd Packet Length Min",
    " Fwd Packet Length Mean",
    " Fwd Packet Length Std",
    "Bwd Packet Length Max",
    " Bwd Packet Length Min",
    " Bwd Packet Length Mean",
    " Bwd Packet Length Std",
    "Flow Bytes/s",
    " Flow Packets/s",
    " Flow IAT Mean",
    " Flow IAT Std",
    " Flow IAT Max",
    " Flow IAT Min",
    "Fwd IAT Total",
    " Fwd IAT Mean",
    " Fwd IAT Std",
    " Fwd IAT Max",
    " Fwd IAT Min",
    "Bwd IAT Total",
    " Bwd IAT Mean",
    " Bwd IAT Std",
    " Bwd IAT Max",
    " Bwd IAT Min",
    " Fwd Header Length",
    " Bwd Header Length",
    "Fwd Packets/s",
    " Bwd Packets/s",
    " Min Packet Length",
    " Max Packet Length",
    " Packet Length Mean",
    " Packet Length Std",
    " Packet Length Variance",
    "FIN Flag Count",
    " SYN Flag Count",
    " RST Flag Count",
    " PSH Flag Count",
    " ACK Flag Count",
    " URG Flag Count",
    " Down/Up Ratio",
    " Average Packet Size",
)
assert len(SELECTED_COLUMNS_46) == 46, len(SELECTED_COLUMNS_46)

LABEL_COL = " Label"

#: Flow records per contiguous split block.
DEFAULT_BLOCK_ROWS = 20_000


def _load_one(path: Path, max_rows: Optional[int]) -> pd.DataFrame:
    df = pd.read_csv(path, nrows=max_rows, low_memory=False)
    # Some CICIDS dumps use stripped header names — accept either.
    if LABEL_COL not in df.columns and "Label" in df.columns:
        df = df.rename(columns={"Label": LABEL_COL})
    # Replace inf with NaN and drop bad rows.
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def load_features_labels(
    root: Path,
    max_rows_per_file: Optional[int] = None,
    multi_class: bool = False,
    block_rows: int = DEFAULT_BLOCK_ROWS,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...], np.ndarray]:
    """Return ``(X (N,46), y (N,), classes, groups (N,))``."""
    feature_blocks: List[np.ndarray] = []
    label_strings: List[np.ndarray] = []
    group_blocks: List[np.ndarray] = []
    group_offset = 0

    files = sorted(root.glob("cleaned_*.csv"))
    if not files:
        raise RuntimeError(f"No CICIDS files under {root}")

    for path in files:
        print(f"[cicids] reading {path.name}")
        df = _load_one(path, max_rows_per_file)
        missing = [c for c in SELECTED_COLUMNS_46 if c not in df.columns]
        if missing:
            raise RuntimeError(
                f"{path.name} is missing {len(missing)} expected columns "
                f"(e.g. {missing[:3]}). Schema drift — check the cleanup script."
            )
        sub = df[list(SELECTED_COLUMNS_46) + [LABEL_COL]].copy()
        sub = sub.dropna()
        feats = sub[list(SELECTED_COLUMNS_46)].to_numpy(dtype=np.float32)
        labs = sub[LABEL_COL].astype(str).to_numpy()

        n = feats.shape[0]
        groups = (np.arange(n) // block_rows).astype(np.int64) + group_offset
        group_offset += max(1, int(np.ceil(n / block_rows)))

        feature_blocks.append(feats)
        label_strings.append(labs)
        group_blocks.append(groups)
        print(f"[cicids]   rows kept: {n:,}  blocks: {len(np.unique(groups)):,}")

    X = np.concatenate(feature_blocks, axis=0)
    labs_all = np.concatenate(label_strings, axis=0)
    g = np.concatenate(group_blocks, axis=0)

    if multi_class:
        classes_unique = sorted(set(labs_all.tolist()))
        idx_map: Dict[str, int] = {c: i for i, c in enumerate(classes_unique)}
        y = np.asarray([idx_map[l] for l in labs_all], dtype=np.int64)
        classes = tuple(classes_unique)
    else:
        y = np.asarray([0 if l.strip().upper() == "BENIGN" else 1
                        for l in labs_all], dtype=np.int64)
        classes = ("BENIGN", "ATTACK")

    return X, y, classes, g

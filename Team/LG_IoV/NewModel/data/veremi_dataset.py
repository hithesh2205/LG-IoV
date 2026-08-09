"""VeReMi dataset adapter — per-beacon plausibility features.

VeReMi is a V2X *misbehaviour* dataset: each row is one BSM (basic safety
message) beacon as received, carrying the sender's claimed kinematics plus the
receiver's noise estimate, and a per-row ground-truth label.

Cleaned columns (20)::

    type, rcvTime,
    pos_0, pos_1,   pos_noise_0, pos_noise_1,
    spd_0, spd_1,   spd_noise_0, spd_noise_1,
    acl_0, acl_1,   acl_noise_0, acl_noise_1,
    hed_0, hed_1,   hed_noise_0, hed_noise_1,
    attack, attack_type

Why the previous windowed formulation failed (defect D5)
--------------------------------------------------------
The earlier adapter slid a 64-row window over *consecutive CSV rows* and took
mean/std, then labelled the window by majority vote. Measured facts:

* The cleaned file carries **no sender/node identifier** — it was dropped during
  cleaning. Consecutive rows are beacons from many different senders, so the
  per-window mean/std averaged kinematics across unrelated vehicles and
  destroyed the very signal misbehaviour detection depends on.
* ``rcvTime`` is **not** monotonic (25202 → 54198 with reversals), confirming the
  file is a concatenation of per-receiver logs rather than one ordered stream.
* ``attack`` is **45.3 %** of rows (1,094,690 benign vs 905,310 attack in a 2 M
  sample) and the 19 attack types are near-uniformly distributed. With attack
  rows interleaved at that density, a 64-row majority vote is close to a coin
  flip — which is exactly the ROC-AUC 0.525 the old pipeline reported.

The label was noise. The model was fine.

Current formulation — and its measured ceiling
----------------------------------------------
Because every row already carries its own label and its own kinematics, VeReMi
is loaded as a **per-beacon** classification problem. Each row is mapped to a
46-D vector of physical *plausibility* descriptors — magnitudes, noise-to-signal
ratios, and internal-consistency terms (heading vs velocity, velocity vs
acceleration, heading unit-norm deviation). These are the quantities a real
V2X misbehaviour detector reasons about.

**This formulation is well-posed but has a low ceiling, and the reason is
fundamental.** Measured over a 200k-row sample:

* best single-feature class separation: **0.046 standard deviations**
* best single-feature threshold accuracy: **0.545**, against a 0.547 majority
  baseline

In other words, an attacking beacon and a benign beacon are nearly
indistinguishable *in isolation*. That is expected once you look at what the 19
VeReMi attack types actually are: ConstPos, ConstPosOffset, RandomPos,
ConstSpeed, EventualStop, DataReplay, DelayedMessages and so on are all defined
by how a sender's claimed state evolves **over time**. A constant-position
attacker's individual beacon reports a perfectly plausible position; only the
fact that it never changes gives it away. Single-beacon features cannot express
"never changes".

Detecting these requires comparing one sender's *sequence* of claims against
physics — which requires the sender identifier that was dropped during cleaning.
So the cleaned export supports neither formulation properly:

* windowing across rows mixes senders and destroys the label (the Month-4 failure)
* per-beacon keeps the label honest but discards the temporal signal the task needs

**Conclusion: VeReMi results from this export should be read as a lower bound,
close to chance, and the dataset must be re-acquired with sender IDs to be
usable.** The per-beacon path is retained because it is at least well-posed and
because it exercises the federated pipeline end to end on a fourth data source.

``rcvTime`` is deliberately **excluded** as a feature: it is an absolute
simulation timestamp that correlates with which scenario file a row came from,
and would act as a leakage channel.

Splitting still uses contiguous row blocks (``groups``) so that near-duplicate
beacons from one trajectory cannot straddle the train/test boundary.

Sender-aware windowing
----------------------
If a re-acquired VeReMi export includes a sender column (any of
``SENDER_ID_CANDIDATES``), ``mode="windowed"`` groups by sender, sorts by
``rcvTime`` and windows *within* each sender's stream — the formulation that
should be used once the raw dataset is recovered. It raises rather than silently
mixing senders if no such column is present.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


KINEMATIC_COLS: Tuple[str, ...] = (
    "type",
    "pos_0", "pos_1", "pos_noise_0", "pos_noise_1",
    "spd_0", "spd_1", "spd_noise_0", "spd_noise_1",
    "acl_0", "acl_1", "acl_noise_0", "acl_noise_1",
    "hed_0", "hed_1", "hed_noise_0", "hed_noise_1",
)

LABEL_BIN_COL = "attack"
LABEL_MULTI_COL = "attack_type"

#: Column names that would carry a sender identity in a re-acquired export.
SENDER_ID_CANDIDATES: Tuple[str, ...] = (
    "sender", "senderId", "sender_id", "node", "nodeId", "node_id", "pseudo",
)

#: Rows per contiguous split block.
DEFAULT_BLOCK_ROWS = 50_000

#: Plausible upper bound on vehicle speed (m/s) used to scale one feature.
_MAX_PLAUSIBLE_SPEED = 40.0

_EPS = 1e-6


def _per_row_features(df: pd.DataFrame) -> np.ndarray:
    """Map each beacon row to a 46-D plausibility vector.

     0      type
     1..16  the 16 kinematic / noise components
    17..20  magnitudes: pos, spd, acl, hed
    21..24  noise magnitudes: pos, spd, acl, hed
    25..28  noise-to-signal ratios
    29      cos angle between heading and velocity
    30      |‖hed‖ − 1|          (heading should be a unit vector)
    31      cos angle between velocity and acceleration
    32..35  signs of spd_0, spd_1, acl_0, acl_1
    36..39  log1p magnitudes
    40..43  per-axis position/speed noise ratios
    44      type == 3 indicator
    45      speed / plausible max
    """
    n = len(df)
    f = np.zeros((n, 46), dtype=np.float32)

    typ = df["type"].to_numpy(dtype=np.float32)
    px = df["pos_0"].to_numpy(dtype=np.float32)
    py = df["pos_1"].to_numpy(dtype=np.float32)
    pnx = df["pos_noise_0"].to_numpy(dtype=np.float32)
    pny = df["pos_noise_1"].to_numpy(dtype=np.float32)
    sx = df["spd_0"].to_numpy(dtype=np.float32)
    sy = df["spd_1"].to_numpy(dtype=np.float32)
    snx = df["spd_noise_0"].to_numpy(dtype=np.float32)
    sny = df["spd_noise_1"].to_numpy(dtype=np.float32)
    ax = df["acl_0"].to_numpy(dtype=np.float32)
    ay = df["acl_1"].to_numpy(dtype=np.float32)
    anx = df["acl_noise_0"].to_numpy(dtype=np.float32)
    any_ = df["acl_noise_1"].to_numpy(dtype=np.float32)
    hx = df["hed_0"].to_numpy(dtype=np.float32)
    hy = df["hed_1"].to_numpy(dtype=np.float32)
    hnx = df["hed_noise_0"].to_numpy(dtype=np.float32)
    hny = df["hed_noise_1"].to_numpy(dtype=np.float32)

    f[:, 0] = typ
    f[:, 1] = px;  f[:, 2] = py;  f[:, 3] = pnx; f[:, 4] = pny
    f[:, 5] = sx;  f[:, 6] = sy;  f[:, 7] = snx; f[:, 8] = sny
    f[:, 9] = ax;  f[:, 10] = ay; f[:, 11] = anx; f[:, 12] = any_
    f[:, 13] = hx; f[:, 14] = hy; f[:, 15] = hnx; f[:, 16] = hny

    pos_mag = np.sqrt(px ** 2 + py ** 2)
    spd_mag = np.sqrt(sx ** 2 + sy ** 2)
    acl_mag = np.sqrt(ax ** 2 + ay ** 2)
    hed_mag = np.sqrt(hx ** 2 + hy ** 2)
    f[:, 17] = pos_mag; f[:, 18] = spd_mag
    f[:, 19] = acl_mag; f[:, 20] = hed_mag

    pn_mag = np.sqrt(pnx ** 2 + pny ** 2)
    sn_mag = np.sqrt(snx ** 2 + sny ** 2)
    an_mag = np.sqrt(anx ** 2 + any_ ** 2)
    hn_mag = np.sqrt(hnx ** 2 + hny ** 2)
    f[:, 21] = pn_mag; f[:, 22] = sn_mag
    f[:, 23] = an_mag; f[:, 24] = hn_mag

    f[:, 25] = pn_mag / (pos_mag + _EPS)
    f[:, 26] = sn_mag / (spd_mag + _EPS)
    f[:, 27] = an_mag / (acl_mag + _EPS)
    f[:, 28] = hn_mag / (hed_mag + _EPS)

    # Heading should point along the velocity vector for a genuine vehicle.
    f[:, 29] = (hx * sx + hy * sy) / ((hed_mag * spd_mag) + _EPS)
    # A genuine heading is a unit vector; spoofed ones often are not.
    f[:, 30] = np.abs(hed_mag - 1.0)
    # Acceleration should be consistent with the velocity it produces.
    f[:, 31] = (sx * ax + sy * ay) / ((spd_mag * acl_mag) + _EPS)

    f[:, 32] = np.sign(sx); f[:, 33] = np.sign(sy)
    f[:, 34] = np.sign(ax); f[:, 35] = np.sign(ay)

    f[:, 36] = np.log1p(np.abs(px))
    f[:, 37] = np.log1p(np.abs(py))
    f[:, 38] = np.log1p(spd_mag)
    f[:, 39] = np.log1p(acl_mag)

    f[:, 40] = np.abs(pnx) / (np.abs(px) + _EPS)
    f[:, 41] = np.abs(pny) / (np.abs(py) + _EPS)
    f[:, 42] = np.abs(snx) / (np.abs(sx) + _EPS)
    f[:, 43] = np.abs(sny) / (np.abs(sy) + _EPS)

    f[:, 44] = (typ == 3).astype(np.float32)
    f[:, 45] = spd_mag / _MAX_PLAUSIBLE_SPEED

    return np.nan_to_num(f, nan=0.0, posinf=0.0, neginf=0.0)


def _find_sender_column(columns) -> Optional[str]:
    for cand in SENDER_ID_CANDIDATES:
        if cand in columns:
            return cand
    return None


def load_features_labels(
    root: Path,
    window: int = 64,
    stride: int = 16,
    max_rows_per_class: Optional[int] = None,
    multi_class: bool = False,
    chunksize: int = 1_000_000,
    mode: str = "per_row",
    block_rows: int = DEFAULT_BLOCK_ROWS,
    max_rows: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...], np.ndarray]:
    """Stream-read the cleaned VeReMi CSV → ``(X (N,46), y (N,), classes, groups)``.

    Args:
        mode: ``"per_row"`` (default, correct for the current cleaned export) or
            ``"windowed"`` (requires a sender column; raises without one).
        multi_class: use the 19-way ``attack_type`` instead of binary ``attack``.
        max_rows: hard cap on rows read, for fast experiment turnaround.
    """
    csv_path = root / "cleaned_Veremi_final_dataset.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"missing {csv_path}")

    header = pd.read_csv(csv_path, nrows=1)
    sender_col = _find_sender_column(header.columns)

    if mode == "windowed" and sender_col is None:
        raise RuntimeError(
            "mode='windowed' needs a sender identifier column (one of "
            f"{SENDER_ID_CANDIDATES}) so beacons can be grouped per sender. "
            "The cleaned export has none — it was dropped during cleaning. "
            "Re-acquire raw VeReMi to use this mode, or use mode='per_row'."
        )
    if mode not in ("per_row", "windowed"):
        raise ValueError(f"unknown mode {mode!r}")

    needed = list(KINEMATIC_COLS) + [LABEL_BIN_COL, LABEL_MULTI_COL]
    if sender_col:
        needed.append(sender_col)
    if mode == "windowed":
        needed.append("rcvTime")

    feat_blocks: List[np.ndarray] = []
    label_blocks: List[np.ndarray] = []
    group_blocks: List[np.ndarray] = []
    label_index: dict = {}
    total_rows = 0
    rows_emitted = 0

    cap = max_rows
    if cap is None and max_rows_per_class is not None:
        cap = max_rows_per_class * 5

    print(f"[veremi] streaming {csv_path.name} "
          f"(mode={mode}, chunk={chunksize:,}, cap={cap})")

    for chunk in pd.read_csv(csv_path, chunksize=chunksize,
                             usecols=needed, low_memory=False):
        chunk = chunk.dropna()
        if len(chunk) == 0:
            continue

        if mode == "windowed":
            Xc, yc, gc = _windowed_by_sender(
                chunk, sender_col, window, stride, multi_class,
                label_index, rows_emitted)
        else:
            Xc = _per_row_features(chunk)
            if multi_class:
                vals = chunk[LABEL_MULTI_COL].astype(str).to_numpy()
                yc = np.empty(len(vals), dtype=np.int64)
                for i, v in enumerate(vals):
                    if v not in label_index:
                        label_index[v] = len(label_index)
                    yc[i] = label_index[v]
            else:
                yc = chunk[LABEL_BIN_COL].to_numpy(dtype=np.int64)
            gc = ((np.arange(len(chunk)) + rows_emitted) // block_rows
                  ).astype(np.int64)

        if Xc.shape[0]:
            feat_blocks.append(Xc)
            label_blocks.append(yc)
            group_blocks.append(gc)
            rows_emitted += len(chunk)

        total_rows += len(chunk)
        if cap is not None and total_rows >= cap:
            break

    if not feat_blocks:
        raise RuntimeError("No VeReMi samples produced — check the CSV.")

    X = np.concatenate(feat_blocks, axis=0)
    y = np.concatenate(label_blocks, axis=0)
    g = np.concatenate(group_blocks, axis=0)

    if multi_class:
        classes = tuple(sorted(label_index, key=label_index.get))
    else:
        classes = ("BENIGN", "ATTACK")

    n_atk = int((y > 0).sum())
    print(f"[veremi] rows={total_rows:,} → samples={X.shape[0]:,} "
          f"(attack={n_atk:,} / {100 * n_atk / max(len(y), 1):.1f}%) "
          f"blocks={len(np.unique(g)):,} classes={len(classes)}")
    if mode == "per_row":
        print("[veremi] NOTE: per-beacon mode. VeReMi's attack types (ConstPos, "
              "ConstSpeed, DataReplay, EventualStop, ...) are defined by how a "
              "sender's claims evolve OVER TIME, which a single beacon cannot "
              "express — measured best single-feature separation is 0.046 sigma. "
              "Treat results as a near-chance lower bound. The cleaned export "
              "has no sender ID; re-acquire raw VeReMi and use mode='windowed'.")
    return X, y, classes, g


def _windowed_by_sender(
    chunk: pd.DataFrame,
    sender_col: str,
    window: int,
    stride: int,
    multi_class: bool,
    label_index: dict,
    group_offset: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Window strictly within one sender's time-ordered beacon stream.

    Only reachable when a sender column exists (re-acquired raw VeReMi).
    """
    rows: List[np.ndarray] = []
    labels: List[int] = []
    groups: List[int] = []

    for gi, (_, grp) in enumerate(chunk.groupby(sender_col, sort=False)):
        grp = grp.sort_values("rcvTime")
        if len(grp) < window:
            continue
        feats = _per_row_features(grp)
        if multi_class:
            raw = grp[LABEL_MULTI_COL].astype(str).to_numpy()
        else:
            raw = grp[LABEL_BIN_COL].to_numpy(dtype=np.int64)

        for start in range(0, len(grp) - window + 1, stride):
            end = start + window
            # Aggregate one sender's own beacons — never across senders.
            w = feats[start:end]
            rows.append(np.concatenate([
                w.mean(axis=0)[:23], w.std(axis=0)[:23],
            ])[:46].astype(np.float32))
            if multi_class:
                vals, counts = np.unique(raw[start:end], return_counts=True)
                dom = vals[counts.argmax()]
                if dom not in label_index:
                    label_index[dom] = len(label_index)
                labels.append(label_index[dom])
            else:
                # Any injected beacon in the sender's window marks it.
                labels.append(int(raw[start:end].max()))
            groups.append(group_offset + gi)

    if not rows:
        return (np.zeros((0, 46), dtype=np.float32),
                np.zeros(0, dtype=np.int64),
                np.zeros(0, dtype=np.int64))
    return (np.stack(rows, axis=0),
            np.asarray(labels, dtype=np.int64),
            np.asarray(groups, dtype=np.int64))

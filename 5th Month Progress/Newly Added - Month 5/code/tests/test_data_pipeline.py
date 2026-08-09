"""Verification tests for the Month-5 data-layer fixes (defects D1, D2, D5).

Run from the NewModel directory::

    python tests/test_data_pipeline.py

These are assertions about *correctness of the experimental setup*, not model
quality. If any of them fail, every accuracy number produced by the pipeline is
meaningless, so they run before any training.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.can_features import windows_from_stream            # noqa: E402
from data.preprocess import (                                 # noqa: E402
    PreprocessingPipeline, assert_no_group_overlap,
)

DATA_ROOT = ROOT.parent / "Preprocessed_Dataset"

_failures: list = []
_passes: list = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        _passes.append(name)
        print(f"  PASS  {name}")
    else:
        _failures.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


# ── D2: windows must never cross a block boundary ────────────────────────
def test_window_block_containment() -> None:
    print("\n[test] D2 — window/block containment")
    rng = np.random.default_rng(0)
    n = 1000
    can_ids = rng.integers(0, 500, size=n).astype(np.int64)
    dlc = np.full(n, 8, dtype=np.float32)
    payload = rng.random((n, 8)).astype(np.float32)
    msg_labels = np.zeros(n, dtype=np.int64)
    msg_labels[600:650] = 1          # one injected burst

    window, stride, block = 64, 16, 200
    X, y, g = windows_from_stream(
        can_ids, dlc, payload, window, stride,
        msg_labels=msg_labels, block_size=block,
    )

    check("emits windows", X.shape[0] > 0, f"got {X.shape[0]}")
    check("feature width is 46", X.shape[1] == 46, f"got {X.shape[1]}")
    check("labels align with windows", y.shape[0] == X.shape[0])
    check("groups align with windows", g.shape[0] == X.shape[0])

    # Every window must lie inside exactly one block.
    n_blocks = int(np.ceil(n / block))
    ok = True
    for b in range(n_blocks):
        b_start, b_end = b * block, min(n, (b + 1) * block)
        idx = np.where(g == b)[0]
        if len(idx) == 0:
            continue
        # Reconstruct each window's span from its position within the block.
        starts = [b_start + k * stride for k in range(len(idx))]
        if starts and (starts[-1] + window) > b_end:
            ok = False
    check("no window crosses a block boundary", ok)

    # The burst at 600:650 sits in block 3 (600-800): that block must contain
    # attack windows, and blocks with no injected message must be all-normal.
    check("injected burst produces attack windows", int((y > 0).sum()) > 0,
          f"attack windows={int((y > 0).sum())}")
    clean_blocks = [b for b in range(n_blocks)
                    if msg_labels[b * block:min(n, (b + 1) * block)].sum() == 0]
    clean_ok = all(int(y[g == b].max(initial=0)) == 0 for b in clean_blocks)
    check("blocks with no injection yield only normal windows", clean_ok)


# ── D1: per-message labelling produces mixed classes per capture ─────────
def test_car_hack_per_message_labels() -> None:
    print("\n[test] D1 — Car-Hacking per-message labels")
    root = DATA_ROOT / "Car_hack_pro" / "Car_hack_pro"
    if not root.is_dir():
        print(f"  SKIP  dataset not present at {root}")
        return

    from data.car_hack_dataset import load_features_labels
    X, y, classes, g = load_features_labels(
        root, window=64, stride=16, max_rows_per_class=120_000)

    check("46 features", X.shape[1] == 46, f"got {X.shape[1]}")
    check("5 classes declared", len(classes) == 5, f"got {classes}")
    present = sorted(set(y.tolist()))
    check("normal class present", 0 in present, f"present={present}")
    check("at least one attack class present", any(c > 0 for c in present),
          f"present={present}")
    # The decisive D1 check: attack captures must yield BOTH normal and attack
    # windows. Under filename labelling every window in a capture had one label.
    n_norm, n_atk = int((y == 0).sum()), int((y > 0).sum())
    check("both normal and attack windows exist", n_norm > 0 and n_atk > 0,
          f"normal={n_norm} attack={n_atk}")
    check("attack windows are not the whole dataset",
          0.01 < n_atk / len(y) < 0.99,
          f"attack fraction={n_atk / len(y):.3f}")


def test_can_vtc_signature_labels() -> None:
    print("\n[test] D1 — CAN-VTC signature labels")
    root = DATA_ROOT / "Can_vtc_pro"
    if not root.is_dir():
        print(f"  SKIP  dataset not present at {root}")
        return

    from data.can_vtc_dataset import load_features_labels
    X, y, classes, g = load_features_labels(
        root, window=64, stride=16, max_rows_per_class=120_000)

    check("46 features", X.shape[1] == 46, f"got {X.shape[1]}")
    check("2 classes (normal, DoS)", len(classes) == 2, f"got {classes}")
    n_norm, n_atk = int((y == 0).sum()), int((y > 0).sum())
    check("both normal and DoS windows exist", n_norm > 0 and n_atk > 0,
          f"normal={n_norm} attack={n_atk}")


# ── D5: VeReMi per-row labelling must preserve the row-level balance ─────
def test_veremi_per_row() -> None:
    print("\n[test] D5 — VeReMi per-beacon features")
    root = DATA_ROOT / "VeReMi_pro"
    if not root.is_dir():
        print(f"  SKIP  dataset not present at {root}")
        return

    from data.veremi_dataset import load_features_labels
    X, y, classes, g = load_features_labels(
        root, max_rows=200_000, chunksize=100_000)

    check("46 features", X.shape[1] == 46, f"got {X.shape[1]}")
    check("one sample per beacon row", X.shape[0] == y.shape[0])
    frac = float((y > 0).mean())
    # Row-level attack share is ~45%; the old windowed majority vote destroyed
    # this. Anything in a sane band proves the label survived.
    check("attack share is realistic (0.2-0.8)", 0.2 < frac < 0.8,
          f"attack fraction={frac:.3f}")
    check("features are finite", bool(np.isfinite(X).all()))
    check("multiple blocks produced", len(np.unique(g)) > 1,
          f"blocks={len(np.unique(g))}")


# ── D2 end-to-end: the split must not share blocks ───────────────────────
def test_split_has_no_group_leakage() -> None:
    print("\n[test] D2 — end-to-end split group disjointness")
    root = DATA_ROOT / "Car_hack_pro" / "Car_hack_pro"
    if not root.is_dir():
        print(f"  SKIP  dataset not present at {root}")
        return

    pipe = PreprocessingPipeline(seed=2025)
    split = pipe.fit_transform(
        "car_hack", DATA_ROOT, window=64, stride=16,
        max_rows_per_class=120_000)

    n_tr = split["X_train"].shape[0]
    n_va = split["X_val"].shape[0]
    n_te = split["X_test"].shape[0]
    check("all three splits non-empty", n_tr > 0 and n_va > 0 and n_te > 0,
          f"train={n_tr} val={n_va} test={n_te}")
    check("train is the largest split", n_tr > n_va and n_tr > n_te)
    check("test split classes seen in train",
          set(split["y_test"].tolist()).issubset(set(split["y_train"].tolist())),
          f"train={sorted(set(split['y_train'].tolist()))} "
          f"test={sorted(set(split['y_test'].tolist()))}")

    # assert_no_group_overlap already ran inside fit_transform; prove it bites.
    groups = np.array([0, 0, 1, 1, 2, 2])
    try:
        assert_no_group_overlap(groups, np.array([0, 2]), np.array([3]), np.array([4]))
        check("overlap detector rejects shared blocks", False,
              "expected AssertionError for block 1 in train+val")
    except AssertionError:
        check("overlap detector rejects shared blocks", True)


def main() -> int:
    print("=" * 68)
    print("Month-5 data pipeline verification")
    print("=" * 68)
    test_window_block_containment()
    test_car_hack_per_message_labels()
    test_can_vtc_signature_labels()
    test_veremi_per_row()
    test_split_has_no_group_leakage()

    print("\n" + "=" * 68)
    print(f"{len(_passes)} passed, {len(_failures)} failed")
    for name, detail in _failures:
        print(f"  FAILED: {name}  {detail}")
    print("=" * 68)
    return 1 if _failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

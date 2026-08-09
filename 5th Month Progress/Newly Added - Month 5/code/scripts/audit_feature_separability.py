"""Measure how separable each dataset's classes are in feature space.

    python scripts/audit_feature_separability.py [dataset ...]

Two things this catches, both of which bit this project:

1. **A giveaway feature.** If one feature alone nearly solves the task, that is
   usually leakage, not learning. This is what a filename-derived label looks
   like from the inside.
2. **A task the features cannot express.** If *no* feature separates the classes
   at all, the model is not at fault — the formulation is. VeReMi is exactly this
   case: its attack types are defined by how a sender's claims evolve over time,
   which a single beacon cannot represent.

Run it before trusting any accuracy number from a new dataset or a new
feature set.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_ROOT = ROOT.parent / "Preprocessed_Dataset"
RESULTS = ROOT / "results"

CAPS = {
    "can_vtc": dict(max_rows_per_class=200_000),
    "car_hack": dict(max_rows_per_class=200_000),
    "cicids": dict(max_rows_per_file=100_000),
    "veremi": dict(max_rows=200_000),
}


def load(name):
    if name == "can_vtc":
        from data.can_vtc_dataset import load_features_labels as f
        return f(DATA_ROOT / "Can_vtc_pro", 64, 16, **CAPS[name])
    if name == "car_hack":
        from data.car_hack_dataset import load_features_labels as f
        return f(DATA_ROOT / "Car_hack_pro" / "Car_hack_pro", 64, 16, **CAPS[name])
    if name == "cicids":
        from data.cicids_dataset import load_features_labels as f
        return f(DATA_ROOT / "CICIDS_pro" / "CICIDS_pro", **CAPS[name])
    if name == "veremi":
        from data.veremi_dataset import load_features_labels as f
        return f(DATA_ROOT / "VeReMi_pro", chunksize=100_000, **CAPS[name])
    raise ValueError(name)


def analyse(name: str) -> dict:
    print(f"\n{'=' * 66}\n{name}\n{'=' * 66}")
    X, y, classes, g = load(name)
    binary = (y > 0).astype(int)
    base = max(binary.mean(), 1 - binary.mean())
    print(f"samples={X.shape[0]:,}  classes={classes}  "
          f"attack share={binary.mean():.3f}  majority baseline={base:.3f}")

    # Standardised mean difference per feature (attack vs benign).
    seps = []
    for j in range(X.shape[1]):
        a, b = X[binary == 1, j], X[binary == 0, j]
        if a.size == 0 or b.size == 0:
            seps.append(0.0)
            continue
        sd = np.sqrt(0.5 * (a.var() + b.var())) + 1e-12
        seps.append(abs(a.mean() - b.mean()) / sd)
    seps = np.asarray(seps)
    order = np.argsort(seps)[::-1]

    print("\ntop separations (standardised mean difference):")
    for j in order[:6]:
        print(f"    feature {j:>2}   {seps[j]:.3f}")

    # Best single-feature threshold accuracy.
    best_acc, best_j = 0.0, -1
    for j in order[:15]:
        v = X[:, j]
        for q in np.quantile(v, [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]):
            for acc in (((v > q) == binary).mean(), ((v <= q) == binary).mean()):
                if acc > best_acc:
                    best_acc, best_j = float(acc), int(j)

    lift = best_acc - base
    if best_acc > 0.95:
        verdict = "SUSPICIOUS - one feature nearly solves it; check for leakage"
    elif lift < 0.02:
        verdict = "WEAK - features barely separate the classes; check the formulation"
    else:
        verdict = "OK - real but non-trivial signal"

    print(f"\nbest single-feature accuracy = {best_acc:.3f} (feature {best_j})")
    print(f"majority baseline            = {base:.3f}")
    print(f"lift over baseline           = {lift:+.3f}")
    print(f"verdict: {verdict}")

    return {
        "dataset": name,
        "n_samples": int(X.shape[0]),
        "n_classes": len(classes),
        "attack_share": float(binary.mean()),
        "majority_baseline": float(base),
        "max_separation_sigma": float(seps.max()),
        "mean_separation_sigma": float(seps.mean()),
        "best_single_feature_accuracy": best_acc,
        "best_single_feature_index": best_j,
        "lift_over_baseline": float(lift),
        "verdict": verdict,
    }


def main() -> int:
    names = sys.argv[1:] or ["can_vtc", "car_hack", "cicids", "veremi"]
    out = []
    for n in names:
        try:
            out.append(analyse(n))
        except Exception as exc:
            print(f"  !! {n} failed: {type(exc).__name__}: {exc}")
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / "feature_separability.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nsaved {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Assemble the FL-noFHE vs FL-FHE comparison table from fresh training summaries
plus the real TenSEAL CKKS overhead benchmark, and write a single JSON + printed
report that the pptx slide builder and the write-up both read from.
"""
from __future__ import annotations

import json
from pathlib import Path

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"
DATASETS = ["can_vtc", "car_hack", "cicids", "veremi"]


def load(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    bench = load(CHECKPOINT_DIR / "real_ckks_benchmark.json") or []
    bench_by_ds = {b["dataset"]: b for b in bench}

    rows = []
    for ds in DATASETS:
        nofhe = load(CHECKPOINT_DIR / f"federated_summary_{ds}_nofhe.json")
        fhe = load(CHECKPOINT_DIR / f"federated_summary_{ds}_fhe.json")
        b = bench_by_ds.get(ds)
        if nofhe is None or fhe is None:
            print(f"[skip] {ds}: missing nofhe={nofhe is None} fhe={fhe is None}")
            continue
        rows.append({
            "dataset": ds,
            "parameters": fhe["parameters"],
            "nofhe_accuracy": nofhe["test_accuracy"],
            "fhe_accuracy": fhe["test_accuracy"],
            "accuracy_delta": fhe["test_accuracy"] - nofhe["test_accuracy"],
            "nofhe_macro_f1": nofhe["test_macro_f1"],
            "fhe_macro_f1": fhe["test_macro_f1"],
            "nofhe_roc_auc": nofhe["test_roc_auc"],
            "fhe_roc_auc": fhe["test_roc_auc"],
            "nofhe_time_sec": nofhe["training_time_sec"],
            "fhe_time_sec": fhe["training_time_sec"],
            "real_ckks_round_overhead_sec": b["real_fhe_round_overhead_sec"] if b else None,
            "real_ckks_ciphertext_expansion": b["ciphertext_expansion_factor"] if b else None,
            "real_ckks_max_abs_error": b["max_abs_error_vs_plaintext_fedavg"] if b else None,
        })

    out_path = CHECKPOINT_DIR / "comparison_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    print(f"\n{'Dataset':<10} {'noFHE Acc':>10} {'FHE Acc':>10} {'Delta':>9} {'noFHE F1':>10} {'FHE F1':>10} {'Real CKKS/round':>16}")
    for r in rows:
        overhead = f"{r['real_ckks_round_overhead_sec']*1000:.0f} ms" if r["real_ckks_round_overhead_sec"] else "n/a"
        print(f"{r['dataset']:<10} {r['nofhe_accuracy']*100:>9.2f}% {r['fhe_accuracy']*100:>9.2f}% {r['accuracy_delta']*100:>+8.3f}% {r['nofhe_macro_f1']:>10.4f} {r['fhe_macro_f1']:>10.4f} {overhead:>16}")

    print(f"\n[build_comparison] Wrote {out_path} ({len(rows)}/{len(DATASETS)} datasets)")


if __name__ == "__main__":
    main()

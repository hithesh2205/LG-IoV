"""Reads Claude's work/FHE_Comparison/results/*.json and writes a single
dashboard_data.json next to it, which dashboard.html fetches has no network
access in the Artifact sandbox, so this JSON is inlined into dashboard.html
by build_dashboard.py at publish time instead of fetched at runtime.
"""
from __future__ import annotations

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
DATASETS = ["can_vtc", "car_hack", "cicids", "veremi"]
DATASET_LABELS = {
    "can_vtc": "CAN-VTC",
    "car_hack": "Car-Hacking",
    "cicids": "CICIDS-2017",
    "veremi": "VeReMi",
}


def load(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> dict:
    bench = load(RESULTS_DIR / "real_ckks_benchmark.json") or []
    bench_by_ds = {b["dataset"]: b for b in bench}

    rows = []
    for ds in DATASETS:
        nofhe = load(RESULTS_DIR / f"federated_summary_{ds}_nofhe.json")
        fhe = load(RESULTS_DIR / f"federated_summary_{ds}_fhe.json")
        b = bench_by_ds.get(ds)
        status = "done" if (nofhe and fhe) else ("running" if ds == _first_incomplete(RESULTS_DIR) else "pending")
        row = {
            "dataset": ds,
            "label": DATASET_LABELS[ds],
            "status": status,
            "parameters": (fhe or nofhe or {}).get("parameters"),
            "nofhe_accuracy": nofhe["test_accuracy"] if nofhe else None,
            "fhe_accuracy": fhe["test_accuracy"] if fhe else None,
            "nofhe_macro_f1": nofhe["test_macro_f1"] if nofhe else None,
            "fhe_macro_f1": fhe["test_macro_f1"] if fhe else None,
            "nofhe_roc_auc": nofhe["test_roc_auc"] if nofhe else None,
            "fhe_roc_auc": fhe["test_roc_auc"] if fhe else None,
            "nofhe_time_sec": nofhe["training_time_sec"] if nofhe else None,
            "fhe_time_sec": fhe["training_time_sec"] if fhe else None,
            "encrypt_ms": b["encrypt_time_sec_per_client"] * 1000 if b else None,
            "aggregate_ms": b["homomorphic_aggregate_time_sec"] * 1000 if b else None,
            "decrypt_ms": b["decrypt_time_sec"] * 1000 if b else None,
            "round_overhead_ms": b["real_fhe_round_overhead_sec"] * 1000 if b else None,
            "ciphertext_expansion": b["ciphertext_expansion_factor"] if b else None,
            "max_abs_error": b["max_abs_error_vs_plaintext_fedavg"] if b else None,
        }
        rows.append(row)

    n_done = sum(1 for r in rows if r["status"] == "done")
    out = {
        "generated_note": "Fresh from-scratch runs; FHE on/off is the only variable.",
        "n_datasets_total": len(DATASETS),
        "n_datasets_done": n_done,
        "rows": rows,
    }
    out_path = RESULTS_DIR / "dashboard_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"[generate_dashboard_data] {n_done}/{len(DATASETS)} datasets complete -> {out_path}")
    return out


def _first_incomplete(results_dir: Path) -> str | None:
    for ds in DATASETS:
        nofhe = (results_dir / f"federated_summary_{ds}_nofhe.json").exists()
        fhe = (results_dir / f"federated_summary_{ds}_fhe.json").exists()
        if not (nofhe and fhe):
            return ds
    return None


if __name__ == "__main__":
    main()

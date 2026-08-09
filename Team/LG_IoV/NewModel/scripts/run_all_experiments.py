"""Month-5 experiment sweep: all datasets x {ckks, none} x 3 seeds.

Run from the NewModel directory::

    python scripts/run_all_experiments.py

Writes one JSON per (dataset, backend) into ``results/`` plus a combined
``results/month5_summary.json``.

Design notes
------------
* ``ckks`` and ``none`` differ in exactly one thing — whether the client→server
  update is encrypted. Everything else (seed, partition, sampling, optimiser)
  is identical, which is what makes the comparison controlled (defect D3).
* Three seeds per cell so a difference can be judged against run-to-run spread
  rather than asserted from a single run.
* **Row caps.** Each seed re-loads and re-splits its dataset from disk (different
  seed, different split), so uncapped runs on the two largest corpora cost hours
  of I/O for no additional insight at this scale. CICIDS is capped at 150k flow
  records per file (8 files -> ~1.2M records) and VeReMi at 250k beacon rows out
  of ~24M. The VeReMi cap in particular costs nothing scientifically: its
  per-beacon features are measurably near-chance regardless of sample count
  (best single-feature separation 0.046 sigma), because the task is temporal and
  the cleaned export has no sender ID -- see
  Documentation/05_defects.md D5. The caps are a compute budget, not a tuned
  hyperparameter; they are recorded in every output JSON via the command line, and
  both remain far larger than the number of samples 10 clients see in 5 rounds.
  CAN captures are capped at 600k messages per file, which comfortably includes
  each capture's injection window.
* **Resumable.** A cell whose result JSON already exists is skipped, so the sweep
  can be interrupted and restarted without losing completed work. Delete the JSON
  to force a re-run.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
PY = sys.executable

SEEDS = [2025, 2026, 2027]
BACKENDS = ["ckks", "none"]

DATASETS = {
    "can_vtc":  ["--max-rows", "600000"],
    "car_hack": ["--max-rows", "600000"],
    "cicids":   ["--max-rows", "150000"],
    "veremi":   ["--max-rows", "250000"],
}

ROUNDS = "5"
CLIENTS = "10"


def run(dataset: str, backend: str, extra: list) -> dict:
    out = RESULTS_DIR / f"federated_{dataset}_{backend}.json"
    if out.exists():
        data = json.loads(out.read_text(encoding="utf-8"))
        data["status"] = "ok"
        data.setdefault("sweep_seconds", 0.0)
        print(f"--- {dataset}/{backend}: reusing existing result "
              f"(acc={data['accuracy_mean']:.4f}) — delete {out.name} to re-run",
              flush=True)
        return data

    cmd = [
        PY, str(ROOT / "train_federated.py"),
        "--dataset", dataset,
        "--backend", backend,
        "--rounds", ROUNDS,
        "--clients", CLIENTS,
        "--seeds", *[str(s) for s in SEEDS],
    ] + extra

    print(f"\n{'=' * 70}\n>>> {dataset} / {backend}\n{'=' * 70}", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    dt = time.time() - t0

    log_dir = ROOT / "run_logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / f"{dataset}_{backend}.log").write_text(
        proc.stdout + "\n---STDERR---\n" + proc.stderr, encoding="utf-8")

    if proc.returncode != 0:
        print(f"!!! FAILED {dataset}/{backend} rc={proc.returncode}", flush=True)
        print(proc.stderr[-2500:], flush=True)
        return {"dataset": dataset, "backend": backend,
                "status": "failed", "returncode": proc.returncode,
                "seconds": dt}

    data = json.loads(out.read_text(encoding="utf-8"))
    data["status"] = "ok"
    data["sweep_seconds"] = dt
    print(f"<<< {dataset}/{backend}: acc={data['accuracy_mean']:.4f}"
          f"+/-{data['accuracy_std']:.4f}  auc={data['roc_auc_mean']:.4f}  "
          f"({dt/60:.1f} min)", flush=True)
    return data


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_results = []
    for dataset, extra in DATASETS.items():
        for backend in BACKENDS:
            all_results.append(run(dataset, backend, extra))

    combined = RESULTS_DIR / "month5_summary.json"
    with open(combined, "w", encoding="utf-8") as f:
        json.dump({
            "seeds": SEEDS,
            "rounds": int(ROUNDS),
            "clients": int(CLIENTS),
            "results": all_results,
        }, f, indent=2)

    print(f"\n{'=' * 70}\nSWEEP COMPLETE\n{'=' * 70}")
    for r in all_results:
        if r.get("status") != "ok":
            print(f"  {r['dataset']:9s} {r['backend']:6s}  FAILED")
            continue
        print(f"  {r['dataset']:9s} {r['backend']:6s}  "
              f"acc {r['accuracy_mean']:.4f}+/-{r['accuracy_std']:.4f}  "
              f"f1 {r['macro_f1_mean']:.4f}  auc {r['roc_auc_mean']:.4f}")
    print(f"\nsaved {combined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

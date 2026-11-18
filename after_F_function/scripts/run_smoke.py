"""Smoke test script executing fast 1-round smoke runs for Plaintext and CKKS."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.utils.helpers import load_yaml
from src.experiments.runner import run_federated_experiment


def main() -> None:
    print("====================================================================")
    print("STAGE 3: Smoke Test Validation (Plaintext vs CKKS)")
    print("====================================================================")

    base_cfg = load_yaml(PROJECT_DIR / "config/base.yaml")
    base_cfg["federated"]["clients"] = 2
    base_cfg["federated"]["rounds"] = 1
    base_cfg["federated"]["local_epochs"] = 1
    base_cfg["federated"]["batch_size"] = 64
    base_cfg["data"]["max_rows_per_class"] = 20000  # fast smoke sample

    part_cfg = {"mode": "iid"}

    # 1. Plaintext Smoke Run
    print("\n[smoke] Running Plaintext Baseline (backend='none')...")
    res_plain = run_federated_experiment(
        base_cfg=base_cfg,
        part_cfg=part_cfg,
        backend="none",
        seed_override=2025,
    )
    print(f"Plaintext Smoke finished! Final Test Accuracy: {res_plain['final_metrics']['accuracy']:.4f}")

    # 2. CKKS Smoke Run
    print("\n[smoke] Running CKKS Homomorphic Run (backend='ckks')...")
    res_ckks = run_federated_experiment(
        base_cfg=base_cfg,
        part_cfg=part_cfg,
        backend="ckks",
        seed_override=2025,
    )
    print(f"CKKS Smoke finished! Final Test Accuracy: {res_ckks['final_metrics']['accuracy']:.4f}")

    print("\nSmoke tests successfully validated both pipelines!")


if __name__ == "__main__":
    main()

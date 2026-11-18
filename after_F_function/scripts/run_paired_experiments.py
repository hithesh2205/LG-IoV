"""Run the 4 Paired Experiments: IID & Non-IID, each with and without CKKS."""
from __future__ import annotations

import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.utils.helpers import load_yaml, save_json
from src.experiments.runner import run_federated_experiment


def main() -> None:
    print("====================================================================")
    print("STAGE 4: Complete Paired Experiments Execution")
    print("====================================================================")

    base_cfg = load_yaml(PROJECT_DIR / "config/base.yaml")
    iid_cfg = load_yaml(PROJECT_DIR / "config/iid.yaml")["partition"]
    non_iid_cfg = load_yaml(PROJECT_DIR / "config/non_iid.yaml")["partition"]

    # We run 3 federated rounds with 5 clients, matching base.yaml
    base_cfg["federated"]["clients"] = 5
    base_cfg["federated"]["rounds"] = 3
    base_cfg["federated"]["local_epochs"] = 1
    base_cfg["data"]["max_rows_per_class"] = 35000  # balanced, representative sample

    experiments = [
        ("iid_plain", iid_cfg, "none", "IID without CKKS (Plaintext Baseline)"),
        ("iid_ckks", iid_cfg, "ckks", "IID with CKKS (Homomorphic Baseline)"),
        ("non_iid_plain", non_iid_cfg, "none", "Non-IID without CKKS (Plaintext Heterogeneous)"),
        ("non_iid_ckks", non_iid_cfg, "ckks", "Non-IID with CKKS (Homomorphic Heterogeneous)"),
    ]

    all_results = {}
    summary_rows = []

    for key, p_cfg, backend, desc in experiments:
        print(f"\n====================================================================")
        print(f"Executing: {desc}")
        print(f"Backend: {backend} | Partition: {p_cfg['mode']} | Seed: 2025")
        print(f"====================================================================")

        t_start = time.perf_counter()
        res = run_federated_experiment(
            base_cfg=base_cfg,
            part_cfg=p_cfg,
            backend=backend,
            seed_override=2025,
        )
        duration = time.perf_counter() - t_start
        all_results[key] = res

        # Save individual experiment result JSON
        json_path = PROJECT_DIR / f"results/metrics/{key}.json"
        save_json(res, json_path)
        print(f"Saved {key} metrics to: {json_path}")

        final_m = res["final_metrics"]
        comm_mb = res["total_comm_bytes"] / (1024 * 1024)
        avg_round_sec = float(np.mean([r["round_duration_sec"] for r in res["round_history"]]))
        avg_agg_sec = float(np.mean([r["agg_time_sec"] for r in res["round_history"]]))

        summary_rows.append({
            "Experiment": key,
            "Description": desc,
            "Partition": p_cfg["mode"],
            "Backend": backend,
            "Test_Accuracy": final_m["accuracy"],
            "Test_F1_Macro": final_m["f1_macro"],
            "Test_Precision_Macro": final_m["precision_macro"],
            "Test_Recall_Macro": final_m["recall_macro"],
            "Test_Loss": final_m["loss"],
            "Total_Duration_s": round(duration, 2),
            "Avg_Round_s": round(avg_round_sec, 2),
            "Avg_Agg_s": round(avg_agg_sec, 4),
            "Total_Comm_MB": round(comm_mb, 2),
        })

    # Summary table
    df_summary = pd.DataFrame(summary_rows)
    csv_path = PROJECT_DIR / "results/metrics/summary_table.csv"
    df_summary.to_csv(csv_path, index=False)

    summary_json_path = PROJECT_DIR / "results/metrics/summary_comparison.json"
    save_json(summary_rows, summary_json_path)

    print("\n====================================================================")
    print("STAGE 4 RESULTS SUMMARY TABLE")
    print("====================================================================")
    print(df_summary[["Experiment", "Partition", "Backend", "Test_Accuracy", "Test_F1_Macro", "Total_Comm_MB", "Avg_Agg_s"]].to_string(index=False))
    print(f"\nSaved CSV summary to: {csv_path}")
    print(f"Saved JSON summary to: {summary_json_path}")


if __name__ == "__main__":
    main()

"""Generate publication-ready plots for the paired experiments."""
from __future__ import annotations

import sys
import os
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

METRICS_DIR = PROJECT_DIR / "results/metrics"
PLOTS_DIR = PROJECT_DIR / "results/plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def plot_convergence() -> None:
    files = {
        "IID Plaintext": METRICS_DIR / "iid_plain.json",
        "IID CKKS": METRICS_DIR / "iid_ckks.json",
        "Non-IID Plaintext": METRICS_DIR / "non_iid_plain.json",
        "Non-IID CKKS": METRICS_DIR / "non_iid_ckks.json",
    }

    colors = {
        "IID Plaintext": "#1f77b4",
        "IID CKKS": "#aec7e8",
        "Non-IID Plaintext": "#d62728",
        "Non-IID CKKS": "#ff9896",
    }
    styles = {
        "IID Plaintext": "-",
        "IID CKKS": "--",
        "Non-IID Plaintext": "-",
        "Non-IID CKKS": "--",
    }

    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)

    for label, path in files.items():
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rounds = [r["round"] for r in data["round_history"]]
        accs = [r["test_accuracy"] for r in data["round_history"]]
        plt.plot(rounds, accs, label=label, color=colors[label], linestyle=styles[label], marker="o", linewidth=2)

    plt.title("Global Test Accuracy vs Federated Round", fontsize=11, fontweight="bold")
    plt.xlabel("Federated Round")
    plt.ylabel("Accuracy")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=9)

    plt.subplot(1, 2, 2)
    for label, path in files.items():
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rounds = [r["round"] for r in data["round_history"]]
        f1s = [r["test_f1_macro"] for r in data["round_history"]]
        plt.plot(rounds, f1s, label=label, color=colors[label], linestyle=styles[label], marker="s", linewidth=2)

    plt.title("Global Macro F1-Score vs Federated Round", fontsize=11, fontweight="bold")
    plt.xlabel("Federated Round")
    plt.ylabel("Macro F1-Score")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=9)

    plt.tight_layout()
    out_path = PLOTS_DIR / "convergence_comparison.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved convergence plot to: {out_path}")


def plot_overhead() -> None:
    summary_path = METRICS_DIR / "summary_comparison.json"
    if not summary_path.exists():
        return

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    labels = [d["Experiment"] for d in data]
    comm_mb = [d["Total_Comm_MB"] for d in data]
    agg_sec = [d["Avg_Agg_s"] for d in data]

    x = np.arange(len(labels))

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    bar_width = 0.35

    color1 = "#2ca02c"
    rects1 = ax1.bar(x - bar_width / 2, comm_mb, bar_width, label="Communication Volume (MB)", color=color1, alpha=0.85)
    ax1.set_ylabel("Total Communication (MB)", color=color1, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=15, ha="right", fontsize=9)

    ax2 = ax1.twinx()
    color2 = "#9467bd"
    rects2 = ax2.bar(x + bar_width / 2, agg_sec, bar_width, label="Avg Aggregation Time (s)", color=color2, alpha=0.85)
    ax2.set_ylabel("Avg Aggregation Time per Round (s)", color=color2, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=color2)

    plt.title("Cryptographic & Communication Overhead (Plaintext vs CKKS)", fontsize=11, fontweight="bold")
    fig.tight_layout()
    out_path = PLOTS_DIR / "overhead_comparison.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Saved overhead plot to: {out_path}")


def main() -> None:
    plot_convergence()
    plot_overhead()
    print("All plots generated successfully!")


if __name__ == "__main__":
    main()

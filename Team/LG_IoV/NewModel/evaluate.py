"""Standalone evaluation script for MamKANformer model.

Loads preprocessed dataset artifacts and best model weights, runs evaluation
on the test split, and displays evaluation reports.

Usage:
    py NewModel/evaluate.py --dataset can_vtc
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from data.preprocess import PreprocessingPipeline
from data.loader import CanFeatureDataset
from models.cheby_kan import ChebyshevKAN
from utils.metrics import compute_all_metrics, print_metrics_report
from utils.helpers import set_seed

# Workspace roots
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT.parent / "Preprocessed_Dataset"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"


def parse_yaml_config(filepath: Path) -> dict:
    """Simple parser to read YAML configuration without dependency."""
    config = {}
    current_section = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            if line.endswith(":"):
                current_section = line[:-1].strip()
                config[current_section] = {}
            elif ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                if val.lower() == "true": val = True
                elif val.lower() == "false": val = False
                elif val.lower() in ("none", "null"): val = None
                elif val.startswith('"') and val.endswith('"'): val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"): val = val[1:-1]
                else:
                    try:
                        if "." in val: val = float(val)
                        else: val = int(val)
                    except ValueError: pass
                if current_section:
                    config[current_section][key] = val
                else:
                    config[key] = val
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate MamKANformer Baseline Model")
    parser.add_argument("--dataset", choices=["can_vtc", "car_hack", "cicids", "veremi"], default="can_vtc")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint file")
    parser.add_argument("--multi-class", action="store_true", help="CICIDS/VeReMi multi-class evaluation")
    args = parser.parse_args()

    # Load configuration
    config_path = PROJECT_ROOT / "config.yaml"
    cfg = parse_yaml_config(config_path)

    # Set random seed
    seed = cfg["train"]["seed"]
    set_seed(seed)

    # Set up device
    device_name = cfg["train"]["device"]
    device = torch.device("cuda" if torch.cuda.is_available() and device_name == "cuda" else "cpu")
    print(f"[init] Evaluation running on device: {device}")

    # Load pipeline artifacts
    pipeline_path = CHECKPOINT_DIR / f"pipeline_{args.dataset}.pkl"
    if not pipeline_path.exists():
        raise FileNotFoundError(f"Preprocessing pipeline artifact not found: {pipeline_path}. Please run train.py first.")
    
    pipeline = PreprocessingPipeline.load(pipeline_path)
    classes = pipeline.classes
    n_classes = len(classes)

    # Resolve raw data for test split reconstruction
    print(f"[data] Loading raw data to reconstruct test split...")
    # Load same raw data and perform same split
    from data.preprocess import (
        assert_no_group_overlap, load_can_vtc, load_car_hack, load_cicids, load_veremi,
    )
    if args.dataset == "can_vtc":
        X, y, _, groups = load_can_vtc(DATA_ROOT / "Can_vtc_pro", cfg["data"]["window"], cfg["data"]["stride"])
    elif args.dataset == "car_hack":
        X, y, _, groups = load_car_hack(DATA_ROOT / "Car_hack_pro" / "Car_hack_pro", cfg["data"]["window"], cfg["data"]["stride"])
    elif args.dataset == "cicids":
        X, y, _, groups = load_cicids(DATA_ROOT / "CICIDS_pro" / "CICIDS_pro", None, args.multi_class)
    elif args.dataset == "veremi":
        X, y, _, groups = load_veremi(DATA_ROOT / "VeReMi_pro", cfg["data"]["window"], cfg["data"]["stride"], None, args.multi_class)
    else:
        raise ValueError(f"Unknown dataset: {args.dataset}")

    # Reconstruct the exact test split — same seed, same group-aware allocation.
    train_idx, val_idx, test_idx = pipeline._grouped_split(y, groups)
    assert_no_group_overlap(groups, train_idx, val_idx, test_idx)
    print(f"[data] Reconstructed test split size: {len(test_idx)}")

    # Apply clipping and scaling to test set
    X_test_scaled = pipeline.transform(X[test_idx])
    y_test = y[test_idx]

    # Create dataset loader
    test_ds = CanFeatureDataset(X_test_scaled, y_test)
    test_loader = DataLoader(
        test_ds,
        batch_size=cfg["train"]["batch_size"],
        shuffle=False,
        num_workers=cfg["train"]["num_workers"],
        pin_memory=True,
    )

    # Instantiate model
    model = ChebyshevKAN(
        dataset=args.dataset,
        n_classes=n_classes,
        hidden_dim=cfg["model"]["hidden_dim"],
        num_layers=cfg["model"]["num_layers"],
        degree=cfg["model"]["degree"],
        dropout=cfg["model"]["dropout"],
    ).to(device)

    # Load weights
    checkpoint_file = args.checkpoint if args.checkpoint is not None else str(CHECKPOINT_DIR / f"best_model_{args.dataset}.pt")
    checkpoint_path = Path(checkpoint_file)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Model checkpoint weights not found: {checkpoint_path}")
        
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    print(f"[eval] Successfully loaded model weights from epoch {checkpoint['epoch']} ({checkpoint_file})")

    # Run predictions
    model.eval()
    all_preds = []
    all_true = []
    all_probs = []

    with torch.no_grad():
        for x, y in test_loader:
            x = x.to(device)
            logits = model(x)
            probs = torch.softmax(logits, dim=-1)
            preds = logits.argmax(dim=-1)
            
            all_preds.append(preds.cpu().numpy())
            all_true.append(y.numpy())
            all_probs.append(probs.cpu().numpy())

    all_preds = np.concatenate(all_preds)
    all_true = np.concatenate(all_true)
    all_probs = np.concatenate(all_probs)

    # Compute & display metrics
    metrics = compute_all_metrics(all_true, all_preds, all_probs, classes)
    print_metrics_report(metrics)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

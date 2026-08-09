"""Train + evaluate MamKANformer baseline model.

Usage:
    py NewModel/train.py --dataset can_vtc
    py NewModel/train.py --dataset can_vtc --smoke
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
import torch.nn as nn

from data.preprocess import PreprocessingPipeline
from data.loader import CanFeatureDataset, get_dataloaders
from models.cheby_kan import ChebyshevKAN
from utils.helpers import set_seed, save_checkpoint
from utils.metrics import compute_all_metrics, print_metrics_report

# Workspace roots
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT.parent / "Preprocessed_Dataset"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"


def parse_yaml_config(filepath: Path) -> Dict[str, Any]:
    """Custom YAML parser to load configuration settings without PyYAML dependency."""
    config = {}
    current_section = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # Strip comments and whitespaces
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
                
                # Parse type
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.lower() in ("none", "null"):
                    val = None
                elif val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                else:
                    try:
                        if "." in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass
                
                if current_section:
                    config[current_section][key] = val
                else:
                    config[key] = val
    return config


def make_optimizer(name: str, params, lr: float, wd: float) -> torch.optim.Optimizer:
    """Create optimizer by string name."""
    name = name.lower()
    if name == "adamw":
        return torch.optim.AdamW(params, lr=lr, weight_decay=wd)
    if name == "rmsprop":
        return torch.optim.RMSprop(params, lr=lr, weight_decay=wd)
    if name == "sgd":
        return torch.optim.SGD(params, lr=lr, momentum=0.9, weight_decay=wd)
    if name == "nadam":
        return torch.optim.NAdam(params, lr=lr, weight_decay=wd)
    raise ValueError(f"Unknown optimizer: {name}")


def evaluate_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    """Run model evaluation for one epoch. Returns (avg_loss, accuracy)."""
    model.eval()
    total_loss = 0.0
    correct = 0
    total_samples = 0

    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = criterion(logits, y)
            
            total_loss += loss.item() * y.size(0)
            preds = logits.argmax(dim=-1)
            correct += (preds == y).sum().item()
            total_samples += y.size(0)

    avg_loss = total_loss / max(total_samples, 1)
    acc = correct / max(total_samples, 1)
    return avg_loss, acc


def main() -> int:
    parser = argparse.ArgumentParser(description="Train MamKANformer Baseline Model")
    parser.add_argument("--dataset", choices=["can_vtc", "car_hack", "cicids", "veremi"], default="can_vtc")
    parser.add_argument("--smoke", action="store_true", help="Run a quick smoke test (1 epoch, limited dataset)")
    parser.add_argument("--multi-class", action="store_true", help="CICIDS/VeReMi multi-class training")
    parser.add_argument("--epochs", type=int, default=None, help="Override epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate")
    parser.add_argument("--seed", type=int, default=None, help="Override seed")
    args = parser.parse_args()

    # Load configuration
    config_path = PROJECT_ROOT / "config.yaml"
    cfg = parse_yaml_config(config_path)

    # Apply command-line overrides
    seed = args.seed if args.seed is not None else cfg["train"]["seed"]
    epochs = 1 if args.smoke else (args.epochs if args.epochs is not None else cfg["train"]["epochs"])
    batch_size = args.batch_size if args.batch_size is not None else cfg["train"]["batch_size"]
    lr = args.lr if args.lr is not None else cfg["train"]["lr"]
    
    # 1. Set seed
    set_seed(seed)

    # Set up device
    device_name = cfg["train"]["device"]
    device = torch.device("cuda" if torch.cuda.is_available() and device_name == "cuda" else "cpu")
    print(f"[init] Training Chebyshev KAN on device: {device}")

    # 2. Run Preprocessing Pipeline
    # Limit rows for fast training during smoke test
    max_rows = 15000 if args.smoke else None
    pipeline = PreprocessingPipeline(
        clip_low=cfg["data"].get("clip_low", 0.005),
        clip_high=cfg["data"].get("clip_high", 0.995),
        val_split=cfg["train"]["val_split"],
        test_split=cfg["train"]["test_split"],
        seed=seed,
    )
    
    split_data = pipeline.fit_transform(
        name=args.dataset,
        data_root=DATA_ROOT,
        window=cfg["data"]["window"],
        stride=cfg["data"]["stride"],
        max_rows_per_class=max_rows,
        cicids_multi_class=args.multi_class,
    )
    
    classes = pipeline.classes
    n_classes = len(classes)

    # Save preprocessing pipeline artifacts for evaluate.py
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    pipeline.save(CHECKPOINT_DIR / f"pipeline_{args.dataset}.pkl")

    # 3. Create Dataset loaders
    train_ds = CanFeatureDataset(split_data["X_train"], split_data["y_train"])
    val_ds = CanFeatureDataset(split_data["X_val"], split_data["y_val"])
    test_ds = CanFeatureDataset(split_data["X_test"], split_data["y_test"])

    train_loader, val_loader, test_loader = get_dataloaders(
        train_ds=train_ds,
        val_ds=val_ds,
        test_ds=test_ds,
        batch_size=batch_size,
        num_workers=cfg["train"]["num_workers"],
        drop_last=True,
    )

    # 4. Instantiate Chebyshev KAN
    model = ChebyshevKAN(
        dataset=args.dataset,
        n_classes=n_classes,
        hidden_dim=cfg["model"]["hidden_dim"],
        num_layers=cfg["model"]["num_layers"],
        degree=cfg["model"]["degree"],
        dropout=cfg["model"]["dropout"],
    ).to(device)

    # Model stats
    param_count = model.num_parameters()
    print(f"[model] Instantiated Chebyshev KAN model successfully.")
    print(f"[model] Total parameters: {param_count:,}")

    # Set up weighted loss function
    class_weights_t = torch.from_numpy(pipeline.class_weights.astype(np.float32)).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights_t)

    # Set up optimizer
    optimizer = make_optimizer(
        name=cfg["train"]["optimizer"],
        params=model.parameters(),
        lr=lr,
        wd=cfg["train"]["weight_decay"],
    )

    # Early stopping configuration
    best_val_loss = float("inf")
    patience = cfg["train"]["early_stopping_patience"]
    patience_counter = 0
    best_model_path = CHECKPOINT_DIR / f"best_model_{args.dataset}.pt"

    print(f"\n[train] Starting training for {epochs} epochs...")
    t_start = time.time()

    for epoch in range(1, epochs + 1):
        epoch_start_time = time.time()
        model.train()
        train_loss = 0.0
        train_samples = 0
        
        for batch_idx, (x, y) in enumerate(train_loader, 1):
            x, y = x.to(device), y.to(device)
            
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * y.size(0)
            train_samples += y.size(0)
            
        avg_train_loss = train_loss / max(train_samples, 1)
        val_loss, val_acc = evaluate_epoch(model, val_loader, criterion, device)
        
        dt_epoch = time.time() - epoch_start_time
        print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f} | Time: {dt_epoch:.1f}s")
        
        # Check early stopping / save best weights
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save checkpoint
            save_checkpoint(
                state={
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "config": cfg,
                    "dataset": args.dataset,
                    "classes": classes,
                    "epoch": epoch,
                },
                checkpoint_dir=CHECKPOINT_DIR,
                filename=f"best_model_{args.dataset}.pt",
            )
        else:
            patience_counter += 1
            if patience_counter >= patience and not args.smoke:
                print(f"[train] Early stopping triggered at epoch {epoch:02d} (patience={patience})")
                break

    total_training_time = time.time() - t_start
    print(f"\n[train] Training completed in {total_training_time:.1f} seconds.")

    # 5. Load best model for testing
    if best_model_path.exists():
        checkpoint = torch.load(best_model_path, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        print(f"[test] Loaded best weights from epoch {checkpoint['epoch']}")
    else:
        print("[test] Best checkpoint not found; evaluating final model state instead.")

    # Evaluate on test set
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

    # 6. Compute metrics
    metrics = compute_all_metrics(all_true, all_preds, all_probs, classes)
    print_metrics_report(metrics)

    # Report parameters & training time as part of benchmark
    print("\nBENCHMARK METADATA:")
    print(f"Total Parameters:    {param_count:,}")
    print(f"Total Training Time: {total_training_time:.2f} seconds")

    # Save metrics benchmark summary as json
    import json
    metrics_summary_path = CHECKPOINT_DIR / f"metrics_summary_{args.dataset}.json"
    summary_data = {
        "dataset": args.dataset,
        "parameters": param_count,
        "training_time_sec": total_training_time,
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "roc_auc": metrics["roc_auc"],
    }
    with open(metrics_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"[test] Benchmark summary saved: {metrics_summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

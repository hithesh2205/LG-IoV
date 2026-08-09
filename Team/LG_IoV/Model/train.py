"""Train + evaluate KANConvNet on any of the unified IoV datasets.

    py train.py --dataset can_vtc
    py train.py --dataset car_hack
    py train.py --dataset cicids
    py train.py --dataset cicids --multi-class
    py train.py --dataset can_vtc --smoke   # 1 epoch, 50k rows/class

Per-dataset best hyperparameters are auto-applied from paper Table 4
(see ``DATASET_HPARAMS`` in config.py). Override with --epochs / --batch-size.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.append(str(Path(__file__).resolve().parent))

from config import CHECKPOINT_DIR, Config, DATA_ROOT                # noqa: E402
from data import build_datasets, DATASETS                           # noqa: E402
from models import KANConvNet                                       # noqa: E402


def make_optimizer(name: str, params, lr: float, momentum: float, wd: float):
    name = name.lower()
    if name == "rmsprop":
        return torch.optim.RMSprop(params, lr=lr, momentum=momentum, weight_decay=wd)
    if name == "adamw":
        return torch.optim.AdamW(params, lr=lr, weight_decay=wd)
    if name == "sgd":
        return torch.optim.SGD(params, lr=lr, momentum=momentum, weight_decay=wd)
    if name == "nadam":
        return torch.optim.NAdam(params, lr=lr, weight_decay=wd)
    if name == "adadelta":
        return torch.optim.Adadelta(params, lr=lr, weight_decay=wd)
    raise ValueError(f"unknown optimizer: {name}")


def evaluate(model, loader, device, criterion, classes):
    model.eval()
    tot_loss = tot_n = correct = 0
    all_pred, all_true = [], []
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = criterion(logits, y)
            tot_loss += loss.item() * y.size(0); tot_n += y.size(0)
            pred = logits.argmax(dim=-1)
            correct += (pred == y).sum().item()
            all_pred.append(pred.cpu().numpy())
            all_true.append(y.cpu().numpy())
    all_pred = np.concatenate(all_pred); all_true = np.concatenate(all_true)
    per_class = []
    for c in range(len(classes)):
        tp = int(((all_pred == c) & (all_true == c)).sum())
        fp = int(((all_pred == c) & (all_true != c)).sum())
        fn = int(((all_pred != c) & (all_true == c)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class.append({"class": classes[c], "precision": precision,
                          "recall": recall, "f1": f1,
                          "support": int((all_true == c).sum())})
    macro_f1 = float(np.mean([m["f1"] for m in per_class]))
    return {"loss": tot_loss / max(tot_n, 1),
            "accuracy": correct / max(tot_n, 1),
            "macro_f1": macro_f1, "per_class": per_class}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=DATASETS, default="can_vtc")
    ap.add_argument("--smoke", action="store_true",
                    help="Quick sanity run: 1 epoch, 50k rows/class.")
    ap.add_argument("--multi-class", action="store_true",
                    help="CICIDS only — predict the full attack family set.")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--no-save", action="store_true",
                    help="Skip writing the best checkpoint.")
    args = ap.parse_args()

    cfg = Config(dataset=args.dataset)
    cfg.data.cicids_multi_class = args.multi_class
    cfg.apply_dataset_defaults()
    if args.epochs is not None: cfg.train.epochs = args.epochs
    if args.batch_size is not None: cfg.train.batch_size = args.batch_size
    if args.lr is not None: cfg.train.lr = args.lr
    if args.smoke: cfg.train.epochs = 1
    if args.no_save: cfg.train.save_best = False

    torch.manual_seed(cfg.train.seed); np.random.seed(cfg.train.seed)
    device = torch.device("cuda" if torch.cuda.is_available()
                          and cfg.train.device == "cuda" else "cpu")
    print(f"[init] device={device}  dataset={cfg.dataset}  "
          f"optimizer={cfg.train.optimizer}  layer_size={cfg.model.layer_size}")

    split = build_datasets(
        name=cfg.dataset,
        data_root=DATA_ROOT,
        window=cfg.data.window,
        stride=cfg.data.stride,
        val_split=cfg.train.val_split,
        test_split=cfg.train.test_split,
        seed=cfg.train.seed,
        max_rows_per_class=50_000 if args.smoke else None,
        clip_low=cfg.data.clip_low,
        clip_high=cfg.data.clip_high,
        cicids_multi_class=cfg.data.cicids_multi_class,
    )
    classes = split.classes
    cfg.model.n_classes = len(classes)
    print(f"[data] train={len(split.train)} val={len(split.val)} "
          f"test={len(split.test)} classes={classes}")

    train_loader = DataLoader(split.train, batch_size=cfg.train.batch_size,
                              shuffle=True, num_workers=cfg.train.num_workers,
                              drop_last=True)
    val_loader = DataLoader(split.val, batch_size=cfg.train.batch_size,
                            shuffle=False, num_workers=cfg.train.num_workers)
    test_loader = DataLoader(split.test, batch_size=cfg.train.batch_size,
                             shuffle=False, num_workers=cfg.train.num_workers)

    model = KANConvNet(
        in_features=cfg.model.in_features,
        n_classes=cfg.model.n_classes,
        layer_size=cfg.model.layer_size,
        dropout=cfg.model.dropout,
        fourier_modes=cfg.model.fourier_modes,
        conv_channels=cfg.model.conv_channels,
        kernel_size=cfg.model.kernel_size,
        use_conv_backbone=cfg.model.use_conv_backbone,
    ).to(device)
    print(f"[model] KANConvNet params={model.num_parameters():,}  "
          f"layer_size={cfg.model.layer_size}  conv_backbone={cfg.model.use_conv_backbone}")

    cls_counts = np.bincount(split.train.labels.numpy(),
                             minlength=cfg.model.n_classes).astype(np.float32)
    cls_weights = cls_counts.sum() / (len(cls_counts) * np.clip(cls_counts, 1.0, None))
    criterion = nn.CrossEntropyLoss(
        weight=torch.from_numpy(cls_weights.astype(np.float32)).to(device)
    )
    optimizer = make_optimizer(
        cfg.train.optimizer, model.parameters(),
        lr=cfg.train.lr, momentum=cfg.train.momentum, wd=cfg.train.weight_decay,
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = CHECKPOINT_DIR / f"training_log_{cfg.dataset}.json"
    best_path = CHECKPOINT_DIR / f"kanconvnet_best_{cfg.dataset}.pt"
    history = []
    best_val_loss = float("inf")

    for epoch in range(1, cfg.train.epochs + 1):
        t0 = time.time()
        model.train()
        run_loss = run_n = 0
        for i, (x, y) in enumerate(train_loader, 1):
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            run_loss += loss.item() * y.size(0); run_n += y.size(0)
            if i % cfg.train.log_every == 0:
                print(f"[epoch {epoch} batch {i}] train_loss={run_loss/run_n:.4f}")
        train_loss = run_loss / max(run_n, 1)

        val = evaluate(model, val_loader, device, criterion, classes)
        dt = time.time() - t0
        print(f"[epoch {epoch}/{cfg.train.epochs}] "
              f"train_loss={train_loss:.4f}  val_loss={val['loss']:.4f}  "
              f"val_acc={val['accuracy']:.4f}  val_f1={val['macro_f1']:.4f}  "
              f"time={dt:.1f}s")
        history.append({"epoch": epoch, "train_loss": train_loss,
                        "val_loss": val["loss"], "val_acc": val["accuracy"],
                        "val_f1": val["macro_f1"], "time_sec": dt})

        if cfg.train.save_best and val["loss"] < best_val_loss:
            best_val_loss = val["loss"]
            torch.save({
                "dataset": cfg.dataset,
                "model_state_dict": model.state_dict(),
                "config": {"model": cfg.model.__dict__, "data": cfg.data.__dict__},
                "feature_mean": split.feature_mean,
                "feature_std":  split.feature_std,
                "classes": list(classes),
                "epoch": epoch,
            }, best_path)
            print(f"[ckpt] saved {best_path}")
        log_path.write_text(json.dumps(history, indent=2))

    if best_path.exists():
        ckpt = torch.load(best_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
    test = evaluate(model, test_loader, device, criterion, classes)
    print("\n[test] " + json.dumps({"loss": test["loss"],
                                    "accuracy": test["accuracy"],
                                    "macro_f1": test["macro_f1"]}, indent=2))
    for m in test["per_class"]:
        print(f"  {m['class']:<24}  P={m['precision']:.4f}"
              f"  R={m['recall']:.4f}  F1={m['f1']:.4f}  n={m['support']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

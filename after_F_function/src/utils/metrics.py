"""Evaluation Metrics Computation for IoV Intrusion Detection."""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix


def evaluate_model(
    model: nn.Module,
    loader: DataLoader,
    device: str = "cpu",
    classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evaluate classification metrics on the given dataset loader."""
    dev = torch.device(device)
    model.to(dev)
    model.eval()

    all_preds: List[int] = []
    all_targets: List[int] = []
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(dev), y.to(dev)
            logits = model(x)
            loss = criterion(logits, y)
            total_loss += loss.item() * y.size(0)
            preds = logits.argmax(dim=-1)
            all_preds.extend(preds.cpu().numpy().tolist())
            all_targets.extend(y.cpu().numpy().tolist())

    model.to("cpu")
    y_true = np.array(all_targets, dtype=np.int64)
    y_pred = np.array(all_preds, dtype=np.int64)

    acc = float(accuracy_score(y_true, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred).tolist()

    # Per-class metrics
    p_per, r_per, f1_per, sup_per = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0
    )

    per_class = {}
    n_cls = len(p_per)
    for c in range(n_cls):
        c_name = classes[c] if classes and c < len(classes) else f"class_{c}"
        per_class[c_name] = {
            "precision": float(p_per[c]),
            "recall": float(r_per[c]),
            "f1": float(f1_per[c]),
            "support": int(sup_per[c]),
        }

    return {
        "loss": float(total_loss / max(len(y_true), 1)),
        "accuracy": acc,
        "precision_macro": float(p_macro),
        "recall_macro": float(r_macro),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(p_weighted),
        "recall_weighted": float(r_weighted),
        "f1_weighted": float(f1_weighted),
        "per_class": per_class,
        "confusion_matrix": cm,
    }

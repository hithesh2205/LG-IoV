"""Evaluation metrics module for logging model performance.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    roc_auc_score,
)
import torch


def compute_all_metrics(
    all_true: np.ndarray,
    all_pred: np.ndarray,
    all_probs: np.ndarray,
    classes: Tuple[str, ...],
) -> Dict[str, Any]:
    """Calculate comprehensive performance metrics: Accuracy, Precision, Recall, F1, AUC, and CM.
    
    Args:
        all_true: Ground truth labels (N,)
        all_pred: Predicted class labels (N,)
        all_probs: Predicted class probabilities (N, n_classes)
        classes: Tuple of class names
        
    Returns:
        dict containing calculated metrics.
    """
    n_classes = len(classes)
    
    # 1. Overall accuracy
    acc = accuracy_score(all_true, all_pred)
    
    # 2. Per-class precision, recall, f1, support
    prec, rec, f1, supp = precision_recall_fscore_support(
        all_true,
        all_pred,
        labels=list(range(n_classes)),
        zero_division=0,
    )
    
    # Compile per-class stats
    per_class_metrics = []
    for idx, name in enumerate(classes):
        per_class_metrics.append({
            "class": name,
            "precision": float(prec[idx]),
            "recall": float(rec[idx]),
            "f1": float(f1[idx]),
            "support": int(supp[idx]),
        })
        
    # Macro averages
    macro_precision = float(np.mean(prec))
    macro_recall = float(np.mean(rec))
    macro_f1 = float(np.mean(f1))
    
    # 3. Confusion matrix
    cm = confusion_matrix(all_true, all_pred, labels=list(range(n_classes)))
    
    # 4. ROC-AUC score (One-vs-Rest for multiclass, binary for 2-classes)
    auc_score = 0.0
    try:
        if n_classes == 2:
            # For binary, use probability of class 1
            auc_score = float(roc_auc_score(all_true, all_probs[:, 1]))
        else:
            # For multi-class, use multi_class='ovr' with probs for all classes
            auc_score = float(roc_auc_score(all_true, all_probs, multi_class="ovr", average="macro"))
    except Exception as e:
        print(f"[metrics] Warning: Could not compute ROC-AUC score: {e}")
        auc_score = 0.0

    return {
        "accuracy": float(acc),
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class_metrics,
        "confusion_matrix": cm.tolist(),
        "roc_auc": auc_score,
    }


def print_metrics_report(metrics: Dict[str, Any]) -> None:
    """Print a clean evaluation report to stdout."""
    print("\n" + "="*50)
    print("           BASELINE BENCHMARK REPORT")
    print("="*50)
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Macro F1:  {metrics['macro_f1']:.4f}")
    print(f"Precision: {metrics['macro_precision']:.4f}")
    print(f"Recall:    {metrics['macro_recall']:.4f}")
    print(f"ROC-AUC:   {metrics['roc_auc']:.4f}")
    
    print("\nPer-Class Metrics:")
    print(f"{'Class Name':<25} | {'Precision':<10} | {'Recall':<10} | {'F1-score':<10} | {'Support':<8}")
    print("-" * 68)
    for m in metrics["per_class"]:
        print(f"{m['class']:<25} | {m['precision']:<10.4f} | {m['recall']:<10.4f} | {m['f1']:<10.4f} | {m['support']:<8}")
        
    print("\nConfusion Matrix:")
    cm = np.array(metrics["confusion_matrix"])
    print(cm)
    print("="*50)

"""Helper utilities for seed control, logging, and checkpointing.
"""
from __future__ import annotations

import random
import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch


def set_seed(seed: int = 2025) -> None:
    """Set random seed across all libraries for deterministic replication."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    
    # Configure PyTorch to be deterministic
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print(f"[helpers] Random seed fixed at: {seed}")


def save_checkpoint(
    state: Dict[str, Any],
    checkpoint_dir: Path,
    filename: str,
) -> Path:
    """Save training states and configuration to a checkpoint file."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    filepath = checkpoint_dir / filename
    torch.save(state, filepath)
    print(f"[helpers] Checkpoint saved: {filepath}")
    return filepath


def load_checkpoint(
    filepath: Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    device: torch.device = torch.device("cpu"),
) -> Dict[str, Any]:
    """Load model states and training info from a checkpoint file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Checkpoint file not found: {filepath}")
        
    state = torch.load(filepath, map_location=device, weights_only=False)
    model.load_state_dict(state["model_state_dict"])
    
    if optimizer is not None and "optimizer_state_dict" in state:
        optimizer.load_state_dict(state["optimizer_state_dict"])
        
    print(f"[helpers] Checkpoint loaded successfully: {filepath}")
    return state

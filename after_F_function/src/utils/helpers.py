"""Helper utilities for logging, seeding, and configuration parsing."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict
import numpy as np
import torch
import yaml


def set_seed(seed: int = 2025) -> None:
    """Set random seed across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_yaml(filepath: Path | str) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_json(data: Any, filepath: Path | str) -> None:
    """Save serializable data to a JSON file."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

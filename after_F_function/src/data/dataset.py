"""Dataset wrapper and DataLoader utilities for IoV features."""
from __future__ import annotations

from typing import Tuple
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


class CanFeatureDataset(Dataset):
    """Memory-efficient wrapper around (N, 46) preprocessed features and (N,) labels."""

    def __init__(self, features: np.ndarray, labels: np.ndarray) -> None:
        if features.shape[0] != labels.shape[0]:
            raise ValueError(f"Features and labels count mismatch: {features.shape[0]} vs {labels.shape[0]}")
        self.features = torch.from_numpy(features.astype(np.float32))
        self.labels = torch.from_numpy(labels.astype(np.int64))

    def __len__(self) -> int:
        return self.features.size(0)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]


def get_dataloaders(
    train_ds: Dataset,
    val_ds: Dataset,
    test_ds: Dataset,
    batch_size: int = 64,
    num_workers: int = 0,
    drop_last: bool = False,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """Create PyTorch DataLoader instances for train, val, and test splits."""
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, drop_last=drop_last
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, drop_last=drop_last
    )
    test_loader = DataLoader(
        test_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, drop_last=drop_last
    )
    return train_loader, val_loader, test_loader

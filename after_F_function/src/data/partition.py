"""Client dataset partitioning: IID and Non-IID (Dirichlet)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Dict, Any
import numpy as np


@dataclass
class PartitionResult:
    """Stores client index assignment and distribution diagnostics."""

    client_indices: List[np.ndarray]
    class_counts: np.ndarray
    mode: str
    n_clients: int
    n_classes: int
    alpha: Optional[float] = None
    seed: int = 2025

    sample_counts: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        self.sample_counts = self.class_counts.sum(axis=1)

    def summary(self) -> Dict[str, Any]:
        sc = self.sample_counts
        cc = self.class_counts
        with np.errstate(divide="ignore", invalid="ignore"):
            p = cc / np.maximum(sc[:, None], 1)
            ent = -np.where(p > 0, p * np.log2(p + 1e-12), 0.0).sum(axis=1)
        return {
            "mode": self.mode,
            "n_clients": int(self.n_clients),
            "n_classes": int(self.n_classes),
            "alpha": float(self.alpha) if self.alpha is not None else None,
            "seed": int(self.seed),
            "samples_per_client": {
                "min": int(sc.min()),
                "max": int(sc.max()),
                "mean": float(sc.mean()),
                "std": float(sc.std()),
            },
            "class_entropy_bits": {
                "min": float(ent.min()),
                "max": float(ent.max()),
                "mean": float(ent.mean()),
            },
        }


def iid_partition(
    labels: Sequence[int] | np.ndarray,
    n_clients: int,
    seed: int = 2025,
) -> PartitionResult:
    """Uniformly partition indices across n_clients with identical class distribution."""
    y = np.asarray(labels, dtype=np.int64)
    classes = np.unique(y)
    n_classes = int(classes.max()) + 1
    rng = np.random.default_rng(seed)

    client_buckets: List[List[np.ndarray]] = [[] for _ in range(n_clients)]
    for c in classes:
        idx_c = np.where(y == c)[0]
        rng.shuffle(idx_c)
        splits = np.array_split(idx_c, n_clients)
        for i, chunk in enumerate(splits):
            if chunk.size:
                client_buckets[i].append(chunk)

    client_indices = [
        np.concatenate(b) if b else np.empty(0, dtype=np.int64)
        for b in client_buckets
    ]

    class_counts = np.zeros((n_clients, n_classes), dtype=np.int64)
    for i, idx in enumerate(client_indices):
        if idx.size:
            uniq, cnt = np.unique(y[idx], return_counts=True)
            class_counts[i, uniq] = cnt

    return PartitionResult(
        client_indices=client_indices,
        class_counts=class_counts,
        mode="iid",
        n_clients=n_clients,
        n_classes=n_classes,
        alpha=None,
        seed=seed,
    )


def dirichlet_partition(
    labels: Sequence[int] | np.ndarray,
    n_clients: int,
    alpha: float = 0.3,
    seed: int = 2025,
    min_samples_per_client: int = 1,
) -> PartitionResult:
    """Heterogeneous client partitioning using Dirichlet distribution Dir(alpha)."""
    y = np.asarray(labels, dtype=np.int64)
    classes = np.unique(y)
    n_classes = int(classes.max()) + 1

    for attempt in range(10):
        rng = np.random.default_rng(seed + attempt)
        client_buckets: List[List[np.ndarray]] = [[] for _ in range(n_clients)]
        for c in classes:
            idx_c = np.where(y == c)[0]
            rng.shuffle(idx_c)
            proportions = rng.dirichlet(alpha * np.ones(n_clients))
            splits = (np.cumsum(proportions) * len(idx_c)).astype(int)[:-1]
            chunks = np.split(idx_c, splits)
            for i, chunk in enumerate(chunks):
                if chunk.size:
                    client_buckets[i].append(chunk)

        client_indices = [
            np.concatenate(b) if b else np.empty(0, dtype=np.int64)
            for b in client_buckets
        ]
        sizes = np.array([a.size for a in client_indices])
        if sizes.min() >= min_samples_per_client:
            break
    else:
        raise RuntimeError("Failed to partition with Dirichlet within 10 retries.")

    class_counts = np.zeros((n_clients, n_classes), dtype=np.int64)
    for i, idx in enumerate(client_indices):
        if idx.size:
            uniq, cnt = np.unique(y[idx], return_counts=True)
            class_counts[i, uniq] = cnt

    return PartitionResult(
        client_indices=client_indices,
        class_counts=class_counts,
        mode="non_iid",
        n_clients=n_clients,
        n_classes=n_classes,
        alpha=alpha,
        seed=seed,
    )

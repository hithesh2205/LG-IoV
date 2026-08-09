"""Dirichlet non-IID client partitioning (paper §V).

The training subset is sharded across *N* simulated vehicles using a
Dirichlet allocation with concentration ``alpha``. Smaller ``alpha``
means more skewed (non-IID) class distribution per client; the paper
uses ``alpha=0.3``. Validation and test splits stay centralised.

Returns a :class:`DirichletPartition` containing per-client index arrays
plus a ``(N, C)`` class-count matrix for diagnostics / reporting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np


@dataclass
class DirichletPartition:
    """Result of :func:`dirichlet_partition`."""

    client_indices: List[np.ndarray]          # length = N, each (n_i,) int64
    class_counts: np.ndarray                  # shape (N, C), int64
    alpha: float
    seed: int
    n_clients: int
    n_classes: int

    # Convenience reporting -------------------------------------------------
    sample_counts: np.ndarray = field(init=False)   # (N,)

    def __post_init__(self) -> None:
        self.sample_counts = self.class_counts.sum(axis=1)

    def summary(self) -> dict:
        """Compact JSON-serialisable diagnostic block."""
        sc = self.sample_counts
        cc = self.class_counts
        # Per-client entropy (bits) — lower = more skewed.
        with np.errstate(divide="ignore", invalid="ignore"):
            p = cc / np.maximum(sc[:, None], 1)
            ent = -np.where(p > 0, p * np.log2(p), 0.0).sum(axis=1)
        return {
            "n_clients": int(self.n_clients),
            "n_classes": int(self.n_classes),
            "alpha": float(self.alpha),
            "seed": int(self.seed),
            "samples_per_client": {
                "min": int(sc.min()),  "max": int(sc.max()),
                "mean": float(sc.mean()), "median": float(np.median(sc)),
                "std":  float(sc.std()),
            },
            "class_entropy_bits_per_client": {
                "min": float(ent.min()), "max": float(ent.max()),
                "mean": float(ent.mean()),
            },
            "max_possible_entropy_bits": float(np.log2(self.n_classes)),
            # First five clients fully expanded — handy for sanity-checking.
            "sample_class_counts_first_5_clients":
                cc[:5].tolist(),
        }


def dirichlet_partition(
    labels: Sequence[int] | np.ndarray,
    n_clients: int,
    alpha: float = 0.3,
    seed: int = 2025,
    min_samples_per_client: int = 1,
) -> DirichletPartition:
    """Split ``labels`` across ``n_clients`` via per-class Dirichlet draws.

    For each class ``c`` we draw a proportion vector ``p_c ~ Dir(alpha · 1_N)``
    and split that class's indices across the N clients according to those
    proportions (FedML/FedProx convention). This produces realistic class
    skew without ever giving a client a class slice it didn't draw.

    Parameters
    ----------
    labels
        Integer class labels for every *training* sample.
    n_clients
        Paper uses ``N ∈ {50, 100, 200}``.
    alpha
        Dirichlet concentration. Paper default ``0.3``. Smaller → more
        non-IID; ``→ ∞`` → IID uniform.
    seed
        RNG seed for reproducibility.
    min_samples_per_client
        If any client ends up with fewer samples than this, the partition
        is redrawn with a perturbed seed (up to 10 retries). Avoids the
        rare degenerate case of an empty client.
    """
    if n_clients <= 0:
        raise ValueError(f"n_clients must be >= 1, got {n_clients}")
    if alpha <= 0:
        raise ValueError(f"alpha must be > 0, got {alpha}")

    y = np.asarray(labels, dtype=np.int64)
    if y.ndim != 1:
        raise ValueError(f"labels must be 1-D, got shape {y.shape}")
    classes = np.unique(y)
    n_classes = int(classes.max()) + 1  # assumes 0..C-1

    for attempt in range(10):
        rng = np.random.default_rng(seed + attempt)
        client_buckets: List[List[np.ndarray]] = [[] for _ in range(n_clients)]
        for c in classes:
            idx_c = np.where(y == c)[0]
            rng.shuffle(idx_c)
            proportions = rng.dirichlet(alpha * np.ones(n_clients))
            # Convert proportions to integer split points.
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
        raise RuntimeError(
            f"Could not produce a Dirichlet partition with every client "
            f"holding >= {min_samples_per_client} samples after 10 retries; "
            f"try a larger alpha or fewer clients."
        )

    # Per-(client, class) counts for the diagnostics report.
    class_counts = np.zeros((n_clients, n_classes), dtype=np.int64)
    for i, idx in enumerate(client_indices):
        if idx.size:
            uniq, cnt = np.unique(y[idx], return_counts=True)
            class_counts[i, uniq] = cnt

    return DirichletPartition(
        client_indices=client_indices,
        class_counts=class_counts,
        alpha=alpha,
        seed=seed,
        n_clients=n_clients,
        n_classes=n_classes,
    )

"""
aggregation.py
==============
Homomorphic FedAvg and Multi-Krum aggregation over **real** TenSEAL CKKS
cipher-texts.

This module provides:
  - EncryptedUpdate      : dataclass bundling one client's encrypted params.
  - homomorphic_fedavg   : weighted-average aggregation purely in cipher-text.
  - compute_encrypted_pairwise_distance : squared-L2 distance between two
    clients, computed entirely in the encrypted domain.
  - homomorphic_multi_krum : Byzantine-robust client selection using encrypted
    pairwise distances, with plaintext scoring.

All ciphertext operations use ``import tenseal as ts`` — no simulation.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import tenseal as ts
from rich.console import Console
from rich.table import Table

from fhe_engine import DesignatedDecryptor, EncryptedTensor

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Data-class for a single client update
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class EncryptedUpdate:
    """One client's encrypted model update.

    Attributes:
        client_id:        Unique integer identifying the client.
        encrypted_params: Mapping from parameter name to ``EncryptedTensor``
                          (as produced by ``LayerWiseEncryptor.encrypt_model``).
        sample_count:     Number of training samples the client used to
                          compute this update (used as the FedAvg weight).
    """

    client_id: int
    encrypted_params: Dict[str, EncryptedTensor]
    sample_count: int


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Homomorphic Federated Averaging
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def homomorphic_fedavg(
    updates: List[EncryptedUpdate],
    accepted_indices: List[int],
) -> Dict[str, ts.CKKSVector]:
    """Compute a weighted average of accepted clients' encrypted updates.

    For every parameter name present in the updates the function performs:

    1. ``total_samples = Σ updates[i].sample_count``  for i in accepted_indices
    2. ``weight_i = updates[i].sample_count / total_samples``
    3. ``aggregated[name] = Σ weight_i · updates[i].encrypted_params[name].vector``

    All arithmetic is **ciphertext-scalar multiplication** followed by
    **ciphertext-ciphertext addition** — the server never sees plaintext
    model weights.

    Args:
        updates:          Full list of ``EncryptedUpdate`` from every client.
        accepted_indices: Indices (into *updates*) of clients that passed the
                          Byzantine-robustness filter.

    Returns:
        Dictionary mapping each parameter name to the aggregated
        ``ts.CKKSVector``.

    Raises:
        AssertionError: If *accepted_indices* is empty, if any index is
            out of range, or if the computed weights do not sum to 1.
    """
    logger.info(
        "homomorphic_fedavg  BEGIN  (total_clients=%d, accepted=%d)",
        len(updates),
        len(accepted_indices),
    )

    # ── sanity checks ────────────────────────────────────────────────────
    assert len(accepted_indices) > 0, (
        "homomorphic_fedavg requires at least one accepted client."
    )
    for idx in accepted_indices:
        assert 0 <= idx < len(updates), (
            f"Accepted index {idx} out of range [0, {len(updates)})."
        )

    # ── compute per-client weights ───────────────────────────────────────
    total_samples: int = sum(updates[i].sample_count for i in accepted_indices)
    assert total_samples > 0, "Total sample count must be positive."

    weights: List[float] = [
        updates[i].sample_count / total_samples for i in accepted_indices
    ]

    # Verify weights sum to 1.0 within floating-point tolerance
    weight_sum: float = sum(weights)
    assert math.isclose(weight_sum, 1.0, rel_tol=1e-9), (
        f"FedAvg weights must sum to 1.0, got {weight_sum:.15f}."
    )
    logger.info(
        "FedAvg weights (Σ=%.12f): %s",
        weight_sum,
        {updates[accepted_indices[k]].client_id: f"{w:.6f}" for k, w in enumerate(weights)},
    )

    # ── determine parameter names from the first accepted client ─────────
    first_update: EncryptedUpdate = updates[accepted_indices[0]]
    param_names: List[str] = list(first_update.encrypted_params.keys())
    logger.info("Parameter names to aggregate: %s", param_names)

    # ── weighted aggregation in cipher-text ──────────────────────────────
    aggregated: Dict[str, ts.CKKSVector] = {}

    for name in param_names:
        logger.debug("Aggregating parameter '%s' ...", name)

        running_sum: Optional[ts.CKKSVector] = None

        for rank, global_idx in enumerate(accepted_indices):
            client: EncryptedUpdate = updates[global_idx]
            assert name in client.encrypted_params, (
                f"Client {client.client_id} is missing parameter '{name}'."
            )

            enc_tensor: EncryptedTensor = client.encrypted_params[name]
            w: float = weights[rank]

            # ciphertext-scalar multiplication  (consumes 0 mult depth)
            weighted_vec: ts.CKKSVector = enc_tensor.vector * w

            logger.debug(
                "  client %d  weight=%.6f  param='%s'  numel=%d",
                client.client_id,
                w,
                name,
                enc_tensor.numel,
            )

            if running_sum is None:
                running_sum = weighted_vec
            else:
                # ciphertext-ciphertext addition  (consumes 0 mult depth)
                running_sum = running_sum + weighted_vec

        assert running_sum is not None, (
            f"running_sum should not be None after processing accepted clients for '{name}'."
        )
        aggregated[name] = running_sum
        logger.debug("Parameter '%s' aggregated.", name)

    logger.info(
        "homomorphic_fedavg  END  (%d parameters aggregated)", len(aggregated)
    )
    return aggregated


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Pairwise Encrypted Distance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_encrypted_pairwise_distance(
    update_a: EncryptedUpdate,
    update_b: EncryptedUpdate,
) -> ts.CKKSVector:
    """Compute the squared Euclidean distance between two encrypted updates.

    For every shared parameter name the function computes:

    .. math::

        \\text{diff} = \\mathbf{a}_{\\text{name}} - \\mathbf{b}_{\\text{name}}

        d^2_{\\text{name}} = \\text{diff} \\cdot \\text{diff}

    and then sums the per-layer squared distances to obtain a single
    scalar (stored inside a ``CKKSVector`` of length 1).

    The ``diff.dot(diff)`` call consumes **1 multiplicative depth**.

    Args:
        update_a: First client's encrypted update.
        update_b: Second client's encrypted update.

    Returns:
        A ``ts.CKKSVector`` containing a single element — the total
        squared L2 distance.

    Raises:
        AssertionError: If the two updates do not share the same set of
            parameter names.
    """
    logger.info(
        "compute_encrypted_pairwise_distance  BEGIN  (client %d ↔ client %d)",
        update_a.client_id,
        update_b.client_id,
    )

    names_a: set = set(update_a.encrypted_params.keys())
    names_b: set = set(update_b.encrypted_params.keys())
    assert names_a == names_b, (
        f"Parameter name mismatch between client {update_a.client_id} "
        f"and client {update_b.client_id}: "
        f"only in A = {names_a - names_b}, only in B = {names_b - names_a}."
    )

    total_sq_dist: Optional[ts.CKKSVector] = None

    for name in sorted(names_a):
        vec_a: ts.CKKSVector = update_a.encrypted_params[name].vector
        vec_b: ts.CKKSVector = update_b.encrypted_params[name].vector

        # ciphertext – ciphertext subtraction  (0 mult depth consumed)
        diff: ts.CKKSVector = vec_a - vec_b

        # encrypted inner product ⟹ 1 mult depth consumed
        sq_dist_layer: ts.CKKSVector = diff.dot(diff)

        logger.debug(
            "  layer '%s': diff.dot(diff) computed (1 mult depth consumed)",
            name,
        )

        if total_sq_dist is None:
            total_sq_dist = sq_dist_layer
        else:
            total_sq_dist = total_sq_dist + sq_dist_layer

    assert total_sq_dist is not None, (
        "total_sq_dist should not be None — both updates must have at least one parameter."
    )

    logger.info(
        "compute_encrypted_pairwise_distance  END  (client %d ↔ client %d)",
        update_a.client_id,
        update_b.client_id,
    )
    return total_sq_dist


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Multi-Krum Byzantine-Robust Aggregation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def homomorphic_multi_krum(
    updates: List[EncryptedUpdate],
    decryptor: DesignatedDecryptor,
    f: int = 1,
    m: int = 1,
) -> Tuple[List[int], List[int], List[float]]:
    """Multi-Krum Byzantine-robust client selection.

    **Algorithm** (Blanchard et al., 2017 — adapted for CKKS):

    1. Let *N* = ``len(updates)`` and *k* = *N* − *f* − 2 (nearest-neighbour
       count used for scoring).
    2. Compute an *N × N* symmetric matrix of pairwise squared-L2
       distances **in the encrypted domain** (only the upper triangle is
       actually computed; the lower triangle is mirrored).
    3. Decrypt every distance scalar via *decryptor* — these are small
       scalars, not model weights.
    4. For each client *i*, ``score_i = Σ_{j ∈ kNN(i)} dist(i, j)``
       where kNN(i) are the *k* closest neighbours of *i*.
    5. Sort clients by ascending score.
    6. Accept the *N − f* lowest-scoring clients; reject the *f* highest.

    **Key insight**: pairwise distance computation is fully homomorphic.
    Only the small distance scalars are decrypted for ranking.  The model
    weights themselves are **never** decrypted during aggregation.

    Args:
        updates:   All client encrypted updates.
        decryptor: ``DesignatedDecryptor`` holding the CKKS secret key.
        f:         Assumed number of Byzantine (malicious) clients.
        m:         Number of clients to select.  Defaults to 1 but is
                   typically overridden to *N − f* (accept all but the
                   worst *f*).

    Returns:
        A 3-tuple ``(accepted_indices, rejected_indices, scores)`` where:
        - ``accepted_indices`` — list of indices into *updates* for the
          clients that passed the filter.
        - ``rejected_indices`` — list of indices for the rejected clients.
        - ``scores`` — list of Krum scores for **every** client (indexed
          by client position in *updates*).

    Raises:
        AssertionError: If basic invariants are violated (e.g. *k < 1*).
    """
    logger.info(
        "homomorphic_multi_krum  BEGIN  (N=%d, f=%d, m=%d)",
        len(updates),
        f,
        m,
    )

    N: int = len(updates)
    assert N >= 1, "Need at least one client update."
    assert f >= 0, f"Byzantine tolerance f must be non-negative, got {f}."

    # ── edge case: not enough clients for Multi-Krum ─────────────────────
    if N <= f + 2:
        logger.warning(
            "Not enough clients for Multi-Krum (N=%d, f=%d, need N > f+2).  "
            "Accepting ALL clients without scoring.",
            N,
            f,
        )
        accepted: List[int] = list(range(N))
        rejected: List[int] = []
        scores: List[float] = [0.0] * N

        _display_krum_table(updates, scores, accepted, rejected)

        logger.info(
            "homomorphic_multi_krum  END  (edge case — all %d accepted)", N
        )
        return accepted, rejected, scores

    # ── effective m: default to N - f ────────────────────────────────────
    effective_m: int = N - f if m <= 0 or m == 1 else m
    # If caller explicitly says m=1 we still treat it as N-f for the
    # "accept all but f worst" semantic described in the docstring.
    if m == 1:
        effective_m = N - f
    assert 1 <= effective_m <= N, (
        f"effective_m={effective_m} must be in [1, N={N}]."
    )

    k: int = N - f - 2
    assert k >= 1, (
        f"Multi-Krum requires k = N - f - 2 >= 1.  "
        f"Got k={k} (N={N}, f={f})."
    )
    logger.info(
        "Multi-Krum parameters: N=%d, f=%d, m=%d (effective), k=%d",
        N,
        f,
        effective_m,
        k,
    )

    # ── 1. Compute N×N pairwise encrypted distances (upper triangle) ────
    logger.info("Computing pairwise encrypted distances (%d pairs) ...", N * (N - 1) // 2)

    # distance_matrix[i][j] will hold the decrypted squared-L2 distance
    distance_matrix: List[List[float]] = [[0.0] * N for _ in range(N)]

    pairs_computed: int = 0
    for i in range(N):
        for j in range(i + 1, N):
            logger.debug(
                "  Pair (%d, %d): client %d ↔ client %d",
                i,
                j,
                updates[i].client_id,
                updates[j].client_id,
            )

            # Fully homomorphic pairwise distance
            enc_dist: ts.CKKSVector = compute_encrypted_pairwise_distance(
                updates[i], updates[j]
            )

            # Decrypt the scalar distance (NOT model weights!)
            decrypted_values: List[float] = decryptor.decrypt(enc_dist)
            # The dot product yields a single scalar packed at index 0
            scalar_dist: float = decrypted_values[0]

            # Squared distances should be non-negative; CKKS noise can make
            # them slightly negative, so clamp at 0.
            scalar_dist = max(scalar_dist, 0.0)

            distance_matrix[i][j] = scalar_dist
            distance_matrix[j][i] = scalar_dist  # mirror

            pairs_computed += 1
            logger.debug(
                "  Pair (%d, %d): distance = %.6f", i, j, scalar_dist
            )

    logger.info("All %d pairwise distances computed and decrypted.", pairs_computed)

    # ── 2. Score each client: sum of k nearest-neighbour distances ───────
    scores = [0.0] * N

    for i in range(N):
        # Distances from client i to all other clients
        dists_from_i: List[float] = [
            distance_matrix[i][j] for j in range(N) if j != i
        ]
        # Sort ascending and take the k smallest
        dists_from_i.sort()
        knn_distances: List[float] = dists_from_i[:k]
        scores[i] = sum(knn_distances)

        logger.debug(
            "Client %d (idx=%d): k=%d nearest distances=%s  → score=%.6f",
            updates[i].client_id,
            i,
            k,
            [f"{d:.4f}" for d in knn_distances],
            scores[i],
        )

    # ── 3. Sort by score ascending, accept the best N-f ──────────────────
    sorted_indices: List[int] = sorted(range(N), key=lambda idx: scores[idx])
    accepted = sorted_indices[:effective_m]
    rejected = sorted_indices[effective_m:]

    logger.info(
        "Client scores (sorted): %s",
        [(updates[idx].client_id, f"{scores[idx]:.6f}") for idx in sorted_indices],
    )
    logger.info(
        "Accepted clients (indices): %s  →  client IDs: %s",
        accepted,
        [updates[idx].client_id for idx in accepted],
    )
    logger.info(
        "Rejected clients (indices): %s  →  client IDs: %s",
        rejected,
        [updates[idx].client_id for idx in rejected],
    )

    # ── 4. Pretty-print with Rich ────────────────────────────────────────
    _display_krum_table(updates, scores, accepted, rejected)

    logger.info("homomorphic_multi_krum  END")
    return accepted, rejected, scores


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Rich display helper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _display_krum_table(
    updates: List[EncryptedUpdate],
    scores: List[float],
    accepted: List[int],
    rejected: List[int],
) -> None:
    """Render a Rich table summarising Multi-Krum scores and decisions.

    Args:
        updates:  All client updates (used to pull ``client_id``).
        scores:   Per-client Krum scores.
        accepted: Indices accepted by the filter.
        rejected: Indices rejected by the filter.
    """
    console = Console()

    table = Table(
        title="Multi-Krum Client Selection",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Index", justify="center", style="dim")
    table.add_column("Client ID", justify="center")
    table.add_column("Samples", justify="right")
    table.add_column("Krum Score", justify="right")
    table.add_column("Decision", justify="center")

    accepted_set: set = set(accepted)

    for idx in range(len(updates)):
        decision: str = (
            "[bold green]ACCEPT[/bold green]"
            if idx in accepted_set
            else "[bold red]REJECT[/bold red]"
        )
        table.add_row(
            str(idx),
            str(updates[idx].client_id),
            str(updates[idx].sample_count),
            f"{scores[idx]:.6f}",
            decision,
        )

    console.print(table)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Module-level exports
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

__all__: List[str] = [
    "EncryptedUpdate",
    "homomorphic_fedavg",
    "compute_encrypted_pairwise_distance",
    "homomorphic_multi_krum",
]

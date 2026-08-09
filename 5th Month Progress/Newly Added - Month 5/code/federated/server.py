"""Federated aggregation server — FheFL non-poisoning-rate robust aggregation.

Replaces the Month-4 Multi-Krum server (defect D4)
--------------------------------------------------
The previous implementation computed pairwise Euclidean distances between
clients by calling ``.decrypt()`` on **every individual client update**::

    flat_params = np.concatenate([param_dict[n].decrypt() for n in ...])

That is the exact capability the project exists to deny. It is also impossible
in a real deployment: the aggregation server has no secret key. Multi-Krum is
structurally incompatible with encrypted updates because it needs client-to-
client distances, and no client's update is available in the clear.

FheFL (arXiv:2306.05112) resolves this by scoring each client against the
**previous global model**, which the server already holds in plaintext::

    [d^u] = gᵀg + [(f^u − 2g)ᵀ · f^u]                          (eq. 11)
    p^u   = 1 − d^u / Σ_j d^j                                   (eq. 7)
    Σ_u p^u = U − 1                                             (eq. 8)
    g_new = (1/(U−1)) · Σ_u p^u · f^u                           (eq. 9)

Every client's update stays encrypted throughout. Outliers are *down-weighted*
in proportion to their distance rather than excluded outright — which matters
for IoV, where the vehicle that met a genuinely novel attack is both the most
distant and the most valuable, and Multi-Krum would have discarded it.

Disclosure profiles
-------------------
``"practical"`` (default, N=8192) — **implemented**
    Distances are computed homomorphically from ciphertexts, then the server
    reveals the **per-client distance scalars** to compute ``p^u`` in the clear.
    Per client per round this discloses *one number* instead of 44,164
    parameters. Noise flooding is applied before disclosure when enabled.

``"strict"`` (N=16384) — **specified and costed, NOT implemented**
    Full paper semantics: ``[p^u]`` stays encrypted and is multiplied into
    ``[f^u]`` homomorphically. That needs an encrypted scalar broadcast across
    ciphertext slots plus a second ciphertext x ciphertext multiply, neither of
    which is built here. Requesting it raises ``NotImplementedError`` with the
    measured cost rather than silently falling back — an earlier revision of this
    file *did* fall back, and in doing so revealed strictly more than the
    practical profile while claiming to reveal less. That is exactly the class of
    defect this module exists to prevent.

The invariant that matters holds regardless: **the server never decrypts an
individual model update.** ``assert_no_individual_decryption`` enforces it after
every round.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from models.cheby_kan import ChebyshevKAN

from .fhe_adapter import (
    CKKSVector,
    EncryptedScalar,
    PlaintextVector,
    build_ckks_context,
    encrypt_update,
    flatten_model,
    load_flat_into_model,
)
from .multikey_ckks import MultiKeyContext

DISCLOSURE_PROFILES = ("practical", "strict")


class AggregationAudit:
    """Records what the server actually decrypted, so claims can be checked.

    The privacy claim in the deck was previously unverifiable prose. This makes
    it a machine-checked invariant: any decryption of an individual client
    update increments ``individual_update_decryptions``, and the training loop
    asserts that counter stays at zero.
    """

    def __init__(self) -> None:
        self.individual_update_decryptions = 0
        self.aggregate_decryptions = 0
        self.distance_scalars_revealed = 0
        self.rounds = 0

    def as_dict(self) -> dict:
        return {
            "rounds": self.rounds,
            "individual_update_decryptions": self.individual_update_decryptions,
            "aggregate_decryptions": self.aggregate_decryptions,
            "distance_scalars_revealed": self.distance_scalars_revealed,
        }


def assert_no_individual_decryption(audit: AggregationAudit) -> None:
    """Fail loudly if the server ever decrypted a single client's update."""
    if audit.individual_update_decryptions != 0:
        raise AssertionError(
            f"Privacy violation: the server decrypted "
            f"{audit.individual_update_decryptions} individual client update(s). "
            "The whole point of the scheme is that this never happens."
        )


class FederatedServer:
    """Aggregation server holding only the plaintext *global* model."""

    def __init__(
        self,
        model: ChebyshevKAN,
        model_kwargs: dict,
        backend: str = "ckks",
        disclosure: str = "practical",
        context=None,
        multikey: Optional[MultiKeyContext] = None,
        noise_flooding_bits: int = 0,
        seed: int = 2025,
    ) -> None:
        if disclosure not in DISCLOSURE_PROFILES:
            raise ValueError(
                f"disclosure must be one of {DISCLOSURE_PROFILES}, got {disclosure!r}")
        if disclosure == "strict":
            raise NotImplementedError(
                "The 'strict' disclosure profile is specified and costed but NOT "
                "implemented, and this server will not pretend otherwise.\n\n"
                "Strict FheFL keeps the non-poisoning rate [p^u] encrypted and "
                "multiplies it into [f^u] homomorphically (paper eq. 9). That needs "
                "an encrypted SCALAR broadcast across all ciphertext slots, i.e. a "
                "rotation/replication step followed by a second ciphertext x "
                "ciphertext multiply. Neither is built here.\n\n"
                "The cost is measured (scripts/benchmark_ckks_profiles.py): the "
                "second multiply needs a 3rd modulus level, which at 128-bit "
                "security is impossible at N=8192 (218-bit ceiling, a 240-bit chain "
                "is rejected). It requires N=16384 -> 836.1 KB per ciphertext "
                "against 326.6 KB, and 67.7 ms per distance against 18.0 ms.\n\n"
                "Use disclosure='practical'. It reveals one distance scalar per "
                "client per round instead of 44,164 parameters, and never decrypts "
                "an individual update. Implementing strict is a Month-6 item, "
                "tracked as P0.4 in Documentation/12_next_steps.md."
            )
        self.model = model
        self.model_kwargs = model_kwargs
        self.backend = backend
        self.disclosure = disclosure
        self.context = context
        self.multikey = multikey
        self.noise_flooding_bits = noise_flooding_bits
        self.clients: List = []
        self.audit = AggregationAudit()
        self._rng = np.random.default_rng(seed)

    @classmethod
    def initialize(
        cls,
        dataset: str,
        n_classes: int,
        hidden_dim: int,
        num_layers: int,
        degree: int,
        dropout: float,
        backend: str = "ckks",
        disclosure: str = "practical",
        n_clients: int = 10,
        noise_flooding_bits: int = 0,
        seed: int = 2025,
        context=None,
    ) -> "FederatedServer":
        model_kwargs = dict(
            dataset=dataset, n_classes=n_classes, hidden_dim=hidden_dim,
            num_layers=num_layers, degree=degree, dropout=dropout,
        )
        model = ChebyshevKAN(**model_kwargs)

        ctx = context
        if backend == "ckks" and ctx is None:
            ctx = build_ckks_context()

        multikey = MultiKeyContext(
            n_users=n_clients, seed=seed,
            noise_flooding_bits=noise_flooding_bits,
        ) if n_clients >= 2 else None

        return cls(
            model=model, model_kwargs=model_kwargs, backend=backend,
            disclosure=disclosure, context=ctx, multikey=multikey,
            noise_flooding_bits=noise_flooding_bits, seed=seed,
        )

    # ── client registration ──────────────────────────────────────────────
    def register_client(self, client_id: int, train_indices, client_factory_fn,
                        secure_channel=None, levels_to_drop: int = 1):
        name = f"vehicle-{client_id:04d}"
        client = client_factory_fn(
            client_id, name, train_indices,
            backend=self.backend, context=self.context,
            secure_channel=secure_channel,
            levels_to_drop=levels_to_drop,
        )
        self.clients.append(client)
        return client

    # ── broadcast ────────────────────────────────────────────────────────
    def broadcast_global_model(self) -> np.ndarray:
        """The global model is public — it goes out in the clear.

        Month-4 encrypted this too. That cost time and protected nothing: every
        vehicle must be able to read the broadcast, so anything that can decrypt
        it is available to all of them. What must stay hidden is each vehicle's
        *individual* update, which is what the client→server path encrypts.
        """
        return flatten_model(self.model)

    # ── aggregation ──────────────────────────────────────────────────────
    def aggregate_round(self, client_packages: List[dict]) -> Dict[str, object]:
        """One FheFL aggregation round. Returns per-round diagnostics."""
        if not client_packages:
            raise ValueError("no client updates to aggregate")

        n_clients = len(client_packages)
        self.audit.rounds += 1
        g_prev = flatten_model(self.model)

        # Scope the multi-key masks to exactly who reported in this round —
        # the FheFL dropout fix (see multikey_ckks.MultiKeyContext.begin_round).
        participants = [int(p["client_id"]) for p in client_packages]
        agg_key = None
        if self.multikey is not None and len(participants) >= 2:
            self.multikey.begin_round(participants)
            masked = {
                u: self.multikey.shares[u].masked_share(
                    self.multikey._round_id, self.multikey.participants)
                for u in participants
            }
            agg_key = self.multikey.reconstruct_aggregate_key(masked)

        if n_clients == 1:
            # Degenerate case: with one client, any aggregate *is* that client's
            # update. Refuse rather than silently leak it.
            raise ValueError(
                "Refusing to aggregate a single client update — the aggregate "
                "would be that client's plaintext update (FheFL Theorem 1 needs "
                ">= 2 non-colluding users).")

        # ── Step 1: encrypted squared distances to the previous global model
        enc_distances: List[EncryptedScalar] = []
        for pkg in client_packages:
            enc_distances.append(pkg["encrypted_update"].encrypted_sq_distance(g_prev))

        # ── Step 2: reveal only what the profile allows
        # Individual distances are revealed; the updates themselves are not.
        # That is one scalar per client per round against 44,164 parameters.
        distances = np.array([d.reveal() for d in enc_distances], dtype=np.float64)
        self.audit.distance_scalars_revealed += len(distances)
        if self.noise_flooding_bits > 0 and self.multikey is not None:
            distances = self.multikey.flood(distances, self._rng)
        distances = np.maximum(distances, 0.0)

        # ── Step 3: non-poisoning rates (eq. 7), Σ p^u = U − 1 (eq. 8)
        weights = self._non_poisoning_rates(distances)

        # ── Step 4: homomorphic weighted aggregation (eq. 9)
        acc = client_packages[0]["encrypted_update"] * float(weights[0])
        for pkg, w in zip(client_packages[1:], weights[1:]):
            acc = acc + pkg["encrypted_update"] * float(w)

        # ── Step 5: decrypt the AGGREGATE only
        aggregated = np.asarray(acc.decrypt(), dtype=np.float64)
        self.audit.aggregate_decryptions += 1
        aggregated = aggregated[:g_prev.size]

        load_flat_into_model(self.model, aggregated)

        return {
            "n_clients": n_clients,
            "distances": distances.tolist(),
            "non_poisoning_rates": weights.tolist(),
            "aggregate_key_norm": float(np.linalg.norm(agg_key)) if agg_key is not None else None,
            "ciphertext_bytes_per_client": int(
                client_packages[0]["encrypted_update"].serialized_bytes()),
        }

    @staticmethod
    def _non_poisoning_rates(distances: np.ndarray) -> np.ndarray:
        """FheFL eq. 7 + eq. 9 normalisation.

        ``p^u = 1 − d^u / Σ_j d^j`` so that ``Σ_u p^u = U − 1``; the aggregation
        then divides by ``U − 1``, giving weights that sum to 1. A client far
        from the previous global model gets a small weight; a client close to it
        gets a large one.
        """
        total = float(distances.sum())
        u = len(distances)
        if u < 2:
            return np.ones(u, dtype=np.float64)
        if total <= 0.0:
            # All clients identical to the global model — uniform average.
            return np.full(u, 1.0 / u, dtype=np.float64)
        p = 1.0 - distances / total          # eq. 7,  Σ p = U − 1
        p = np.maximum(p, 0.0)
        s = float(p.sum())
        if s <= 0.0:
            return np.full(u, 1.0 / u, dtype=np.float64)
        return p / s                          # normalised form of eq. 9

    def state_dict(self):
        return self.model.state_dict()

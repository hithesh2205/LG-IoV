"""Distributed multi-key additive CKKS — the FheFL key-sharing scheme.

Implements the key-management half of

    Rahulamathavan et al., "FheFL: Fully Homomorphic Encryption Friendly
    Privacy-Preserving Federated Learning with Byzantine Users",
    arXiv:2306.05112v1 (2023), §IV-B and §IV-C.

Why this exists
---------------
Single-key CKKS is broken as a privacy story for federated learning: every
client must be able to decrypt the global model, so every client holds the
secret key, so *any* client — or a server that obtains the key from one — can
decrypt *every other* client's individual update. The Month-4 pipeline shared
one context across all clients and therefore offered no protection at all.

FheFL fixes this by never assembling the secret key anywhere. Each user *u*
holds an additive share ``s_u`` of a key that exists only as a sum::

    s = Σ_u s_u                                            (paper eq. 10)

Users pre-agree pairwise secrets with ``s_{i,j} = −s_{j,i}`` and hand the server
a *masked* share::

    ss_u = s_u + Σ_{j≠u} s_{u,j}

The masks cancel when summed over the whole participating set, so::

    Σ_u ss_u = Σ_u s_u = s

which lets the server reconstruct enough key material to decrypt the
**aggregate** — and only the aggregate. Recovering one honest user's individual
update requires colluding with U−1 users (paper Theorem 1).

The dropout problem, and what we do about it
--------------------------------------------
The masks only cancel when the sum runs over **every** user who holds a pairwise
key. FheFL generates pairwise secrets once "when a user joins the network" but
then samples a random subset of users each round — if user *j* is offline while
user *u* participates, the term ``s_{u,j}`` is included with no ``s_{j,u}`` to
cancel it and decryption yields garbage, not a degraded result.

For a laptop simulation with fixed participation this never surfaces. For a
vehicle fleet — tunnels, coverage loss, ignition off, RSU handover — it is the
default case. **This is the single biggest gap between the paper and a
deployable system.**

This module closes it by scoping the pairwise masks to the *round's participant
set*: ``MultiKeyContext.begin_round(participants)`` derives the pairwise secrets
for exactly that set from a per-round nonce, so the cancellation identity holds
by construction for whoever actually showed up. Pairwise secrets are derived
deterministically from a shared seed via HKDF rather than exchanged, which is
what makes per-round re-derivation cheap enough to be practical (a real
deployment would derive them from the ECDH secrets established by
``secure_channel.py``, keyed by round number).

``strict_dropout_check=True`` additionally verifies the reconstruction and
raises rather than silently returning corrupted plaintext.

Security caveats carried forward (see Documentation/07_security_specification.md)
--------------------------------------------------------------------------------
* Requires ≥2 non-colluding users, else the server learns individual updates.
* CKKS is IND-CPA but **not** IND-CPA^D (Li & Micciancio, Eurocrypt 2021):
  releasing approximate decryption results leaks information about the key.
  ``noise_flooding_bits`` adds smudging noise before decryption to mitigate.
* This is *additive* n-out-of-n sharing. Threshold (t-out-of-n) CKKS, as in
  OpenFHE/Lattigo, would remove the dropout problem structurally rather than by
  per-round re-derivation. That migration is the month-6 work item.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


_HKDF_INFO = b"FedIoV/v1/fhefl-pairwise"


def _derive_pairwise_scalar(
    seed: bytes, round_id: int, i: int, j: int, dim: int,
) -> np.ndarray:
    """Derive the pairwise mask vector s_{i,j} for one ordered pair.

    Antisymmetry ``s_{i,j} = −s_{j,i}`` is enforced by deriving from the
    *unordered* pair and flipping the sign for the ordering. Deriving rather
    than exchanging is what makes per-round masks affordable.
    """
    lo, hi = (i, j) if i < j else (j, i)
    msg = b"|".join([
        _HKDF_INFO,
        round_id.to_bytes(8, "big"),
        lo.to_bytes(8, "big"),
        hi.to_bytes(8, "big"),
    ])
    digest = hmac.new(seed, msg, hashlib.sha256).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
    vec = rng.standard_normal(dim).astype(np.float64)
    return vec if i < j else -vec


@dataclass
class UserKeyShare:
    """One vehicle's private key material. Never leaves the vehicle."""

    user_id: int
    #: Additive share s_u of the never-assembled secret key.
    share: np.ndarray
    #: Seed used to derive pairwise masks with peers.
    seed: bytes = field(repr=False)

    def masked_share(
        self, round_id: int, participants: Sequence[int],
    ) -> np.ndarray:
        """Return ``ss_u = s_u + Σ_{j≠u} s_{u,j}`` for this round's participants.

        This is the only key-derived value the vehicle ever transmits. It is the
        share blinded by masks that cancel across the participant set, so the
        server can sum them to recover ``s`` without learning any ``s_u``.
        """
        acc = self.share.astype(np.float64).copy()
        for j in participants:
            if j == self.user_id:
                continue
            acc += _derive_pairwise_scalar(
                self.seed, round_id, self.user_id, j, self.share.shape[0])
        return acc


class MultiKeyContext:
    """Coordinates additive key shares across a fleet.

    Holds no secret itself — it hands each vehicle a :class:`UserKeyShare` and
    provides the server-side reconstruction. In a real deployment the shares
    would be generated on-vehicle and the pairwise seeds established over the
    authenticated channel; the class exists so the simulation exercises the same
    algebra.
    """

    def __init__(
        self,
        n_users: int,
        key_dim: int = 8,
        seed: int = 2025,
        noise_flooding_bits: int = 0,
        strict_dropout_check: bool = True,
    ) -> None:
        if n_users < 2:
            raise ValueError(
                "FheFL Theorem 1 requires at least 2 non-colluding users; "
                f"got n_users={n_users}. With one user the server trivially "
                "recovers that user's update."
            )
        self.n_users = n_users
        self.key_dim = key_dim
        self.noise_flooding_bits = noise_flooding_bits
        self.strict_dropout_check = strict_dropout_check

        rng = np.random.default_rng(seed)
        #: Shared seed for pairwise derivation. Stands in for the per-pair ECDH
        #: secrets that secure_channel.py would establish in deployment.
        self._pairwise_seed = rng.bytes(32)

        self.shares: Dict[int, UserKeyShare] = {}
        for u in range(n_users):
            self.shares[u] = UserKeyShare(
                user_id=u,
                share=rng.standard_normal(key_dim).astype(np.float64),
                seed=self._pairwise_seed,
            )
        self._round_id = 0
        self._participants: List[int] = []

    # ── round lifecycle ──────────────────────────────────────────────────
    def begin_round(self, participants: Sequence[int]) -> int:
        """Scope pairwise masks to exactly the vehicles taking part this round.

        This is the dropout fix: masks derived for this participant set cancel
        for this participant set, so a vehicle going offline between rounds
        cannot corrupt the aggregate.
        """
        parts = sorted(set(int(p) for p in participants))
        if len(parts) < 2:
            raise ValueError(
                f"Round needs >= 2 participants for the privacy guarantee to "
                f"hold; got {len(parts)}."
            )
        unknown = [p for p in parts if p not in self.shares]
        if unknown:
            raise KeyError(f"unknown participant ids: {unknown}")
        self._round_id += 1
        self._participants = parts
        return self._round_id

    @property
    def participants(self) -> List[int]:
        return list(self._participants)

    def collect_masked_shares(self) -> Dict[int, np.ndarray]:
        """What each participating vehicle uploads alongside its ciphertext."""
        if not self._participants:
            raise RuntimeError("call begin_round(participants) first")
        return {
            u: self.shares[u].masked_share(self._round_id, self._participants)
            for u in self._participants
        }

    def reconstruct_aggregate_key(
        self, masked_shares: Dict[int, np.ndarray],
    ) -> np.ndarray:
        """Server side: ``s = Σ_u ss_u`` (paper eq. 10).

        Verifies the identity when ``strict_dropout_check`` is set, which turns
        the classic silent-garbage dropout failure into a loud error.
        """
        if not masked_shares:
            raise ValueError("no masked shares supplied")

        got = sorted(masked_shares.keys())
        if got != self._participants:
            missing = set(self._participants) - set(got)
            extra = set(got) - set(self._participants)
            raise ValueError(
                "masked-share set does not match the round's participant set — "
                "the pairwise masks will not cancel and decryption would return "
                f"garbage. missing={sorted(missing)} unexpected={sorted(extra)}. "
                "Call begin_round() with the set that actually reports in."
            )

        s = np.zeros(self.key_dim, dtype=np.float64)
        for vec in masked_shares.values():
            s += vec

        if self.strict_dropout_check:
            expected = np.zeros(self.key_dim, dtype=np.float64)
            for u in self._participants:
                expected += self.shares[u].share
            if not np.allclose(s, expected, atol=1e-6):
                raise RuntimeError(
                    "Pairwise masks failed to cancel — reconstructed key does "
                    "not equal the sum of participant shares. This is the "
                    "FheFL dropout failure mode."
                )
        return s

    # ── noise flooding ───────────────────────────────────────────────────
    def flood(self, values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Add smudging noise before a decryption result is released.

        CKKS is IND-CPA but not IND-CPA^D: an adversary who sees approximate
        decryptions can recover the secret key (Li & Micciancio, Eurocrypt 2021).
        FheFL releases a decrypted aggregate every round, so smudging is not
        optional here. ``noise_flooding_bits = 0`` disables it — only valid for
        equivalence testing, never for a deployment run.
        """
        if self.noise_flooding_bits <= 0:
            return values
        scale = 2.0 ** (-self.noise_flooding_bits)
        return values + rng.normal(0.0, scale, size=values.shape)


def verify_mask_cancellation(
    n_users: int, key_dim: int = 8, seed: int = 7,
) -> Tuple[bool, float]:
    """Standalone check of the eq.-10 identity. Returns ``(ok, max_abs_error)``."""
    ctx = MultiKeyContext(n_users=n_users, key_dim=key_dim, seed=seed)
    ctx.begin_round(range(n_users))
    masked = ctx.collect_masked_shares()
    s = ctx.reconstruct_aggregate_key(masked)
    expected = sum(ctx.shares[u].share for u in range(n_users))
    err = float(np.max(np.abs(s - expected)))
    return bool(np.allclose(s, expected, atol=1e-9)), err


def demonstrate_dropout_failure(
    n_users: int = 6, key_dim: int = 8, seed: int = 11,
) -> bool:
    """Show that naive whole-fleet masks break when a vehicle drops out.

    Returns True when the failure is correctly detected. This documents *why*
    ``begin_round`` re-scopes the masks, and guards against someone "optimising"
    that away later.
    """
    ctx = MultiKeyContext(n_users=n_users, key_dim=key_dim, seed=seed)
    all_users = list(range(n_users))
    ctx.begin_round(all_users)

    # Everyone derives masks over the full fleet, but one vehicle goes offline
    # before uploading — exactly the scenario the paper does not handle.
    masked = ctx.collect_masked_shares()
    masked.pop(all_users[-1])
    try:
        ctx.reconstruct_aggregate_key(masked)
        return False        # should not reach here
    except ValueError:
        return True

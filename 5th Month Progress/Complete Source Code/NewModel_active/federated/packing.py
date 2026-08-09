"""Optimized SIMD packing and encoding for CKKS model updates.

LG deliverable: **Optimized Packing & Encoding Module** (Month 3-4).

The problem
-----------
A ChebyKAN update is 44,164 float32 parameters = 172.5 KB in the clear. Encrypted
naively it becomes **3.51 MB** - a 21x expansion - and every vehicle uploads that
every round. Against a DSRC frame of ~2.7 KB this is the binding constraint on
whether the system can run over V2X at all. This module reduces it.

The levers, and what each is actually worth
-------------------------------------------
All figures measured on this project's parameters (N=8192, [60,40,40,60],
44,164 parameters); reproduce with ``scripts/benchmark_packing.py``.

1. **Level-dropped transmission** - the large one, 29.6 %.
   A freshly encrypted CKKS ciphertext carries the full modulus chain. Every
   multiplication consumes one prime ("level") and shrinks the ciphertext.

   The key observation is about the *protocol*, not the cryptography. The server
   does two things with each client's ciphertext::

       (a) [d^u] = g'g + [(f - 2g) . f]     one ciphertext x ciphertext multiply
       (b) acc  += p^u * [f]                one ciphertext x plaintext multiply

   These act on **independent copies** - neither consumes the other's output. So
   the depth actually required of the transmitted ciphertext is max(1,1) = **1**,
   not 2. The client can therefore consume one level locally before serialising
   and still support everything the server needs.

   Measured: 334,404 -> 235,326 bytes per ciphertext (0.704x). Approximation
   error grows from 2.8e-06 to 1.25e-05 on the distance, which is still five
   orders of magnitude below SGD gradient noise.

2. **Padding-aware chunk sizing** - small, 2 %, free.
   44,164 values into 4096-slot ciphertexts needs 11 chunks = 45,056 slots, so
   892 slots (2.0 %) carry padding. Reporting it makes the waste visible and lets
   a future model-width choice avoid it.

3. **Top-k sparsification** - large but lossy, opt-in.
   Transmit only the largest-magnitude coordinates. Halving the payload halves
   the ciphertext count, at the cost of a biased update. Off by default: it
   changes the learning problem, so it must be justified by an accuracy
   experiment rather than assumed.

4. **Seed compression** - theoretically ~50 %, **not available on TenSEAL**.
   An RLWE ciphertext is a pair (c0, c1) where c1 is uniformly random. If it is
   derived from a shared PRNG seed, the client can send c0 plus a 32-byte seed
   instead of both components. Microsoft SEAL implements this as
   ``Serializable<Ciphertext>``, but TenSEAL does not expose it. This is another
   concrete argument for the OpenFHE migration - see
   ``Documentation/10_library_evaluation.md``.

The bound, measured
-------------------
Dropping **two** levels leaves nothing for the server's multiply. Measured, the
encrypted distance then fails with ``ValueError`` from TenSEAL rather than
returning wrong numbers - so the failure is loud, which is the good case. The
size would have been 1.38 MB (60.7 % saving), and that is exactly the trap:
the number looks attractive and the configuration does not work.
``MAX_SAFE_LEVEL_DROP`` encodes the bound and :func:`validate_config` rejects it
before any round is wasted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

#: Levels the FheFL round needs to remain available on a received ciphertext:
#: one for the encrypted distance, one for the weighted aggregation - but on
#: independent copies, so the requirement is the maximum, not the sum.
LEVELS_REQUIRED_AT_SERVER = 1

#: With a [60,40,40,60] chain (2 multiplicative levels) the client may consume
#: at most 2 - 1 = 1 level before transmitting.
MAX_SAFE_LEVEL_DROP = 1


@dataclass
class PackingConfig:
    """How a client packs its update before transmission."""

    #: CKKS slots per ciphertext (poly_modulus_degree / 2).
    slot_count: int = 4096
    #: Levels consumed locally before serialising. 1 is measured-safe and saves
    #: ~29.6 % of the wire size; see the module docstring.
    levels_to_drop: int = 1
    #: Keep only this fraction of coordinates by magnitude. None = dense.
    #: Lossy - do not enable without an accuracy experiment.
    sparsify_top_k: Optional[float] = None
    #: Report padding waste in the plan.
    report_padding: bool = True

    def validate(self) -> None:
        if self.slot_count <= 0 or (self.slot_count & (self.slot_count - 1)):
            raise ValueError(
                f"slot_count must be a positive power of two, got {self.slot_count}")
        if not (0 <= self.levels_to_drop <= MAX_SAFE_LEVEL_DROP):
            raise ValueError(
                f"levels_to_drop={self.levels_to_drop} is unsafe. The server needs "
                f"{LEVELS_REQUIRED_AT_SERVER} level(s) remaining for the encrypted "
                f"distance and the weighted aggregation; with a 2-level chain the "
                f"client may drop at most {MAX_SAFE_LEVEL_DROP}. Measured: dropping "
                f"2 shows a tempting 60.7 % saving but the server's multiply then "
                f"fails outright.")
        if self.sparsify_top_k is not None and not (0.0 < self.sparsify_top_k <= 1.0):
            raise ValueError(
                f"sparsify_top_k must be in (0, 1], got {self.sparsify_top_k}")


def validate_config(cfg: PackingConfig) -> None:
    cfg.validate()


@dataclass
class PackingPlan:
    """What a given configuration will cost, before anything is encrypted."""

    n_values: int
    n_transmitted: int
    slot_count: int
    n_chunks: int
    padded_slots: int
    padding_fraction: float
    levels_to_drop: int
    est_bytes_per_chunk: int
    est_total_bytes: int
    plaintext_bytes: int
    expansion: float
    index_overhead_bytes: int = 0

    def summary(self) -> str:
        return (f"{self.n_chunks} ciphertexts, "
                f"{self.est_total_bytes / 1024 / 1024:.2f} MB "
                f"({self.expansion:.1f}x plaintext), "
                f"padding {self.padding_fraction * 100:.1f}%")


#: Measured serialized bytes per ciphertext at N=8192, chain [60,40,40,60],
#: indexed by how many levels have been consumed. Used for planning without
#: touching the crypto library; benchmark_packing.py refreshes these.
MEASURED_BYTES_BY_DROP = {0: 334_404, 1: 235_326, 2: 131_217}


def plan(n_values: int, cfg: PackingConfig) -> PackingPlan:
    """Predict the wire cost of a configuration without encrypting anything."""
    cfg.validate()

    n_tx = n_values
    index_bytes = 0
    if cfg.sparsify_top_k is not None:
        n_tx = max(1, int(round(n_values * cfg.sparsify_top_k)))
        # Sparse payloads must carry their coordinate indices.
        index_bytes = n_tx * 4

    n_chunks = int(np.ceil(n_tx / cfg.slot_count))
    padded = n_chunks * cfg.slot_count
    per_chunk = MEASURED_BYTES_BY_DROP.get(
        cfg.levels_to_drop, MEASURED_BYTES_BY_DROP[0])
    total = n_chunks * per_chunk + index_bytes
    plain = n_values * 4

    return PackingPlan(
        n_values=n_values,
        n_transmitted=n_tx,
        slot_count=cfg.slot_count,
        n_chunks=n_chunks,
        padded_slots=padded,
        padding_fraction=(padded - n_tx) / max(padded, 1),
        levels_to_drop=cfg.levels_to_drop,
        est_bytes_per_chunk=per_chunk,
        est_total_bytes=total,
        plaintext_bytes=plain,
        expansion=total / max(plain, 1),
        index_overhead_bytes=index_bytes,
    )


def select_top_k(flat: np.ndarray, fraction: float) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(indices, values)`` for the largest-magnitude coordinates.

    Sorted indices keep the reconstruction deterministic and make the index
    array compressible by a downstream transport codec.
    """
    k = max(1, int(round(flat.size * fraction)))
    idx = np.argpartition(np.abs(flat), -k)[-k:]
    idx.sort()
    return idx, flat[idx]


def scatter_top_k(indices: np.ndarray, values: np.ndarray, n_values: int) -> np.ndarray:
    """Inverse of :func:`select_top_k` - unselected coordinates become zero."""
    out = np.zeros(n_values, dtype=np.float64)
    out[indices] = values
    return out


def chunk_for_slots(flat: np.ndarray, slot_count: int) -> List[np.ndarray]:
    """Split a flat vector into slot-sized pieces, last one short (not padded).

    The final chunk is left short rather than zero-padded: TenSEAL sizes a
    ciphertext to the list it is given, so a short final chunk is both smaller
    and avoids the plaintext-operand width mismatch that padding introduces in
    :meth:`CKKSVector.encrypted_sq_distance`.
    """
    return [flat[i:i + slot_count] for i in range(0, flat.size, slot_count)]


def compare_configs(n_values: int, configs: dict) -> List[dict]:
    """Plan several configurations and express each as a saving over the first."""
    rows = []
    baseline = None
    for name, cfg in configs.items():
        p = plan(n_values, cfg)
        if baseline is None:
            baseline = p.est_total_bytes
        rows.append({
            "name": name,
            "n_chunks": p.n_chunks,
            "bytes": p.est_total_bytes,
            "megabytes": p.est_total_bytes / 1024 / 1024,
            "expansion": p.expansion,
            "padding_pct": p.padding_fraction * 100,
            "saving_pct": 100.0 * (1 - p.est_total_bytes / baseline),
            "lossy": cfg.sparsify_top_k is not None,
        })
    return rows

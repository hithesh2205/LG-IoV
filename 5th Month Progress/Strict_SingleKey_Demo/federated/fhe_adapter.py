"""FHE adapter for FedIoV — real CKKS, exact-simulation, and plaintext backends.

What changed in Month 5
-----------------------
The Month-4 adapter exposed a class called ``SimulatedCKKSVector`` that held a
float32 numpy array and added ``N(0, 1e-9)`` noise to it. That is not
encryption, and because 1e-9 sits near float32 ULP it was also not a faithful
model of CKKS precision loss. Worse, it made the FHE-vs-no-FHE comparison
*uncontrolled*: the injected noise perturbed training just enough to send the
two arms down different trajectories, producing a spurious 5-point accuracy gap
on VeReMi (defect D3).

There are now three explicit backends, selected by name:

``"ckks"``
    **Real** CKKS via TenSEAL. Genuine lattice ciphertexts, genuine noise growth,
    genuine rescaling, genuine ~1e-8 approximation error, genuine cost. This is
    what the reported FHE results use.

``"exact"``
    Plain numpy arithmetic with **no** injected noise, wrapped in the identical
    interface. Used to prove the aggregation algebra is lossless and to run fast
    ablations. Because it adds nothing, an ``"exact"`` run and a ``"none"`` run
    are bitwise identical — which is the property the old adapter destroyed and
    ``tests/test_fhe_backends.py`` now asserts.

``"none"``
    No encryption at all — the plaintext FedAvg baseline.

Protocol note
-------------
Only the **client → server** direction is encrypted. The global model that the
server broadcasts is not secret: under FheFL the server itself decrypts the
aggregate, and every vehicle must be able to read the broadcast anyway. The
Month-4 code encrypted the broadcast too, which cost time and protected nothing.
What must stay hidden is each vehicle's *individual* update, and that is exactly
what these backends protect.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
import torch.nn as nn

try:                                    # TenSEAL is optional at import time
    import tenseal as ts
    _TENSEAL_AVAILABLE = True
except Exception:                       # pragma: no cover
    ts = None                           # type: ignore[assignment]
    _TENSEAL_AVAILABLE = False


BACKENDS = ("ckks", "exact", "none")

#: CKKS parameters for the default *practical* profile.
#:
#: Measured on this machine (see ``scripts/benchmark_ckks_profiles.py``):
#:
#:   N=8192,  [60,40,40,60]      200 bits  326.6 KB/ct  eq.11 OK   2nd ct-ct FAIL
#:   N=8192,  [60,40,40,40,60]   240 bits  REJECTED — exceeds the 218-bit ceiling
#:                                          for 128-bit security at N=8192
#:   N=16384, [60,40,40,40,60]   240 bits  836.1 KB/ct  eq.11 OK   2nd ct-ct OK
#:
#: So the encrypted squared-distance of FheFL eq. 11 (one ciphertext×ciphertext
#: multiply) *does* fit at N=8192 — but with exactly zero headroom. The strict
#: variant, which also multiplies the encrypted non-poisoning rate by the
#: encrypted update, needs a second level and therefore N=16384, at 2.56× the
#: ciphertext size. See ``STRICT_*`` below.
DEFAULT_POLY_MODULUS_DEGREE = 8192
DEFAULT_COEFF_MOD_BIT_SIZES = [60, 40, 40, 60]
DEFAULT_GLOBAL_SCALE_BITS = 40

#: Profile for strict-FheFL semantics (encrypted non-poisoning rate).
STRICT_POLY_MODULUS_DEGREE = 16384
STRICT_COEFF_MOD_BIT_SIZES = [60, 40, 40, 40, 60]


# ─────────────────────────────────────────────────────────────────────────
# Vector wrappers — one interface, three backends
# ─────────────────────────────────────────────────────────────────────────


class EncryptedScalar:
    """A single value that may still be under encryption.

    Produced by :meth:`CKKSVector.encrypted_sq_distance` (FheFL eq. 11). It can
    be added to other encrypted scalars — which is how the server forms
    ``Σ_u d^u`` without ever seeing an individual ``d^u`` — and revealed only by
    an explicit :meth:`reveal`.
    """

    def __init__(self, value=None, offset: float = 0.0) -> None:
        #: Encrypted part — a ts.CKKSVector whose slot 0 holds the value, a
        #: float for the plaintext backends, or None when purely an offset.
        self._v = value
        #: Public additive term the server already knows in the clear (e.g. the
        #: ``gᵀg`` term of eq. 11). Kept separate so it never has to be encoded
        #: into a ciphertext of a particular slot width.
        self._offset = float(offset)

    def __add__(self, other: "EncryptedScalar") -> "EncryptedScalar":
        if not isinstance(other, EncryptedScalar):
            raise TypeError("EncryptedScalar adds only to EncryptedScalar")
        if self._v is None:
            v = other._v
        elif other._v is None:
            v = self._v
        else:
            v = self._v + other._v
        return EncryptedScalar(v, self._offset + other._offset)

    __radd__ = __add__

    def reveal(self) -> float:
        """Decrypt this scalar. Every call site must justify the disclosure."""
        if self._v is None:
            return self._offset
        if isinstance(self._v, (int, float)):
            return float(self._v) + self._offset
        return float(np.asarray(self._v.decrypt())[0]) + self._offset


class PlaintextVector:
    """No encryption. The FedAvg baseline, and the ``"exact"`` simulation.

    Deliberately noiseless: the whole point is that toggling encryption changes
    exactly one thing. Any divergence between an ``"exact"`` run and a ``"none"``
    run is a bug in the aggregation code, not an effect of encryption.
    """

    backend = "none"

    def __init__(self, data: np.ndarray) -> None:
        self.data = np.asarray(data, dtype=np.float64)

    def __add__(self, other):
        if isinstance(other, PlaintextVector):
            return PlaintextVector(self.data + other.data)
        return PlaintextVector(self.data + np.asarray(other))

    __radd__ = __add__

    def __mul__(self, other):
        return PlaintextVector(self.data * np.asarray(other, dtype=np.float64))

    __rmul__ = __mul__

    def decrypt(self) -> np.ndarray:
        return self.data

    def size(self) -> int:
        return int(self.data.size)

    def serialized_bytes(self) -> int:
        return int(self.data.size * 4)      # float32 on the wire

    def encrypted_sq_distance(self, g: np.ndarray) -> "EncryptedScalar":
        """Plaintext mirror of FheFL eq. 11 — same algebra, no encryption."""
        v = self.data
        n = min(v.size, g.size)
        return EncryptedScalar(None, offset=float(np.sum((g[:n] - v[:n]) ** 2)))


class CKKSVector:
    """A real CKKS ciphertext over a flat parameter vector.

    The vector is split into ``slot_count``-sized chunks because one CKKS
    ciphertext holds ``poly_modulus_degree / 2`` real slots. Homomorphic
    addition and plaintext-scalar multiplication act chunk-wise.
    """

    backend = "ckks"

    def __init__(
        self,
        context: "ts.Context",
        data: Optional[np.ndarray] = None,
        chunks: Optional[List] = None,
        n_values: Optional[int] = None,
        slot_count: int = DEFAULT_POLY_MODULUS_DEGREE // 2,
        levels_to_drop: int = 0,
    ) -> None:
        if not _TENSEAL_AVAILABLE:
            raise RuntimeError(
                "backend='ckks' needs TenSEAL. Install it with "
                "`pip install tenseal`, or use backend='exact'."
            )
        self.context = context
        self.slot_count = slot_count
        self.levels_to_drop = int(levels_to_drop)
        if chunks is not None:
            self._chunks = chunks
            self.n_values = int(n_values) if n_values is not None else 0
        else:
            vec = np.asarray(data, dtype=np.float64).ravel()
            self.n_values = int(vec.size)
            n_chunks = max(1, int(np.ceil(vec.size / slot_count)))
            self._chunks = [
                ts.ckks_vector(context, vec[i * slot_count:(i + 1) * slot_count].tolist())
                for i in range(n_chunks)
            ]
            if self.levels_to_drop:
                # Consume levels locally before this ever hits the wire. A
                # freshly encrypted ciphertext carries the whole modulus chain;
                # the server only needs ONE level left, because the encrypted
                # distance and the weighted aggregation act on independent
                # copies rather than in sequence. Measured saving: 29.6 %.
                # TenSEAL exposes no mod-switch, so multiplying by exactly 1.0
                # is how a level is dropped without changing the value.
                from .packing import MAX_SAFE_LEVEL_DROP
                if self.levels_to_drop > MAX_SAFE_LEVEL_DROP:
                    raise ValueError(
                        f"levels_to_drop={self.levels_to_drop} exceeds the safe "
                        f"maximum of {MAX_SAFE_LEVEL_DROP}: the server would have "
                        f"no level left for the encrypted distance.")
                for _ in range(self.levels_to_drop):
                    for ch in self._chunks:
                        ch *= 1.0

    def _like(self, chunks: List) -> "CKKSVector":
        return CKKSVector(self.context, chunks=chunks,
                          n_values=self.n_values, slot_count=self.slot_count,
                          levels_to_drop=0)   # already applied to these chunks

    def __add__(self, other):
        if isinstance(other, CKKSVector):
            if len(self._chunks) != len(other._chunks):
                raise ValueError("ciphertext chunk-count mismatch")
            return self._like([a + b for a, b in zip(self._chunks, other._chunks)])
        raise TypeError(
            "CKKS ciphertexts add to other ciphertexts; adding a plaintext "
            "array here would silently leave the encrypted domain."
        )

    __radd__ = __add__

    def __mul__(self, scalar):
        """Ciphertext × public scalar — the FedAvg / non-poisoning-rate weight."""
        s = float(scalar)
        return self._like([c * s for c in self._chunks])

    __rmul__ = __mul__

    def decrypt(self) -> np.ndarray:
        """Requires the secret key — server-side this is the *aggregate* only."""
        out = np.concatenate([np.asarray(c.decrypt()) for c in self._chunks])
        return out[:self.n_values]

    def size(self) -> int:
        return self.n_values

    def serialized_bytes(self) -> int:
        return int(sum(len(c.serialize()) for c in self._chunks))

    def encrypted_sq_distance(self, g: np.ndarray) -> EncryptedScalar:
        """FheFL eq. 11 — ``[d^u] = gᵀg + [(f^u − 2g)ᵀ·f^u]``, fully homomorphic.

        The server holds ``g`` (the previous global model) in plaintext, so only
        the cross term needs the encrypted domain. Costs **one** ciphertext ×
        ciphertext multiply plus the rotations for the slot sum — which is
        exactly the depth the default profile affords, and why the strict
        variant needs a larger ring.

        The result stays encrypted: the server can sum these across clients
        without learning any individual distance.
        """
        gg = float(np.dot(g[:self.n_values], g[:self.n_values]))
        acc = None
        for k, chunk in enumerate(self._chunks):
            lo = k * self.slot_count
            hi = min(lo + self.slot_count, self.n_values)
            if lo >= hi:
                break
            # The final chunk is partial — its ciphertext holds exactly
            # (hi - lo) slots, so the plaintext operand must match that width.
            g_slice = np.zeros(hi - lo, dtype=np.float64)
            g_slice[:] = g[lo:hi]
            # (f − 2g) · f , evaluated entirely on ciphertexts
            term = (chunk - (2.0 * g_slice).tolist()).dot(chunk)
            acc = term if acc is None else acc + term
        # gᵀg is public (the server holds g), so it rides along as a plaintext
        # offset rather than being encoded into a ciphertext.
        return EncryptedScalar(acc, offset=gg)


# ─────────────────────────────────────────────────────────────────────────
# Context construction
# ─────────────────────────────────────────────────────────────────────────


def build_ckks_context(
    poly_modulus_degree: int = DEFAULT_POLY_MODULUS_DEGREE,
    coeff_mod_bit_sizes: Optional[Sequence[int]] = None,
    global_scale_bits: int = DEFAULT_GLOBAL_SCALE_BITS,
) -> "ts.Context":
    """Build the CKKS context used by every ``"ckks"``-backend run."""
    if not _TENSEAL_AVAILABLE:
        raise RuntimeError("TenSEAL is not installed; cannot build a CKKS context")
    coeff = list(coeff_mod_bit_sizes or DEFAULT_COEFF_MOD_BIT_SIZES)
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=poly_modulus_degree,
        coeff_mod_bit_sizes=coeff,
    )
    context.global_scale = 2 ** global_scale_bits
    context.generate_galois_keys()
    context.generate_relin_keys()
    return context


def multiplicative_depth(coeff_mod_bit_sizes: Sequence[int]) -> int:
    """Levels available for ciphertext×ciphertext multiplication.

    A chain ``[p0, ..., pL]`` supports ``L - 1`` rescalings. FheFL's aggregation
    needs 2 (squared distance, then the non-poisoning-rate weighting), so the
    default chain has exactly enough and no margin.
    """
    return max(0, len(coeff_mod_bit_sizes) - 2)


# ─────────────────────────────────────────────────────────────────────────
# Model ↔ vector plumbing
# ─────────────────────────────────────────────────────────────────────────


def flatten_model(model: nn.Module) -> np.ndarray:
    """Flatten all trainable parameters into one float64 vector."""
    parts = [p.data.detach().cpu().numpy().ravel()
             for _, p in model.named_parameters() if p.requires_grad]
    return np.concatenate(parts).astype(np.float64)


def parameter_layout(model: nn.Module) -> List[tuple]:
    """``[(name, numel, shape), ...]`` in the same order as :func:`flatten_model`."""
    return [(n, int(p.numel()), tuple(p.shape))
            for n, p in model.named_parameters() if p.requires_grad]


def load_flat_into_model(model: nn.Module, flat: np.ndarray) -> None:
    """Inverse of :func:`flatten_model`."""
    layout = parameter_layout(model)
    total = sum(n for _, n, _ in layout)
    if flat.size != total:
        raise ValueError(
            f"flat vector has {flat.size} values but the model needs {total}")
    offset = 0
    params = dict(model.named_parameters())
    for name, numel, shape in layout:
        chunk = flat[offset:offset + numel]
        offset += numel
        params[name].data.copy_(
            torch.from_numpy(np.asarray(chunk, dtype=np.float32)).view(*shape))


def encrypt_update(
    flat: np.ndarray,
    backend: str = "ckks",
    context: Optional["ts.Context"] = None,
    levels_to_drop: int = 0,
):
    """Encrypt one client's flattened update under the chosen backend.

    ``levels_to_drop=1`` shrinks the transmitted ciphertext by ~29.6 % and is
    safe for the FheFL round; see ``federated/packing.py``.
    """
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}, got {backend!r}")
    if backend == "ckks":
        if context is None:
            raise ValueError("backend='ckks' requires a CKKS context")
        return CKKSVector(context, data=flat, levels_to_drop=levels_to_drop)
    # "exact" and "none" share the noiseless plaintext carrier — that identity
    # is what makes the FHE/no-FHE comparison controlled.
    return PlaintextVector(flat)


# ─────────────────────────────────────────────────────────────────────────
# Backwards-compatible layer-wise helpers (Month-4 call sites)
# ─────────────────────────────────────────────────────────────────────────


def encrypt_layerwise(
    model: nn.Module,
    backend: str = "ckks",
    context: Optional["ts.Context"] = None,
) -> Dict[str, object]:
    """Encrypt each parameter tensor separately.

    Retained because the Month-4 reports describe layer-wise encryption. Whole-
    vector encryption (:func:`encrypt_update`) is strictly cheaper — it packs
    4096 reals per ciphertext instead of padding every small bias tensor into
    its own ciphertext — so the federated path uses that instead.
    """
    out: Dict[str, object] = {}
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        flat = param.data.detach().cpu().numpy().ravel().astype(np.float64)
        out[name] = encrypt_update(flat, backend=backend, context=context)
    return out


def inject_layerwise(model: nn.Module, encrypted: Dict[str, object]) -> None:
    """Decrypt a layer-wise dict back into the model's parameters."""
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if name not in encrypted:
            raise KeyError(f"Parameter {name!r} missing from the encrypted dict")
        values = np.asarray(encrypted[name].decrypt())
        if values.size != param.numel():
            raise ValueError(
                f"Size mismatch for {name!r}: expected {param.numel()}, "
                f"got {values.size}")
        param.data.copy_(
            torch.from_numpy(values.astype(np.float32)).view_as(param.data))

"""OpenFHE CKKS backend — single-key and real threshold (multiparty) CKKS.

OpenFHE migration, phases M1-M3 (Documentation/10_library_evaluation.md §5)
-------------------------------------------------------------------------
TenSEAL cannot express multi-key CKKS, so ``multikey_ckks.py`` is an algebraic
model of key sharing, not cryptography. This module replaces it with OpenFHE's
multiparty CKKS: every vehicle generates its own secret key, the fleet derives
one joint public key interactively, and **no party ever holds the joint secret
key**. Decrypting anything needs a partial decryption ("share") from every
vehicle, or from enough vehicles to rebuild a missing one (t-of-n Shamir).

Two backends share the :class:`OpenFHEVector` interface, which mirrors
``fhe_adapter.CKKSVector`` exactly (``+``, ``* scalar``, ``decrypt``,
``serialized_bytes``, ``encrypted_sq_distance``), so ``server.py`` and
``client.py`` do not change:

``"openfhe"``
    Single-key CKKS. A like-for-like replacement for the TenSEAL ``"ckks"``
    backend, used to check parity before the threshold path is trusted.

``"openfhe-threshold"``
    Threshold CKKS across the fleet. The server fuses decryption shares; it
    never holds a key.

Parameter profile — and why it differs from TenSEAL
---------------------------------------------------
TenSEAL's profile is N=8192 with chain [60, 40, 40 | 60], 200 bits in total,
under the 218-bit ceiling for 128-bit security. OpenFHE **rejects** that chain
at N=8192 (measured on openfhe 1.6.1). OpenFHE's hybrid key switching sizes
the auxiliary modulus P from the largest digit, and with a 60-bit first prime
P needs two 60-bit primes, which pushes Q·P past 218 bits. Measured:

    first modulus 60, 59 or 58 bits, any dnum     -> rejected at N=8192
    first modulus 55 bits, dnum = 3               -> accepted, 128-bit
    BV key switching instead of hybrid            -> accepted, but the encrypted
                                                     distance error is 2.7e-3 and
                                                     joint-key decryption fails

So this profile uses **[55, 40, 40]** with dnum = 3. The only cost is decoding
headroom: after the server's ciphertext × ciphertext multiply a decrypted value
must stay below 2^(55-40) = 32768, against 2^20 under TenSEAL. The trained
ChebyKAN models measure ||w||² ≈ 175-200 on every dataset, so the encrypted
distance cross term sits ~160x inside that bound. An oversized (e.g. malicious)
update does not decrypt to a wrong number: OpenFHE raises
"approximation error is too high", which is the loud failure we want.

Measured at this profile (openfhe 1.6.1, WSL Ubuntu 24.04, dev laptop;
tests/test_openfhe.py checks the first three):
    ciphertext 394,207 B fresh, 263,309 B after the 1-level drop (0.668x)
    one 44,164-parameter update on the wire: 2.90 MB (TenSEAL: 2.59 MB)
    encrypted squared distance error ~7e-8 (TenSEAL: 2.8e-6 .. 1.25e-5)
    10-party threshold decryption of one ciphertext: ~39 ms, share 132 KB

What this does NOT yet claim
----------------------------
* The vehicles' key holders live in one process here. The decryption policy
  (:func:`_check_disclosure`) is enforced at the API level; a real deployment
  needs each vehicle to check that what it is asked to decrypt is the round's
  sum (for example by recomputing it from the broadcast uploads).
* Smudging is not yet sized (phase M4). OpenFHE adds fixed noise (sigma 2^20)
  to every CKKS decryption share (``FIXED_NOISE_MULTIPARTY``); the Python
  bindings reject ``SetMultipartyMode`` for CKKS, so ``NOISE_FLOODING_MULTIPARTY``
  is not reachable from here. Measured effect: a ciphertext at scale 2^40
  decrypts with a ~7e-4 slot error (the noise spread by ~sqrt(N) in decoding).
  The server's ciphertexts are always multiplied by a plaintext weight first,
  so they sit at scale 2^80 and decrypt to ~1e-7. But at that scale the fixed
  2^20 noise no longer dominates the ciphertext's own noise, so it is weaker
  smudging than it looks. M4 has to size it against IND-CPA^D properly.
* Shamir recovery of a dropped vehicle exposes that vehicle's key share to the
  recovering vehicle, so a recovered vehicle must be re-keyed before it rejoins.
  :attr:`ThresholdKeySet.needs_rekey` records which ones.
"""
from __future__ import annotations

import itertools
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence

import numpy as np

try:                                    # OpenFHE ships Linux wheels only
    import openfhe as ofhe
    OPENFHE_AVAILABLE = True
except Exception:                       # pragma: no cover - Windows host
    ofhe = None                         # type: ignore[assignment]
    OPENFHE_AVAILABLE = False


OPENFHE_BACKENDS = ("openfhe", "openfhe-threshold")

OPENFHE_RING_DIM = 8192
OPENFHE_DEPTH = 2
OPENFHE_FIRST_MOD_BITS = 55
OPENFHE_SCALE_BITS = 40
OPENFHE_NUM_LARGE_DIGITS = 3

#: Purposes a decryption may serve. "aggregate" needs >= 2 contributors;
#: "distance" is the practical-profile disclosure of one scalar per client.
DECRYPTION_PURPOSES = ("aggregate", "distance")
MIN_AGGREGATE_CONTRIBUTORS = 2

_anon_ids = itertools.count()


class DisclosureRefused(PermissionError):
    """A key holder refused to help decrypt something outside the policy."""


class ThresholdUnavailable(RuntimeError):
    """Too few vehicles are online to decrypt, even with Shamir recovery."""


def _require_openfhe() -> None:
    if not OPENFHE_AVAILABLE:
        raise RuntimeError(
            "The OpenFHE backends need the `openfhe` package, which ships Linux "
            "wheels only. On this project's Windows machine, run under WSL:\n"
            "  wsl -d Ubuntu -- ~/ofhe-venv/bin/python train_federated.py ...")


def _check_disclosure(contributors: FrozenSet, purpose: str) -> None:
    """The decryption policy every key holder applies before issuing a share.

    Doc 18 §10: shares are only ever computed on the round's *summed*
    ciphertext, never on one vehicle's upload. The single exception is the
    practical-profile distance scalar, which the server is allowed to learn.
    """
    if purpose not in DECRYPTION_PURPOSES:
        raise DisclosureRefused(f"unknown decryption purpose {purpose!r}")
    if purpose == "aggregate" and len(contributors) < MIN_AGGREGATE_CONTRIBUTORS:
        raise DisclosureRefused(
            f"refusing to decrypt a model vector with {len(contributors)} "
            f"contributor(s): only the sum of >= {MIN_AGGREGATE_CONTRIBUTORS} "
            "vehicles' updates may be decrypted")


# ─────────────────────────────────────────────────────────────────────────
# Crypto context
# ─────────────────────────────────────────────────────────────────────────


def build_openfhe_cc(
    ring_dim: int = OPENFHE_RING_DIM,
    depth: int = OPENFHE_DEPTH,
    first_mod_bits: int = OPENFHE_FIRST_MOD_BITS,
    scale_bits: int = OPENFHE_SCALE_BITS,
    num_large_digits: int = OPENFHE_NUM_LARGE_DIGITS,
):
    """A 128-bit CKKS crypto context with multiparty support enabled."""
    _require_openfhe()
    p = ofhe.CCParamsCKKSRNS()
    p.SetRingDim(ring_dim)
    p.SetMultiplicativeDepth(depth)
    p.SetFirstModSize(first_mod_bits)
    p.SetScalingModSize(scale_bits)
    p.SetBatchSize(ring_dim // 2)
    p.SetSecurityLevel(ofhe.SecurityLevel.HEStd_128_classic)
    p.SetScalingTechnique(ofhe.FLEXIBLEAUTO)
    p.SetKeySwitchTechnique(ofhe.HYBRID)
    if num_large_digits:
        p.SetNumLargeDigits(num_large_digits)
    cc = ofhe.GenCryptoContext(p)
    for feature in (ofhe.PKE, ofhe.KEYSWITCH, ofhe.LEVELEDSHE,
                    ofhe.ADVANCEDSHE, ofhe.MULTIPARTY):
        cc.Enable(feature)
    return cc


class VehicleKeyHolder:
    """One vehicle's part of the threshold key. Its secret key never leaves it."""

    def __init__(self, index: int, secret_key) -> None:
        self.index = index                  # 1-based, as OpenFHE's Shamir API expects
        self._sk = secret_key
        #: Shamir shares of the *other* vehicles' keys that this vehicle holds:
        #: ``{owner_index: DCRTPoly}``. Used only to rebuild a dropped vehicle.
        self.held_shares: Dict[int, object] = {}
        self.shares_issued = 0

    def partial_decrypt(self, cc, cts: Sequence, contributors: FrozenSet,
                        purpose: str, lead: bool) -> List:
        _check_disclosure(contributors, purpose)
        self.shares_issued += len(cts)
        if lead:
            return list(cc.MultipartyDecryptLead(list(cts), self._sk))
        return list(cc.MultipartyDecryptMain(list(cts), self._sk))


class ThresholdKeySet:
    """The fleet's joint key, generated interactively — OpenFHE multiparty CKKS.

    Key generation runs the protocol of OpenFHE's ``threshold-fhe`` example:

    1. public key: vehicle 1 runs ``KeyGen``; vehicle i runs
       ``MultipartyKeyGen`` on vehicle i-1's public key. The last public key is
       the joint key ``pk`` for ``s = Σ s_i``.
    2. relinearisation key: two rounds (``MultiKeySwitchGen`` +
       ``MultiAddEvalKeys``, then ``MultiMultEvalKey`` + ``MultiAddEvalMultKeys``).
    3. rotation-sum keys: ``MultiEvalSumKeyGen`` + ``MultiAddEvalSumKeys``. These
       are what the encrypted distance needs, and they answer open item S2 /
       Q5 of docs 17/18: **yes, OpenFHE generates joint Galois keys.**
    4. Shamir t-of-n: each vehicle splits its secret key with ``ShareKeys`` and
       hands one share to every other vehicle. This answers open item S1:
       **OpenFHE does support t-of-n**, via share-and-recover on top of the
       n-of-n multiparty decryption.
    """

    def __init__(self, cc, n_parties: int, threshold: Optional[int] = None) -> None:
        if n_parties < 2:
            raise ValueError("threshold CKKS needs at least 2 vehicles")
        self.cc = cc
        self.n = int(n_parties)
        self.t = int(threshold) if threshold is not None else self.n // 2 + 1
        if not 1 <= self.t <= self.n:
            raise ValueError(f"threshold must be in [1, {self.n}], got {self.t}")
        self.offline: set = set()
        #: Vehicles whose key was rebuilt by someone else — re-key before reuse.
        self.needs_rekey: set = set()
        self.decryptions = 0
        self.last_share_bytes = 0
        self.holders = self._generate()

    def _generate(self) -> List[VehicleKeyHolder]:
        cc, n = self.cc, self.n
        kps = [cc.KeyGen()]
        for _ in range(1, n):
            kps.append(cc.MultipartyKeyGen(kps[-1].publicKey))
        self.public_key = kps[-1].publicKey
        tag = self.public_key.GetKeyTag()

        ek = cc.KeySwitchGen(kps[0].secretKey, kps[0].secretKey)
        ek_joint = ek
        for kp in kps[1:]:
            ek_joint = cc.MultiAddEvalKeys(
                ek_joint, cc.MultiKeySwitchGen(kp.secretKey, kp.secretKey, ek), tag)
        mult_parts = [cc.MultiMultEvalKey(kp.secretKey, ek_joint, tag) for kp in kps]
        mult_key = mult_parts[0]
        for part in mult_parts[1:]:
            mult_key = cc.MultiAddEvalMultKeys(mult_key, part, ek_joint.GetKeyTag())
        cc.InsertEvalMultKey([mult_key])

        cc.EvalSumKeyGen(kps[0].secretKey)
        sum0 = cc.GetEvalSumKeyMap(kps[0].secretKey.GetKeyTag())
        sum_joint = sum0
        for kp in kps[1:]:
            sum_joint = cc.MultiAddEvalSumKeys(
                sum_joint, cc.MultiEvalSumKeyGen(kp.secretKey, sum0, tag), tag)
        cc.InsertEvalSumKey(sum_joint)

        holders = [VehicleKeyHolder(i + 1, kp.secretKey) for i, kp in enumerate(kps)]
        for owner in holders:
            shares = cc.ShareKeys(owner._sk, n, self.t, owner.index, "shamir")
            for h in holders:
                if h.index != owner.index:
                    h.held_shares[owner.index] = shares[h.index]
        return holders

    # ── availability ─────────────────────────────────────────────────────
    def set_offline(self, indices: Iterable[int]) -> None:
        """Mark vehicles (1-based) unreachable for the decryption step."""
        self.offline = {int(i) for i in indices}

    def online(self) -> List[VehicleKeyHolder]:
        return [h for h in self.holders if h.index not in self.offline]

    # ── decryption ───────────────────────────────────────────────────────
    def decrypt(self, cts: Sequence, contributors: FrozenSet, purpose: str) -> List:
        """Fuse one share per vehicle into plaintexts, rebuilding dropped vehicles."""
        cc = self.cc
        online = self.online()
        missing = sorted(self.offline)
        if missing and len(online) < self.t:
            raise ThresholdUnavailable(
                f"{len(online)} of {self.n} vehicles online; at least {self.t} are "
                f"needed to rebuild the {len(missing)} missing share(s)")
        _check_disclosure(contributors, purpose)

        partials = [online[0].partial_decrypt(cc, cts, contributors, purpose, lead=True)]
        partials += [h.partial_decrypt(cc, cts, contributors, purpose, lead=False)
                     for h in online[1:]]
        for m in missing:
            # The first online vehicle rebuilds m's key from t shares and
            # issues m's share in its place. It now knows m's key share, so m
            # must be re-keyed before it takes part again.
            donors = online[:self.t]
            sk = ofhe.PrivateKey(cc)
            cc.RecoverSharedKey(sk, {h.index: h.held_shares[m] for h in donors},
                                self.n, self.t, "shamir")
            stand_in = VehicleKeyHolder(m, sk)
            partials.append(stand_in.partial_decrypt(
                cc, cts, contributors, purpose, lead=False))
            self.needs_rekey.add(m)

        self.decryptions += 1
        self.last_share_bytes = len(ofhe.Serialize(partials[-1][0], ofhe.BINARY))
        return [cc.MultipartyDecryptFusion([p[k] for p in partials])
                for k in range(len(cts))]


class OpenFHEContext:
    """The crypto context plus whatever can decrypt: one key, or the fleet."""

    def __init__(self, cc, public_key, secret_key=None,
                 keyset: Optional[ThresholdKeySet] = None,
                 depth: int = OPENFHE_DEPTH) -> None:
        self.cc = cc
        self.public_key = public_key
        self._sk = secret_key
        self.keyset = keyset
        self.depth = depth
        self.slot_count = cc.GetRingDimension() // 2
        self.decryptions_by_purpose: Dict[str, int] = {p: 0 for p in DECRYPTION_PURPOSES}

    @property
    def mode(self) -> str:
        return "threshold" if self.keyset is not None else "single"

    @classmethod
    def single_key(cls, **params) -> "OpenFHEContext":
        cc = build_openfhe_cc(**params)
        kp = cc.KeyGen()
        cc.EvalMultKeyGen(kp.secretKey)
        cc.EvalSumKeyGen(kp.secretKey)
        return cls(cc, kp.publicKey, secret_key=kp.secretKey,
                   depth=params.get("depth", OPENFHE_DEPTH))

    @classmethod
    def threshold(cls, n_parties: int, threshold: Optional[int] = None,
                  **params) -> "OpenFHEContext":
        cc = build_openfhe_cc(**params)
        keyset = ThresholdKeySet(cc, n_parties, threshold)
        return cls(cc, keyset.public_key, keyset=keyset,
                   depth=params.get("depth", OPENFHE_DEPTH))

    def encrypt(self, values: np.ndarray):
        pt = self.cc.MakeCKKSPackedPlaintext(np.asarray(values, dtype=np.float64).tolist())
        return self.cc.Encrypt(self.public_key, pt)

    def decrypt(self, cts: Sequence, length: int, contributors: FrozenSet,
                purpose: str) -> np.ndarray:
        """Decrypt ciphertext chunks and concatenate the first ``length`` values."""
        _check_disclosure(contributors, purpose)
        if self.keyset is not None:
            pts = self.keyset.decrypt(cts, contributors, purpose)
        else:
            pts = [self.cc.Decrypt(self._sk, ct) for ct in cts]
        self.decryptions_by_purpose[purpose] += 1
        out = []
        for pt in pts:
            pt.SetLength(self.slot_count)
            out.append(np.asarray(pt.GetRealPackedValue(), dtype=np.float64))
        return np.concatenate(out)[:length]

    def levels_remaining(self, ct) -> int:
        """Multiplicative levels still available on ``ct``."""
        return self.depth - int(ct.GetLevel()) - (int(ct.GetNoiseScaleDeg()) - 1)


# ─────────────────────────────────────────────────────────────────────────
# Vector wrappers — same interface as fhe_adapter.CKKSVector
# ─────────────────────────────────────────────────────────────────────────


class OpenFHEScalar:
    """An encrypted scalar (slot 0) — the payload of ``EncryptedScalar._v``."""

    def __init__(self, ctx: OpenFHEContext, ct, contributors: FrozenSet) -> None:
        self.ctx = ctx
        self.ct = ct
        self.contributors = contributors

    def __add__(self, other: "OpenFHEScalar") -> "OpenFHEScalar":
        return OpenFHEScalar(self.ctx, self.ctx.cc.EvalAdd(self.ct, other.ct),
                             self.contributors | other.contributors)

    def decrypt(self) -> np.ndarray:
        return self.ctx.decrypt([self.ct], 1, self.contributors, "distance")


class OpenFHEVector:
    """A flat parameter vector as OpenFHE CKKS ciphertexts, ``slot_count`` per chunk."""

    backend = "openfhe"

    def __init__(
        self,
        ctx: OpenFHEContext,
        data: Optional[np.ndarray] = None,
        chunks: Optional[List] = None,
        n_values: Optional[int] = None,
        levels_to_drop: int = 0,
        contributors: Optional[FrozenSet] = None,
    ) -> None:
        _require_openfhe()
        self.ctx = ctx
        self.slot_count = ctx.slot_count
        self.contributors = (frozenset(contributors) if contributors
                             else frozenset({("anon", next(_anon_ids))}))
        if chunks is not None:
            self._chunks = list(chunks)
            self.n_values = int(n_values) if n_values is not None else 0
            return
        vec = np.asarray(data, dtype=np.float64).ravel()
        self.n_values = int(vec.size)
        s = self.slot_count
        n_chunks = max(1, int(np.ceil(vec.size / s)))
        self._chunks = [ctx.encrypt(vec[i * s:(i + 1) * s]) for i in range(n_chunks)]
        if levels_to_drop:
            from .packing import MAX_SAFE_LEVEL_DROP
            if levels_to_drop > MAX_SAFE_LEVEL_DROP:
                raise ValueError(
                    f"levels_to_drop={levels_to_drop} exceeds the safe maximum of "
                    f"{MAX_SAFE_LEVEL_DROP}: the server would have no level left "
                    "for the encrypted distance.")
            # A real modulus drop: discard RNS towers before the wire. TenSEAL
            # had to fake this by multiplying by 1.0.
            towers_left = ctx.depth + 1 - int(levels_to_drop)
            self._chunks = [ctx.cc.Compress(c, towers_left) for c in self._chunks]

    def _like(self, chunks: List, contributors: FrozenSet) -> "OpenFHEVector":
        return OpenFHEVector(self.ctx, chunks=chunks, n_values=self.n_values,
                             contributors=contributors)

    def __add__(self, other):
        if not isinstance(other, OpenFHEVector):
            raise TypeError(
                "OpenFHE ciphertexts add to other ciphertexts; adding a plaintext "
                "array here would silently leave the encrypted domain.")
        if other.ctx is not self.ctx:
            raise ValueError("ciphertexts belong to different crypto contexts")
        if len(self._chunks) != len(other._chunks):
            raise ValueError("ciphertext chunk-count mismatch")
        cc = self.ctx.cc
        return self._like([cc.EvalAdd(a, b) for a, b in zip(self._chunks, other._chunks)],
                          self.contributors | other.contributors)

    __radd__ = __add__

    def __mul__(self, scalar):
        """Ciphertext × public scalar — the FedAvg / non-poisoning-rate weight."""
        s = float(scalar)
        cc = self.ctx.cc
        return self._like([cc.EvalMult(c, s) for c in self._chunks], self.contributors)

    __rmul__ = __mul__

    def decrypt(self) -> np.ndarray:
        """Refused unless this is a sum over >= 2 vehicles (see _check_disclosure)."""
        return self.ctx.decrypt(self._chunks, self.n_values, self.contributors, "aggregate")

    def size(self) -> int:
        return self.n_values

    def serialized_bytes(self) -> int:
        return int(sum(len(ofhe.Serialize(c, ofhe.BINARY)) for c in self._chunks))

    def encrypted_sq_distance(self, g: np.ndarray):
        """FheFL eq. 11 — ``[d^u] = gᵀg + [(f^u − 2g)ᵀ·f^u]`` on OpenFHE ciphertexts.

        One ciphertext × ciphertext multiply and a rotation sum per chunk, all
        under the (joint) evaluation keys. The result stays encrypted.
        """
        from .fhe_adapter import EncryptedScalar
        cc = self.ctx.cc
        if any(self.ctx.levels_remaining(c) < 1 for c in self._chunks):
            raise ValueError(
                "no multiplicative level left for the encrypted distance — "
                "too many levels were dropped before upload")
        gg = float(np.dot(g[:self.n_values], g[:self.n_values]))
        acc = None
        for k, chunk in enumerate(self._chunks):
            lo = k * self.slot_count
            hi = min(lo + self.slot_count, self.n_values)
            if lo >= hi:
                break
            two_g = cc.MakeCKKSPackedPlaintext((2.0 * np.asarray(g[lo:hi], dtype=np.float64)).tolist())
            term = cc.EvalSum(cc.EvalMult(cc.EvalSub(chunk, two_g), chunk), self.slot_count)
            acc = term if acc is None else cc.EvalAdd(acc, term)
        return EncryptedScalar(OpenFHEScalar(self.ctx, acc, self.contributors), offset=gg)


def build_openfhe_context(backend: str, n_parties: int = 0,
                          threshold: Optional[int] = None) -> OpenFHEContext:
    """Context for ``backend`` — ``"openfhe"`` (one key) or ``"openfhe-threshold"``."""
    if backend == "openfhe":
        return OpenFHEContext.single_key()
    if backend == "openfhe-threshold":
        return OpenFHEContext.threshold(n_parties, threshold)
    raise ValueError(f"not an OpenFHE backend: {backend!r}")

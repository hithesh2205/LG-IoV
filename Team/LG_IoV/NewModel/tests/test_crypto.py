"""Verification tests for the Month-5 cryptographic layer (defects D3, D4, D6).

Run from the NewModel directory::

    python tests/test_crypto.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from federated.fhe_adapter import (                       # noqa: E402
    BACKENDS, CKKSVector, PlaintextVector, build_ckks_context,
    encrypt_update, multiplicative_depth,
    DEFAULT_COEFF_MOD_BIT_SIZES, STRICT_COEFF_MOD_BIT_SIZES,
)
from federated.multikey_ckks import (                     # noqa: E402
    MultiKeyContext, demonstrate_dropout_failure, verify_mask_cancellation,
)
from federated.secure_channel import (                    # noqa: E402
    HandshakeError, IdentityKey, handshake_pair,
)
from federated.server import (                            # noqa: E402
    AggregationAudit, FederatedServer, assert_no_individual_decryption,
)

_failures: list = []
_passes: list = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        _passes.append(name)
        print(f"  PASS  {name}")
    else:
        _failures.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


# ── D3: exact backend must be arithmetically identical to plaintext ──────
def test_backend_equivalence() -> None:
    print("\n[test] D3 — exact backend is bitwise identical to plaintext")
    rng = np.random.default_rng(0)
    vecs = [rng.normal(0, 0.05, 500) for _ in range(5)]
    w = rng.dirichlet(np.ones(5))

    def aggregate(backend):
        enc = [encrypt_update(v, backend=backend) for v in vecs]
        acc = enc[0] * float(w[0])
        for e, wi in zip(enc[1:], w[1:]):
            acc = acc + e * float(wi)
        return acc.decrypt()

    a = aggregate("exact")
    b = aggregate("none")
    check("exact == none, bitwise", np.array_equal(a, b),
          f"max diff {np.max(np.abs(a - b)):.2e}")

    truth = np.sum([wi * v for wi, v in zip(w, vecs)], axis=0)
    check("aggregation algebra is lossless",
          np.allclose(a, truth, atol=1e-12),
          f"max err {np.max(np.abs(a - truth)):.2e}")


def test_real_ckks_roundtrip() -> None:
    print("\n[test] real CKKS encrypt → aggregate → decrypt")
    ctx = build_ckks_context()
    rng = np.random.default_rng(1)
    vecs = [rng.normal(0, 0.05, 5000) for _ in range(4)]
    w = rng.dirichlet(np.ones(4))

    enc = [encrypt_update(v, backend="ckks", context=ctx) for v in vecs]
    check("produced real ciphertexts", all(isinstance(e, CKKSVector) for e in enc))

    acc = enc[0] * float(w[0])
    for e, wi in zip(enc[1:], w[1:]):
        acc = acc + e * float(wi)
    got = acc.decrypt()
    truth = np.sum([wi * v for wi, v in zip(w, vecs)], axis=0)
    err = float(np.max(np.abs(got - truth)))
    check("CKKS aggregation matches plaintext to ~1e-7", err < 1e-6,
          f"max abs err {err:.2e}")
    check("ciphertext is much larger than plaintext",
          enc[0].serialized_bytes() > 10 * (vecs[0].size * 4),
          f"ct={enc[0].serialized_bytes()} pt={vecs[0].size * 4}")

    # Adding a raw array must be refused — it would leave the encrypted domain.
    try:
        _ = enc[0] + np.zeros(5000)
        check("refuses ciphertext + plaintext array", False, "no TypeError raised")
    except TypeError:
        check("refuses ciphertext + plaintext array", True)


def test_encrypted_distance() -> None:
    print("\n[test] FheFL eq. 11 — encrypted squared distance")
    ctx = build_ckks_context()
    rng = np.random.default_rng(2)
    g = rng.normal(0, 0.05, 3000)
    f = rng.normal(0, 0.05, 3000)

    enc = encrypt_update(f, backend="ckks", context=ctx)
    d = enc.encrypted_sq_distance(g).reveal()
    truth = float(np.sum((g - f) ** 2))
    check("encrypted distance matches plaintext", abs(d - truth) < 1e-4,
          f"got {d:.6f} true {truth:.6f}")

    # Plaintext backend must agree, so the server code is backend-agnostic.
    dp = encrypt_update(f, backend="exact").encrypted_sq_distance(g).reveal()
    check("plaintext mirror agrees", abs(dp - truth) < 1e-9,
          f"got {dp:.6f} true {truth:.6f}")

    # The server computes the distance from a ciphertext and then aggregates
    # that SAME ciphertext. If the distance computation consumed or mutated it,
    # aggregation would silently produce garbage.
    reused = enc * 0.5
    got = reused.decrypt()
    check("ciphertext is still usable after distance computation",
          float(np.max(np.abs(got - 0.5 * f))) < 1e-5,
          f"max err {float(np.max(np.abs(got - 0.5 * f))):.2e}")

    # And the distance must be recomputable to the same value.
    d2 = enc.encrypted_sq_distance(g).reveal()
    check("distance is stable on recomputation", abs(d2 - truth) < 1e-4,
          f"first {d:.6f} second {d2:.6f}")


def test_depth_budget() -> None:
    print("\n[test] multiplicative depth budget")
    check("default profile affords 2 levels",
          multiplicative_depth(DEFAULT_COEFF_MOD_BIT_SIZES) == 2,
          f"got {multiplicative_depth(DEFAULT_COEFF_MOD_BIT_SIZES)}")
    check("strict profile affords 3 levels",
          multiplicative_depth(STRICT_COEFF_MOD_BIT_SIZES) == 3,
          f"got {multiplicative_depth(STRICT_COEFF_MOD_BIT_SIZES)}")


# ── multi-key key sharing ────────────────────────────────────────────────
def test_mask_cancellation() -> None:
    print("\n[test] FheFL eq. 10 — pairwise masks cancel")
    for n in (2, 5, 10, 25):
        ok, err = verify_mask_cancellation(n)
        check(f"masks cancel for U={n}", ok, f"max err {err:.2e}")

    try:
        MultiKeyContext(n_users=1)
        check("rejects single-user fleet", False, "no ValueError")
    except ValueError:
        check("rejects single-user fleet", True)


def test_dropout_is_detected() -> None:
    print("\n[test] dropout produces a loud error, not silent garbage")
    check("naive whole-fleet masks + dropout is caught",
          demonstrate_dropout_failure(n_users=6))

    # The fix: re-scope masks to whoever actually reports in.
    ctx = MultiKeyContext(n_users=8, seed=3)
    survivors = [0, 1, 2, 5, 7]
    ctx.begin_round(survivors)
    masked = ctx.collect_masked_shares()
    s = ctx.reconstruct_aggregate_key(masked)
    expected = sum(ctx.shares[u].share for u in survivors)
    check("round-scoped masks cancel for the surviving subset",
          np.allclose(s, expected, atol=1e-9),
          f"max err {np.max(np.abs(s - expected)):.2e}")


# ── D6: secure channel ───────────────────────────────────────────────────
def test_secure_channel() -> None:
    print("\n[test] D6 — authenticated encrypted channel")
    a = IdentityKey.generate("aggregator-server")
    b = IdentityKey.generate("vehicle-0001")
    ca, cb = handshake_pair(a, b)
    check("both sides derive the same key", ca.aes_key == cb.aes_key)

    msg = np.random.default_rng(4).normal(0, 1, 128).tobytes()
    sealed = ca.encrypt(msg)
    check("ciphertext differs from plaintext", sealed != msg)
    check("round-trip recovers the payload", cb.decrypt(sealed) == msg)

    tampered = bytearray(sealed)
    tampered[20] ^= 0x01
    try:
        cb.decrypt(bytes(tampered))
        check("tampering is rejected", False, "decrypt accepted a modified frame")
    except Exception:
        check("tampering is rejected", True)


# ── D4: the server must never decrypt an individual update ──────────────
def test_audit_invariant() -> None:
    print("\n[test] D4 — no individual update is ever decrypted")
    audit = AggregationAudit()
    assert_no_individual_decryption(audit)
    check("clean audit passes", True)

    audit.individual_update_decryptions = 1
    try:
        assert_no_individual_decryption(audit)
        check("dirty audit is rejected", False, "no AssertionError")
    except AssertionError:
        check("dirty audit is rejected", True)


def test_strict_profile_refuses_rather_than_degrades() -> None:
    print("\n[test] unimplemented 'strict' profile fails loudly")
    try:
        FederatedServer.initialize(
            dataset="car_hack", n_classes=5, hidden_dim=64, num_layers=2,
            degree=4, dropout=0.2, backend="exact", disclosure="strict",
            n_clients=4,
        )
        check("strict profile raises NotImplementedError", False,
              "server was constructed — it would silently behave like 'practical'")
    except NotImplementedError as exc:
        msg = str(exc)
        check("strict profile raises NotImplementedError", True)
        check("the error explains what is missing",
              "second ciphertext" in msg or "second multiply" in msg or "N=16384" in msg,
              msg[:80])
    except Exception as exc:
        check("strict profile raises NotImplementedError", False,
              f"raised {type(exc).__name__} instead")


def test_non_poisoning_rates() -> None:
    print("\n[test] FheFL eq. 7/8 — non-poisoning rates")
    d = np.array([1.0, 1.0, 1.0, 1.0])
    p = FederatedServer._non_poisoning_rates(d)
    check("equal distances give uniform weights",
          np.allclose(p, 0.25), f"got {p}")
    check("weights sum to 1", abs(p.sum() - 1.0) < 1e-12)

    d = np.array([1.0, 1.0, 1.0, 100.0])       # one clear outlier
    p = FederatedServer._non_poisoning_rates(d)
    check("outlier gets the smallest weight", p[3] == p.min(), f"got {p}")
    check("outlier is down-weighted vs the honest majority",
          p[3] < p[0] / 2, f"outlier {p[3]:.4f} honest {p[0]:.4f}")
    check("weights still sum to 1", abs(p.sum() - 1.0) < 1e-12)


def main() -> int:
    print("=" * 68)
    print("Month-5 cryptographic layer verification")
    print("=" * 68)
    test_backend_equivalence()
    test_real_ckks_roundtrip()
    test_encrypted_distance()
    test_depth_budget()
    test_mask_cancellation()
    test_dropout_is_detected()
    test_secure_channel()
    test_audit_invariant()
    test_strict_profile_refuses_rather_than_degrades()
    test_non_poisoning_rates()

    print("\n" + "=" * 68)
    print(f"{len(_passes)} passed, {len(_failures)} failed")
    for name, detail in _failures:
        print(f"  FAILED: {name}  {detail}")
    print("=" * 68)
    return 1 if _failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

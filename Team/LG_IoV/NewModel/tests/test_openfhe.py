"""Verification tests for the OpenFHE backend (migration phases M1-M3).

Covers the checklist in Documentation/18_dmk_ckks_decision.md §10 that can be
tested on the real library, plus parity with the TenSEAL "ckks" backend.

OpenFHE ships Linux wheels only, so on this project's Windows machine run it
under WSL::

    wsl -d Ubuntu -- ~/ofhe-venv/bin/python tests/test_openfhe.py

On a host without ``openfhe`` the suite reports SKIP and exits 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from federated.openfhe_backend import (                   # noqa: E402
    OPENFHE_AVAILABLE, DisclosureRefused, OpenFHEContext, OpenFHEVector,
    ThresholdUnavailable,
)

_failures: list = []
_passes: list = []

N_PARAMS = 44_164       # ChebyKAN, 46 features, hidden 64, 2 layers, degree 4


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        _passes.append(name)
        print(f"  PASS  {name}")
    else:
        _failures.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def raises(fn, exc) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


rng = np.random.default_rng(2025)


# ── M1: the profile ──────────────────────────────────────────────────────
def test_profile(ctx: OpenFHEContext) -> None:
    print("\n[test] M1 — 128-bit profile at N=8192")
    check("ring dimension is 8192", ctx.cc.GetRingDimension() == 8192)
    check("4096 slots per ciphertext", ctx.slot_count == 4096)
    v = OpenFHEVector(ctx, data=np.zeros(N_PARAMS))
    check("a ChebyKAN update needs 11 ciphertexts", len(v._chunks) == 11,
          f"got {len(v._chunks)}")
    check("depth 2 on a fresh ciphertext", ctx.levels_remaining(v._chunks[0]) == 2)


# ── M2: single-key parity ────────────────────────────────────────────────
def test_single_key_roundtrip(ctx: OpenFHEContext) -> None:
    print("\n[test] M2 — single-key aggregation matches plaintext")
    vecs = [rng.normal(0, 0.05, 9000) for _ in range(4)]
    w = rng.dirichlet(np.ones(4))
    enc = [OpenFHEVector(ctx, data=v, levels_to_drop=1, contributors={i})
           for i, v in enumerate(vecs)]
    acc = enc[0] * float(w[0])
    for e, wi in zip(enc[1:], w[1:]):
        acc = acc + e * float(wi)
    got = acc.decrypt()
    want = sum(wi * v for wi, v in zip(w, vecs))
    err = float(np.max(np.abs(got - want)))
    check("weighted aggregate within 1e-6", err < 1e-6, f"max err {err:.2e}")
    check("length preserved across the partial last chunk", got.size == 9000)


def test_level_drop(ctx: OpenFHEContext) -> None:
    print("\n[test] M2 — level-dropped transmission (packing lever 1)")
    v = rng.normal(0, 0.05, 4096)
    full = OpenFHEVector(ctx, data=v).serialized_bytes()
    dropped = OpenFHEVector(ctx, data=v, levels_to_drop=1)
    ratio = dropped.serialized_bytes() / full
    check("1-level drop shrinks the ciphertext to ~2/3", 0.6 < ratio < 0.72,
          f"ratio {ratio:.3f}")
    check("1 level left for the server", ctx.levels_remaining(dropped._chunks[0]) == 1)
    check("2-level drop is rejected before upload",
          raises(lambda: OpenFHEVector(ctx, data=v, levels_to_drop=2), ValueError))


def test_encrypted_distance(ctx: OpenFHEContext) -> None:
    print("\n[test] M2 — FheFL eq. 11 encrypted squared distance")
    f = rng.normal(0, 0.07, N_PARAMS)
    g = rng.normal(0, 0.07, N_PARAMS)
    enc = OpenFHEVector(ctx, data=f, levels_to_drop=1, contributors={0})
    d = enc.encrypted_sq_distance(g).reveal()
    truth = float(np.sum((g - f) ** 2))
    check("encrypted distance matches plaintext to 1e-5", abs(d - truth) < 1e-5,
          f"got {d:.8f} want {truth:.8f}")
    d2 = (enc.encrypted_sq_distance(g) + enc.encrypted_sq_distance(g)).reveal()
    check("encrypted distances add homomorphically", abs(d2 - 2 * truth) < 2e-5)
    agg = (enc * 0.5 + OpenFHEVector(ctx, data=f, levels_to_drop=1, contributors={1}) * 0.5)
    check("ciphertext still usable after the distance",
          float(np.max(np.abs(agg.decrypt() - f))) < 1e-6)


def test_parity_with_tenseal(ctx: OpenFHEContext) -> None:
    print("\n[test] M2 — OpenFHE agrees with the TenSEAL 'ckks' backend")
    try:
        from federated.fhe_adapter import build_ckks_context, encrypt_update
        ts_ctx = build_ckks_context()
    except Exception as e:                       # pragma: no cover
        print(f"  SKIP  TenSEAL unavailable ({e})")
        return
    vecs = [rng.normal(0, 0.05, N_PARAMS) for _ in range(3)]
    g = rng.normal(0, 0.05, N_PARAMS)
    w = [0.5, 0.3, 0.2]
    ofh = [encrypt_update(v, "openfhe", ctx, levels_to_drop=1, owner=i) for i, v in enumerate(vecs)]
    tsv = [encrypt_update(v, "ckks", ts_ctx, levels_to_drop=1) for v in vecs]
    a = (ofh[0] * w[0] + ofh[1] * w[1] + ofh[2] * w[2]).decrypt()
    b = (tsv[0] * w[0] + tsv[1] * w[1] + tsv[2] * w[2]).decrypt()
    check("aggregates agree to 1e-5", float(np.max(np.abs(a - b))) < 1e-5,
          f"max diff {np.max(np.abs(a - b)):.2e}")
    da = ofh[0].encrypted_sq_distance(g).reveal()
    db = tsv[0].encrypted_sq_distance(g).reveal()
    check("distances agree to 1e-3", abs(da - db) < 1e-3, f"{da:.6f} vs {db:.6f}")
    print(f"  info  wire bytes per update: openfhe {ofh[0].serialized_bytes():,} "
          f"vs tenseal {tsv[0].serialized_bytes():,}")


# ── M3: threshold CKKS ───────────────────────────────────────────────────
def test_threshold(n: int = 5) -> None:
    print(f"\n[test] M3 — threshold CKKS over {n} vehicles (doc 18 §10 checklist)")
    ctx = OpenFHEContext.threshold(n)
    ks = ctx.keyset
    check(f"default threshold is a majority ({n // 2 + 1}-of-{n})", ks.t == n // 2 + 1)
    vecs = [rng.normal(0, 0.05, 5000) for _ in range(n)]
    enc = [OpenFHEVector(ctx, data=v, levels_to_drop=1, contributors={i})
           for i, v in enumerate(vecs)]
    # The server always weights before it decrypts (FedAvg / eq. 9), so test
    # the aggregate in that form.
    w = rng.dirichlet(np.ones(n))
    acc = enc[0] * float(w[0])
    for e, wi in zip(enc[1:], w[1:]):
        acc = acc + e * float(wi)
    truth = sum(wi * v for wi, v in zip(w, vecs))

    got = acc.decrypt()
    check("weighted aggregate decrypts to Σ w_i W_i within CKKS error",
          float(np.max(np.abs(got - truth))) < 1e-5,
          f"max err {np.max(np.abs(got - truth)):.2e}")
    check("every vehicle issued a share", all(h.shares_issued > 0 for h in ks.holders))

    # OpenFHE adds fixed smudging noise (sigma 2^20) to every CKKS share. On a
    # ciphertext that was never rescaled it is visible at ~1e-3 in the slots;
    # this detects that the noise is present at all (migration phase M4).
    plain_sum = enc[0]
    for e in enc[1:]:
        plain_sum = plain_sum + e
    floor = float(np.max(np.abs(plain_sum.decrypt() - sum(vecs))))
    check("share smudging noise is present (unrescaled floor 1e-5 .. 5e-3)",
          1e-5 < floor < 5e-3, f"floor {floor:.2e}")
    print(f"  info  unrescaled threshold-decryption floor: {floor:.2e}")

    def lone_decrypt():
        pt = ctx.cc.Decrypt(ks.holders[1]._sk, enc[0]._chunks[0])
        pt.SetLength(16)
        vals = np.asarray(pt.GetRealPackedValue())
        if np.max(np.abs(vals - vecs[0][:16])) < 1e-3:
            raise AssertionError("one vehicle's key decrypted another's update")
    ok = True
    try:
        lone_decrypt()
    except AssertionError:
        ok = False
    except Exception:
        ok = True           # OpenFHE refuses to decode: also a pass
    check("no single vehicle's key decrypts another vehicle's ct_i", ok)

    check("an individual upload is never share-decrypted",
          raises(lambda: enc[2].decrypt(), DisclosureRefused))
    check("a scaled individual upload is still refused",
          raises(lambda: (enc[2] * 3.0).decrypt(), DisclosureRefused))
    before = [h.shares_issued for h in ks.holders]
    raises(lambda: enc[2].decrypt(), DisclosureRefused)
    check("a refused request issues no shares",
          [h.shares_issued for h in ks.holders] == before)

    d = enc[0].encrypted_sq_distance(np.zeros(5000)).reveal()
    check("practical-profile distance scalar is allowed",
          abs(d - float(vecs[0] @ vecs[0])) < 1e-5)

    # Dropout within the threshold: rebuild the missing shares.
    ks.set_offline({n})
    got2 = acc.decrypt()
    check("1 vehicle offline: Shamir recovery still decrypts correctly",
          float(np.max(np.abs(got2 - truth))) < 1e-5)
    check("the recovered vehicle is flagged for re-keying", ks.needs_rekey == {n})

    # Dropout beyond the threshold: refuse, never garbage.
    ks.set_offline(set(range(ks.t, n + 1)))
    check(f"only {ks.t - 1} of {n} online: the round refuses to decrypt",
          raises(lambda: acc.decrypt(), ThresholdUnavailable))
    ks.set_offline(set())


def test_server_round() -> None:
    print("\n[test] M3 — FederatedServer round on the threshold backend")
    import torch
    from federated.fhe_adapter import encrypt_update, flatten_model
    from federated.server import FederatedServer, assert_no_individual_decryption
    torch.manual_seed(0)
    n = 4
    server = FederatedServer.initialize(
        dataset="car_hack", n_classes=2, hidden_dim=64, num_layers=2, degree=4,
        dropout=0.2, backend="openfhe-threshold", n_clients=n, seed=2025)
    g = flatten_model(server.model)
    updates = [g + rng.normal(0, 0.01, g.size) for _ in range(n - 1)]
    updates.append(g + rng.normal(0, 0.2, g.size))        # one outlier
    pkgs = [{"client_id": i,
             "encrypted_update": encrypt_update(u, "openfhe-threshold", server.context,
                                                levels_to_drop=1, owner=i),
             "sample_size": 100, "n_parameters": g.size}
            for i, u in enumerate(updates)]
    diag = server.aggregate_round(pkgs)
    assert_no_individual_decryption(server.audit)
    w = np.asarray(diag["non_poisoning_rates"])
    expect = sum(wi * u for wi, u in zip(w, updates))
    got = flatten_model(server.model)
    check("server aggregate matches the plaintext weighted sum",
          float(np.max(np.abs(got - expect))) < 1e-5,
          f"max err {np.max(np.abs(got - expect)):.2e}")
    check("the outlier gets the smallest weight", int(np.argmin(w)) == n - 1, f"{w}")
    check("zero individual-update decryptions",
          server.audit.individual_update_decryptions == 0)
    check("server holds no secret key", server.context._sk is None)
    check("decryption share size is reported",
          (diag["decryption_share_bytes"] or 0) > 0)
    print(f"  info  ciphertext bytes/client {diag['ciphertext_bytes_per_client']:,}; "
          f"share bytes/ct {diag['decryption_share_bytes']:,}")


def main() -> int:
    print("=" * 68)
    print("OpenFHE backend verification (migration M1-M3)")
    print("=" * 68)
    if not OPENFHE_AVAILABLE:
        print("SKIP: the `openfhe` package is not installed on this host "
              "(Linux only; run under WSL)")
        return 0
    ctx = OpenFHEContext.single_key()
    test_profile(ctx)
    test_single_key_roundtrip(ctx)
    test_level_drop(ctx)
    test_encrypted_distance(ctx)
    test_parity_with_tenseal(ctx)
    test_threshold()
    test_server_round()

    print("\n" + "=" * 68)
    print(f"{len(_passes)} passed, {len(_failures)} failed")
    for name, detail in _failures:
        print(f"  FAILED: {name}  {detail}")
    print("=" * 68)
    return 1 if _failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

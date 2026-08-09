"""Measure every packing/encoding lever end to end.

    python scripts/benchmark_packing.py

Produces ``results/packing_benchmark.json`` and the table used in the
Optimized Packing & Encoding Module report. Each lever is measured against the
real ChebyKAN parameter count with real CKKS ciphertexts, and correctness is
re-verified after each change - a bandwidth saving that breaks the protocol is
not a saving.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import tenseal as ts

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from federated.packing import (                                   # noqa: E402
    MAX_SAFE_LEVEL_DROP, PackingConfig, compare_configs, plan,
    scatter_top_k, select_top_k,
)

RESULTS = ROOT / "results"
N_PARAMS = 44_164          # ChebyKAN, 5-class configuration
N_CLIENTS = 7              # 10 vehicles x 0.7 sampling
SLOTS = 4096


def make_context():
    c = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                   coeff_mod_bit_sizes=[60, 40, 40, 60])
    c.global_scale = 2 ** 40
    c.generate_galois_keys()
    c.generate_relin_keys()
    return c


def encrypt(ctx, vec, drop):
    chunks = [ts.ckks_vector(ctx, vec[i:i + SLOTS].tolist())
              for i in range(0, vec.size, SLOTS)]
    for _ in range(drop):
        for ch in chunks:
            ch *= 1.0
    return chunks


def round_trip(ctx, clients, g, drop):
    """One full FheFL round; returns (bytes/client, distance err, agg err, ok)."""
    encs = [encrypt(ctx, v, drop) for v in clients]
    nbytes = sum(len(c.serialize()) for c in encs[0])

    # (a) encrypted squared distance, eq. 11
    d_err = float("nan")
    try:
        got, truth = [], []
        for cl, v in zip(encs, clients):
            acc = None
            for k, ch in enumerate(cl):
                lo, hi = k * SLOTS, min((k + 1) * SLOTS, v.size)
                gs = g[lo:hi]
                term = (ch - (2.0 * gs).tolist()).dot(ch)
                acc = term if acc is None else acc + term
            got.append(float(np.asarray(acc.decrypt())[0]) + float(np.dot(g, g)))
            truth.append(float(np.sum((g - v) ** 2)))
        d_err = max(abs(a - b) for a, b in zip(got, truth))
    except Exception as exc:
        return nbytes, float("nan"), float("nan"), f"distance failed: {type(exc).__name__}"

    # (b) weighted homomorphic aggregation
    try:
        w = np.random.default_rng(7).dirichlet(np.ones(len(clients)))
        n_chunks = len(encs[0])
        agg = []
        for ci in range(n_chunks):
            a = encs[0][ci] * float(w[0])
            for cl in range(1, len(encs)):
                a += encs[cl][ci] * float(w[cl])
            agg.append(a)
        out = np.concatenate([np.asarray(a.decrypt()) for a in agg])[:N_PARAMS]
        exp = np.sum([wi * v for wi, v in zip(w, clients)], axis=0)
        a_err = float(np.max(np.abs(out - exp)))
    except Exception as exc:
        return nbytes, d_err, float("nan"), f"aggregation failed: {type(exc).__name__}"

    return nbytes, d_err, a_err, "ok"


def main() -> int:
    rng = np.random.default_rng(42)
    clients = [rng.normal(0, 0.05, N_PARAMS) for _ in range(N_CLIENTS)]
    g = rng.normal(0, 0.05, N_PARAMS)
    ctx = make_context()
    plaintext_bytes = N_PARAMS * 4

    print("=" * 74)
    print("Lever 1 - level-dropped transmission (measured, lossless)")
    print("=" * 74)
    lever1 = []
    baseline_bytes = None
    for drop in (0, 1, 2):
        t0 = time.perf_counter()
        nbytes, d_err, a_err, status = round_trip(ctx, clients, g, drop)
        dt = time.perf_counter() - t0
        if baseline_bytes is None:
            baseline_bytes = nbytes
        saving = 100.0 * (1 - nbytes / baseline_bytes)
        safe = drop <= MAX_SAFE_LEVEL_DROP
        print(f"  drop={drop}  {nbytes/1024/1024:5.2f} MB/client  "
              f"saving={saving:5.1f}%  dist_err={d_err:.2e}  agg_err={a_err:.2e}  "
              f"{status}{'' if safe else '   <-- EXCEEDS SAFE BOUND'}")
        lever1.append({
            "levels_dropped": drop, "bytes_per_client": nbytes,
            "megabytes": nbytes / 1024 / 1024, "saving_pct": saving,
            "distance_max_err": d_err, "aggregation_max_err": a_err,
            "status": status, "within_safe_bound": safe,
            "round_seconds": dt,
        })

    print()
    print("=" * 74)
    print("Lever 2 - padding waste")
    print("=" * 74)
    p = plan(N_PARAMS, PackingConfig(levels_to_drop=1))
    print(f"  {N_PARAMS:,} values into {p.n_chunks} x {SLOTS} slots = "
          f"{p.padded_slots:,} slots")
    print(f"  wasted: {p.padded_slots - N_PARAMS:,} slots "
          f"({p.padding_fraction*100:.1f}%)")

    print()
    print("=" * 74)
    print("Lever 3 - top-k sparsification (LOSSY, opt-in)")
    print("=" * 74)
    lever3 = []
    for frac in (1.0, 0.5, 0.25, 0.1):
        idx, vals = select_top_k(clients[0], frac)
        recon = scatter_top_k(idx, vals, N_PARAMS)
        rel = float(np.linalg.norm(recon - clients[0]) / np.linalg.norm(clients[0]))
        cfg = PackingConfig(levels_to_drop=1,
                            sparsify_top_k=None if frac == 1.0 else frac)
        pl = plan(N_PARAMS, cfg)
        print(f"  keep {frac*100:5.1f}%  -> {pl.n_chunks:2d} ciphertexts  "
              f"{pl.est_total_bytes/1024/1024:5.2f} MB  "
              f"(idx overhead {pl.index_overhead_bytes/1024:5.1f} KB)  "
              f"relative reconstruction error {rel:.3f}")
        lever3.append({
            "keep_fraction": frac, "n_chunks": pl.n_chunks,
            "bytes": pl.est_total_bytes,
            "index_overhead_bytes": pl.index_overhead_bytes,
            "relative_reconstruction_error": rel,
        })

    print()
    print("=" * 74)
    print("Combined configurations")
    print("=" * 74)
    combos = compare_configs(N_PARAMS, {
        "baseline (Month 4: no drop, dense)": PackingConfig(levels_to_drop=0),
        "level-dropped (Month 5 default)": PackingConfig(levels_to_drop=1),
        "level-dropped + top-50% (lossy)": PackingConfig(levels_to_drop=1, sparsify_top_k=0.5),
        "level-dropped + top-25% (lossy)": PackingConfig(levels_to_drop=1, sparsify_top_k=0.25),
    })
    for r in combos:
        tag = "  LOSSY" if r["lossy"] else ""
        print(f"  {r['name']:<38} {r['megabytes']:5.2f} MB  "
              f"{r['expansion']:5.1f}x  saving {r['saving_pct']:5.1f}%{tag}")

    out = {
        "n_parameters": N_PARAMS,
        "plaintext_bytes": plaintext_bytes,
        "slot_count": SLOTS,
        "active_clients": N_CLIENTS,
        "max_safe_level_drop": MAX_SAFE_LEVEL_DROP,
        "lever1_level_drop": lever1,
        "lever2_padding": {
            "padded_slots": p.padded_slots,
            "wasted_slots": p.padded_slots - N_PARAMS,
            "padding_pct": p.padding_fraction * 100,
        },
        "lever3_sparsification": lever3,
        "combined": combos,
        "lever4_seed_compression": {
            "available": False,
            "reason": "TenSEAL exposes no Serializable<Ciphertext>; SEAL and "
                      "OpenFHE do. Would send c0 plus a 32-byte seed instead of "
                      "(c0, c1).",
            "theoretical_saving_pct": 50.0,
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "packing_benchmark.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nsaved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

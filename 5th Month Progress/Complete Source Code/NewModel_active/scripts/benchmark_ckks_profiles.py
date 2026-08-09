"""Measure real CKKS cost for both FheFL disclosure profiles.

Supersedes ``benchmark_real_ckks.py`` (Month 4), which measured **addition and
plaintext-scalar multiplication only**. FheFL also needs a ciphertext ×
ciphertext multiply for the squared-distance term of eq. 11, which is far more
expensive and constrains the parameter set. Quoting the addition-only number in
an FheFL context understates the cost by roughly an order of magnitude.

What this measures, per profile:

* encryption time per client update
* homomorphic weighted aggregation time (the FedAvg / non-poisoning-rate sum)
* encrypted squared-distance time (eq. 11 — the ct×ct multiply)
* aggregate decryption time
* serialized ciphertext size and expansion factor over float32
* numerical error versus the plaintext computation

Run from the NewModel directory::

    python scripts/benchmark_ckks_profiles.py
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

RESULTS_DIR = ROOT / "results"

#: ChebyKAN parameter counts. can_vtc and cicids/veremi differ only by the
#: output layer width (n_classes).
DATASET_PARAMS = {
    "can_vtc": 43_394,      # 2 classes
    "car_hack": 44_549,     # 5 classes
    "cicids": 43_394,       # 2 classes
    "veremi": 43_394,       # 2 classes
}

PROFILES = {
    "practical": dict(poly_modulus_degree=8192,
                      coeff_mod_bit_sizes=[60, 40, 40, 60]),
    "strict":    dict(poly_modulus_degree=16384,
                      coeff_mod_bit_sizes=[60, 40, 40, 40, 60]),
}

N_ACTIVE_CLIENTS = 7        # 10 clients x 0.7 sampling


def build(profile: dict):
    ctx = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=profile["poly_modulus_degree"],
        coeff_mod_bit_sizes=profile["coeff_mod_bit_sizes"],
    )
    ctx.global_scale = 2 ** 40
    ctx.generate_galois_keys()
    ctx.generate_relin_keys()
    return ctx


def chunk(vec: np.ndarray, slots: int):
    return [vec[i * slots:(i + 1) * slots].tolist()
            for i in range(int(np.ceil(vec.size / slots)))]


def benchmark(name: str, n_params: int, profile_name: str, profile: dict) -> dict:
    ctx = build(profile)
    slots = profile["poly_modulus_degree"] // 2
    rng = np.random.default_rng(42)

    clients = [rng.normal(0, 0.05, n_params) for _ in range(N_ACTIVE_CLIENTS)]
    g_prev = rng.normal(0, 0.05, n_params)
    weights = rng.dirichlet(np.ones(N_ACTIVE_CLIENTS))

    # ── encryption ───────────────────────────────────────────────────────
    t0 = time.perf_counter()
    enc = [[ts.ckks_vector(ctx, c) for c in chunk(v, slots)] for v in clients]
    t_encrypt = (time.perf_counter() - t0) / N_ACTIVE_CLIENTS

    ct_bytes = sum(len(c.serialize()) for c in enc[0])
    pt_bytes = n_params * 4

    # ── encrypted squared distance, eq. 11 (ct x ct) ─────────────────────
    t0 = time.perf_counter()
    for cl in range(N_ACTIVE_CLIENTS):
        acc = None
        for k, c in enumerate(enc[cl]):
            lo = k * slots
            hi = min(lo + slots, n_params)
            gs = np.zeros(hi - lo)
            gs[:] = g_prev[lo:hi]
            term = (c - (2.0 * gs).tolist()).dot(c)
            acc = term if acc is None else acc + term
        _ = float(np.asarray(acc.decrypt())[0]) + float(np.dot(g_prev, g_prev))
    t_distance = (time.perf_counter() - t0) / N_ACTIVE_CLIENTS

    # ── homomorphic weighted aggregation ─────────────────────────────────
    enc2 = [[ts.ckks_vector(ctx, c) for c in chunk(v, slots)] for v in clients]
    n_chunks = len(enc2[0])
    t0 = time.perf_counter()
    agg = []
    for ci in range(n_chunks):
        acc = enc2[0][ci] * float(weights[0])
        for cl in range(1, N_ACTIVE_CLIENTS):
            acc += enc2[cl][ci] * float(weights[cl])
        agg.append(acc)
    t_aggregate = time.perf_counter() - t0

    # ── decryption of the aggregate ──────────────────────────────────────
    t0 = time.perf_counter()
    out = np.concatenate([np.asarray(c.decrypt()) for c in agg])[:n_params]
    t_decrypt = time.perf_counter() - t0

    truth = np.sum([w * v for w, v in zip(weights, clients)], axis=0)
    max_err = float(np.max(np.abs(out - truth)))

    return {
        "dataset": name,
        "profile": profile_name,
        "poly_modulus_degree": profile["poly_modulus_degree"],
        "coeff_mod_bit_sizes": profile["coeff_mod_bit_sizes"],
        "total_coeff_bits": int(sum(profile["coeff_mod_bit_sizes"])),
        "multiplicative_levels": len(profile["coeff_mod_bit_sizes"]) - 2,
        "n_params": n_params,
        "n_ciphertext_chunks": n_chunks,
        "active_clients": N_ACTIVE_CLIENTS,
        "encrypt_sec_per_client": t_encrypt,
        "encrypted_distance_sec_per_client": t_distance,
        "homomorphic_aggregate_sec": t_aggregate,
        "decrypt_aggregate_sec": t_decrypt,
        "round_overhead_sec": (t_encrypt + t_distance * N_ACTIVE_CLIENTS
                               + t_aggregate + t_decrypt),
        "ciphertext_bytes_per_client": ct_bytes,
        "plaintext_bytes_per_client": pt_bytes,
        "ciphertext_expansion": ct_bytes / pt_bytes,
        "max_abs_error_vs_plaintext": max_err,
    }


def main() -> int:
    results = []
    for profile_name, profile in PROFILES.items():
        print(f"\n=== profile '{profile_name}': N={profile['poly_modulus_degree']}, "
              f"chain={profile['coeff_mod_bit_sizes']} "
              f"({sum(profile['coeff_mod_bit_sizes'])} bits, "
              f"{len(profile['coeff_mod_bit_sizes']) - 2} levels) ===")
        for name, n_params in DATASET_PARAMS.items():
            r = benchmark(name, n_params, profile_name, profile)
            results.append(r)
            print(f"  {name:9s} enc/client={r['encrypt_sec_per_client']*1000:7.1f}ms  "
                  f"dist/client={r['encrypted_distance_sec_per_client']*1000:7.1f}ms  "
                  f"agg={r['homomorphic_aggregate_sec']*1000:7.1f}ms  "
                  f"dec={r['decrypt_aggregate_sec']*1000:6.1f}ms  "
                  f"ct={r['ciphertext_bytes_per_client']/1024:8.1f}KB  "
                  f"x{r['ciphertext_expansion']:.1f}  "
                  f"err={r['max_abs_error_vs_plaintext']:.1e}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "ckks_profile_benchmark.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nsaved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

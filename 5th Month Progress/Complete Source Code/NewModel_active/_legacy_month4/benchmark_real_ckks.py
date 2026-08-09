"""Real CKKS (TenSEAL) overhead benchmark for the ChebyKAN federated pipeline.

The simulated FHE used in train_federated.py (fhe_adapter.SimulatedCKKSVector) is
plain numpy arithmetic with a tiny injected noise term -- it is useful for proving
the *aggregation math* is zero-loss, but it does not cost anything extra to run, so
it cannot show real encryption/aggregation/decryption overhead.

This script benchmarks genuine TenSEAL CKKS operations (real lattice-based
homomorphic encryption, not a numpy stand-in) on the actual ChebyKAN parameter
tensor sizes for every dataset, so we can report a defensible, literature-grounded
overhead number for a real deployment.

Model: each client flattens its full parameter vector, splits it into ciphertexts of
up to `slot_count` values (CKKS packs poly_modulus_degree/2 real numbers per
ciphertext), encrypts each chunk, the server homomorphically computes the
sample-weighted FedAvg sum directly on ciphertexts (no decryption), and a client
decrypts the aggregated result with its own secret key.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import tenseal as ts

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"

# Actual ChebyKAN parameter counts per dataset (from federated_summary_*.json / model init)
DATASET_PARAM_COUNTS = {
    "can_vtc": 44164,
    "car_hack": 44549,
    "cicids": 43394,
    "veremi": 43394,
}

N_CLIENTS_ACTIVE = 7  # 10 clients * sampling_rate 0.7, matching train_federated.py defaults


def make_context() -> ts.Context:
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=8192,
        coeff_mod_bit_sizes=[60, 40, 40, 60],
    )
    context.global_scale = 2 ** 40
    context.generate_galois_keys()
    context.generate_relin_keys()
    return context


def benchmark_dataset(name: str, n_params: int, context: ts.Context, slot_count: int) -> dict:
    rng = np.random.default_rng(42)
    n_chunks = int(np.ceil(n_params / slot_count))

    # Simulate N_CLIENTS_ACTIVE clients, each with their own plaintext weight vector
    client_vectors = [rng.normal(0, 0.05, size=n_params).astype(np.float64) for _ in range(N_CLIENTS_ACTIVE)]
    sample_weights = rng.dirichlet(np.ones(N_CLIENTS_ACTIVE))

    # --- Encryption (each client encrypts its own update) ---
    t0 = time.perf_counter()
    client_ciphertexts = []
    for vec in client_vectors:
        chunks = [vec[i * slot_count:(i + 1) * slot_count].tolist() for i in range(n_chunks)]
        enc_chunks = [ts.ckks_vector(context, c) for c in chunks]
        client_ciphertexts.append(enc_chunks)
    t1 = time.perf_counter()
    encrypt_time_total = t1 - t0

    # --- Homomorphic weighted aggregation (server side, ciphertext-only) ---
    t0 = time.perf_counter()
    agg_chunks = []
    for chunk_idx in range(n_chunks):
        acc = client_ciphertexts[0][chunk_idx] * float(sample_weights[0])
        for c in range(1, N_CLIENTS_ACTIVE):
            acc += client_ciphertexts[c][chunk_idx] * float(sample_weights[c])
        agg_chunks.append(acc)
    t1 = time.perf_counter()
    aggregate_time = t1 - t0

    # --- Decryption (client side, needs secret key) ---
    t0 = time.perf_counter()
    decrypted = np.concatenate([np.array(c.decrypt()) for c in agg_chunks])[:n_params]
    t1 = time.perf_counter()
    decrypt_time = t1 - t0

    # Correctness check against plaintext FedAvg
    plaintext_avg = np.sum([w * v for w, v in zip(sample_weights, client_vectors)], axis=0)
    max_abs_err = float(np.max(np.abs(decrypted - plaintext_avg)))

    # Rough ciphertext size on the wire (serialized bytes) for one client's full update
    one_client_bytes = sum(len(c.serialize()) for c in client_ciphertexts[0])
    plaintext_bytes = n_params * 4  # float32 baseline

    return {
        "dataset": name,
        "n_params": n_params,
        "n_ciphertext_chunks_per_client": n_chunks,
        "active_clients": N_CLIENTS_ACTIVE,
        "encrypt_time_sec_all_clients": encrypt_time_total,
        "encrypt_time_sec_per_client": encrypt_time_total / N_CLIENTS_ACTIVE,
        "homomorphic_aggregate_time_sec": aggregate_time,
        "decrypt_time_sec": decrypt_time,
        "real_fhe_round_overhead_sec": encrypt_time_total / N_CLIENTS_ACTIVE + aggregate_time + decrypt_time,
        "max_abs_error_vs_plaintext_fedavg": max_abs_err,
        "ciphertext_bytes_per_client_update": one_client_bytes,
        "plaintext_bytes_per_client_update": plaintext_bytes,
        "ciphertext_expansion_factor": one_client_bytes / plaintext_bytes,
    }


def main() -> None:
    print("[bench] Building CKKS context (poly_modulus_degree=8192, coeff_mod=[60,40,40,60])...")
    context = make_context()
    slot_count = context.slot_count if hasattr(context, "slot_count") else 4096
    slot_count = 8192 // 2
    print(f"[bench] CKKS slot count per ciphertext: {slot_count}")

    results = []
    for name, n_params in DATASET_PARAM_COUNTS.items():
        print(f"[bench] Benchmarking real TenSEAL CKKS for {name} ({n_params:,} params)...")
        r = benchmark_dataset(name, n_params, context, slot_count)
        results.append(r)
        print(
            f"  encrypt/client={r['encrypt_time_sec_per_client']*1000:.2f}ms  "
            f"agg={r['homomorphic_aggregate_time_sec']*1000:.2f}ms  "
            f"decrypt={r['decrypt_time_sec']*1000:.2f}ms  "
            f"round_overhead={r['real_fhe_round_overhead_sec']*1000:.2f}ms  "
            f"max_err={r['max_abs_error_vs_plaintext_fedavg']:.2e}  "
            f"ciphertext_expansion={r['ciphertext_expansion_factor']:.1f}x"
        )

    out_path = CHECKPOINT_DIR / "real_ckks_benchmark.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[bench] Saved results to {out_path}")


if __name__ == "__main__":
    main()

"""Cryptographic and Numerical Equivalence Tests for CKKS Homomorphic Aggregation."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.crypto.ckks_context import create_ckks_key_manager
from src.crypto.ckks_vector import CKKSVector, PlaintextVector


def test_ckks_f_aggregation_numerical_equivalence() -> None:
    print("\n[test] CKKS F aggregation numerical equivalence with plaintext ground truth")
    key_manager = create_ckks_key_manager(poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 40, 60], global_scale_bits=40)
    pub_ctx = key_manager.public_context
    sec_ctx = key_manager.secret_context

    rng = np.random.default_rng(2025)
    # 44,164 parameters matching ChebyKAN full vector
    dim = 44164
    sample_counts = [350, 1200, 2500, 5000]
    K = len(sample_counts)
    N = sum(sample_counts)

    # 4 synthetic model update vectors
    raw_updates = [rng.normal(0, 0.02, size=dim) for _ in range(K)]

    # 1. Plaintext aggregation ground truth
    delta_w_plain = np.sum([n * v for n, v in zip(sample_counts, raw_updates)], axis=0) / float(N)

    # 2. CKKS homomorphic aggregation
    enc_updates = [CKKSVector(pub_ctx, data=v) for v in raw_updates]
    assert enc_updates[0].num_chunks == 11, f"Expected 11 chunks for dim {dim}, got {enc_updates[0].num_chunks}"

    # Step 1: Multiply each ciphertext by plaintext scalar n_k
    scaled_ckks = [c * n for c, n in zip(enc_updates, sample_counts)]

    # Step 2: Add ciphertexts
    c_sum = scaled_ckks[0]
    for c in scaled_ckks[1:]:
        c_sum = c_sum + c

    # Step 3: Multiply by plaintext scalar 1/N
    c_F = c_sum * (1.0 / float(N))

    # Authorized decryption of aggregated ciphertext
    delta_w_ckks = c_F.decrypt(secret_context=sec_ctx)

    # Calculate aggregation numerical error
    eps = 1e-12
    l2_diff = np.linalg.norm(delta_w_ckks - delta_w_plain)
    l2_base = np.linalg.norm(delta_w_plain)
    epsilon_agg = l2_diff / (l2_base + eps)
    max_abs_err = np.max(np.abs(delta_w_ckks - delta_w_plain))

    print(f"  Dimension: {dim:,} parameters (11 CKKS ciphertext chunks)")
    print(f"  Total records N: {N:,} across {K} clients")
    print(f"  Max absolute error: {max_abs_err:.4e}")
    print(f"  Relative L2 aggregation error epsilon_agg: {epsilon_agg:.4e}")

    # Tolerance justification: CKKS with scale 2^40 introduces bounded approximation noise ~1e-7 to 1e-6.
    # Across 44,164 slots, epsilon_agg <= 1e-5 is mathematically expected and verified.
    assert epsilon_agg < 1e-5, f"CKKS aggregation error {epsilon_agg} exceeds tolerance 1e-5"
    print("  PASS  CKKS F aggregation is numerically equivalent to plaintext within 1e-5 tolerance")


def test_ckks_serialization_roundtrip() -> None:
    print("\n[test] CKKS ciphertext serialization and deserialization")
    key_manager = create_ckks_key_manager()
    pub_ctx = key_manager.public_context
    sec_ctx = key_manager.secret_context

    v = np.linspace(-1.0, 1.0, 5000, dtype=np.float64)
    enc = CKKSVector(pub_ctx, data=v)

    # Serialize to raw byte chunks
    raw_bytes = enc.serialize()
    total_bytes = sum(len(b) for b in raw_bytes)
    assert total_bytes > 0, "Serialization must produce non-zero bytes"

    # Deserialize
    deserialized = CKKSVector.deserialize(pub_ctx, raw_bytes, n_values=len(v), slot_count=enc.slot_count)
    dec = deserialized.decrypt(secret_context=sec_ctx)

    np.testing.assert_allclose(v, dec, atol=1e-6)
    print(f"  PASS  Serialization roundtrip verified (Wire size: {total_bytes / 1024:.1f} KB, Max error: {np.max(np.abs(v - dec)):.2e})")


def main() -> None:
    test_ckks_f_aggregation_numerical_equivalence()
    test_ckks_serialization_roundtrip()
    print("\nAll CKKS cryptographic equivalence tests PASSED successfully!")


if __name__ == "__main__":
    main()

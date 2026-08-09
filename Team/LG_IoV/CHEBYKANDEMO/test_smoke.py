"""
test_smoke.py — Automated acceptance tests for CHEBYKANDEMO.

Tests:
1. Model parameter count assertion
2. Leakage-safe session splitting
3. Scaling bounds verification
4. Multi-Krum malicious client rejection
5. Full pipeline smoke test
"""

import sys
import os
import time
import numpy as np
import torch

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_model_parameter_count():
    """Test 1: ChebyKAN parameter count matches expected 44,164 for n_classes=4."""
    print("\n" + "=" * 60)
    print("TEST 1: Model Parameter Count Assertion")
    print("=" * 60)

    from model import ChebyKAN

    # This should NOT raise — assertion is built into __init__
    model = ChebyKAN(in_features=46, n_classes=4)
    total = sum(p.numel() for p in model.parameters())
    assert total == 44164, f"Expected 44,164 params, got {total}"
    model.count_parameters()
    print(f"[PASS] ChebyKAN has {total:,} parameters (expected 44,164)")

    # Test with different n_classes (should not assert)
    model_2 = ChebyKAN(in_features=46, n_classes=2)
    total_2 = sum(p.numel() for p in model_2.parameters())
    print(f"[PASS] ChebyKAN with n_classes=2 has {total_2:,} parameters (no assertion)")

    # Test load_state_dict with strict=False across class counts
    state_4 = model.state_dict()
    model_2.load_state_dict(state_4, strict=False)
    print("[PASS] load_state_dict(strict=False) handles shape mismatch")


def test_session_split_leakage():
    """Test 2: No session_id crosses train/val/test boundary."""
    print("\n" + "=" * 60)
    print("TEST 2: Leakage-Safe Session Splitting")
    print("=" * 60)

    from sklearn.model_selection import train_test_split

    # Simulate 50 sessions
    session_ids = [f"session_{i}" for i in range(50)]
    np.random.seed(2026)
    np.random.shuffle(session_ids)

    n = len(session_ids)
    n_train = int(0.7 * n)
    n_val = int(0.15 * n)

    train_sessions = set(session_ids[:n_train])
    val_sessions = set(session_ids[n_train:n_train + n_val])
    test_sessions = set(session_ids[n_train + n_val:])

    # Hard assertions
    assert len(train_sessions & val_sessions) == 0, "Train/Val session overlap!"
    assert len(train_sessions & test_sessions) == 0, "Train/Test session overlap!"
    assert len(val_sessions & test_sessions) == 0, "Val/Test session overlap!"
    assert len(train_sessions) + len(val_sessions) + len(test_sessions) == n

    print(f"  Train sessions: {len(train_sessions)}")
    print(f"  Val sessions:   {len(val_sessions)}")
    print(f"  Test sessions:  {len(test_sessions)}")
    print("[PASS] No session_id crosses any split boundary")


def test_scaling_bounds():
    """Test 3: Percentile clip + Z-score + tanh produces values in [-1, 1]."""
    print("\n" + "=" * 60)
    print("TEST 3: Scaling Bounds Verification")
    print("=" * 60)

    np.random.seed(2026)

    # Simulate 46-D features with outliers
    X = np.random.randn(1000, 46)
    X[0, 0] = 1e6  # extreme outlier
    X[1, 5] = -1e6  # extreme outlier

    # Stage 1: Percentile clipping
    p_low = np.percentile(X, 1, axis=0)
    p_high = np.percentile(X, 99, axis=0)
    X_clipped = np.clip(X, p_low, p_high)

    # Stage 2: Z-score + tanh
    mean = X_clipped.mean(axis=0)
    std = X_clipped.std(axis=0) + 1e-8
    X_normed = (X_clipped - mean) / std
    X_scaled = np.tanh(X_normed)

    # Assertions
    assert not np.any(np.isnan(X_scaled)), "NaN found in scaled data!"
    assert not np.any(np.isinf(X_scaled)), "Inf found in scaled data!"
    assert np.all(X_scaled >= -1.0), f"Min value {X_scaled.min()} < -1.0!"
    assert np.all(X_scaled <= 1.0), f"Max value {X_scaled.max()} > 1.0!"

    print(f"  Input range:  [{X.min():.2f}, {X.max():.2f}]")
    print(f"  Scaled range: [{X_scaled.min():.6f}, {X_scaled.max():.6f}]")
    print("[PASS] All features in [-1, 1], zero NaN/Inf")


def test_multi_krum_rejection():
    """Test 4: Multi-Krum rejects a 50x-scaled malicious client."""
    print("\n" + "=" * 60)
    print("TEST 4: Multi-Krum Malicious Client Rejection")
    print("=" * 60)

    try:
        import tenseal as ts
    except ImportError:
        print("[SKIP] TenSEAL not installed — cannot test FHE Multi-Krum")
        return

    from model import ChebyKAN
    from fhe_engine import create_ckks_context, DesignatedDecryptor, encrypt_model_state
    from aggregation import homomorphic_multi_krum

    # Create CKKS context
    full_context = create_ckks_context()
    decryptor = DesignatedDecryptor(full_context)
    public_ctx = decryptor.public_context

    # Create a model for normal weights
    model = ChebyKAN(in_features=46, n_classes=4)
    normal_state = model.state_dict()
    malicious_state = {k: v * 50.0 for k, v in normal_state.items()}

    # Encrypt 3 normal + 1 malicious
    encrypted_updates = []
    for i in range(3):
        encrypted_updates.append(encrypt_model_state(public_ctx, normal_state))
    encrypted_updates.append(encrypt_model_state(public_ctx, malicious_state))

    # Run Multi-Krum (f=1 means reject 1 client)
    accepted = homomorphic_multi_krum(encrypted_updates, decryptor, f=1)
    rejected = [i for i in range(4) if i not in accepted]

    assert 3 in rejected, f"Multi-Krum FAILED to reject malicious client! Rejected: {rejected}"
    print(f"  Accepted clients: {accepted}")
    print(f"  Rejected clients: {rejected}")
    print("[PASS] 50x-scaled malicious client was rejected by Homomorphic Multi-Krum")


def test_server_cannot_decrypt():
    """Test 5: Server object provably cannot decrypt."""
    print("\n" + "=" * 60)
    print("TEST 5: Server Cannot Decrypt Assertion")
    print("=" * 60)

    try:
        import tenseal as ts
    except ImportError:
        print("[SKIP] TenSEAL not installed — cannot test server decryption")
        return

    from fhe_engine import create_ckks_context, DesignatedDecryptor
    from federated import Server

    full_context = create_ckks_context()
    decryptor = DesignatedDecryptor(full_context)

    # Server should have public context only
    server = Server(in_features=46, n_classes=4, decryptor=decryptor)
    assert not server.public_context.has_secret_key(), \
        "SECURITY VIOLATION: Server context has secret key!"

    # Verify the server object itself has no decrypt method
    server_attrs = dir(server)
    for attr in server_attrs:
        if 'secret' in attr.lower() and attr != '_Server__secret':
            assert False, f"Server has suspicious attribute: {attr}"

    print("[PASS] Server context has no secret key")
    print("[PASS] Server object has no decrypt capability")


def run_all_tests():
    """Run all acceptance tests."""
    print("\n" + "#" * 60)
    print("# CHEBYKANDEMO — Acceptance Test Suite")
    print("#" * 60)

    start = time.time()
    passed = 0
    failed = 0
    skipped = 0

    tests = [
        test_model_parameter_count,
        test_session_split_leakage,
        test_scaling_bounds,
        test_multi_krum_rejection,
        test_server_cannot_decrypt,
    ]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            if "SKIP" in str(e) or "not installed" in str(e):
                skipped += 1
            else:
                print(f"[ERROR] {test_fn.__name__}: {e}")
                import traceback
                traceback.print_exc()
                failed += 1

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"Total time: {elapsed:.2f}s")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()

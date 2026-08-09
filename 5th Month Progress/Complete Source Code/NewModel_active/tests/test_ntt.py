"""Correctness tests for the negacyclic NTT (M3-4 deliverable).

    python tests/test_ntt.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crypto.ntt import (                                        # noqa: E402
    NTTContext, bit_reverse_indices, find_ntt_prime, is_prime,
    negacyclic_convolution_schoolbook, primitive_root,
)

_fail, _pass = [], []


def check(name, cond, detail=""):
    if cond:
        _pass.append(name)
        print(f"  PASS  {name}")
    else:
        _fail.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def test_number_theory():
    print("\n[test] number-theoretic prerequisites")
    check("Miller-Rabin agrees with known primes",
          all(is_prime(p) for p in (2, 3, 12289, 1000003, 2147483647)))
    check("Miller-Rabin rejects composites",
          not any(is_prime(c) for c in (1, 4, 12288, 1000001, 2147483646)))

    for n in (256, 1024, 8192):
        q = find_ntt_prime(n)
        check(f"n={n}: prime found, q={q}", is_prime(q))
        check(f"n={n}: q = 1 mod 2n", (q - 1) % (2 * n) == 0,
              f"q-1 mod 2n = {(q - 1) % (2 * n)}")
        g = primitive_root(q)
        check(f"n={n}: g={g} has full order",
              pow(g, q - 1, q) == 1 and pow(g, (q - 1) // 2, q) != 1)


def test_roots():
    print("\n[test] psi is a primitive 2n-th root with psi^n = -1")
    for n in (256, 1024, 4096):
        ctx = NTTContext.build(n)
        check(f"n={n}: psi^(2n) = 1", pow(ctx.psi, 2 * n, ctx.q) == 1)
        check(f"n={n}: psi^n = -1", pow(ctx.psi, n, ctx.q) == ctx.q - 1)
        check(f"n={n}: psi * psi_inv = 1", ctx.psi * ctx.psi_inv % ctx.q == 1)
        check(f"n={n}: n * n_inv = 1", n * ctx.n_inv % ctx.q == 1)


def test_bit_reverse():
    print("\n[test] bit-reversal permutation")
    check("n=8 matches hand-computed",
          bit_reverse_indices(8).tolist() == [0, 4, 2, 6, 1, 5, 3, 7],
          str(bit_reverse_indices(8).tolist()))
    for n in (16, 256, 1024):
        r = bit_reverse_indices(n)
        check(f"n={n}: is a permutation", sorted(r.tolist()) == list(range(n)))
        check(f"n={n}: is an involution", np.array_equal(r[r], np.arange(n)))


def test_roundtrip():
    print("\n[test] inverse(forward(a)) == a")
    rng = np.random.default_rng(0)
    for n in (256, 512, 1024, 4096):
        ctx = NTTContext.build(n)
        a = rng.integers(0, ctx.q, n, dtype=np.int64)
        back = ctx.inverse(ctx.forward(a))
        check(f"n={n}: round-trip exact", np.array_equal(a % ctx.q, back),
              f"max diff {int(np.max(np.abs(a % ctx.q - back)))}")


def test_against_schoolbook():
    print("\n[test] NTT product == schoolbook negacyclic product")
    rng = np.random.default_rng(1)
    for n in (256, 512, 1024):
        ctx = NTTContext.build(n)
        a = rng.integers(0, ctx.q, n, dtype=np.int64)
        b = rng.integers(0, ctx.q, n, dtype=np.int64)
        fast = ctx.multiply(a, b)
        ref = negacyclic_convolution_schoolbook(a, b, ctx.q)
        check(f"n={n}: matches oracle exactly", np.array_equal(fast, ref),
              f"{int(np.sum(fast != ref))} coefficients differ")


def test_negacyclic_property():
    print("\n[test] the wrap really is negacyclic (X^n = -1)")
    ctx = NTTContext.build(256)
    n, q = ctx.n, ctx.q
    # X^(n-1) * X = X^n, which must equal -1 in this ring.
    a = np.zeros(n, dtype=np.int64); a[n - 1] = 1
    b = np.zeros(n, dtype=np.int64); b[1] = 1
    prod = ctx.multiply(a, b)
    expect = np.zeros(n, dtype=np.int64); expect[0] = q - 1
    check("X^(n-1) * X == -1", np.array_equal(prod, expect),
          f"got nonzero at {np.nonzero(prod)[0][:4].tolist()}")

    # Identity: 1 * a == a
    rng = np.random.default_rng(2)
    a = rng.integers(0, q, n, dtype=np.int64)
    one = np.zeros(n, dtype=np.int64); one[0] = 1
    check("1 * a == a", np.array_equal(ctx.multiply(a, one), a % q))


def test_batched_matches_scalar():
    print("\n[test] stage-vectorised form == literal per-butterfly form")
    rng = np.random.default_rng(11)
    for n in (256, 512, 1024, 4096):
        ctx = NTTContext.build(n)
        a = rng.integers(0, ctx.q, n, dtype=np.int64)
        check(f"n={n}: forward agrees",
              np.array_equal(ctx.forward(a), ctx.forward_scalar(a)),
              f"{int(np.sum(ctx.forward(a) != ctx.forward_scalar(a)))} differ")
        f = ctx.forward(a)
        check(f"n={n}: inverse agrees",
              np.array_equal(ctx.inverse(f), ctx.inverse_scalar(f)))


def test_linearity():
    print("\n[test] transform is linear")
    rng = np.random.default_rng(3)
    ctx = NTTContext.build(512)
    a = rng.integers(0, ctx.q, ctx.n, dtype=np.int64)
    b = rng.integers(0, ctx.q, ctx.n, dtype=np.int64)
    lhs = ctx.forward((a + b) % ctx.q)
    rhs = (ctx.forward(a) + ctx.forward(b)) % ctx.q
    check("NTT(a+b) == NTT(a)+NTT(b)", np.array_equal(lhs, rhs))


def main() -> int:
    print("=" * 68)
    print("Negacyclic NTT verification")
    print("=" * 68)
    test_number_theory()
    test_roots()
    test_bit_reverse()
    test_roundtrip()
    test_against_schoolbook()
    test_negacyclic_property()
    test_batched_matches_scalar()
    test_linearity()
    print("\n" + "=" * 68)
    print(f"{len(_pass)} passed, {len(_fail)} failed")
    for n, d in _fail:
        print(f"  FAILED: {n}  {d}")
    print("=" * 68)
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

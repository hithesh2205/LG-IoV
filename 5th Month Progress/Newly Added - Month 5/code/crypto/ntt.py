"""Negacyclic Number Theoretic Transform over Z_q[X]/(X^N + 1).

LG deliverable: **High-Performance NTT Implementation** (Month 3-4).

Why the NTT is the thing worth optimising
-----------------------------------------
Every RLWE operation - encryption, homomorphic addition, homomorphic
multiplication, rescaling - reduces to arithmetic on polynomials in
``Z_q[X]/(X^N + 1)`` with N = 8192 in this project. Multiplying two such
polynomials naively costs O(N^2) = 67 million modular multiplications. The NTT
is a discrete Fourier transform over a finite field: it turns convolution into
pointwise multiplication, so a product costs O(N log N) instead::

    a * b  =  INTT( NTT(a) (.) NTT(b) )

That is the single hottest kernel in any FHE library, and it is where an
embedded port lives or dies.

What "negacyclic" means, and why it matters here
------------------------------------------------
Ordinary convolution computes modulo ``X^N - 1`` (cyclic). RLWE needs modulo
``X^N + 1`` (negacyclic), where a coefficient wrapping past degree N comes back
*negated*. The standard fix would be to zero-pad to 2N and throw half away -
double the work. Instead we fold a primitive **2N-th** root of unity psi into
the transform, which makes the negacyclic wrap fall out for free at length N.
``psi^2 = omega``, the usual N-th root.

Implementation notes
--------------------
This is the Longa-Naehrig formulation, the one a NEON or AVX2 kernel would
mirror:

* **Forward**: Cooley-Tukey decimation-in-time, natural order in, bit-reversed
  order out. No separate bit-reversal pass.
* **Inverse**: Gentleman-Sande decimation-in-frequency, bit-reversed in, natural
  out. Again no permutation pass.
* Twiddle factors are precomputed **in bit-reversed order** so the inner loop
  reads them sequentially - which is what makes the memory access pattern
  vectorisable.
* Butterflies are executed as whole numpy slices rather than element loops, so
  the inner loop runs in compiled code over contiguous memory. That is the
  closest a Python reference gets to the SIMD structure of the real kernel.

Scope, stated honestly
----------------------
This is a **correct, tested, benchmarked reference implementation**, not the
shippable embedded kernel. The production artefact is a C core with NEON
intrinsics and Montgomery or Shoup reduction, cross-compiled for the target
board. What this module provides for that work:

1. a specification precise enough to port from,
2. a correctness oracle - :func:`negacyclic_convolution_schoolbook`,
3. exported **test vectors** (``export_test_vectors``) so the C port can be
   validated bit-for-bit before it is trusted,
4. a measured baseline curve to beat.

Modulus size: this reference uses primes below 2^31 so that products fit in
int64 and numpy can do the arithmetic natively. Production CKKS uses ~60-bit
RNS primes, where each product needs a 128-bit intermediate (or Montgomery
form). The algorithm is identical; only the reduction changes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


# ─────────────────────────────────────────────────────────────────────────
# number theory helpers
# ─────────────────────────────────────────────────────────────────────────
def is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin for n < 3.3e24."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def find_ntt_prime(n: int, bits: int = 30) -> int:
    """Smallest prime q < 2^bits with ``q = 1 (mod 2n)``.

    The congruence is what guarantees a primitive 2n-th root of unity exists,
    which is what makes the negacyclic transform possible at length n.
    """
    step = 2 * n
    k = (1 << bits) // step
    while k > 0:
        q = k * step + 1
        if q < (1 << bits) and is_prime(q):
            return q
        k -= 1
    raise ValueError(f"no NTT prime found for n={n}, bits={bits}")


def primitive_root(q: int) -> int:
    """A generator of the multiplicative group mod prime q."""
    phi = q - 1
    factors, m = [], phi
    d = 2
    while d * d <= m:
        if m % d == 0:
            factors.append(d)
            while m % d == 0:
                m //= d
        d += 1
    if m > 1:
        factors.append(m)
    for g in range(2, q):
        if all(pow(g, phi // f, q) != 1 for f in factors):
            return g
    raise ValueError(f"no primitive root mod {q}")


def bit_reverse_indices(n: int) -> np.ndarray:
    """Permutation array for bit-reversal of length n (a power of two)."""
    bits = n.bit_length() - 1
    idx = np.arange(n, dtype=np.int64)
    out = np.zeros(n, dtype=np.int64)
    for b in range(bits):
        out |= ((idx >> b) & 1) << (bits - 1 - b)
    return out


# ─────────────────────────────────────────────────────────────────────────
# the transform
# ─────────────────────────────────────────────────────────────────────────
@dataclass
class NTTContext:
    """Precomputed constants for one (n, q) pair.

    Building this is the expensive part and it is done once. The transforms
    themselves then touch only precomputed tables, which is exactly the
    structure the embedded kernel needs.
    """

    n: int
    q: int
    psi: int
    psi_inv: int
    n_inv: int
    psi_rev: np.ndarray        # bit-reversed powers of psi,      forward
    psi_inv_rev: np.ndarray    # bit-reversed powers of psi^-1,   inverse

    @classmethod
    def build(cls, n: int, q: Optional[int] = None) -> "NTTContext":
        if n & (n - 1):
            raise ValueError(f"n must be a power of two, got {n}")
        q = q or find_ntt_prime(n)
        if (q - 1) % (2 * n):
            raise ValueError(f"q={q} is not congruent to 1 mod 2n={2*n}")

        g = primitive_root(q)
        psi = pow(g, (q - 1) // (2 * n), q)      # primitive 2n-th root
        if pow(psi, n, q) != q - 1:
            raise ValueError("psi^n != -1; not a valid negacyclic root")
        psi_inv = pow(psi, q - 2, q)
        n_inv = pow(n, q - 2, q)

        rev = bit_reverse_indices(n)
        pw = np.ones(n, dtype=np.int64)
        pwi = np.ones(n, dtype=np.int64)
        for i in range(1, n):
            pw[i] = pw[i - 1] * psi % q
            pwi[i] = pwi[i - 1] * psi_inv % q

        return cls(n=n, q=q, psi=psi, psi_inv=psi_inv, n_inv=n_inv,
                   psi_rev=pw[rev].copy(), psi_inv_rev=pwi[rev].copy())

    # ── forward: Cooley-Tukey DIT, natural -> bit-reversed ───────────────
    def forward(self, a: np.ndarray) -> np.ndarray:
        """NTT of a length-n coefficient vector (stage-vectorised).

        Each stage is executed as **one** batched numpy operation rather than
        one per butterfly block. At stage ``m`` the array holds ``m`` contiguous
        blocks of ``2t`` coefficients, so reshaping to ``(m, 2t)`` exposes every
        block's low and high half at once and the whole stage becomes a single
        broadcast multiply-add.

        This matters: the per-butterfly form issues ~n numpy calls per transform
        and is dominated by interpreter overhead. The batched form issues
        ``log2(n)`` - about 13 at n=8192 - and is ~50x faster while computing
        exactly the same thing (cross-checked in tests/test_ntt.py).

        It is also the structure a SIMD kernel wants: contiguous lanes, one
        twiddle broadcast per block.
        """
        q = self.q
        x = (np.asarray(a, dtype=np.int64) % q).copy()
        t = self.n
        m = 1
        while m < self.n:
            t //= 2
            s = self.psi_rev[m:2 * m].reshape(m, 1)     # one twiddle per block
            blk = x.reshape(m, 2 * t)
            lo = blk[:, :t]
            hi = blk[:, t:]
            v = hi * s % q
            new_lo = (lo + v) % q
            new_hi = (lo - v) % q
            blk[:, :t] = new_lo
            blk[:, t:] = new_hi
            m *= 2
        return x

    # ── inverse: Gentleman-Sande DIF, bit-reversed -> natural ────────────
    def inverse(self, a: np.ndarray) -> np.ndarray:
        """Inverse NTT (stage-vectorised). Bit-reversed in, natural out."""
        q = self.q
        x = (np.asarray(a, dtype=np.int64) % q).copy()
        t = 1
        m = self.n
        while m > 1:
            h = m // 2
            s = self.psi_inv_rev[h:2 * h].reshape(h, 1)
            blk = x.reshape(h, 2 * t)
            lo = blk[:, :t]
            hi = blk[:, t:]
            new_lo = (lo + hi) % q
            new_hi = (lo - hi) * s % q
            blk[:, :t] = new_lo
            blk[:, t:] = new_hi
            t *= 2
            m //= 2
        return x * self.n_inv % q

    # ── literal reference forms, for porting and cross-validation ────────
    def forward_scalar(self, a: np.ndarray) -> np.ndarray:
        """Per-butterfly Cooley-Tukey - the literal pseudocode to port from.

        Slower in Python, but this is the loop structure a C or NEON kernel
        implements. :func:`forward` must agree with it exactly.
        """
        q = self.q
        x = (np.asarray(a, dtype=np.int64) % q).copy()
        t = self.n
        m = 1
        while m < self.n:
            t //= 2
            for i in range(m):
                j1 = 2 * i * t
                s = int(self.psi_rev[m + i])
                lo = slice(j1, j1 + t)
                hi = slice(j1 + t, j1 + 2 * t)
                # u must be a COPY - x[lo] is a view, and writing x[lo] below
                # would otherwise mutate u before x[hi] consumes it.
                u = x[lo].copy()
                v = x[hi] * s % q
                x[lo] = (u + v) % q
                x[hi] = (u - v) % q
            m *= 2
        return x

    def inverse_scalar(self, a: np.ndarray) -> np.ndarray:
        """Per-butterfly Gentleman-Sande - the literal pseudocode to port from."""
        q = self.q
        x = (np.asarray(a, dtype=np.int64) % q).copy()
        t = 1
        m = self.n
        while m > 1:
            j1 = 0
            h = m // 2
            for i in range(h):
                s = int(self.psi_inv_rev[h + i])
                lo = slice(j1, j1 + t)
                hi = slice(j1 + t, j1 + 2 * t)
                u = x[lo].copy()
                v = x[hi].copy()
                x[lo] = (u + v) % q
                x[hi] = (u - v) * s % q
                j1 += 2 * t
            t *= 2
            m //= 2
        return x * self.n_inv % q

    def multiply(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Negacyclic product a*b mod (X^n + 1), via NTT."""
        fa = self.forward(a)
        fb = self.forward(b)
        return self.inverse(fa * fb % self.q)


# ─────────────────────────────────────────────────────────────────────────
# reference oracle
# ─────────────────────────────────────────────────────────────────────────
def negacyclic_convolution_schoolbook(a, b, q: int) -> np.ndarray:
    """O(n^2) reference. Correctness oracle for the transform and the C port.

    Computes the full convolution then folds the upper half back with a sign
    flip, which is what ``mod (X^n + 1)`` means.
    """
    a = np.asarray(a, dtype=object)
    b = np.asarray(b, dtype=object)
    n = a.size
    full = np.convolve(a, b)                       # length 2n-1
    out = np.zeros(n, dtype=object)
    out[:] = full[:n]
    out[:n - 1] -= full[n:]                        # X^n = -1
    return np.array([int(v) % q for v in out], dtype=np.int64)


# ─────────────────────────────────────────────────────────────────────────
# test vectors for the C / NEON port
# ─────────────────────────────────────────────────────────────────────────
def export_test_vectors(path: Path, sizes: Tuple[int, ...] = (256, 512, 1024),
                        seed: int = 2025) -> dict:
    """Emit known-good vectors so a C port can be validated bit-for-bit.

    Each entry carries the modulus, the roots, two input polynomials, their
    forward transforms, and the negacyclic product verified against the
    schoolbook oracle.
    """
    rng = np.random.default_rng(seed)
    out = {"description":
           "Negacyclic NTT test vectors over Z_q[X]/(X^n+1). "
           "Forward: Cooley-Tukey DIT, natural in / bit-reversed out. "
           "Inverse: Gentleman-Sande DIF, bit-reversed in / natural out. "
           "Twiddles are bit-reversed powers of psi, a primitive 2n-th root.",
           "cases": []}

    for n in sizes:
        ctx = NTTContext.build(n)
        a = rng.integers(0, ctx.q, n, dtype=np.int64)
        b = rng.integers(0, ctx.q, n, dtype=np.int64)
        prod = ctx.multiply(a, b)
        ref = negacyclic_convolution_schoolbook(a, b, ctx.q)
        assert np.array_equal(prod, ref), f"self-check failed at n={n}"
        out["cases"].append({
            "n": n, "q": int(ctx.q),
            "psi": int(ctx.psi), "psi_inv": int(ctx.psi_inv),
            "n_inv": int(ctx.n_inv),
            "a": a.tolist(), "b": b.tolist(),
            "ntt_a": ctx.forward(a).tolist(),
            "product_negacyclic": prod.tolist(),
        })

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out), encoding="utf-8")
    return {"path": str(path), "sizes": list(sizes),
            "bytes": path.stat().st_size}

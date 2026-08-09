# High-Performance NTT Implementation

**LG deliverable:** *High-Performance NTT Implementation* (Month 3–4)
**Status:** 🟡 reference implementation delivered and validated; the shippable ARM/NEON kernel is blocked on hardware
**Code:** `crypto/ntt.py` · tests `tests/test_ntt.py` · benchmark `scripts/benchmark_ntt.py`
**Version:** 1.0 · 2026-08-09

---

## 1. Why the NTT is *the* kernel to optimise

Every RLWE operation — encryption, homomorphic addition, homomorphic
multiplication, rescaling — reduces to arithmetic on polynomials in
`Z_q[X]/(X^N + 1)` with N = 8192 here.

Multiplying two such polynomials naively costs O(N²) = **67 million** modular
multiplications. The **Number Theoretic Transform** is a discrete Fourier
transform over a finite field: it turns convolution into pointwise
multiplication, so a product costs O(N log N):

```
a · b  =  INTT( NTT(a) ⊙ NTT(b) )
```

At N = 8192 that is a **630× reduction in operation count**. This is the hottest
kernel in any FHE library, and it is where an embedded port lives or dies.

---

## 2. What "negacyclic" means, and why it matters

Ordinary convolution works modulo `X^N − 1` (cyclic). RLWE needs modulo
`X^N + 1` (**negacyclic**), where a coefficient wrapping past degree N comes back
**negated**.

The naive fix is to zero-pad to 2N and discard half — double the work. Instead we
fold a primitive **2N-th** root of unity ψ into the transform, which makes the
negacyclic wrap fall out for free at length N. Here `ψ² = ω`, the usual N-th root,
and the defining property is `ψ^N = −1`.

Verified directly: `X^(N−1) · X == −1` in the ring
(`tests/test_ntt.py::test_negacyclic_property`).

---

## 3. Implementation

The Longa–Naehrig formulation — the one a NEON or AVX2 kernel mirrors:

| Direction | Algorithm | Input order | Output order |
|---|---|---|---|
| Forward | Cooley–Tukey, decimation-in-time | natural | bit-reversed |
| Inverse | Gentleman–Sande, decimation-in-frequency | bit-reversed | natural |

Pairing them this way means **no separate bit-reversal pass** in either
direction. Twiddle factors are precomputed in bit-reversed order so the inner
loop reads them sequentially, which is what makes the access pattern
vectorisable.

### Two forms, cross-validated

- `forward_scalar` / `inverse_scalar` — the literal per-butterfly pseudocode.
  This is the **porting specification**: the loop structure a C kernel implements.
- `forward` / `inverse` — **stage-batched**. At stage *m* the array holds *m*
  contiguous blocks of *2t* coefficients, so reshaping to `(m, 2t)` exposes every
  block's halves at once and the entire stage becomes one broadcast
  multiply-add.

The tests assert the two agree exactly at every size. That cross-check is what
makes the fast path trustworthy.

---

## 4. Performance

Measured on the development host (AMD Zen 3, Python 3.12, NumPy 2.4.1).
Baseline is `np.convolve` plus the negacyclic fold — O(N²), but running entirely
in optimised C, so it is a hard baseline.

| N | NTT forward | NTT multiply | Schoolbook | Speedup |
|---|---|---|---|---|
| 256 | 0.05 ms | 0.16 ms | 0.03 ms | 0.15× |
| 512 | 0.07 ms | 0.22 ms | 0.09 ms | 0.40× |
| **1024** | 0.11 ms | 0.33 ms | 0.33 ms | **1.02× — crossover** |
| 2048 | 0.17 ms | 0.53 ms | 1.30 ms | 2.43× |
| 4096 | 0.31 ms | 0.98 ms | 5.16 ms | 5.26× |
| **8192** | **0.62 ms** | **1.84 ms** | 20.63 ms | **11.22×** |

At the production ring size: **53,248 butterflies** per transform, 0.62 ms.

### A result worth recording

The first version of this module was **slower than schoolbook** — 0.21× at
N = 8192. The algorithm was correct; the implementation issued ~8,191 tiny NumPy
calls per transform and was dominated by interpreter overhead, not arithmetic.

Batching each stage into a single operation reduced that to ~13 calls and made
it **53× faster** (33.05 ms → 0.62 ms), turning 0.21× into 11.22×.

The lesson transfers directly to the C port: **the NTT's performance is
governed by memory access pattern and per-operation overhead, not by the
butterfly arithmetic.** That is precisely why the production kernel needs
contiguous SIMD lanes rather than a literal transcription of the pseudocode.

The 11.22× is also a **lower bound** for the C kernel — it still carries Python
overhead the compiled version will not have, and the theoretical operation-count
ratio at N = 8192 is 630×.

---

## 5. A bug worth documenting

The first implementation failed round-trip while **passing linearity**. The cause
was NumPy aliasing:

```python
u = x[lo]              # a VIEW, not a copy
x[lo] = (u + v) % q    # this mutates u
x[hi] = (u - v) % q    # u is now the NEW value — wrong
```

Linearity still held because the map remained linear; only the round-trip
exposed it. This is a good argument for testing **algebraic identities**
(`INTT(NTT(a)) == a`, agreement with a schoolbook oracle) rather than just
"does it run".

---

## 6. What the C/NEON port gets from this

1. **A precise specification** — `forward_scalar` / `inverse_scalar` are
   transcribable line by line.
2. **A correctness oracle** — `negacyclic_convolution_schoolbook`, exact
   arbitrary-precision.
3. **Test vectors** — `results/ntt_test_vectors.json` (77 KB): for N ∈ {256, 512,
   1024}, the modulus, ψ, ψ⁻¹, n⁻¹, two input polynomials, `NTT(a)`, and the
   negacyclic product. Every case self-checked against the oracle. The C port can
   be validated **bit-for-bit** before it is trusted.
4. **A baseline to beat** — 0.62 ms per forward transform at N = 8192.

---

## 7. Honest scope

**This is a correct, tested, benchmarked reference implementation — not the
shippable embedded kernel.** The deliverable LG asked for is a C core with NEON
intrinsics and Montgomery or Shoup reduction, cross-compiled for the target
board. That is blocked on hardware selection (item P0.1).

One further difference: this reference uses primes below 2³¹ so products fit in
int64 and NumPy handles them natively. Production CKKS uses ~60-bit RNS primes
where each product needs a 128-bit intermediate or Montgomery form. **The
algorithm is identical; only the reduction changes.**

| Sub-item | Status |
|---|---|
| Negacyclic NTT, correct and tested | ✅ 48 assertions |
| Stage-batched optimisation | ✅ 53× over per-butterfly |
| Benchmark vs O(N²) baseline | ✅ 11.22× at N = 8192 |
| Test vectors for the port | ✅ exported |
| C implementation with NEON intrinsics | 🔴 blocked on hardware |
| Montgomery/Shoup 60-bit reduction | 🔴 blocked on hardware |
| Cross-compiled and measured on target | 🔴 blocked on hardware |

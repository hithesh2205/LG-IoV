# Optimized Packing & Encoding Module

**LG deliverable:** *Optimized Packing & Encoding Module* (Month 3–4)
**Status:** ✅ delivered · module `federated/packing.py`, benchmark `scripts/benchmark_packing.py`
**Version:** 1.0 · 2026-08-09

---

## 1. The problem this solves

A ChebyKAN update is 44,164 float32 parameters — **172.5 KB** in the clear.
Encrypted naively it becomes **3.51 MB**, a 20.8× expansion, and every vehicle
uploads that every round.

For context: a DSRC frame is ~2.7 KB. One naive update is ~1,300 frames, and a
50-vehicle round moves ~180 MB. Bandwidth, not compute, is the binding
constraint on whether this system can run over V2X at all.

---

## 2. What CKKS packing actually is

CKKS encodes a **vector** of reals into a single ciphertext. At
`poly_modulus_degree` N = 8192 there are N/2 = **4096 slots**, and one
homomorphic addition adds all 4096 slots simultaneously — this is SIMD in the
encrypted domain, and it is the property that makes the scheme affordable here.

Our 44,164 parameters therefore need `ceil(44164 / 4096)` = **11 ciphertexts**,
not 44,164. The module's job is to reduce that further.

---

## 3. The levers, measured

All figures from `scripts/benchmark_packing.py` at the real parameter count.
Correctness is re-verified after every change — a bandwidth saving that breaks
the protocol is not a saving.

### Lever 1 — Level-dropped transmission ⭐ the significant one

A fresh CKKS ciphertext carries the entire modulus chain. Each multiplication
consumes one prime ("level") and the ciphertext **shrinks**.

The insight is about the *protocol*, not the cryptography. The server does two
things with each client's ciphertext:

```
(a)  [d^u] = gᵀg + [(f − 2g)·f]      one ciphertext × ciphertext multiply
(b)  acc  += p^u · [f]                one ciphertext × plaintext multiply
```

These act on **independent copies** — neither consumes the other's output. So
the depth actually required of the transmitted ciphertext is **max(1,1) = 1**,
not 2. The client can consume one level locally before serialising.

| Levels dropped | Wire size | Saving | Distance error | Aggregation error | Status |
|---|---|---|---|---|---|
| 0 (Month-4 behaviour) | 3.51 MB | — | 2.52e-05 | 2.93e-08 | ok |
| **1 (Month-5 default)** | **2.47 MB** | **29.6 %** | 1.13e-04 | 9.26e-08 | ok |
| 2 | 1.38 MB | 60.7 % | — | — | **fails** |

**Dropping 2 levels is the trap.** The 60.7 % saving looks attractive and the
configuration does not work — the server's multiply raises `ValueError`.
`MAX_SAFE_LEVEL_DROP = 1` encodes the bound and `PackingConfig.validate()`
rejects it before a round is wasted.

Error grows ~4.5× but remains five orders of magnitude below SGD gradient noise,
and a full federated run with level-dropping enabled returned **identical
accuracy** (0.9990 on the Car-Hacking smoke run). The 29.6 % is free.

### Lever 2 — Padding waste

44,164 values into 11 × 4096 slots = 45,056 slots, so **892 slots (2.0 %)** carry
padding. Small, but now visible — and it is a consideration for any future choice
of hidden dimension.

### Lever 3 — Top-k sparsification (lossy, opt-in, off by default)

Transmit only the largest-magnitude coordinates, plus their indices.

| Keep | Ciphertexts | Wire size | Index overhead | Relative reconstruction error |
|---|---|---|---|---|
| 100 % | 11 | 2.47 MB | — | 0.000 |
| 50 % | 6 | 1.43 MB | 86.3 KB | 0.264 |
| 25 % | 3 | 0.72 MB | 43.1 KB | 0.524 |
| 10 % | 2 | 0.47 MB | 17.2 KB | 0.749 |

**Off by default.** A 0.264 relative error on the update is not obviously
survivable — it changes the learning problem, so it must be justified by an
accuracy experiment rather than assumed. That experiment is scheduled.

### Lever 4 — Seed compression (not available on TenSEAL)

An RLWE ciphertext is a pair `(c0, c1)` where `c1` is uniformly random. If it is
derived from a seed shared with the server, the client sends `c0` plus a 32-byte
seed instead of both halves — **~50 %**. Microsoft SEAL implements exactly this
as `Serializable<Ciphertext>`; TenSEAL does not expose it.

This is another concrete, costed argument for the OpenFHE migration — see
[10_library_evaluation.md](10_library_evaluation.md).

---

## 4. Combined result

| Configuration | Wire size | Expansion | Saving | Lossy? |
|---|---|---|---|---|
| Month-4 baseline | 3.51 MB | 20.8× | — | no |
| **Month-5 default** | **2.47 MB** | **14.7×** | **29.6 %** | no |
| + top-50 % | 1.43 MB | 8.5× | 59.2 % | **yes** |
| + top-25 % | 0.72 MB | 4.2× | 79.6 % | **yes** |

**Shipped: 29.6 % reduction at zero accuracy cost.** With seed compression on
OpenFHE this would reach ~65 % losslessly.

---

## 5. Where this leaves V2X feasibility

2.47 MB per vehicle per round is still ~915 DSRC frames. The remaining levers,
in expected order of value:

1. **Seed compression** — ~50 % more, needs OpenFHE
2. **Hierarchical RSU aggregation** — RSUs pre-aggregate so only one ciphertext
   per RSU reaches the server. Changes the architecture; decide early
3. **Sparsification** — large, but requires the accuracy experiment first
4. **Smaller model** — parameter count is the direct multiplier

Even at 2.47 MB this does not fit a per-round V2X budget for a large fleet. The
honest conclusion is that **hierarchical aggregation is likely mandatory**, and
that is an architectural decision, not a tuning one.

---

## 6. API

```python
from federated.packing import PackingConfig, plan

cfg = PackingConfig(levels_to_drop=1)
p = plan(44_164, cfg)
print(p.summary())     # "11 ciphertexts, 2.47 MB (14.7x plaintext), padding 2.0%"
```

Wired through `encrypt_update(..., levels_to_drop=1)`, defaulted on in
`FederatedClient`, so every run since Month 5 benefits automatically.

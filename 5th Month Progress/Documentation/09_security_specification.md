# Security Specification — CKKS Parameters and Cryptographic Design

**LG deliverable:** *Security specification report* (Month 1–2)
**Status:** delivered Month 5 (overdue — see [03_lg_gap_analysis.md](03_lg_gap_analysis.md))
**Version:** 1.0 · 2026-08-08

---

## 1. Scope

This document fixes the cryptographic parameters of the system, justifies them,
states the security level they achieve, and records the measurements that
constrain them. It covers:

1. the CKKS homomorphic encryption scheme and its parameters,
2. the FheFL distributed multi-key layer built on top,
3. the transport channel,
4. known cryptographic caveats and their mitigations.

Every number here was measured on the project machine and is reproducible with
`scripts/benchmark_ckks_profiles.py`.

---

## 2. Concepts from the ground up

### 2.1 Homomorphic encryption

Ordinary encryption turns a message into ciphertext that must be decrypted
before it can be used. **Homomorphic encryption (HE)** allows computation
*directly on ciphertext*, such that decrypting the result gives the same answer
as computing on the plaintext:

```
Dec( Enc(a) ⊕ Enc(b) )  =  a + b
```

This is what lets an aggregation server average model updates it cannot read.

### 2.2 Why CKKS specifically

| Scheme | Data type | Suitability here |
|---|---|---|
| Paillier | integers | Additive only; one ciphertext per number → ~44,164 ciphertexts per update |
| BFV / BGV | exact integers | Would need fixed-point encoding of every weight |
| TFHE | bits | Fast bootstrapping, but bit-level — catastrophic at this scale |
| **CKKS** | **approximate reals** | Neural-network weights *are* real vectors; packs thousands per ciphertext |

CKKS (Cheon–Kim–Kim–Song, 2017) is the only mainstream scheme that natively
encodes vectors of real numbers, and its **SIMD packing** puts
`poly_modulus_degree / 2` reals into a single ciphertext. For our 44,164
parameters at N=8192 that is 11 ciphertexts instead of 44,164. This is the
decisive property and the reason for the choice.

The trade is that CKKS is **approximate**: decryption returns the right answer
plus a small error (~1e-8 in our measurements). For gradient averaging this is
irrelevant — stochastic gradient noise is orders of magnitude larger.

### 2.3 The security foundation: Ring-LWE

CKKS security rests on the **Ring Learning With Errors** problem. Informally:
given `a` (public, random) and `b = a·s + e` where `s` is secret and `e` is small
noise, recover `s`. Without `e` this is trivial linear algebra; with it, the
problem is believed hard even for quantum computers.

Everything about parameter selection is a balance between three quantities:

* **N** (`poly_modulus_degree`) — the ring dimension. Larger N = more security,
  more slots, bigger and slower ciphertexts. Must be a power of two.
* **q** (the coefficient modulus, given as a chain of prime bit-sizes) — larger q
  = more computation possible before noise swamps the message, but **less
  security** for a given N.
* **Δ** (`global_scale`) — fixed-point precision.

The security level is a function of the **ratio** of N to total q bits. This is
the single most important fact for parameter selection, and it produces a hard
ceiling that we hit (§4).

### 2.4 Multiplicative depth

Every ciphertext × ciphertext multiplication consumes one prime from the modulus
chain (a "level") via *rescaling*. A chain of `L` primes supports `L − 2`
multiplications. Run out and the ciphertext can no longer be decrypted
correctly. **Depth budget is the binding constraint on protocol design.**

---

## 3. Parameter selection

### 3.1 Depth requirement, derived from the protocol

FheFL's aggregation needs:

| Step | Operation | Depth cost |
|---|---|---|
| eq. 11 — `[d^u] = gᵀg + [(f^u − 2g)ᵀ·f^u]` | ciphertext × ciphertext + rotations | **1** |
| eq. 12 — `[p^u] = 1 − (1/Σd)·[d^u]` | ciphertext × *plaintext scalar* | 0 (rescale only) |
| eq. 9 — `[p^u]·[f^u]` | ciphertext × ciphertext | **1** |

So **strict FheFL needs depth 2**; the *practical* profile, which reveals the
distance scalars and therefore weights with public scalars, needs **depth 1**
plus headroom for the weighted sum.

### 3.2 Selected parameters

#### Profile A — `practical` (default)

| Parameter | Value |
|---|---|
| Scheme | CKKS |
| `poly_modulus_degree` (N) | **8192** |
| `coeff_mod_bit_sizes` | **[60, 40, 40, 60]** (200 bits total) |
| `global_scale` | 2^40 |
| Slots per ciphertext | 4096 |
| Multiplicative levels | 2 |
| Security level | **128-bit** (HomomorphicEncryption.org standard tables: max 218 bits at N=8192; we use 200) |

#### Profile B — `strict` *(specified and costed; **not implemented**)*

> This profile is fully parameterised and its cost is measured, but the code path
> is **not built**: keeping `[p^u]` encrypted requires broadcasting an encrypted
> scalar across all ciphertext slots (a rotation/replication step) followed by a
> second ciphertext × ciphertext multiply. Requesting it raises
> `NotImplementedError` carrying these numbers rather than silently degrading.
>
> An earlier revision of the server accepted `strict` and fell back to revealing
> both the distance *sum* and the individual distances — strictly more disclosure
> than `practical`, while documented as less. That fallback was removed and
> `tests/test_crypto.py` now asserts the refusal.

| Parameter | Value |
|---|---|
| `poly_modulus_degree` (N) | **16384** |
| `coeff_mod_bit_sizes` | **[60, 40, 40, 40, 60]** (240 bits total) |
| `global_scale` | 2^40 |
| Slots per ciphertext | 8192 |
| Multiplicative levels | 3 |
| Security level | **128-bit** (max 438 bits at N=16384; we use 240 — comfortable margin) |

### 3.3 Justification of the scale Δ = 2^40

The scale sets fixed-point precision. Model weights lie roughly in [−1, 1] and
gradients are far smaller. Δ = 2^40 gives ≈12 significant decimal digits, and
the 60-bit outer primes leave room for the integer part. Measured end-to-end
error after encrypt → weighted-aggregate → decrypt is **≤ 3.0 × 10⁻⁸**, which is
~6 orders of magnitude below SGD noise.

---

## 4. The measured security ceiling — and why it shapes the design

Attempting N=8192 with `[60, 40, 40, 40, 60]` (240 bits) to buy a third level:

```
ValueError: encryption parameters are not set correctly
```

The library **rejects** it. At N=8192, 128-bit security permits at most **218
bits** of total coefficient modulus; 240 exceeds it. Buying a level therefore
requires doubling the ring to N=16384.

Measured consequences:

| Profile | N | chain | total | ct size | eq. 11 time | 2nd ct×ct |
|---|---|---|---|---|---|---|
| practical | 8192 | [60,40,40,60] | 200 b | **326.6 KB** | **18.0 ms** | ✗ fails |
| — | 8192 | [60,40,40,40,60] | 240 b | *rejected* | — | — |
| strict | 16384 | [60,40,40,40,60] | 240 b | **836.1 KB** | **67.7 ms** | ✓ |
| — | 16384 | [60,40,40,40,40,60] | 280 b | 1028.6 KB | 92.5 ms | ✓ |

Those figures are **per ciphertext**. Per *client update* — the whole
44,164-parameter vector — the picture is considerably better, because doubling
the ring also doubles the slots per ciphertext, so the update needs **6**
ciphertexts at N=16384 instead of **11** at N=8192:

| Per client update (7 active clients) | practical | strict | ratio |
|---|---|---|---|
| Ciphertext on the wire | 3.51 MB | 4.90 MB | **1.40×** |
| Expansion over float32 | 21.2× | 29.6× | 1.40× |
| Encrypt | 41.7 ms | 54.6 ms | 1.31× |
| Encrypted distance (eq. 11) | 230.8 ms | 463.4 ms | **2.01×** |
| Homomorphic aggregation | 51.9 ms | 79.8 ms | 1.54× |
| Decrypt aggregate | 9.3 ms | 13.4 ms | 1.44× |

**Correction.** An earlier revision of this document quoted "2.56× ciphertext
size and 3.76× distance time" for strict FheFL. Those were per-ciphertext ratios.
Measured end to end per client update the real costs are **1.40×** bandwidth and
**2.01×** distance time. Strict FheFL is materially more affordable than the
per-ciphertext comparison suggested.

⚠️ Do not confuse the two distance figures: **18.0 ms** is one ciphertext,
**230.8 ms** is a full 11-ciphertext client update.

This corrects an earlier estimate in [04_decision_audit.md](04_decision_audit.md)
§16, which predicted the modulus chain would have to be extended for eq. 11
itself. Measurement shows eq. 11 *does* fit at N=8192 — the ceiling binds only
on the **second** multiplication. Recording the correction here rather than
silently updating it.

---

## 5. The FheFL multi-key layer

### 5.1 The problem with single-key CKKS in FL

Under one shared key, every vehicle can decrypt the global model — therefore
every vehicle holds the secret key — therefore any vehicle, or a server that
obtains the key from any vehicle, can decrypt **every other vehicle's individual
update**. The privacy property is vacuous. This was the Month-4 design.

### 5.2 Distributed additive key sharing

Each vehicle `u` holds an additive share `s_u` of a key that is never assembled:

```
s = Σ_u s_u                                                    (eq. 10)
```

Vehicles pre-agree pairwise secrets with `s_{i,j} = −s_{j,i}` and upload a
*masked* share:

```
ss_u = s_u + Σ_{j≠u} s_{u,j}
```

Because the masks are antisymmetric they cancel in the sum:

```
Σ_u ss_u = Σ_u s_u + Σ_u Σ_{j≠u} s_{u,j} = Σ_u s_u = s
                     └──────── = 0 ────────┘
```

The server reconstructs `s`, decrypts the **aggregate**, and learns nothing
about any individual `s_u`.

**Security property (FheFL Theorem 1):** to recover one honest vehicle's update,
the server must collude with U−1 vehicles.

### 5.3 Dropout — the gap we closed

The cancellation identity holds only when the sum runs over **every** vehicle
holding a pairwise key. FheFL generates pairwise secrets once at enrolment but
samples a random subset each round. If vehicle `j` is offline while `u`
participates, the term `s_{u,j}` has no partner and decryption yields **garbage**
— not a degraded result.

For a vehicle fleet (tunnels, coverage loss, ignition off, RSU handover) this is
the normal case, not an edge case.

**Our fix.** `MultiKeyContext.begin_round(participants)` derives pairwise
secrets for exactly the round's participant set, from a per-round nonce via
HMAC-SHA256. Cancellation then holds by construction for whoever reports in.
`strict_dropout_check=True` additionally verifies `Σ ss_u == Σ s_u` and raises
rather than returning corrupted plaintext.

Verified: `tests/test_crypto.py::test_dropout_is_detected` — masks cancel for an
arbitrary surviving subset {0,1,2,5,7} of an 8-vehicle fleet, and the naive
whole-fleet scheme is correctly rejected on dropout.

### 5.4 Implementation boundary — stated plainly

TenSEAL and Microsoft SEAL expose **no multi-key or threshold API**. Therefore:

* the **homomorphic arithmetic is real** — genuine CKKS ciphertexts, genuine
  noise growth, genuine rescaling, genuine cost;
* the **multi-key key management is modelled at the algebraic level** in
  `multikey_ckks.py`, because the library cannot express it.

This is an honest partial implementation, not a complete one. Unifying the two
requires migrating to OpenFHE or Lattigo — see
[10_library_evaluation.md](10_library_evaluation.md). Nothing in this project
should be described as "full multi-key CKKS" until that migration lands.

---

## 6. Transport security

FHE protects the *payload* from the server. It provides no authentication, no
integrity, no replay protection, and no Sybil resistance. Those come from the
channel, which is a complementary layer and not an alternative.

| Property | Mechanism |
|---|---|
| Key agreement | ECDH over NIST P-256 (SECP256R1), ephemeral per session |
| Entity authentication | Ed25519 long-term identity keys, mutual; signature covers `ephemeral_pub ‖ peer_identity_pub` |
| Key derivation | HKDF-SHA256, salt = handshake transcript, info = `"FedIoV/v1/aes-256-gcm"` |
| Bulk encryption | AES-256-GCM, fresh 96-bit nonce per message |
| Integrity | GCM authentication tag |

Verified in `tests/test_crypto.py::test_secure_channel`: both sides derive the
same key, round-trip succeeds, and a single flipped bit is rejected.

**Open item (threat S5):** the round number is not yet bound into the AEAD
associated data, so a captured frame could in principle be replayed in a later
round. Fix is one line; tracked in [12_next_steps.md](12_next_steps.md).

---

## 7. Cryptographic caveats

### 7.1 CKKS is not IND-CPA^D

Li & Micciancio (Eurocrypt 2021) showed that CKKS, while IND-CPA secure, is
**not** secure when *decryption results* are released to an adversary — the
approximation error carries information about the secret key. FheFL releases a
decrypted aggregate every round, for hundreds of rounds, to a party that also
holds `s`. This is squarely in scope.

**Mitigation:** noise flooding (smudging) — add noise statistically larger than
the inherent approximation error before releasing any decryption.
Implemented as `MultiKeyContext.flood()`, exposed as
`--noise-flooding-bits`.

**Default is 0 (off)** so that equivalence tests remain exact.
**Deployment configurations must set it.** This is requirement R6 in the threat
model and is currently enforced by documentation only, not by code.

### 7.2 Additive n-out-of-n vs threshold t-out-of-n

Our sharing is n-out-of-n: every participant is required. Per-round mask
re-derivation makes this workable, but a **threshold** scheme (t-out-of-n), as in
Mouchet et al. (PETS 2021) and implemented in OpenFHE and Lattigo, removes the
problem structurally. That migration is the month-6 work item.

### 7.3 Minimum fleet size

With U = 2 the collusion bound U−1 = 1 means a single colluding vehicle breaks
the other's privacy. Recommended operational minimum is **U ≥ 5** per round.
Code enforces U ≥ 2 (the absolute floor); the operational recommendation is a
deployment policy.

---

## 8. Parameter change control

Changing any of the following invalidates this specification and requires
re-running `scripts/benchmark_ckks_profiles.py` and re-checking the security
tables:

* `poly_modulus_degree`
* `coeff_mod_bit_sizes` (both total bits and chain length)
* `global_scale`
* the number of ciphertext × ciphertext multiplications in the aggregation path

Current values live in `federated/fhe_adapter.py` as
`DEFAULT_*` and `STRICT_*` constants, with the measurement table reproduced in
the module docstring so it cannot drift silently from this document.

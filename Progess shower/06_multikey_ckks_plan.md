# 06 — Multi-key CKKS: FheFL adoption plan

**Source:** Rahulamathavan, Herath, Liu, Lambotharan, Maple — *"FheFL: Fully
Homomorphic Encryption Friendly Privacy-Preserving Federated Learning with
Byzantine Users"*, arXiv:2306.05112v1, June 2023.

**Verdict: adopt the design, but not naively, and not on TenSEAL.**

---

## 1. Why this paper is the right one

It solves the exact deadlock the project is in. Our current position:

- Encrypt the updates → the server can no longer run Multi-Krum (defect D4).
- Let the server decrypt to run Multi-Krum → the privacy claim collapses.

FheFL breaks the deadlock with two ideas that fit our architecture directly.

### Idea 1 — Robustness scoring that needs no plaintext

Instead of pairwise distances between clients (which requires seeing each client),
score each client by squared distance to the **previous global model**, which the
server already holds in plaintext:

```
[dᵘᵢ] = gᵀᵢ₋₁gᵢ₋₁ + [(fᵘᵢ − 2gᵢ₋₁)ᵀ · fᵘᵢ]          (paper eq. 11)
```

Then a *non-poisoning rate* that scales each client's contribution down in
proportion to how far it strayed, rather than excluding it outright:

```
pᵘᵢ = 1 − dᵘᵢ / Σⱼ dʲᵢ        Σᵤ pᵘ = U − 1        gᵢ = (1/(U−1)) Σᵤ pᵘᵢ · fᵘᵢ⁻¹
```

This is strictly better than our Multi-Krum for IoV. Multi-Krum's all-or-nothing
exclusion punishes a vehicle that encountered a genuinely novel attack — exactly
the vehicle whose update is most valuable. Soft weighting keeps it, discounted.

### Idea 2 — Distributed multi-key CKKS on a single server

Each user *u* holds an additive share `sᵤ` of a secret key nobody ever assembles:
`s = Σᵤ sᵤ`. Users pre-agree pairwise secrets with `s_{i,j} = −s_{j,i}` and send
the server a masked share:

```
ssᵤ = sᵤ + Σ_{j≠u} s_{u,j}
```

The masks cancel in the sum, so `Σᵤ ssᵤ = Σᵤ sᵤ = s` (paper eq. 10). The server
can therefore decrypt the **aggregate** — and only the aggregate. With a common
public `a` and `c₀ᵘ = a·sᵤ + xᵤ + eᵤ`:

```
Σᵤ c₀ᵘ − a · Σᵤ ssᵤ  =  Σᵤ xᵤ
```

**Theorem 1:** to recover one benign user's update the server must collude with
`U − 1` users. That is a real privacy guarantee, and it eliminates the
single-key flaw where any key-holder decrypts everything.

Critically: **one server, no trusted third party, no user-to-user interaction per
round.** Both properties matter for IoV, where an RSU is a single aggregation
point and vehicles cannot be assumed to be mutually reachable.

---

## 2. What this changes in our codebase

| Component | Now | After |
|---|---|---|
| Key model | one shared simulated context | additive shares `sᵤ`, pairwise masks, server reconstructs `s` only |
| Robust filter | Multi-Krum, decrypts each client (`server.py:118-125`) | non-poisoning rate, fully homomorphic |
| Aggregation | sample-weighted FedAvg | `pᵘ`-weighted, `1/(U−1)` normalised |
| Server plaintext access | every client's full update | the aggregate only |
| Key exchange | removed (defect D6) | **required back** — DH for pairwise secrets |
| Crypto library | TenSEAL | must change — see §4 |

Note the pleasing consequence: adopting FheFL forces the restoration of the
Diffie–Hellman key exchange that was deleted in the ChebyKAN pivot. D6 fixes
itself as a side effect.

---

## 3. Risks the paper does not solve — read before committing

### 3.1 Client dropout breaks decryption 🔴 highest risk for IoV

Algorithm 2 line 4 says *"the server randomly selects a set of users"* per epoch,
but pairwise secrets are generated *"once when a user joins the network"*.

The masks `Σ_{j≠u} s_{u,j}` only cancel when the sum runs over **every** user who
holds a pairwise key. If user *j* is offline and user *u* participates, the term
`s_{u,j}` is included with no `s_{j,u}` to cancel it. **Decryption produces
garbage** — not a degraded result, garbage.

For a laptop simulation with fixed participation this never surfaces. For an
actual vehicle fleet — tunnels, coverage loss, ignition off, handover between
RSUs — it is the default case. This is the single biggest gap between the paper
and our deployment target.

**Mitigations, in increasing order of cost:**
1. Re-run pairwise DH over the *round's participant set* only. Simple, but
   O(U²) key agreements per round and still fails on mid-round dropout.
2. **Bonawitz-style Shamir sharing of the masks** with a recovery round, as in
   SecAgg. Standard, well-analysed, handles mid-round dropout. Recommended.
3. **Threshold CKKS** (t-out-of-n) instead of additive n-out-of-n — see §4.

### 3.2 Multiplicative depth vs. our modulus chain 🟠

FheFL needs, per round:
- `[fᵘ]ᵀ·[fᵘ]` — ciphertext × ciphertext, plus rotations for the inner-product sum
- relinearisation with `evkᵤ`
- `[pᵘ]·[fᵘ]` — a second ciphertext × ciphertext

That is **depth 2 minimum**. Our benchmark context
(`benchmark_real_ckks.py:44-47`) uses `coeff_mod_bit_sizes=[60,40,40,60]`, which
gives exactly **2 multiplicative levels — zero headroom**.

Also: `[pᵘᵢ] = 1 − (1/Σⱼdʲ)·[dᵘᵢ]` (eq. 12) is only a *plaintext-scalar*
multiply, because the server decrypts `Σⱼ dʲ` first. That helps. But the inner
product and the final weighting do not.

**Consequence: the measured 0.14 s/round and 20.8× expansion will not hold.**
Both are addition-only figures. Expect the modulus chain to need extending
(more primes → larger ciphertexts → worse than 20.8×) and per-round cost to move
from ~10² ms toward seconds. **Re-benchmark before quoting any FheFL cost number
in a review.**

### 3.3 CKKS approximate decryption is not IND-CPA^D 🟠

Li & Micciancio (Eurocrypt 2021, *"On the Security of Homomorphic Encryption on
Approximate Numbers"*) showed that releasing CKKS *decryption results* leaks
information about the secret key — CKKS is IND-CPA but not IND-CPA^D.

FheFL has the server decrypt `Σᵤ dᵘ` and the aggregate every round, then
broadcast the global model. Over 200+ rounds that is a lot of approximate
decryptions released to a party that also knows `s`. The paper's security
analysis does not address this.

**Mitigation:** noise flooding (add statistically-large smudging noise before
decryption). Standard, cheap, and OpenFHE/Lattigo expose it. Must be in the
design from day one, not retrofitted.

### 3.4 Minimum two non-colluding users

Theorem 1 requires ≥2 non-colluding users or the scheme provides nothing. With
per-round sampling at q=0.7 and small fleets this needs stating explicitly in the
threat model (which is also the overdue month-1 deliverable — write both at once).

### 3.5 The distance metric can be gamed

Scoring by distance to the previous global model rewards *staying close to the
current model*. A patient attacker who submits small, consistently-biased updates
scores a high non-poisoning rate every round. The paper's own text concedes the
distance assumption "may not be always true if a user is trying to update the
model using novel but legitimate data". Worth an explicit experiment: a
low-magnitude persistent label-flip attacker, not just the paper's 20% loud one.

---

## 4. Library decision — TenSEAL cannot do this 🔴

**TenSEAL and Microsoft SEAL do not support multi-key or threshold CKKS.** They
expose no API for additive key shares, distributed decryption, or partial
decryption. FheFL cannot be implemented on the current stack. This is a hard
blocker and it needs deciding first, before any FheFL code is written.

| Library | Multiparty/threshold CKKS | Language | Notes |
|---|---|---|---|
| **OpenFHE** | ✅ threshold FHE, multiparty CKKS | C++ (Python bindings) | Actively maintained, successor to PALISADE, noise flooding available |
| **Lattigo** | ✅ native multiparty CKKS (Mouchet et al.) | Go | Cleanest multiparty API; the reference implementation of threshold CKKS |
| TenSEAL / SEAL | ❌ | Python / C++ | Current stack. Single-key only |
| HEaaN | partial | C++ | Licensing constraints |

**Recommendation: OpenFHE.** It supports threshold CKKS, has Python bindings that
keep the existing PyTorch pipeline intact, and is C++ underneath — which is also
the path to the overdue **cross-compilation and embedded** deliverables. Lattigo
is the cleaner API but Go would strand the ML pipeline.

**Bonus:** carrying out this comparison properly and writing it up closes the
overdue month 3–4 *"Library Evaluation & Cross-Compilation"* deliverable (see 03).
Do it as a deliverable, not as an implementation detail.

### Consider threshold over additive

Mouchet et al.'s threshold CKKS (PETS 2021), which OpenFHE and Lattigo both
implement, gives *t-out-of-n* decryption instead of FheFL's *n-out-of-n*
additive shares. That solves §3.1 structurally rather than by bolting SecAgg on
top. FheFL's aggregation logic (eq. 6–12) is independent of how the key is shared
— **you can keep FheFL's robustness scheme and swap its key-sharing for threshold
CKKS.** That is likely the strongest configuration for IoV, and it is a
defensible novelty contribution in its own right.

---

## 5. Phased implementation plan

### Phase 0 — Prerequisites (do not skip)
- [ ] Fix D1 (labels) and D2 (window leakage). Any FheFL result built on the
      current labels is worthless.
- [ ] Restore `secure_channel.py` — FheFL needs DH regardless.
- [ ] Write the threat model document (overdue, and FheFL's assumptions —
      semi-honest server, ≤20% malicious, ≥2 non-colluding — are exactly its content).

### Phase 1 — Library evaluation *(closes an overdue deliverable)*
- [ ] Benchmark OpenFHE vs Lattigo vs TenSEAL: threshold support, encrypt/aggregate/
      decrypt timing at 44k params, ciphertext size, noise-flooding availability,
      cross-compilation story.
- [ ] Write it up as the month 3–4 Library Evaluation report.
- [ ] Pick one. Expected: OpenFHE.

### Phase 2 — Correct depth and parameters *(closes another overdue deliverable)*
- [ ] Choose a modulus chain giving ≥3 multiplicative levels with headroom.
- [ ] State the security level explicitly (128-bit) with LWE-estimator evidence.
- [ ] Add noise flooding before every decryption (§3.3).
- [ ] Write it up as the month 1–2 Security Specification report.

### Phase 3 — Key infrastructure
- [ ] DH pairwise secret establishment over the restored secure channel.
- [ ] Additive share generation, `ssᵤ` masking, server-side reconstruction of `s`.
- [ ] **Dropout handling** — Shamir recovery or threshold decryption (§3.1).
- [ ] Unit test: aggregate decrypts correctly with 0%, 10%, 30% mid-round dropout.

### Phase 4 — Encrypted robust aggregation
- [ ] `[dᵘ]` via eq. 11 (inner product with rotations + relinearisation).
- [ ] Decrypt `Σᵤ dᵘ` only; verify individual `dᵘ` remain encrypted.
- [ ] `[pᵘ]` via eq. 12, then `[pᵘ]·[fᵘ]`, sum, decrypt, divide by `U−1`.
- [ ] Equivalence test vs. a plaintext reference implementation of eq. 6–9.

### Phase 5 — Validation
- [ ] Re-benchmark real cost. Publish honest numbers, superseding the 0.14 s figure.
- [ ] Label-flip attack at 5%, 10%, 20% malicious — reproduce the paper's claims.
- [ ] **Add the paper's blind spot:** low-magnitude persistent attacker (§3.5).
- [ ] Scale toward the roadmap's 50 clients before claiming a system result.

---

## 6. Bottom line

**The decision to move to multi-key CKKS is correct and is the most important
call made on this project.** It is the only way the "server never sees plaintext"
claim becomes true, and FheFL's distance-to-global-model scoring is a genuinely
better fit for IoV than Multi-Krum.

Three things must be true before it pays off:

1. **The library changes.** TenSEAL cannot do multi-key. Decide this first.
2. **Dropout is handled.** The paper's additive n-out-of-n sharing breaks the
   moment a vehicle goes offline. Threshold CKKS or SecAgg-style recovery is
   mandatory, not optional.
3. **The data defects are fixed first.** FheFL on leaky labels produces a
   cryptographically elegant result about nothing.

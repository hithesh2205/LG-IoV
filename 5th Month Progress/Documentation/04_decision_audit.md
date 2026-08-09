# 04 — Decision audit

Every major technical decision, judged. Verdicts: **Correct**, **Correct but
mis-argued**, **Wrong**, **Unproven**.

---

## ✅ Correct

### 1. CKKS as the FHE scheme
Model updates are vectors of reals. CKKS is the only mainstream scheme that
natively encodes approximate reals and packs thousands of them per ciphertext
(SIMD). BFV/BGV would force fixed-point encoding; TFHE would be catastrophic at
44k parameters. Matches what FheFL, and essentially all FL+FHE literature, does.

### 2. The 46-D "timeless" unified feature vector
Mapping CAN, IP-flow and V2X-kinematic data into one feature space so a single
architecture serves all four datasets. This is the strongest engineering idea in
the project and it is what makes cross-dataset federation coherent at all.

### 3. Shrinking MamKANformer → ChebyKAN
609k → 44,164 parameters. Under FHE, parameter count is the cost driver: it sets
ciphertext count, bandwidth, and aggregation time. A 14× reduction is the right
call. (The *stated reason* is wrong — see "mis-argued" below — but the decision
is right.)

### 4. Running a real TenSEAL benchmark alongside the simulation
`benchmark_real_ckks.py` is the most defensible artifact in the repo. Its
docstring explicitly states that the simulation "does not cost anything extra to
run, so it cannot show real encryption overhead". That honesty is exactly right
and should be preserved in the decks.

### 5. `PlaintextVector` as a drop-in for `SimulatedCKKSVector`
Identical add/mul/decrypt interface so the FHE on/off toggle changes exactly one
variable. Correct experimental design. (It did not survive contact with reality —
see 05 — but the intent was right.)

### 6. Quarantining legacy 3-round results in `legacy_prior_results/`
Correct research hygiene. Do not mix scales.

### 7. Dirichlet α = 0.3 for non-IID sharding
Standard, appropriate, and genuinely representative of an IoV fleet where
different vehicles meet different attack mixes.

### 8. **Adopting multi-key CKKS now**
This is the correct call and the most important one on the list. Single-key CKKS
in FL is fundamentally broken as a privacy story: whoever holds the secret key
can decrypt *every* client's individual update. In the current code every client
shares one simulated context, so the threat model collapses — the deck's claim
that "the server never sees plaintext" cannot be met by any single-key design
where clients must decrypt the global model.
Multi-key / threshold CKKS is the standard fix and FheFL is a reasonable,
FL-specific instantiation. Pursue it. See 06 for the caveats.

---

## 🟡 Correct but mis-argued

### 9. The ChebyKAN-vs-MamKANformer comparison table (deck slide 10)
The table argues ChebyKAN wins on *"CKKS Encryption Compatibility — Chebyshev
polynomials evaluate natively on ciphertexts using specialized algorithms
(BSGS)"* and that MamKANformer's *"multiplicative depth explodes"*.

That argument is about **encrypted inference** — evaluating the model forward
pass on ciphertexts. The pipeline does not do encrypted inference. It encrypts
*weights for aggregation*, and aggregation is `Σ wᵢ · Encrypt(θᵢ)` — a weighted
sum. **Every architecture's weights are just a flat vector under a weighted
sum.** Multiplicative depth of the forward pass is irrelevant to it.

Worse, ChebyKAN as implemented is *not* HE-evaluable anyway:
- `torch.tanh(x)` — `cheby_kan.py:57`, transcendental, needs polynomial approximation
- `nn.LayerNorm` — `cheby_kan.py:107,113`, needs mean, variance and inverse square root
- `nn.Dropout` — `cheby_kan.py:108,114`

**Fix:** re-argue the slide on the honest ground, which is stronger anyway —
*44k vs 609k parameters means 14× fewer ciphertexts, 14× less V2X bandwidth,
14× less aggregation time.* Keep the encrypted-inference argument only if
encrypted inference becomes a real goal, and then first replace tanh/LayerNorm.

### 10. Multi-Krum for Byzantine robustness
Right *goal*, wrong *mechanism for an encrypted pipeline*. Multi-Krum needs
pairwise distances between individual client updates, so the server must see
them. The implementation does exactly that (`server.py:122` calls `.decrypt()`
on every client's parameters). Under real FHE this is impossible.

This is precisely the problem FheFL solves, and it is the best argument for the
pivot: FheFL scores each client by distance **to the previous global model**,
which the server already holds in plaintext, so `[dᵘ]` is computable
homomorphically. Keep the robustness goal, swap the mechanism.

---

## ❌ Wrong

### 11. Labelling CAN windows by source file
`car_hack_dataset.py` documents this explicitly:

> *"The flat CSV's R/T flag (R=regular, T=injected attack) is dropped — it is
> attack-row-level information; we operate at the window level and use the file
> label."*

The R/T flag is the **ground truth**. The DoS capture file contains normal
messages *and* injected messages; labelling every window from it "DoS" teaches
the model to recognise *which capture session this is*, not whether an intrusion
is present. Same pattern in `can_vtc_dataset.py:76`.

This is why CAN-VTC reports **100.0% accuracy and 1.0 ROC-AUC**. That number is
not an achievement, it is a symptom. See 05 for the fix.

### 12. Removing ECDH / AES-256-GCM transport security
Deck slide 11: *"No Transport-Layer AES/ECDH: Handshakes, key exchanges, and
symmetric transport encryption are completely removed... security is guaranteed
by FHE mathematical bounds."*

FHE provides **confidentiality of the payload only**. It does not provide:
- authentication (who sent this update?)
- integrity (was the ciphertext tampered with in flight?)
- replay protection (can an attacker resend round 3's update in round 9?)
- Sybil resistance (Multi-Krum's 20%-malicious assumption is meaningless if one
  attacker can register 500 vehicles)

`Model/federated/secure_channel.py` already implemented ECDH + AES-256-GCM with
mutual authentication. Deleting it from the new generation removed a working
control and replaced it with nothing. And FheFL *itself requires* Diffie–Hellman
to establish the pairwise secrets `s_{i,j}` — so the key-exchange machinery has
to come back regardless.

**Fix:** restore the secure channel. FHE and TLS/DTLS are complementary layers,
not alternatives. Re-word the slide to "FHE protects the update from the server;
the secure channel protects it from the network."

### 13. Presenting simulated-FHE accuracy deltas as results
`SimulatedCKKSVector` adds `N(0, 1e-9)` noise to a float32 array
(`fhe_adapter.py:25-30`). Nothing else. It is arithmetically a no-op relative to
float32 precision. So the FHE-vs-no-FHE accuracy delta **cannot carry signal** —
any difference is chaotic divergence, not an encryption effect. Reporting
VeReMi's −5.16 pp as an FHE cost would be wrong (and it is contradicted by the
FHE run being *faster*: 262 s vs 436 s). See 05.

The honest framing: *simulated FHE proves the aggregation algebra is lossless;
real TenSEAL measures the actual cost (0.14 s/round, 20.8× expansion, 3e-8
error). Accuracy is unaffected by CKKS to within 1e-8, which the max-abs-error
figure demonstrates directly.*

### 14. Dropping to 10 clients / 5 rounds without retiring the roadmap
`ROADMAP.md` specifies N ∈ {50,100,200}, R = 200–300, TOPSIS + Multi-Krum,
client-level DP, and 15-run statistical testing with Wilcoxon/Holm–Bonferroni.
The current runs are 10 clients, 5 rounds, no TOPSIS, no DP, single seed. Both
documents are live in the repo and they contradict each other.

Either scale up or formally amend the roadmap. Do not leave a reviewer to find
the discrepancy.

---

## ❓ Unproven

### 15. That the IDS works at all on VeReMi
ROC-AUC 0.5251 is a coin flip. 1.39M windows, and the model has learned nothing.
This is not a tuning issue; something in the VeReMi feature path is broken —
most likely that V2X kinematic data is being forced through a CAN-shaped 46-D
descriptor that discards the position/velocity-consistency signal misbehaviour
detection actually depends on. Do not present VeReMi numbers until this is
diagnosed.

### 16. That 0.14 s/round FHE overhead will survive the move to FheFL
The benchmark measures **addition and plaintext-scalar multiplication only**.
FheFL needs ciphertext × ciphertext multiplication, relinearisation, and rotations
for the inner products in `[dᵘ] = g^T g + [(fᵘ − 2g)^T fᵘ]`. Those are one to
three orders of magnitude more expensive than addition, and the current modulus
chain `[60,40,40,60]` gives only **2 multiplicative levels** for a computation
that needs at least 2 (distance, then `[pᵘ]·[fᵘ]`) — with zero headroom.

Expect the real number to be seconds, not 140 ms, and expect to need a longer
modulus chain, which increases ciphertext size beyond the measured 20.8×.
Re-benchmark before quoting overhead in any FheFL context.

> **✅ RESOLVED — and the prediction was partly wrong.** Measured after
> implementation:
>
> | Config | Total bits | Levels | Ciphertext | eq. 11 | 2nd ct×ct |
> |---|---|---|---|---|---|
> | N=8192, [60,40,40,60] | 200 | 2 | 326.6 KB | **18.0 ms ✓** | ✗ fails |
> | N=8192, [60,40,40,40,60] | 240 | — | **rejected** | — | — |
> | N=16384, [60,40,40,40,60] | 240 | 3 | 836.1 KB | 67.7 ms | ✓ |
>
> The encrypted squared distance of eq. 11 **does** fit at N=8192, in 18 ms —
> the chain did not need extending for it. The ceiling binds only on the
> *second* ciphertext×ciphertext multiply (`[pᵘ]·[fᵘ]`), and a 240-bit chain at
> N=8192 is rejected outright because 128-bit security permits at most 218 bits
> there. Strict FheFL therefore needs N=16384: **2.56× ciphertext size, 3.76×
> distance time**.
>
> The "seconds, not 140 ms" estimate was too pessimistic for the practical
> profile. Recorded here rather than silently corrected.

### 17. That CICIDS-2017 results are meaningful for IoV
CICIDS is enterprise IP traffic, not vehicular. It is a reasonable sanity dataset
but the 3-round run reported 99.58% accuracy at 0.8236 ROC-AUC — an
accuracy/AUC combination that indicates severe class imbalance being exploited
rather than a working detector. The 5-round run reports 98.18% / 0.9978. Two runs
disagreeing that much on the same data is itself a finding.

---

## Summary scorecard

| Verdict | Count | Items |
|---|---|---|
| Correct | 8 | CKKS, 46-D features, ChebyKAN size, real benchmark, PlaintextVector, legacy quarantine, Dirichlet, **multi-key pivot** |
| Correct but mis-argued | 2 | Slide-10 comparison, Multi-Krum |
| Wrong | 4 | File-level labels, dropped transport security, simulated-FHE deltas, unretired roadmap |
| Unproven | 3 | VeReMi, FheFL cost, CICIDS |

**Direct answer to "were my decisions correct":** the *strategic* ones were —
CKKS, the unified feature space, shrinking the model, and especially the move to
multi-key. The *methodological* ones were not: the labelling scheme invalidates
the headline accuracy, and removing transport security traded a working control
for a slogan. Neither is hard to fix, and both are much cheaper to fix now than
after the month-6 review.

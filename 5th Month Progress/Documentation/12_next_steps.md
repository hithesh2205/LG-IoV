# What To Do Next — Prioritised Roadmap

**As of:** end of Month 5 (2026-08-08) · 7 months remain of a 12-month programme

Tasks are ordered so that each unblocks the next. Priority bands:
**P0** = do first, blocks other work · **P1** = month 6 · **P2** = months 7–9 ·
**P3** = months 10–12.

---

## P0 — Immediate (week 1 of month 6)

### P0.1 Order target hardware  ⏱ 1 hour
**Blocks:** the entire embedded track, which is the largest schedule gap.
Order an **NXP S32G evaluation board** (production target) **and** a
**Raspberry Pi 5** (interim ARM host, available immediately). The Pi removes
procurement delay from the critical path — cross-compilation and NTT profiling
can start this week on it.

### P0.2 Bind the round number into the AEAD associated data  ⏱ 1 hour
**Closes:** threat S5 (replay). `secure_channel.encrypt(payload, aad=round_id)`
already accepts the parameter; the call sites in `client.py` do not pass it.

### P0.3 Enable noise flooding in the deployment config  ⏱ 2 hours
**Closes:** threat model requirement R6. `--noise-flooding-bits` defaults to 0
so equivalence tests stay exact; a deployment profile must set it > 0. Make the
server **refuse to start** in a deployment profile when it is 0, rather than
relying on documentation.

### P0.4 Implement the strict-disclosure profile  ⏱ 3 days · **cheaper than we thought**
`strict` is **specified and costed but not implemented** — requesting it raises
`NotImplementedError`. Implementing it needs an encrypted scalar broadcast across
ciphertext slots (rotation/replication) plus a second ciphertext × ciphertext
multiply at N=16384.

End-to-end measurement revised the cost sharply downward. Per **client update**
(not per ciphertext) strict costs only **1.40× the bandwidth** and **2.01× the
distance time**, because the larger ring packs twice as many slots so an update
needs 6 ciphertexts instead of 11. The earlier per-ciphertext framing (2.56× /
3.76×) overstated it. That makes the privacy upgrade meaningfully more attractive
— it removes the last per-round disclosure for ~40 % more bandwidth.

This is likely to be subsumed by P1.1 — OpenFHE exposes the rotation primitives
more directly than TenSEAL, so it may be cheaper to implement *after* the
migration than before it.

---

## P1 — Month 6

### P1.1 Migrate to OpenFHE  ⏱ 12 days · **the single most important item**
Detailed plan in [10_library_evaluation.md](10_library_evaluation.md) §5.
TenSEAL cannot express multi-key CKKS, so the current multi-key layer is an
algebraic model rather than a cryptographic implementation. Until this lands,
the system must **not** be described as full multi-key CKKS.

Sub-tasks: M1 install/verify · M2 port `CKKSVector` · M3 **real threshold key
generation and distributed decryption** · M4 native smudging · M5 re-run sweep ·
M6 first cross-compile.

### P1.2 Adopt threshold (t-of-n) key sharing  ⏱ folded into P1.1 M3
Replaces our per-round mask re-derivation with a scheme that tolerates dropout
*structurally*. This is also a defensible novelty contribution: keep FheFL's
robust aggregation, swap its n-of-n sharing for threshold CKKS.

### P1.3 The low-magnitude poisoning experiment  ⏱ 3 days
**Closes:** threat S3, the known blind spot. Scoring by distance to the current
global model *rewards* staying close, so a patient attacker submitting small
consistently-biased updates scores a high non-poisoning rate every round.
Implement the attacker, sweep magnitude × attacker fraction, and report the
failure envelope. If FheFL breaks here, that is a publishable finding.

### P1.4 Scale toward the roadmap  ⏱ 4 days
Currently 10 clients / 5 rounds; `ROADMAP.md` specifies 50–200 clients and
200–300 rounds. Move to **50 clients / 50 rounds** first and confirm convergence
and cost scale as expected before going further.

### P1.5 Re-acquire raw VeReMi with sender IDs  ⏱ 2 days · **higher priority than it looks**
`veremi_dataset.py` already implements `mode="windowed"` and activates it
automatically when a sender column is present. Blocked because the cleaning step
dropped the identifier.

This is not cosmetic. Measurement shows the per-beacon fallback has a hard
ceiling — best single-feature class separation **0.046σ**, best threshold
accuracy **0.545** against a 0.547 baseline. VeReMi's 19 attack types (ConstPos,
ConstSpeed, DataReplay, EventualStop, DelayedMessages, …) are all defined by how
one sender's claims evolve **over time**, which a single beacon cannot express.
Until the sender ID is restored, **one of the project's four datasets cannot
contribute a meaningful result**, and any V2X claim rests on nothing.

Source: <https://github.com/josephkamel/VeReMi-Dataset>. Preserve the sender
column through cleaning this time.

### P1.6 Client-level differential privacy  ⏱ 3 days
The only `ROADMAP.md` mechanism deliberately dropped that is a genuine gap
(gradient clipping C=1.0, Gaussian σ, RDP accountant). Addresses threat P3
(property inference from the aggregate).

---

## P2 — Months 7–9 · the embedded track

This is where the schedule debt sits. Nothing here has started.

> **Updated after the Month 1–4 catch-up pass.** Three of these were built in
> software during Month 5; what remains of each is specifically the part that
> needs a board.

| # | Task | Effort | Status after catch-up |
|---|---|---|---|
| P2.1 | Cross-compile the OpenFHE core for ARM64 | 3 d | 🔴 blocked on hardware |
| P2.2 | On-hardware baseline benchmark | **0.5 d** | 🟡 harness + host baseline done ([16](16_hardware_baseline.md)); **only the board is missing** |
| P2.3 | SIMD packing / encoding module | — | ✅ **done** ([14](14_packing_and_encoding.md)) — 29.6 % lossless |
| P2.4 | NTT kernel acceleration (NEON intrinsics) | **6 d** | 🟡 reference + test vectors done ([15](15_ntt_implementation.md)); the C/NEON port remains |
| P2.5 | Model quantization (INT8/QAT) — note CKKS encodes reals, so quantization interacts with encoding and needs design, not just `torch.quantization` | 5 d | 🔴 not started |
| P2.6 | On-device inference engine + embedded IDS executable | 8 d | 🔴 not started |
| P2.7 | **V2X transport protocol** — the bandwidth problem below | 5 d | 🟡 packing has already cut the payload 29.6 % |

**The embedded track shrank from ~40 days to ~22**, and P2.2 went from 2 days to
half a day. The remaining work is genuinely hardware-dependent rather than
merely unstarted.

### The V2X bandwidth problem — P2.7 in detail
A single ciphertext is **326.6 KB** and a full 44k-parameter update is
**3.59 MB**. A DSRC frame is ~2.7 KB. One update is therefore ~1,300 frames, and
a 50-vehicle round moves ~180 MB. **This does not fit.** Reduction levers, in
expected order of value:

1. **Modulus switching before transmission** — drop to the lowest level; saves ~40 %
2. **Top-k / sparse update selection** — send only the largest-magnitude coordinates
3. **Seeded `a`** — transmit a PRNG seed instead of the second ciphertext component; up to ~50 %
4. **Update compression / quantization before encryption**
5. **Hierarchical aggregation** — RSUs pre-aggregate so only one ciphertext per RSU reaches the server

Item 5 is likely the decisive one and changes the architecture, so it should be
decided early.

---

## P3 — Months 10–12 · integration, evaluation, publication

| # | Task | LG deliverable |
|---|---|---|
| P3.1 | End-to-end encryption pipeline integration | Month 7–8 |
| P3.2 | Hardware-in-the-loop validation | Month 9–10 |
| P3.3 | Performance and power-consumption audit | Month 9–10 |
| P3.4 | Attack-vector injection campaign + false-positive tuning | Month 7–8 |
| P3.5 | Privacy audit and differential analysis | Month 11–12 |
| P3.6 | Privacy–utility trade-off analysis | Month 11–12 |
| P3.7 | Production-ready IDS FHE library + final report | Month 11–12 |

---

## Experiments still required

| Experiment | Why | Priority |
|---|---|---|
| Low-magnitude persistent poisoning | Known blind spot in the scoring function | **P1** |
| Attacker fraction sweep 0–40 % | AS2 assumes ≤20 %; untested above it | P1 |
| Dropout rate sweep 0–50 % | Mask re-scoping is verified in unit tests but not under training | P1 |
| Strict vs practical disclosure, accuracy + cost | Quantify what the privacy upgrade costs | P0.4 |
| Client scaling 10 → 50 → 100 | Roadmap target | P1 |
| Round scaling 5 → 50 → 200 | Roadmap target | P1 |
| Noise-flooding bits vs accuracy | Find the usable operating point | P1 |
| Per-attack-type breakdown (VeReMi 19 classes) | Currently binary only | P2 |
| Cross-dataset transfer | Does a model trained on Car-Hacking help on CAN-VTC? | P2 |
| Ablation: non-poisoning rate vs plain FedAvg | Isolate the robustness contribution | P1 |

---

## Documentation still required

| Document | Status |
|---|---|
| Threat model | ✅ [08](08_threat_model.md) |
| Security specification | ✅ [09](09_security_specification.md) |
| Library evaluation | ✅ [10](10_library_evaluation.md) — cross-compilation half still open |
| Model accuracy report | ✅ [11](11_current_status.md) |
| Optimized packing & encoding module doc | 🔴 blocked on P2.3 |
| NTT implementation doc | 🔴 blocked on P2.4 |
| Ciphertext serialization & V2X protocol spec | 🔴 blocked on P2.7 |
| Vulnerability assessment report | 🔴 months 7–8 |
| Privacy–utility trade-off analysis | 🔴 months 11–12 |

---

## Before submission or publication

1. **Do not claim full multi-key CKKS until P1.1 M3 lands.** Today the
   homomorphic arithmetic is real and the key management is an algebraic model.
   State that boundary in every write-up.
2. **Report CAN-VTC honestly** — the DoS flood saturates every window, so the
   near-perfect score measures flood detection, not generalisation. Car-Hacking
   is the meaningful CAN benchmark.
3. **Never re-report the Month-4 numbers.** They are in
   `Results/month4_legacy_INVALID/` for provenance only.
4. Run the S3 poisoning experiment before claiming Byzantine robustness.
5. Get statistical significance right: ≥5 seeds and a paired test before any
   "method A beats method B" claim.

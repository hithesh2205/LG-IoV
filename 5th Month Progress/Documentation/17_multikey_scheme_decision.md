# 17 — Multi-key scheme decision: xMK-CKKS vs threshold CKKS

**Status:** decision record · open, pending measurement (§10)
**Version:** 1.0 · 2026-08-28
**Supersedes the key-management half of:** [06_multikey_ckks_plan.md](06_multikey_ckks_plan.md)

---

## 1. What this document decides

Month 5 established that single-key CKKS cannot support the project's privacy
claim, and that TenSEAL cannot express any multi-key scheme
([10_library_evaluation.md](10_library_evaluation.md)). Two candidate schemes
remain for Month 6:

| | Scheme | Sharing model |
|---|---|---|
| **A** | **xMK-CKKS** — Ma, Naas, Sigg, Lyu, arXiv:2104.06824 (2021) | additive, n-out-of-n |
| **B** | **Threshold CKKS** — Shamir sharing over the ring (Mouchet et al., PETS 2021, and successors) | t-out-of-n |

**Current position: adopt A (xMK-CKKS), with the participant-set fix in §5.1,
and treat B as a conditional upgrade gated on the measurement in §10.**

Threshold CKKS is *not* automatically better. It buys availability and pays for
it in collusion resistance (§6.2). Which side of that trade we want is an
empirical question we have not yet measured.

---

## 2. Why plain MK-CKKS is not a candidate

Two independent reasons, either sufficient.

**2.1 Ciphertext growth.** In vanilla MK-CKKS, combining ciphertexts encrypted
under *k* distinct keys yields a ciphertext of dimension *k+1*. Aggregating a
50-vehicle round would produce a 51-component ciphertext. Against a bandwidth
budget that is already the binding constraint
([14_packing_and_encoding.md](14_packing_and_encoding.md)), this is
disqualifying on its own.

**2.2 The privacy flaw xMK exists to fix.** Under MK-CKKS each device encrypts
under its *own* public key and produces decryption shares against *its own*
ciphertext component. Partial decryption information can then be steered at an
individual update, and a curious server can recover it.

---

## 3. What xMK-CKKS changes — the one detail that matters

The fix is a single structural change, and it is easy to get wrong when
implementing from a summary.

**Devices do not encrypt under their own public key.** They encrypt under the
**sum of all participants' public keys**:

```
each device i:   s_i  (secret, never leaves the device)
                 P_i = -a*s_i + e_i          (common public a)

aggregated key:  P~ = SUM_i P_i              a valid public key for  s~ = SUM_i s_i

encryption:      CT_i = Encrypt(W_i, P~)     <-- P~ , NOT P_i
```

Aggregation is then ordinary homomorphic addition, and the ciphertext **stays 2
components** regardless of fleet size — which is what removes §2.1.

Decryption shares are computed against the **summed** ciphertext component, not
the device's own:

```
server holds:    C_sum = ( SUM_i c0_i , SUM_i c1_i )

device i sends:  mu_i = s_i * ( SUM_i c1_i ) + e_i^smudge    <-- the SUM, not c1_i

server computes: SUM_i c0_i + SUM_i mu_i  =  SUM_i W_i
```

Because a share is only meaningful against the aggregate, it cannot be redirected
at an individual ciphertext. That is the whole of the fix.

> **Implementation trap.** Encrypting under `P_i` instead of `P~`, or computing
> `mu_i` against `c1_i` instead of `SUM c1`, silently rebuilds the MK-CKKS
> vulnerability while appearing to work. Both must be asserted in tests.

**Noise flooding is mandatory, not optional.** `e_i^smudge` is what stops the
released decryption from leaking key material — the same IND-CPA^D concern
already recorded in
[09_security_specification.md](09_security_specification.md) §7.1.

---

## 4. Fit with our architecture

The scheme's disclosure model matches what we already do, so this part needs no
change:

| Property | Our current pipeline | xMK-CKKS | Match |
|---|---|---|---|
| Global model at the server | plaintext (`broadcast_global_model`) | plaintext | yes |
| Server sees the aggregate in the clear | yes, by design | yes, by design | yes |
| Server sees an individual update | never (`server.py` audit) | never | yes |
| Broadcast to devices | plaintext | plaintext | yes |

---

## 5. The real obstacle: dropout, stated precisely

xMK-CKKS is **n-out-of-n**. Decryption requires a share from every device whose
public key went into `P~`. Two dropout cases behave completely differently, and
conflating them overstates the problem.

### 5.1 Dropout known *before* the round — solvable, cheaply

Public keys are **static**. Every device caches all of them at enrolment. When
the server announces the round's participant set, each participant recomputes

```
P~_round = SUM over i in participants of P_i
```

locally. Cancellation then holds by construction for whoever is actually
present. **No extra round trip, no key re-exchange.** This is the same technique
`MultiKeyContext.begin_round(participants)` already uses for the FheFL masks.

**This fix is mandatory and should land with the first implementation.** Without
it, every enrolled vehicle must produce a share every round — including vehicles
that did no training — which is untenable for a fleet.

### 5.2 Dropout *during* the round — fatal, and irreducible under n-of-n

A vehicle that uploads `CT_i` and then loses coverage before sending `mu_i`
leaves the sum missing a term. Decryption returns **garbage, not a degraded
result**, and the round is lost.

This window is genuinely new. Our FheFL mask re-scoping does not help: it settles
masks *before* aggregation, whereas this failure occurs *after*. For a vehicle
fleet — tunnels, handover, ignition off — the window is real.

**This is the only thing threshold CKKS buys us.** Everything else is equal.

---

## 6. Threshold CKKS

### 6.1 What it is

Only the **key-splitting method** changes. Encryption, homomorphic addition, and
the server-sees-only-the-aggregate property are identical.

**Additive (xMK-CKKS):** `s = s_1 + s_2 + ... + s_n`. Every term required. A
combination lock where each party holds one digit.

**Shamir t-of-n:** the secret sits at the y-intercept of a secret polynomial of
degree `t-1`; each device holds one *point* on the curve.

```
      f(x)                       secret  s = f(0)
       |
  s *--+--.                      degree t-1
       |   `--* D1               any t points   -> determine f -> recover s
       |      `---* D2           any t-1 points -> reveal nothing
       |          `--* D3
       +---------------- x
```

Each partial decryption carries a **Lagrange coefficient** so that any `t` shares
combine correctly.

**The ring wrinkle.** Lagrange interpolation divides by differences
`(x_i - x_j)`, which must be **invertible in** `R_q = Z_q[x]/(x^N+1)`. This
constrains the choice of evaluation points and is why the scheme must come from a
library rather than be hand-rolled.

### 6.2 The trade nobody states — availability against collusion

| | Colluders needed to unmask an honest device |
|---|---|
| xMK-CKKS (n-of-n) | **n − 1** |
| Threshold t-of-n | **t − 1** |

Lowering `t` to survive dropout **directly weakens the privacy bound.** At
`t = n` threshold degenerates to xMK-CKKS's guarantee and tolerates no dropout at
all.

This lands on assumption **AS3** in [08_threat_model.md](08_threat_model.md),
currently *"≥2 non-colluding vehicles"*. Under threshold it must be restated as
**"at most t−2 vehicles collude with the server"** — a materially stronger claim
requiring justification for a real fleet. **Choosing `t` is a documented risk
decision, not a tuning parameter.**

---

## 7. Impact on Byzantine robustness — check this first

This is the highest-severity interaction and it is easy to miss.

`federated/server.py::aggregate_round` performs **N + 1 decryptions per round**,
not one:

| Line | Operation | Count |
|---|---|---|
| `server.py:254` | `[d.reveal() for d in enc_distances]` — per-client distance scalars | **N** |
| `server.py:269` | `acc.decrypt()` — the aggregate | **1** |

Under **any** multi-key scheme, every decryption becomes a *distributed*
decryption requiring a share from each participant. A 10-vehicle round would go
from 1 decryption to **11 full participation round-trips**. That is not
deployable.

**Mitigation — slot-batched distance decryption.** Rotate client *u*'s distance
into slot *u* of a single ciphertext, sum, and perform **one** distributed
decryption that reveals all N distances at once:

```
[d_batch] = SUM_u rotate( [d^u], u )     -> one ciphertext, N occupied slots
```

This returns the round to **2 distributed decryptions** (distances, then the
aggregate) and preserves FheFL's non-poisoning-rate scoring exactly.

**Dependency:** rotation requires **joint Galois keys**, generated
collaboratively rather than by one party. Confirm library support before
committing to this design — it is the load-bearing assumption of the whole plan.

---

## 8. Comparison

| | FheFL additive (today) | **xMK-CKKS** | Threshold t-of-n |
|---|---|---|---|
| Server opens only the aggregate | yes | yes | yes |
| Ciphertext grows with fleet size | no | **no** | no |
| Round trips per FL round | **1** | 2 | 2 |
| Dropout known before round | partial | yes (§5.1) | yes |
| Dropout mid-round | n/a | **round lost** | degrades |
| Colluders needed to break | n−1 | **n−1** | t−1 |
| Expressible in TenSEAL | no | no | no |
| Implementable in OpenFHE | — | yes | **verify — S1** |
| Implementable in Lattigo | — | yes | yes |

---

## 9. Decision and conditions

**Adopt xMK-CKKS for Month 6**, because:

1. It is peer-reviewed, and its privacy argument is sound.
2. Its disclosure model already matches our architecture (§4) — zero redesign.
3. The ciphertext does not grow with fleet size.
4. It preserves the **n−1** collusion bound, which threshold would weaken.
5. The dominant dropout case is fixable at no cost (§5.1).

**Mandatory with the first implementation:**

- [ ] Per-round `P~` derivation from the participant set (§5.1)
- [ ] Noise flooding enabled before every released decryption (§3)
- [ ] Test asserting encryption uses `P~`, never `P_i` (§3 trap)
- [ ] Test asserting `mu_i` is computed against `SUM c1`, never `c1_i` (§3 trap)
- [ ] Slot-batched distance decryption, keeping the round at 2 trips (§7)

**Escalate to threshold CKKS only if** the measurement below shows mid-round
dropout is material — and only after re-deriving AS3 for the chosen `t`.

---

## 10. Open items to resolve in the OpenFHE M1 spike

| # | Question | Why it is load-bearing |
|---|---|---|
| S1 | Does OpenFHE expose **t-of-n** threshold, or only n-of-n? | Decides whether B is available at all without a Go boundary. **Currently unverified — do not plan around an assumed answer.** |
| S2 | Does OpenFHE support **joint Galois key** generation for multiparty rotation? | §7 batching depends on it entirely |
| S3 | Measured **decryption-share size** per client per round | Plausibly 1–2 MB, i.e. up to a doubling of upload; bandwidth is already the binding constraint |
| S4 | Does dropping to the lowest modulus level before sending shares reduce S3? | Expected yes; quantify |
| S5 | **Instrument the mid-round dropout rate** — how often does a vehicle drop between the `CT` upload and the `mu` upload? | This single number decides §9. If low, xMK-CKKS is sufficient and the collusion trade is avoided |

S5 is the decisive one and needs no cryptography to answer — it can be measured
from participation traces alone.

---

## 11. What must not be claimed until this lands

Carried forward from [12_next_steps.md](12_next_steps.md) §1:

> The homomorphic arithmetic is real CKKS. The multi-key **key management** is
> currently an algebraic model, because TenSEAL exposes no multi-key API.
> Nothing may be described as "full multi-key CKKS" — or as xMK-CKKS — until the
> OpenFHE migration lands and the §9 checklist is green.

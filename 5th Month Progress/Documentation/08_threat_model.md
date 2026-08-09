# Threat Model — Privacy-Preserving Collaborative IDS for IoV

**LG deliverable:** *Threat model document* (Month 1–2)
**Status:** delivered Month 5 (overdue — see [03_lg_gap_analysis.md](03_lg_gap_analysis.md))
**Version:** 1.0 · 2026-08-08

---

## 1. What is a threat model, and why does this document exist?

A **threat model** is a structured statement of *who might attack a system*,
*what they are able to do*, *what they want*, and *which of those attacks the
design actually stops*. It is written before or alongside the design so that
every security mechanism can be traced to a threat it addresses — and, just as
importantly, so that threats with no mechanism are visible rather than
forgotten.

Without one, security work drifts toward whatever is interesting to build. This
project is a concrete example: four months of effort went into homomorphic
encryption (which defeats *one* adversary, the curious server) while
authentication and replay protection were removed entirely (which hands the
system to a *different* adversary, the network attacker). A threat model written
in Month 1 would have caught that trade immediately.

---

## 2. System under consideration

### 2.1 Assets — what we are protecting

| Asset | Why it matters | Exposure if lost |
|---|---|---|
| **A1 — Raw vehicle telemetry** (CAN traffic, GPS position, speed, driving behaviour) | Directly identifies a driver's routes, habits, and vehicle condition | Location tracking, driver profiling, insurance discrimination |
| **A2 — Local model updates** (the 44,164-parameter gradient vector) | Gradients are invertible: an adversary can reconstruct training samples from them | Indirect leakage of A1 |
| **A3 — Global IDS model** | Its decision boundary reveals what the fleet can detect | Adversary crafts attacks that evade detection |
| **A4 — Fleet membership and identity** | Which vehicles participate, and when | Presence/absence tracking of individual vehicles |
| **A5 — Detection integrity** | The IDS must actually fire on real intrusions | Undetected CAN injection → physical safety risk |

A5 is the one that makes this a safety system, not just a privacy system. A CAN
bus intrusion can command braking, steering, or acceleration. An IDS that has
been poisoned into silence is worse than no IDS, because it creates false
confidence.

### 2.2 Trust boundaries

```
┌─────────────────────────────┐
│  VEHICLE (trusted)          │   A1 raw telemetry never leaves
│  - sensors, CAN bus         │   A2 exists here in the clear
│  - local training           │   holds its own key share s_u
└──────────────┬──────────────┘
               │  ◄── TRUST BOUNDARY 1: the radio link (V2X / DSRC / C-V2X / 5G)
               │      adversary: anyone with a radio
┌──────────────┴──────────────┐
│  RSU / EDGE RELAY           │   forwards; should learn nothing
└──────────────┬──────────────┘
               │  ◄── TRUST BOUNDARY 2: the aggregation interface
               │      adversary: the server operator
┌──────────────┴──────────────┐
│  AGGREGATION SERVER         │   sees ciphertexts + the global model
│  (semi-honest)              │   must NOT see any individual A2
└─────────────────────────────┘
```

### 2.3 Assumptions

| # | Assumption | Justification | What breaks without it |
|---|---|---|---|
| AS1 | The server is **semi-honest**: follows the protocol, but tries to infer | Standard PPFL model; a commercial operator has reputational and legal constraints, not protocol-level ones | A malicious server can send different global models to different vehicles and isolate one vehicle's update |
| AS2 | **≤20 %** of participating vehicles are malicious | FheFL §V; matches the FL literature. Compromising more of a real fleet requires physical access at scale | The non-poisoning-rate weighting can be outvoted; the "honest majority" reference point moves |
| AS3 | **≥2 non-colluding** vehicles per round | FheFL Theorem 1 — with one honest vehicle the aggregate *is* its update | Complete loss of privacy for the lone honest vehicle. Enforced in code: `MultiKeyContext` refuses `n_users < 2` and the server refuses to aggregate a single package |
| AS4 | The vehicle platform itself is **not compromised** | Out of scope; a rooted ECU defeats any cryptography above it | Key share `s_u` is extracted; that vehicle's privacy is gone (but not others') |
| AS5 | Key exchange happens over an **authenticated** channel | Provided by `secure_channel.py` (ECDH-P256 + Ed25519 mutual auth) | Man-in-the-middle on the pairwise secrets → total break |

---

## 3. Adversaries

### ADV-1 — Honest-but-curious aggregation server
**Capability:** sees every ciphertext, all masked key shares, the global model each round, and timing/volume metadata.
**Goal:** reconstruct A1 or A2 for a target vehicle.
**Cannot:** deviate from the protocol, or obtain a vehicle's key share.

### ADV-2 — Malicious participating vehicle
**Capability:** trains on falsified data, submits arbitrary updates, may register several identities.
**Goal:** degrade A5 (make the IDS miss a specific attack class) or bias the global model.
**Bounded by:** AS2.

### ADV-3 — Network adversary on the V2X link
**Capability:** eavesdrop, inject, replay, drop, delay frames. Assumed *not* to have vehicle key material.
**Goal:** impersonate a vehicle, replay stale updates, or deny service.

### ADV-4 — Colluding coalition (vehicles + server)
**Capability:** union of ADV-1 and several ADV-2, pooling key shares.
**Goal:** decrypt a specific honest vehicle's update.
**Bounded by:** AS3 — needs U−1 colluders.

### ADV-5 — Model-extraction adversary
**Capability:** legitimate participant, observes the global model every round.
**Goal:** learn the IDS decision boundary well enough to craft evasive attacks (A3).

---

## 4. Attack catalogue and mitigation status

Legend: ✅ mitigated · 🟡 partial · 🔴 unmitigated · ⬜ out of scope

### 4.1 Privacy attacks (target A1, A2)

| ID | Attack | Adversary | Status | Mechanism / gap |
|---|---|---|---|---|
| P1 | **Gradient inversion** — reconstruct training samples from an update | ADV-1 | ✅ | Updates are CKKS-encrypted client→server. `AggregationAudit` asserts `individual_update_decryptions == 0` each round |
| P2 | **Membership inference** — was this driver's data used? | ADV-1 | ✅ | Same as P1: no individual update is ever visible |
| P3 | **Property inference** from the aggregate | ADV-1 | 🟡 | The aggregate *is* released by design. Mitigation is the U−1 collusion bound; client-level DP is not yet implemented |
| P4 | **Distance-scalar leakage** — the `practical` profile reveals one distance per client per round | ADV-1 | 🟡 | Quantified: 1 scalar vs 44,164 parameters. Noise flooding available via `--noise-flooding-bits`. The `strict` profile removes it at 2.56× bandwidth |
| P5 | **CKKS approximate-decryption key recovery** (IND-CPA^D, Li & Micciancio 2021) | ADV-1 | 🟡 | `MultiKeyContext.flood()` implements smudging; **must be enabled** for deployment runs. Off by default so equivalence tests stay exact |
| P6 | **Collusion to isolate one vehicle** | ADV-4 | ✅ | FheFL Theorem 1 — needs U−1 colluders. Enforced by AS3 checks |
| P7 | **Traffic analysis** — presence/absence of a vehicle from ciphertext timing (A4) | ADV-1, ADV-3 | 🔴 | Not addressed. Ciphertext sizes are constant, but participation timing is observable. Would need cover traffic or fixed schedules |

### 4.2 Security / integrity attacks (target A5)

| ID | Attack | Adversary | Status | Mechanism / gap |
|---|---|---|---|---|
| S1 | **Label-flipping data poisoning** | ADV-2 | ✅ | FheFL non-poisoning-rate weighting (eq. 7–9). Distance to the previous global model, computed homomorphically |
| S2 | **Model poisoning** (large arbitrary update) | ADV-2 | ✅ | Large `‖g − f^u‖²` → small `p^u`. Verified in `tests/test_crypto.py::test_non_poisoning_rates` |
| S3 | **Low-magnitude persistent bias** — small consistent nudges each round | ADV-2 | 🔴 | **The known blind spot.** Scoring by distance to the current global model *rewards* staying close. The paper concedes the distance assumption "may not always be true". Experiment pending (see [12_next_steps.md](12_next_steps.md)) |
| S4 | **Sybil registration** — one attacker, many vehicle identities | ADV-2, ADV-3 | 🟡 | Ed25519 identity keys + mutual auth make anonymous registration impossible, but nothing binds an identity key to a *physical* vehicle. Needs hardware attestation / PKI enrolment |
| S5 | **Replay of a previous round's update** | ADV-3 | 🟡 | AES-GCM gives per-frame integrity; round-number binding as AEAD associated data is **not yet wired in**. One-line fix, tracked |
| S6 | **Free-riding** — submit the received global model unchanged | ADV-2 | 🟡 | Such a client has distance ≈ 0 and gets the *highest* weight — an inversion of intent. Needs a minimum-contribution check |
| S7 | **Byzantine collusion** to shift the reference point | ADV-4 | 🟡 | Bounded by AS2; untested above 20 % |

### 4.3 Network attacks

| ID | Attack | Adversary | Status | Mechanism / gap |
|---|---|---|---|---|
| N1 | **Eavesdropping** on the V2X link | ADV-3 | ✅ | AES-256-GCM over ECDH-P256 (`secure_channel.py`) |
| N2 | **Man-in-the-middle** during handshake | ADV-3 | ✅ | Ed25519 mutual authentication; signature covers both ephemeral key and peer identity |
| N3 | **Tampering** with a ciphertext in flight | ADV-3 | ✅ | AEAD tag; verified in `tests/test_crypto.py::test_secure_channel` |
| N4 | **Denial of service** — jam the link, or drop updates | ADV-3 | 🟡 | Round-scoped masks (`begin_round`) mean dropouts degrade rather than corrupt. Sustained jamming is unaddressed |
| N5 | **Dropout-induced decryption corruption** | ADV-3 | ✅ | The FheFL gap. Fixed by per-round mask scoping + `strict_dropout_check`; verified in `test_dropout_is_detected` |

### 4.4 Model-confidentiality attacks

| ID | Attack | Adversary | Status | Mechanism / gap |
|---|---|---|---|---|
| M1 | **Evasion** — craft an intrusion the IDS misses | ADV-5 | 🔴 | Inherent: participants must receive the global model. Adversarial-robustness training is out of scope for Month 5 |
| M2 | **Model theft** | ADV-5 | ⬜ | Out of scope — every participant legitimately holds the model |

---

## 5. Residual risk summary

| Severity | Item | Why it remains |
|---|---|---|
| **High** | S3 low-magnitude persistent poisoning | No mechanism; the scoring function is structurally vulnerable |
| **High** | M1 evasion | Inherent to collaborative learning |
| **Medium** | S4 Sybil | Needs hardware attestation, i.e. embedded track |
| **Medium** | P7 traffic analysis | Needs protocol-level padding/scheduling |
| **Medium** | S6 free-riding | Needs a contribution floor |
| **Low** | S5 replay | Fix identified (bind round id into AEAD AAD) |
| **Low** | P4/P5 | Mitigations implemented; must be *enabled* in deployment config |

---

## 6. Requirements this generates

| Req | Statement | Verified by |
|---|---|---|
| R1 | The server shall never obtain an individual model update in plaintext | `assert_no_individual_decryption`, asserted every round |
| R2 | All vehicle↔server traffic shall be authenticated and integrity-protected | `test_secure_channel` |
| R3 | Aggregation shall proceed correctly when any subset (≥2) of vehicles reports | `test_dropout_is_detected` |
| R4 | A vehicle whose update is far from the consensus shall be down-weighted | `test_non_poisoning_rates` |
| R5 | Encryption shall not change the aggregation result beyond CKKS precision | `test_backend_equivalence`, `test_real_ckks_roundtrip` |
| R6 | Deployment configurations shall enable noise flooding | **Config-level; not enforced in code yet** |
| R7 | Updates shall be bound to a round number to prevent replay | **Not yet implemented (S5)** |

R6 and R7 are open and are carried into the next-steps list rather than being
quietly dropped.

# 18 — Multi-key scheme decision, revised: DMK-CKKS replaces xMK-CKKS

**Status:** decision record · adopted at the 8 Oct 2026 weekly meeting · source paper identified 9 Nov 2026 (§3) · option still to be confirmed (§6.3, §11)
**Version:** 1.1 · 2026-11-09
**Supersedes:** the scheme choice in [17_multikey_scheme_decision.md](17_multikey_scheme_decision.md) §9 (adopt xMK-CKKS). Doc 17's analysis of dropout (§5), collusion (§6.2) and Byzantine robustness (§7) still applies and is used below.
**Slides:** `Presentation/01_Final_Presentations/08.10.26 Weekly_Meet Final draft.pptx`, slides 14–18
**Most likely source paper:** X. Ma, "A secure aggregation method for federated learning based on homomorphic encryption" (the scheme is called **PFLMA**), *Advances in Engineering Innovation* 16(2), pp. 80–85, 2025, [doi:10.54254/2977-3903/2025.21661](https://doi.org/10.54254/2977-3903/2025.21661)

---

## 1. Decision history

| Date | What happened | Recorded in |
|---|---|---|
| 28 Aug 2026 | xMK-CKKS adopted as the multi-key scheme for Month 6 | doc 17 §9; `Presentation_28th_August_Baseline.pptx`, slides 19–24 |
| 7–16 Sep 2026 | Single-key CKKS paper drafted. Transport encryption (AES-GCM / ECDH) left out; CKKS alone carries confidentiality | `Paper/iov_ckks_paper.tex` §III-C |
| 5 Oct 2026 | Dr. Praveen K asks how to handle "broadcasting certain group key things safely" — the single-key weakness, where one compromised vehicle exposes every vehicle's updates. The answer given then was xMK-CKKS key masking | `October_5_Progress_Meeting.pptx`, slide 12 |
| **8 Oct 2026** | **Multi-key scheme changed to DMK-CKKS**, after comparing it with centralized multi-key CKKS (CMK-CKKS) | 8 Oct deck, slides 14–18 |
| 9 Nov 2026 | Confirmed: (1) the server is untrusted and holds no decryption key; (2) no AES-GCM transport layer; (3) the single-key paper goes first, and DMK-CKKS follows | this document |
| 9 Nov 2026 | The DMK-CKKS slides traced to the PFLMA paper, and the CMK-CKKS column to MK-CKKS (§3) | this document |

**Note on (2).** It reverses the transport recommendation in
[04_decision_audit.md](04_decision_audit.md) #12,
[09_security_specification.md](09_security_specification.md) §6,
[12_next_steps.md](12_next_steps.md) P0.2 and `13_why_AES_with_FHE.pdf`. What
those documents say FHE does **not** provide (authentication, integrity, replay
protection, Sybil resistance) is still true, so it has to be covered by
threat-model assumptions instead (§9).

---

## 2. DMK-CKKS as presented on 8 Oct

From slide 17 and the overall-flow figure on slide 16:

```
1. Key generation (Key Generation Center, KGC, once)
     every client i:          SK_i = (s_i1, s_i2)          individual private key
     aggregated public key:   b̄ = Σ_i b_i                   published
     decryption key:          s̄ = Σ_i (s_i1 + e_i*)         sent to every client ("or its component")

2. Local training and encryption (each vehicle)
     ct_i = (c0_i, c1_i) = Enc_b̄(W_i)                       under the aggregated key b̄

3. Encrypted aggregation (server: semi-honest, holds no key)
     c_sum = Σ_i ct_i = Enc(W_1 + ... + W_N)

4. Broadcast and decryption (each vehicle)
     W_global = Dec_s̄(c_sum)                                no decryption shares sent

5. Repeat steps 2-4 every round.
```

**Stated advantages (slides 17–18, compared with centralized multi-key CKKS):**

- **Less client communication during decryption.** Vehicles decrypt with a key
  they already hold, with no share round.
- **Better protection against client–server collusion.**

---

## 3. Where the 8 Oct slides come from

No publication uses the names "DMK-CKKS" or "CMK-CKKS" (web search, 9 Nov 2026).
Both columns of slide 18 do match published work.

### 3.1 DMK-CKKS → PFLMA (Ma, 2025)

PFLMA has the same three parties as the slides (Key Generation Center, cloud
server, participants). It writes the aggregated public key as `b̄`, as the slide
does. Its conclusion makes the same two claims as slide 17: lower communication
cost, and resistance to collusion between participants and the server.

| 8 Oct slides | PFLMA | Match |
|---|---|---|
| KGC generates the clients' private keys | §3.1: the KGC generates participants' key pairs. §3.2.1 also has each participant generate `sk_i = s_i`. Either way, the KGC ends up holding `sk = Σ sk_i` | yes |
| Aggregated public key `b̄ = Σ b_i` | KGC computes `pk = Σ b_i`; encryption uses `b̄` | yes |
| Decryption key `s̄ = Σ (s_i1 + e_i*)`, sent to every client | KGC holds `sk = Σ sk_i`. No `s_i2`, no `e_i*`, and nothing says participants receive `sk` | **no** |
| Clients encrypt with `b̄` | eq. 1: `cm_i = (v·b̄ + e_i0 + m_i, v_i·a + e_i1)` | yes |
| Server adds ciphertexts | `C_sum = Σ cm_i'` | yes |
| Clients decrypt alone with the pre-generated key | Every participant sends a partial decryption `D_i`, and the server sums them (§3.2.3–3.2.4; Fig. 1 step 2, "share decryption") | **no** |
| Less decryption communication; better collusion protection | Same claims in the conclusion. The measured saving is against **MK-CKKS** (§4.3, Fig. 4), not against xMK-CKKS | claim matches; comparison differs |
| — | An extra key-switching step, `R_i = (−sk_i·a + sk·a + se_i) mod q`, before upload | not on the slides |

Two things in the 8 Oct figure come from neither PFLMA nor xMK-CKKS:

- the two-part key `SK_i = (s_i1, s_i2)`;
- the noise term `e_i*` *inside* the decryption key. In xMK-CKKS, `e_i*` is the
  smudging noise added to each decryption share (§7).

**Reading PFLMA critically.**

- **It is a short paper with no security proof.** Six pages, single author; the
  security analysis is three informal paragraphs.
- **Its decryption formulas don't work as printed.** Summing
  `D_i = C_sum1 − s_i·C_sum0` over n participants gives
  `n·C_sum1 − (Σ s_i)·C_sum0`. Eq. 1 puts the `a`-term in `c_i1`, so the key
  must multiply `C_sum1`. The correct version is xMK-CKKS's:
  `m ≈ C_sum0 + Σ_i (s_i·C_sum1 + e_i*)`.
- **It doesn't cite the work it builds on.** Its reference list has neither
  MK-CKKS nor xMK-CKKS, though its core — an aggregated public key `Σ b_i` and
  per-participant shares summed by the server — is xMK-CKKS's design.
- **Its experiments are small.** 510-weight models on two small UCI medical
  datasets (Heart Disease, Pima).

**What this means.** PFLMA is xMK-CKKS with a trusted KGC and a key-switching
step added. In our paper, cite xMK-CKKS as the basis (Ma, Naas, Sigg, Lyu,
*International Journal of Intelligent Systems* 37, 2022,
[doi:10.1002/int.22818](https://doi.org/10.1002/int.22818)), and cite PFLMA only
for the KGC variant. Don't implement from PFLMA's printed formulas.

### 3.2 CMK-CKKS → MK-CKKS (Chen, Dai, Kim, Song, ACM CCS 2019)

The "Centralized MK-CKKS" column on slide 18 describes MK-CKKS: H. Chen, W. Dai,
M. Kim, Y. Song, "Efficient Multi-Key Homomorphic Encryption with Packed
Ciphertexts with Application to Oblivious Neural Network Inference", ACM CCS 2019
([IACR ePrint 2019/524](https://eprint.iacr.org/2019/524)). Each client encrypts
under its own key, decryption needs every client, and client communication is
higher. MK-CKKS is the baseline PFLMA compares against. Its ciphertext grows
with the number of parties, and that growth is where PFLMA's (and xMK-CKKS's)
communication saving comes from (doc 17 §2.1).

Slide 15 describes "centralized" differently: a parent authority holds a master
secret key and decrypts results, and children derive their own key pairs. No
paper matches that design. The closest relative is L. Xiao, O. Bastani,
I-L. Yen, "An Efficient Homomorphic Encryption Protocol for Multi-User Systems"
([IACR ePrint 2012/193](https://eprint.iacr.org/2012/193)): a master key is
turned into per-user keys, with optional key agents to stop user–server
collusion. It is not CKKS-based. **Slides 15 and 18 should be made to agree
before this comparison is presented again.**

---

## 4. Four schemes side by side

| | Single-key (the paper) | xMK-CKKS (doc 17) | DMK-CKKS as drawn on 8 Oct | PFLMA (the source) |
|---|---|---|---|---|
| Who creates the keys | trusted dealer | each vehicle, locally | KGC | KGC (holds `Σ sk_i`) |
| Encryption key | shared public key | aggregated `P~` | aggregated `b̄` | aggregated `b̄` |
| Ciphertext size as the fleet grows | constant | constant | constant | constant |
| Server holds a decryption key | no | no | no | no |
| How the aggregate is decrypted | any vehicle, alone | every vehicle sends a share | any vehicle, alone, with `s̄` | every participant sends a share `D_i` |
| Who can read one vehicle's update | any vehicle (by overhearing the upload) | only n − 1 vehicles colluding with the server | any vehicle (by overhearing the upload), see §6 | the KGC; otherwise n − 1 vehicles colluding with the server |
| A vehicle drops out mid-round | harmless | round lost | harmless | round lost; the KGC could supply the missing share (§6.2) |
| Server can evaluate any f (weighted FedAvg, `f_dist`, `f_cos`) | yes | yes | yes | yes |
| Trusted third party | dealer | none | KGC | KGC |
| Library | TenSEAL | OpenFHE multiparty | none ready-made | OpenFHE multiparty for the shares; the KGC is our own code |

---

## 5. The KGC is a trusted party

The KGC holds every private key (`Σ sk_i`), so it can decrypt any vehicle's
update. PFLMA itself defines the KGC as a trusted third party that also handles
key updates and revocation. That puts it in the same position as the single-key
trusted dealer (`setup.py`), and unlike xMK-CKKS, where no party ever holds the
full key. The threat model needs three statements:

- **Who runs the KGC** (for example the OEM or the LG back end), and that it is
  a different entity from the RSU / aggregation server, which is untrusted by
  design.
- **The KGC never colludes with the server.** If the KGC supplies decryption
  shares (§6.2, option D), it must only ever issue a share for the round's
  summed ciphertext — never for a ciphertext the server picks. Otherwise it
  becomes a decryption service for individual updates.
- **Re-keying.** `b̄` is a sum over a fixed set of vehicles, so the KGC must
  re-issue it whenever a vehicle joins or leaves the fleet.

---

## 6. Does DMK-CKKS stop vehicles from reading each other? Settle this first

### 6.1 As drawn, it is single-key CKKS

Two facts from the 8 Oct figure:

1. **The individual keys `SK_i` are never used after key generation.** Vehicles
   encrypt with `b̄` and decrypt with `s̄`.
2. **`b̄` is a public key whose secret is `s = Σ s_i1`**, and every vehicle
   receives `s̄`, which is that secret (apart from the noise term, see §7).

A public key whose secret key every vehicle holds is single-key CKKS, with the
KGC in the dealer's role. CKKS decryption is linear and `c_sum` is just the sum
of the `ct_i`, so **the key that opens `c_sum` also opens every `ct_i` on its
own.** With no AES-GCM layer (§1), a V2X upload is a radio broadcast, so:

- any vehicle that overhears another vehicle's upload can decrypt it — no
  collusion needed;
- one vehicle colluding with the RSU hands it `s̄`, and the RSU can then read
  every update.

That is the single-key weakness raised on 5 Oct, so the collusion advantage on
slide 17 does not hold for the scheme *as drawn*. **The source paper does not
work this way.** In PFLMA every participant sends a partial decryption, and only
the KGC holds the full key (§3.1). The "pre-generated decryption key" on
slide 17 isn't in the source.

### 6.2 The options, and what each costs

| Option | What it means | Vehicles can read each other? | To read one vehicle | Mid-round dropout | What the server can compute | Decryption round |
|---|---|---|---|---|---|---|
| **A — as drawn on 8 Oct** | every vehicle holds `s̄` | **yes** | any one vehicle | harmless | any f | none |
| **B — zero-sum masks** | before encrypting under `b̄`, each vehicle adds a fresh per-round mask; all masks sum to zero (pairwise seeds, as on the 5 Oct slide 12) | no | n − 1 colluding vehicles | masks no longer cancel; needs a recovery step | plain sum only | none |
| **C — own-key encryption** (private stream aggregation) | each vehicle encrypts with its own `s_i1` and a common polynomial `a_t = H(t, chunk)`, fresh every round; `s̄ = Σ s_i1` opens only the full sum | no | n − 1 colluding vehicles | missing key term; the KGC must supply it | plain sum only | none |
| **D — follow the source (PFLMA)** | every vehicle sends a share computed on the final summed ciphertext, as in xMK-CKKS; only the KGC holds `Σ s_i` | no | n − 1 vehicles colluding with the server, or the KGC | the KGC can compute the missing share (it knows `s_j`), if it is online | any f | one share round, as in xMK-CKKS |

Notes:

- **Option D is xMK-CKKS with a KGC added.** The share round stays, so slide
  18's "reduced client communication during decryption" does not hold against
  xMK-CKKS. PFLMA's saving is against MK-CKKS. What the KGC adds is a way to
  recover from a mid-round dropout, the case doc 17 §5.2 calls fatal. The price
  is a trusted party that knows every key.
- **Option C is the closest of A–C to published work.** In private stream
  aggregation, a trusted dealer gives each user a key and gives the decryptor a
  key equal to their sum, so only the total can be opened. Original scheme: Shi
  et al., "Privacy-Preserving Aggregation of Time-Series Data", NDSS 2011.
  Lattice version: Becker, Guajardo and Zimmermann, "Revisiting Private Stream
  Aggregation: Lattice-Based PSA", NDSS 2018.
- **`a_t` must be fresh every round and every chunk** (option C). If it repeats,
  subtracting two of a vehicle's ciphertexts cancels the mask and reveals the
  difference between its updates.
- **"Plain sum only" is the real price of B and C.** The masks cancel only when
  every vehicle's contribution is added with the same weight. So:
  - **The F function still works** if each vehicle pre-weights its own update
    (encrypts `n_k · Δw_k`) and the server multiplies the sum by `1/N`.
  - **FheFL robust weighting breaks.** In `Σ p_u·[f_u]` the server chooses each
    `p_u`.
  - **`f_dist` and `f_cos` break.** They are per-vehicle values nobody holding
    `s̄` can open.
  - **Byzantine robustness then needs a different mechanism.** For example,
    zero-knowledge proofs that each update's norm is bounded, as in RoFL (IEEE
    S&P 2023) and EIFFeL (ACM CCS 2022).

**The trade, stated plainly.** Removing the decryption round means the
decryption key is fixed *before* the server computes anything. A fixed key
either opens everything (option A: single-key privacy) or opens only one fixed
function, the plain sum (options B and C). Keeping the round (option D, and
xMK-CKKS) works because each share is computed on whatever ciphertext the server
actually produced. That keeps every server function and the n − 1 bound.

### 6.3 Current position

DMK-CKKS stays the decision. **Read it the way its source does: option D.** That
means KGC-issued keys, encryption under `b̄`, and shares computed on the summed
ciphertext, with the corrected formulas (§7).

**What D keeps:**
- FheFL robust aggregation (with slot-batched distance decryption, doc 17 §7);
- the n − 1 collusion bound.

**What D adds:** the KGC turns xMK-CKKS's fatal mid-round dropout into a
recoverable one.

**What D costs:**
- a trusted KGC that knows every key;
- the KGC must be online whenever a vehicle drops;
- no saving in decryption communication over xMK-CKKS.

**The other options:**
- **Option A** must not be presented as multi-key.
- **Options B and C** only make sense if removing the decryption round becomes a
  hard requirement. FheFL would then have to be replaced.

---

## 7. The decryption formulas need correcting

**In the 8 Oct figure.** `s̄ = Σ_i (s_i1 + e_i*)` puts noise inside a key, and a
noisy key cannot decrypt:

```
Dec(ct, s + E) = c0 + c1·(s + E) = (c0 + c1·s) + c1·E = W + noise + c1·E
```

`c1` is a uniformly random polynomial mod `q`, so `c1·E` is as large as `q` and
the result is garbage. **Fix the figure before it goes into the paper or another
deck.**

**In PFLMA.** The printed decryption doesn't work either (§3.1). Use the
xMK-CKKS form (doc 17 §3):

```
vehicle i sends:   D_i = s_i · C_sum1 + e_i*      <-- the SUMMED c1, plus smudging noise
server computes:   C_sum0 + Σ_i D_i  ≈  Σ_i W_i
```

**Noise flooding is still mandatory.** In option D it sits on each share, as
`e_i*`. CKKS is not IND-CPA^D
([09_security_specification.md](09_security_specification.md) §7.1): anyone who
sees an exact decryption together with its ciphertext can solve for key
material. Under option A that key opens every update.

---

## 8. Impact on the single-key paper

- **The paper stays single-key.** DMK-CKKS appears only under Future Work, as a
  KGC-based variant of xMK-CKKS following PFLMA. Cite xMK-CKKS (IJIS 2022) and
  PFLMA (AEI 2025), and MK-CKKS (CCS 2019) as background.
- **Don't present "DMK-CKKS" as an established name.** If the paper uses it,
  define it as our term.
- **Don't use the 8 Oct DMK-CKKS figure as drawn** (§7).
- **Keep the single-key limitation explicit** in the Discussion: with one shared
  key and no transport encryption, vehicles can read each other's updates. That
  limitation is why the multi-key step exists.
- **A separate gap in the current draft:** the RSU computes an FheFL distance
  `[d^u]` for each vehicle (§IV-C) but holds no key, and the draft does not say
  who decrypts these values. State it.

---

## 9. Threat-model changes

Applies to [08_threat_model.md](08_threat_model.md).

| Item | Change |
|---|---|
| New trusted party | KGC: honest, separate from the RSU, never colludes with it, and issues shares only for the round's summed ciphertext (§5) |
| AS1 (server semi-honest) | Unchanged; the 8 Oct figure labels the server semi-honest |
| AS3 (≥2 non-colluding vehicles) | Holds under options B, C and D (n − 1 colluders needed). Under option A it becomes "no vehicle colludes with the server or eavesdrops on another vehicle", which is the single-key assumption |
| No transport encryption | FHE gives confidentiality only. Authentication, integrity and replay protection must be assumed, or come from signed V2X messages (IEEE 1609.2), as the doc 04 #12 analysis says |
| Byzantine robustness (S1–S2) | Option D keeps FheFL scoring. Under options B and C it is not available (§6.2) |

---

## 10. Implementation plan

Replaces the checklist in doc 17 §9.

| Step | Work | Done when |
|---|---|---|
| D0 | Source identified: PFLMA (§3.1). Confirm with the team that the 8 Oct slides were based on it, and fix the option (§6.3) | Confirmed, option recorded here |
| D1 | Write the exact algorithms (KeyGen, Enc, Eval, Dec) for the chosen option, with both formula fixes from §7 | Algorithms checked against §6 and §7 |
| D2 | Small RLWE prototype of the key structure at N = 8192, reusing the validated NTT reference ([15_ntt_implementation.md](15_ntt_implementation.md)) for ring arithmetic | Tests below pass |
| D3 | Build on OpenFHE: its multiparty CKKS covers option D's share-based decryption, and the KGC is our own code. TenSEAL cannot express this ([10_library_evaluation.md](10_library_evaluation.md)) | D2 tests pass on the real library |
| D4 | Add it as a new `--backend` in `train_federated.py` (today: `ckks`, `exact`, `none`) and re-run the 3-seed sweep | Accuracy and cost table against single-key |
| D5 | Dropout and collusion experiments during training | Results recorded in [11_current_status.md](11_current_status.md) |

Tests that must exist before any result is reported:

- [ ] Decrypting the round's aggregate gives `Σ W_i` within CKKS error
- [ ] No single vehicle's key decrypts another vehicle's `ct_i`
- [ ] Option D: shares are computed on the **summed** `C_sum1`, never on an individual `c1_i` (doc 17 §3 trap)
- [ ] Option D: the KGC refuses to issue a share for anything other than the round's summed ciphertext
- [ ] Option D: a missing share (with no KGC replacement) makes the round refuse to decrypt — never silent garbage
- [ ] No noise term inside any key, and smudging noise on every share (§7)
- [ ] Options B and C only: masks or `a_t` are fresh every round and every chunk

---

## 11. Open items

| # | Question | Why it matters |
|---|---|---|
| Q1 | Were the 8 Oct slides based on PFLMA? Who prepared them, and from which paper? | If another source exists, §3 changes |
| Q2 | Which option (§6.2)? Recommended: D | Decides the privacy guarantee, robustness and dropout behaviour |
| Q3 | Where do `s_i2` and the `e_i*` inside the key come from? Neither is in PFLMA or xMK-CKKS | The figure needs fixing either way (§7) |
| Q4 | What is PFLMA's key-switching step (`R_i`) for, and do we need it? | It adds work on every vehicle every round |
| Q5 | Option D: does OpenFHE support joint Galois keys for slot-batched distance decryption? | FheFL robustness at 2 share rounds (doc 17 §7, item S2) |
| Q6 | Option D: is the KGC online during rounds, and how fast can it replace a missing share? | Dropout recovery is the KGC's main benefit |
| Q7 | Who runs the KGC? | Trust model and re-keying (§5) |
| Q8 | Measured share size per vehicle per round | The share round stays under D; bandwidth is already the binding constraint (doc 17 item S3) |

---

## 12. What must not be claimed until this lands

> The code today is single-key CKKS (TenSEAL) plus the Month-5 algebraic
> multi-key model. Nothing may be described as multi-key CKKS or as DMK-CKKS
> until D3 lands and the §10 tests pass.

- Don't present "DMK-CKKS" as a published scheme. The source paper calls its
  scheme PFLMA, and neither PFLMA nor this project has a security proof for it.
- Don't claim reduced decryption communication versus xMK-CKKS: option D keeps
  the share round.
- Don't claim collusion resistance until the chosen option is implemented and
  tested.

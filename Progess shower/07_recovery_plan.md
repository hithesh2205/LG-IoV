# 07 — Month-5 recovery plan

**Written 2026-08-08.** Assumes ~4 weeks to the month-5 boundary; compress or
stretch the weeks to fit your actual date.

---

## The honest starting position

You cannot close the embedded/hardware gap by the end of month 5. It is three
deliverables that have not started (hardware benchmarking, NTT acceleration,
quantization + embedded executable), and no amount of effort in four weeks
produces a cross-compiled FHE stack on an automotive target from a standing
start. Any plan that claims otherwise will fail visibly at the review.

So "getting back on track" means three different things, and only the first two
are about catching up:

1. **Close every deliverable that is pure documentation.** Three are overdue and
   all three are writing, not engineering. These are what LG will actually ask to
   see, and they are fully achievable.
2. **Make the accuracy numbers real**, so the Model Accuracy Report stops being
   invalidated by leakage.
3. **Convert the embedded gap from a hidden failure into a managed, dated
   recovery item** with named target hardware. Arriving at a review saying "we
   are behind on embedded, here is the schedule and here is the board we ordered"
   is a completely different conversation from being caught out.

**Defer FheFL implementation to month 6.** Only its library-evaluation step
belongs in month 5 — and that step is itself an overdue deliverable, so it pays
for itself twice. Attempting the full FheFL build now would consume the entire
month and close zero deliverables.

---

## New findings that change the plan

Two things I confirmed while scoping this, both good news:

### Car-Hacking ground truth is fully recoverable ✅
All four attack CSVs retain the `R/T` flag as field 11:

```
0316,8,05,21,68,09,21.1,21.2,00,6f,R
```

In the first 200k rows of `cleaned_DoS_dataset.csv`: **149,841 `R` vs 48,687 `T`**
(~24% injected). The parser at `car_hack_dataset.py` throws this away by choice,
not by necessity. Fixing D1 for Car-Hacking is a **two-hour change**, not a
re-acquisition.

⚠️ 1,472 rows in that sample have `0` in the last field instead of `R`/`T` —
malformed/short rows. Handle explicitly (drop and count), do not let them silently
become a third class.

### VeReMi is diagnosed — and it is not the model 🔴
`cleaned_Veremi_final_dataset.csv` has proper per-row `attack` and `attack_type`
columns, and `veremi_dataset.py` uses them correctly. So D5 is not a labelling
problem. The cause is **windowing across mixed senders**:

- The cleanup step deleted the node/sender ID (`veremi_dataset.py` docstring:
  *"any node-ID / RSSI removed"*).
- `_extract_windows` slides a 64-row window over **consecutive CSV rows**
  (`veremi_dataset.py:86`), which are beacon *reception events from many
  different vehicles* interleaved.
- It then takes mean/std across that window (`:90-91`).

Misbehaviour detection works by checking one sender's claimed trajectory against
physics. Averaging position and speed across 64 beacons from unrelated vehicles
destroys precisely that signal. The `rcvTime` deltas at `feat[43:45]` are pure
noise for the same reason, and the majority-vote label at `:116` is meaningless
when a window mixes honest and attacking senders.

**AUC 0.525 is exactly what this predicts.** The fix is to re-clean from raw
VeReMi preserving the sender ID, then group by sender, sort by `rcvTime`, and
window *within each sender's stream*. This requires re-downloading raw VeReMi.

### CAN-VTC remains the one hard case ❌
`cleaned_*_dataset.csv` files are log-format only — `ID: 0316  000  DLC: 8  ...` —
with no per-message flag. Ground truth is not recoverable from the cleaned data.
Three options, in order of preference:

1. **Re-acquire the raw dataset.** The label was most likely discarded during
   cleaning, not absent upstream. Check first — cheapest path by far.
2. **Derive labels from published injection signatures.** The DoS file shows the
   classic flood pattern (`ID: 0000` with all-zero payload repeating). Fuzzy
   injections are identifiable as CAN IDs outside the attack-free ID set.
   Impersonation is genuinely hard. Document every rule you apply.
3. **Reframe honestly** as "normal capture vs. attack capture" session
   classification and state that limitation in every table. Do not present it as
   intrusion detection.

---

## Week 1 — Data integrity (gates everything else)

Nothing downstream is worth doing until this is done. Every number generated
before it has to be thrown away.

| # | Task | Effort | File |
|---|---|---|---|
| 1.1 | Parse `R/T` field 11; label window = attack class if any `T` present, else normal (class 0). Count and drop malformed `0` rows | 2 h | `data/car_hack_dataset.py` |
| 1.2 | Replace `rng.shuffle` split with **contiguous-segment split** — cut each capture into 70/15/15 message ranges *before* windowing, so no window spans a boundary | 4 h | `data/preprocess.py:126-148` |
| 1.3 | Decide the CAN-VTC route (re-acquire / heuristic / reframe). Check for raw data first | 0.5 d | `data/can_vtc_dataset.py` |
| 1.4 | Re-download raw VeReMi; re-clean preserving sender ID; group + sort by sender, window within sender | 2–3 d | `data/veremi_dataset.py` |
| 1.5 | Re-run all four datasets, 3 seeds | 1 d compute | — |

**Expected outcome:** CAN-VTC drops well below 100%. Car-Hacking becomes a real
5-class problem. VeReMi should move decisively off 0.52 AUC — if it does not,
run a gradient-boosted tree on the same features as a floor to prove whether the
features or the model are at fault.

**These lower numbers are the project starting to work.** Say so explicitly in
the deck; do not let a reviewer discover the drop and interpret it as regression.

---

## Week 2 — The three overdue paper deliverables

Pure writing. This is the week that actually puts you back on schedule.

### 2.1 Threat model document *(month 1–2, ~3 months overdue)* — 2 days
Write it against FheFL's assumptions, which you are adopting anyway, so this
doubles as design work:
- Adversary classes: semi-honest aggregation server; malicious vehicles (≤20%);
  colluding vehicles; network attacker; compromised RSU
- Attack catalogue: gradient inversion / membership inference; label-flip data
  poisoning; model poisoning; Sybil registration; replay; free-riding
- Explicit assumption that ≥2 users are non-colluding (FheFL Theorem 1) and what
  breaks if that fails
- Per-attack mapping: which control stops it, and which are currently unmitigated

### 2.2 Security specification report *(month 1–2, overdue)* — 2 days
The parameters already exist inside `benchmark_real_ckks.py`; they just need a
justification written around them:
- Target security level (128-bit) with LWE-estimator evidence
- Ring dimension, coefficient modulus chain, scale — and the multiplicative-depth
  budget. **Note now that `[60,40,40,60]` gives only 2 levels, which FheFL will
  exhaust with zero headroom**
- Noise budget analysis across rounds
- Noise flooding before decryption, and why (CKKS is not IND-CPA^D — Li &
  Micciancio, Eurocrypt 2021)

### 2.3 Library evaluation *(month 3–4, overdue)* — 2 days
This is also the decision that unblocks FheFL, so it is not overhead:

| Library | Threshold/multi-key CKKS | Language | Cross-compiles |
|---|---|---|---|
| OpenFHE | ✅ | C++ + Python bindings | ✅ |
| Lattigo | ✅ (reference impl.) | Go | ✅ |
| TenSEAL / SEAL | ❌ | Python / C++ | partial |

Benchmark encrypt/aggregate/decrypt at 44k params on each, tabulate ciphertext
size and noise-flooding support, and pick one. **Expected answer: OpenFHE** — it
keeps your PyTorch pipeline via Python bindings while being C++ underneath, which
is also the path to the embedded deliverables.

---

## Week 3 — Honest results and restored controls

| # | Task | Effort |
|---|---|---|
| 3.1 | Regenerate the **Model Accuracy Report** on fixed data, 3 seeds, with confidence intervals | 1 d |
| 3.2 | Restore `Model/federated/secure_channel.py` into `NewModel/federated/`; wire into `register_client` | 4 h |
| 3.3 | Fix the FHE/no-FHE experiment: set `precision_noise_std=0`, assert **bitwise-identical** aggregation, delete wall-clock timings from the comparison, cite `max_abs_error ≈ 3e-8` as the real numerical effect | 4 h |
| 3.4 | Correct the decks (below) | 1 d |

### Deck corrections — do not present these slides unchanged again

| Slide | Currently says | Change to |
|---|---|---|
| 10 | ChebyKAN wins on "CKKS encryption compatibility / multiplicative depth" | Re-argue on parameter count: 44k vs 609k = 14× fewer ciphertexts, bandwidth, aggregation time. The depth argument is about encrypted *inference*, which you do not do — and ChebyKAN's `tanh` and `LayerNorm` are not HE-evaluable anyway |
| 11 | "No Transport-Layer AES/ECDH… completely removed" | "FHE protects the update from the server; the secure channel protects it from the network." FHE gives no authentication, integrity, or replay protection — and FheFL needs Diffie–Hellman regardless |
| 14/15 | "maintaining zero plaintext exposure" | State the current limitation plainly: Multi-Krum decrypts individual updates server-side today; multi-key CKKS in month 6 is what closes it |
| 18 | 100% / 98% accuracy headlines | Post-fix numbers, with the labelling change explained |

---

## Week 4 — The month 5–6 deliverable, and the embedded recovery plan

### 4.1 Ciphertext serialization & V2X feasibility *(month 5–6, due now)* — 2 days
Mostly analysis you can do immediately from numbers you already have:
- **3.68 MB per client update per round vs a ~2.7 KB DSRC frame.** One CKKS
  ciphertext (~334 KB) is already ~120× a single frame
- Fragmentation and reassembly strategy; per-round bandwidth for a 50-vehicle fleet
- Reduction levers: modulus switching before transmission, dropping to the lowest
  level before send, sparse/top-k update selection, seeded-`a` transmission
- Serialization format with explicit versioning
- Honest conclusion on what fleet size is deliverable over each bearer

This is a real month 5–6 deliverable and it is achievable in two days because the
measurements already exist.

### 4.2 Embedded recovery plan — 1 day
- **Name and order the target hardware.** Until a board is chosen, nothing on the
  embedded track can start. Candidates: NXP S32G, Renesas R-Car, TI Jacinto, or
  a Raspberry Pi 5 / Jetson as an interim stand-in to unblock work now
- Dated schedule for months 6–8: cross-compilation → hardware baseline benchmark
  → SIMD packing module → NTT acceleration → quantization → embedded executable
- Flag explicitly that months 7–12 (HiL validation, power audit) depend on this

### 4.3 Repository cleanup for the GitHub push — 4 h
- Update `Team/LG_IoV/GEMINI.md` (still describes KANConvNet / Fourier / `Model/`)
- Archive or delete the unused MamKANformer branch; fix `config.yaml`
- Remove the TOPSIS claim from `server.py:3` or implement it
- Add a "current scope vs. target scope" note to `ROADMAP.md` reconciling
  10 clients / 5 rounds against the promised 50–200 / 200–300

---

## What you present at the month-5/6 review

**Delivered:**
1. Threat model document ✅
2. Security specification report ✅
3. Library evaluation with a justified pick ✅
4. Model Accuracy Report on leak-free data, multi-seed ✅
5. Ciphertext serialization & V2X feasibility analysis ✅
6. Real CKKS cost benchmark (already done) ✅

**Declared behind, with a dated plan:**
7. Embedded track — hardware named and ordered, months 6–8 schedule attached

**Ahead of schedule:**
8. Multi-key CKKS design (a months 7–12 item) scoped and library-selected,
   implementation starting month 6

That is a credible month-5 position. Six deliverables closed, one gap owned and
scheduled, one item running early.

---

## If you only have one week

Do these five, in this order, and nothing else:

1. Car-Hacking `R/T` labels (2 h) — the single highest value-per-hour fix
2. Contiguous-segment split (4 h)
3. Threat model document (2 d) — the most overdue deliverable
4. Security specification report (2 d) — the second most overdue
5. Name and order the target hardware (1 h) — unblocks everything downstream

VeReMi and CAN-VTC re-acquisition can slip to month 6 **provided you stop
presenting their current numbers**.

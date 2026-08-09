# 05 — Confirmed defects

Each entry: what is wrong, the evidence, why it matters, and the fix.
Paths are relative to `Team/LG_IoV/NewModel/` unless stated.

> ## ✅ RESOLUTION STATUS — all seven defects fixed in Month 5
>
> This document was written during the Month-5 audit, when every defect below was
> open. **All seven have since been fixed and verified.** The original diagnosis
> is preserved unchanged because it is the evidence trail; this banner records
> the outcome.
>
> | Defect | Status | Verified by |
> |---|---|---|
> | D1 — filename labels | ✅ Fixed | `tests/test_data_pipeline.py` — attack captures now yield both normal and attack windows; separability audit confirms Car-Hacking has real but non-trivial signal (best single feature 0.935 vs 0.595 baseline) |
> | D2 — window/split leakage | ✅ Fixed | `assert_no_group_overlap`, enforced on every split |
> | D3 — uncontrolled FHE comparison | ✅ Fixed | `tests/test_crypto.py::test_backend_equivalence` — `exact` and `none` are bitwise identical |
> | D4 — server decrypted individual updates | ✅ Fixed | `assert_no_individual_decryption`, asserted every round |
> | D5 — VeReMi not learning | 🟡 **Diagnosed, not solved** — see below | Root cause was cross-sender windowing, not the model |
> | D6 — transport security removed | ✅ Fixed | `secure_channel.py` restored; `test_secure_channel` |
> | D7 — documentation drift | ✅ Fixed | GEMINI.md, config.yaml, ROADMAP.md all rewritten |
>
> **D5 is the one defect that is diagnosed but not solved, and the honest answer
> is that it cannot be solved from the cleaned data.**
>
> The original guess — "CAN-shaped features discard the kinematic signal" — was
> wrong. The measured cause is sharper: VeReMi rows carry proper per-row labels,
> but `attack` is 45.3 % of rows and the adapter windowed across *mixed senders*
> (the sender ID had been dropped during cleaning), so the 64-row majority-vote
> label was close to a coin flip. The label was noise; the model was fine.
>
> Switching to per-beacon features makes the problem **well-posed** — the label
> now means something. But measurement shows it also has a low ceiling: best
> single-feature class separation **0.046σ**, best single-feature threshold
> accuracy **0.545** against a 0.547 majority baseline.
>
> That is not a bug. VeReMi's 19 attack types (ConstPos, ConstSpeed, DataReplay,
> EventualStop, DelayedMessages, …) are all defined by how one sender's claims
> evolve **over time**. A constant-position attacker's individual beacon reports a
> perfectly plausible position; only its never changing gives it away, and a
> single beacon cannot express "never changes".
>
> The prediction was then **confirmed by training**: the federated run returned
> accuracy 0.4839 ± 0.0433 and ROC-AUC 0.5161 ± 0.0018, with a confusion matrix
> showing a degenerate classifier labelling almost everything "attack". The audit
> was run *before* the experiments, so prediction and outcome agree — which means
> `audit_feature_separability.py` can be trusted to flag an unlearnable
> formulation before compute is spent on it.
>
> So the cleaned export supports **neither** formulation: windowing mixes senders
> and destroys the label; per-beacon keeps the label but discards the temporal
> signal. **VeReMi requires re-acquisition with sender IDs.**
> `mode="windowed"` is implemented and activates automatically once the column is
> present. Until then, VeReMi numbers are a near-chance lower bound and should be
> reported as such.
>
> Current results and remaining limitations: [11_current_status.md](11_current_status.md).

---

## D1 — Window labels come from the filename, not the ground truth  🔴 blocker

**Evidence**
- `data/car_hack_dataset.py` docstring: *"The flat CSV's R/T flag (R=regular,
  T=injected attack) is dropped — it is attack-row-level information; we operate
  at the window level and use the file label."*
- `data/car_hack_dataset.py:37-43` — `FILE_TO_LABEL` maps filename → class.
- `data/can_vtc_dataset.py:76` — `y = np.full(X.shape[0], idx)` where `idx` is
  the index of the source file in `CLASSES`.

**Why it matters**
Attack capture files contain mostly normal traffic with injected attack messages
interleaved. Labelling every window from `cleaned_DoS_dataset.csv` as "DoS"
trains a *capture-session classifier*, not an intrusion detector. The model can
score 100% by learning each file's baseline CAN-ID distribution and never
detecting a single injected frame.

This is the direct cause of **CAN-VTC: 100.0% accuracy, 1.0 ROC-AUC**.

**Fix**
1. Car-Hacking: stop dropping the `R/T` column. Label a window by its injected
   messages — either `1` if any message in the window is `T` (detection), or by
   attack type if any `T` present else normal (classification).
2. CAN-VTC has no per-message flag. Either derive labels from the published
   injection intervals, or reframe it honestly as *normal vs each attack capture*
   and state that limitation in every report.
3. Re-run everything. Expect accuracy to drop substantially. That drop is the
   experiment starting to work, not a regression.

---

## D2 — Overlapping windows leak across the train/test split  🔴 blocker

**Evidence**
- `config.yaml`: `window: 64`, `stride: 16` → consecutive windows share 48 of 64
  messages (75% overlap).
- `data/preprocess.py:126-148` `_stratified_split()` — `rng.shuffle(idx)` then
  slices. A uniformly random split over overlapping windows.

**Why it matters**
Window *k* and window *k+1* share three quarters of their messages. A random
split puts near-duplicates on both sides of the train/test boundary. Test
accuracy then measures memorisation, not generalisation. This inflates every CAN
and VeReMi number in the repo, independently of D1.

**Fix**
Split by **contiguous time block or capture session**, not by shuffled window.
Cut each capture into train/val/test segments *before* windowing, or use
`GroupShuffleSplit` with the source segment as the group. Keep the existing
fit-stats-on-train-only discipline — that part is already correct.

---

## D3 — The FHE-vs-no-FHE comparison is not a controlled experiment  🔴

**Evidence** — `checkpoints/federated_summary_veremi_{fhe,nofhe}.json`, identical
config: seed 2025, 10 clients, 5 rounds, 2 local epochs, α=0.3. Yet:

| | FHE | no-FHE |
|---|---|---|
| accuracy | 0.5290 | 0.5806 |
| confusion matrix | `[[83105 70077],[27792 26818]]` | `[[100046 53136],[34020 20590]]` |
| training time | **262.2 s** | **435.9 s** |

**Why it matters**
`SimulatedCKKSVector` adds `N(0,1e-9)` noise to float32
(`federated/fhe_adapter.py:25-30`) and does nothing else. Two runs that differ
only by that should be near-identical. Instead the confusion matrices are
completely different, and the *encrypted* run finished **40% faster** than the
plaintext one — impossible if encryption only adds work.

Two things are happening:
1. Wall-clock timings are contaminated by background load on a shared laptop.
   They cannot be quoted as FHE overhead at all.
2. The 1e-9 perturbation sits near float32 ULP for small weights, and with a
   model that is barely above chance on VeReMi (AUC 0.525) the decision boundary
   is unstable enough for that to flip large numbers of predictions. The −5.16 pp
   "FHE cost" is chaotic divergence, not a property of encryption.

**Fix**
- Drop wall-clock time from the comparison entirely; cite `benchmark_real_ckks.py`
  for cost. That is what it is for.
- Set `precision_noise_std=0` for the equivalence run, and assert bitwise-identical
  aggregation between FHE and no-FHE paths. That proves what the simulation is
  actually able to prove: *the aggregation algebra is lossless.*
- Quote CKKS's real numerical effect from the measured
  `max_abs_error_vs_plaintext_fedavg ≈ 3e-8`, which is the honest number.
- Run ≥3 seeds before quoting any delta.

---

## D4 — Multi-Krum decrypts individual client updates server-side  🔴

**Evidence** — `federated/server.py:118-125`:
```python
for u in updates:
    param_dict = u["encrypted_model"]
    flat_params = np.concatenate([param_dict[name].decrypt() for name in sorted(param_dict.keys())])
```
The server calls `.decrypt()` on **every individual client's** parameters to
compute pairwise distances.

**Why it matters**
This is the exact capability the whole project exists to deny. The deck claims
*"maintaining zero plaintext exposure"* and *"the server never sees plaintext"*;
the code exposes every client's full update in plaintext on the server every
round. Under real (non-simulated) CKKS this code simply cannot run — the server
has no secret key.

*(Note: the server also decrypts the **aggregate** at `server.py:102` via
`inject_layerwise`. That one is defensible — FheFL's design has the server decrypt
the aggregate. Only the per-client decryption is a violation.)*

**Fix**
Replace Multi-Krum with FheFL's non-poisoning-rate scoring, which scores each
client by squared distance to the **previous global model** — already plaintext
at the server — so the whole computation stays homomorphic. See 06.

---

## D5 — VeReMi is not learning  🟠

**Evidence** — ROC-AUC 0.5251 (FHE) / 0.5240 (no-FHE) on 1,385,281 windows.
Per-class from `run_logs/veremi_fhe.log`: ATTACK precision 0.277, recall 0.491.

**Why it matters**
0.52 AUC is a coin flip. Presenting VeReMi alongside CAN-VTC's "100%" invites the
reviewer to conclude the pipeline is unreliable across the board.

**Likely cause**
V2X misbehaviour detection depends on kinematic plausibility — position/velocity
consistency, claimed vs. observed movement. Forcing that through a 46-D descriptor
designed for CAN ID/DLC/payload statistics discards the signal. The NewModel
README describes a dedicated VeReMi modality split (Kinematics, Speed Mag, Accel
Mag, Metadata) for MamKANformer; ChebyKAN's flat 46-input layer does not use it.

**Fix**
Diagnose before presenting. Train a plain gradient-boosted tree on the VeReMi
features as a floor — if that is also ~0.52, the features are the problem, not
the model. Then restore genuine kinematic features.

---

## D6 — Transport security was implemented, then removed  🟠

**Evidence**
- `Model/federated/secure_channel.py` — ECDH + AES-256-GCM + mutual auth, working.
- `NewModel/federated/server.py:64` — `"""Register client without secure
  handshakes (model is fully encrypted under FHE)."""`
- Deck slide 11: *"Handshakes, key exchanges, and symmetric transport encryption
  are completely removed."*

**Why it matters**
See 04 §12. FHE gives payload confidentiality only — no authentication, integrity,
replay protection, or Sybil resistance. And FheFL needs Diffie–Hellman anyway to
establish pairwise secrets.

**Fix** Restore `secure_channel.py` into the NewModel path. Correct the slide.

---

## D7 — Documentation drift  🟡

| File | Says | Reality |
|---|---|---|
| `Team/LG_IoV/GEMINI.md` | KANConvNet, Fourier basis, code in `Model/` | ChebyKAN, Chebyshev basis, code in `NewModel/` |
| `NewModel/config.yaml` | MamKANformer hyperparameters, `window`/`stride`/`n_features` | Federated path uses `ChebyshevKAN`; MamKANformer is unused |
| `NewModel/federated/server.py:3` | *"Manages homomorphic aggregation, TOPSIS ranking, and Multi-Krum"* | No TOPSIS anywhere in the file |
| `Team/LG_IoV/Reports/ROADMAP.md` | N ∈ {50,100,200}, R = 200–300, DP, GA, 15 runs | 10 clients, 5 rounds, no DP, no GA, 1 seed |

**Fix** Before the GitHub push: update GEMINI.md, delete or clearly mark the
MamKANformer branch as archived, remove the TOPSIS claim or implement it, and add
a "current scope vs. target scope" note to ROADMAP.md.

---

## Priority order

| | Defect | Effort | Blocks |
|---|---|---|---|
| 1 | D1 labels | 1–2 days | Every accuracy number |
| 2 | D2 window leakage | 1 day | Every accuracy number |
| 3 | D4 Multi-Krum decryption | folded into the FheFL work | The core privacy claim |
| 4 | D3 comparison methodology | hours | The FHE-cost story |
| 5 | D6 transport security | hours (restore existing file) | Security narrative |
| 6 | D5 VeReMi | 2–3 days diagnosis | One of four datasets |
| 7 | D7 docs | hours | GitHub readiness |

D1 and D2 must be fixed **before** any further model work — every number
generated until they are fixed will have to be thrown away.

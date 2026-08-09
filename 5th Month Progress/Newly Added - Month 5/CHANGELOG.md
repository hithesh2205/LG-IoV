# Newly Added / Changed — Month 5

Everything in this folder was created or substantially rewritten during Month 5.
The **latest working version of every file also lives in
`../Complete Source Code/NewModel_active/`** — this folder is the record of
*what changed*, not a second copy of the system.

---

## 1. New files

### Cryptography

| File | Purpose |
|---|---|
| `federated/multikey_ckks.py` | **New.** FheFL distributed multi-key key sharing — additive shares, antisymmetric pairwise masks, server-side reconstruction (eq. 10), and the per-round mask re-scoping that fixes the paper's dropout failure. |
| `federated/secure_channel.py` | **Restored** from generation 1. ECDH-P256 + AES-256-GCM + Ed25519 mutual authentication. Had been deleted in Month 4. |

### Tests

| File | Purpose |
|---|---|
| `tests/test_data_pipeline.py` | **New.** 25 assertions on labelling, window/block containment, split disjointness, VeReMi label survival. |
| `tests/test_crypto.py` | **New.** 32 assertions on backend equivalence, real CKKS round-trip, eq. 11 correctness, mask cancellation, dropout detection, channel integrity, audit invariant, non-poisoning rates. |

### Scripts

| File | Purpose |
|---|---|
| `scripts/benchmark_ckks_profiles.py` | **New.** Measures both disclosure profiles including the ciphertext×ciphertext multiply. Supersedes `benchmark_real_ckks.py`, which measured addition only. |
| `scripts/run_all_experiments.py` | **New.** Full sweep: 4 datasets × 2 backends × 3 seeds. |
| `scripts/generate_diagrams.py` | **New.** Generates all six figures as PNG + SVG. |
| `scripts/build_master_pdf.py` | **New.** Builds the master documentation PDF from live results. |
| `scripts/content.py` | **New.** Text content of the PDF. |

### Documentation

`Documentation/01`–`12` plus the master PDF. Documents 08, 09 and 10 are the
three overdue LG deliverables.

---

## 2. Substantially rewritten files

| File | What changed | Defect |
|---|---|---|
| `data/car_hack_dataset.py` | Uses the HCRL `R/T` flag as ground truth instead of discarding it and labelling by filename. Counts and drops malformed rows. | **D1** |
| `data/can_vtc_dataset.py` | Derives DoS labels from the `0x000` injection signature. Excludes Fuzzy/Impersonation, which have no recoverable ground truth, rather than mislabelling them. Legacy path retained behind a flag with a loud warning. | **D1** |
| `data/veremi_dataset.py` | Replaced cross-sender windowing with per-beacon plausibility features. Added sender-grouped windowing that activates automatically if a sender column is present. | **D5** |
| `data/can_features.py` | `windows_from_stream` now returns `(X, y, groups)`; windows are emitted only when fully inside one contiguous block. Added `report_window_purity` saturation warning. | **D1, D2** |
| `data/cicids_dataset.py` | Emits `groups` for a uniform interface. | D2 |
| `data/preprocess.py` | Replaced the random per-window shuffle with a group-aware split assigning whole blocks to one split. Added `assert_no_group_overlap` and a missing-class warning. | **D2** |
| `data/build_dataset.py` | Was a full duplicate of the loading/splitting/scaling logic with its own leaky splitter. Now delegates to `PreprocessingPipeline` — one implementation. | D2, D7 |
| `data/loader.py` | Fixed a missing `Tuple` import that only survived via lazy annotations. | — |
| `federated/fhe_adapter.py` | Removed `SimulatedCKKSVector` (numpy + 1e-9 noise). Added real TenSEAL `CKKSVector`, noiseless `PlaintextVector`, `EncryptedScalar`, and `encrypted_sq_distance` implementing eq. 11. Three explicit backends. | **D3** |
| `federated/server.py` | Removed the Multi-Krum filter that decrypted every individual client update. Implemented FheFL non-poisoning-rate aggregation. Added `AggregationAudit` and `assert_no_individual_decryption`. | **D4** |
| `federated/client.py` | Whole-vector encryption instead of per-tensor. Plaintext broadcast (the global model is not secret). Wired through the secure channel. | D4, D6 |
| `federated/__init__.py` | Exports the new crypto surface. | — |
| `train_federated.py` | Backend selection, multi-seed runs with mean ± std, secure-channel handshakes, audit assertions, richer result JSON. | **D3** |
| `evaluate.py` | Updated to the group-aware split API. | D2 |
| `config.yaml` | Corrected header (was "MamKANformer"); added federated and crypto sections. | **D7** |
| `../GEMINI.md` | Rewritten — described generation 1 for ~3 months. Now documents the actual architecture plus four invariants. | **D7** |
| `../Reports/ROADMAP.md` | Added an explicit scope-reconciliation table: roadmap target vs what actually runs. | **D7** |

---

## 3. Removed

| Item | Why |
|---|---|
| `SimulatedCKKSVector` | Not encryption — numpy plus N(0,1e-9) noise, below float32 ULP. It also made the FHE/no-FHE comparison uncontrolled. |
| Multi-Krum filter | Structurally requires decrypting individual client updates; impossible under real FHE and fatal to the privacy claim. |
| Duplicate `_stratified_split` in `build_dataset.py` | Second, leaky implementation that had diverged from the canonical one. |
| Duplicate `CanFeatureDataset` in `build_dataset.py` | Two definitions of the same class. |
| Silent fallback in the `strict` disclosure profile | See below. |
| Stale Month-4 scripts (7 files) | Referenced removed APIs and would fail if run. Moved to `_legacy_month4/` with a README explaining why their outputs are invalid. |

### A defect introduced and caught within Month 5

The first revision of the new server accepted `disclosure="strict"` and quietly
fell back to revealing **both** the distance sum **and** the individual
distances — strictly *more* disclosure than the `practical` profile, while its
docstring claimed strictly less.

That is the same class of defect as the Month-4 Multi-Krum filter: a mode
advertising a privacy property it does not deliver. It was caught during
self-review, before any result was reported with it.

The fix was not to paper over it. `strict` now raises `NotImplementedError`
carrying the measured cost of what it would take to build
(N=16384, 836.1 KB per ciphertext against 326.6 KB, 67.7 ms per distance against
18.0 ms), and `tests/test_crypto.py` asserts the refusal so it cannot silently
return.

### A second one: smoke runs overwrote real results

`train_federated.py` wrote to `results/federated_<dataset>_<backend>.json`
regardless of whether `--smoke` was passed. A smoke run is 1 round, 1 seed, on a
row-capped subset — so testing the new packing module silently replaced the real
**3-seed** `car_hack/ckks` result (0.9976 ± 0.0013) with a **1-seed** smoke
number (0.9990 ± 0.0000).

It was caught by `verify_snapshot.py`'s `3 seeds per cell` check, which is
exactly the kind of thing that check exists for. Fixed by tagging smoke output
`_smoke`, for both result JSONs and checkpoints, and the affected cell was
re-run properly.

**Both of these are recorded deliberately.** A changelog that only lists other
people's mistakes is not a changelog — and in both cases the value was in the
guard firing, not in the mistake being avoided.

---

## 4. New results

| File | Contents |
|---|---|
| `results/month5_summary.json` | Full sweep: 4 datasets × 2 backends × 3 seeds |
| `results/federated_<dataset>_<backend>.json` | Per-cell results with per-round logs and audit counters |
| `results/ckks_profile_benchmark.json` | Measured cost of both disclosure profiles |

Month-4 results are preserved in `../Results/month4_legacy_INVALID/`. They are
retained for provenance and **must not be re-reported** — they were produced
with filename labels, a leaky split and simulated encryption.

---

## 5. New diagrams

`01_system_architecture` · `02_fhefl_round_protocol` ·
`03_data_pipeline_and_defects` · `04_multikey_sharing` ·
`05_ckks_profile_tradeoff` · `06_month5_results` — each as PNG and SVG.

---

## 6. Verification

```bash
python tests/test_data_pipeline.py
```

```bash
python tests/test_crypto.py
```

```bash
python tests/test_ntt.py
```

105 assertions total, all passing at the time of writing.

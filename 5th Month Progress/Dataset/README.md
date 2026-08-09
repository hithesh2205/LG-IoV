# Dataset Manifest

## Why the data is referenced, not copied

The preprocessed corpus is **8.6 GB** — VeReMi alone is 6.9 GB. Duplicating it
into this snapshot would make the folder unusable for review, email or Git
(GitHub rejects files over 100 MB and the whole corpus far exceeds any
reasonable repository size).

The canonical copy lives at:

```
Team/LG_IoV/Preprocessed_Dataset/
```

Every loader resolves paths relative to that directory via `DATA_ROOT` in
`train_federated.py` and `train.py`, so the code in
`Complete Source Code/NewModel_active/` runs directly against it with no
changes.

---

## Inventory

| Dataset | Folder | Size | Files | Records |
|---|---|---:|---:|---|
| IEEE VTC-CAN | `Can_vtc_pro/` | 227.7 MB | 4 | ~4.6 M CAN messages |
| Car-Hacking (HCRL) | `Car_hack_pro/Car_hack_pro/` | 569.8 MB | 5 | ~17 M CAN messages |
| CICIDS-2017 | `CICIDS_pro/CICIDS_pro/` | 908.5 MB | 8 | ~2.8 M flow records |
| VeReMi | `VeReMi_pro/` | 6,919.4 MB | 1 | ~24 M beacon receptions |
| **Total** | | **8.6 GB** | 18 | |

---

## Per-dataset detail

### 1. IEEE VTC-CAN — `Can_vtc_pro/`

Format: `ID: <hex>    000    DLC: <n>    <up to 8 hex bytes>`

| File | Messages (first 3 M sampled) | Ground truth |
|---|---|---|
| `cleaned_Attack_free_dataset.csv` | 2,369,398 | all normal |
| `cleaned_DoS_attack_dataset.csv` | 656,579 | **recoverable** — CAN ID `0x000` |
| `cleaned_Fuzzy_attack_dataset.csv` | 591,990 | ✗ not recoverable |
| `cleaned_Impersonation_attack_dataset.csv` | 995,472 | ✗ not recoverable |

**Measured ID census** (attack captures vs the 45 IDs in attack-free):

| Capture | Novel IDs | Share of traffic |
|---|---|---|
| DoS | 1 (`0x000`) | **51.1 %** |
| Fuzzy | 0 | 0.0 % |
| Impersonation | 0 | 0.0 % |

Fuzzy and Impersonation inject on *legitimate* CAN IDs, so no per-message label
survives the cleaning step. They are **excluded by default** — including them
would require filename labelling, which is defect D1. Loaded as a **2-class**
problem (normal vs DoS).

⚠️ At 51.1 % injection density every 64-message window contains an injected
frame, so the DoS capture separates trivially from the clean capture. Near-perfect
accuracy on CAN-VTC measures *flood detection*, not generalisation. The loader
prints a `report_window_purity` warning to keep this visible in every run log.

### 2. Car-Hacking (HCRL) — `Car_hack_pro/Car_hack_pro/`

**The primary CAN benchmark**, because it retains per-message ground truth.

Format: `id_hex, dlc, b0..b7, R/T` — field 11 is the label
(`R` = regular, `T` = injected).

| File | Class | Injection rate (measured, 120 k sample) | Malformed rows dropped |
|---|---|---:|---:|
| `cleaned_normal_run_data.csv` | normal | 0.0 % | 0 |
| `cleaned_DoS_dataset.csv` | DoS | 24.3 % | 876 |
| `cleaned_Fuzzy_dataset.csv` | Fuzzy | 12.7 % | 6,510 |
| `cleaned_RPM_dataset.csv` | RPM | 19.0 % | 1,021 |
| `cleaned_gear_dataset.csv` | gear | 18.5 % | 1,036 |

At 12–24 % density each attack capture produces **both** normal and attack
windows — the realistic setting, and why this dataset is the meaningful one.

Malformed rows (trailing field neither `R` nor `T`) are counted and dropped, never
coerced into a class.

### 3. CICIDS-2017 — `CICIDS_pro/CICIDS_pro/`

Eight daily captures of enterprise IP flow records, 78 numeric columns plus a
`Label` column. 46 columns are selected to match the unified feature contract.
Each row is an independent flow with its own label, so this adapter never
suffered the window-overlap problem.

Included as a sanity/transfer dataset — it is **not vehicular traffic**, and
results on it say nothing directly about IoV performance.

### 4. VeReMi — `VeReMi_pro/`

One 6.9 GB CSV, 20 columns, ~24 M beacon reception events.

```
type, rcvTime,
pos_0, pos_1, pos_noise_0, pos_noise_1,
spd_0, spd_1, spd_noise_0, spd_noise_1,
acl_0, acl_1, acl_noise_0, acl_noise_1,
hed_0, hed_1, hed_noise_0, hed_noise_1,
attack, attack_type
```

Measured over a 2 M-row sample:

- `attack`: 1,094,690 benign / 905,310 attack — **45.3 % attack**, well balanced
- `attack_type`: 19 classes, near-uniform (102 k–113 k each)
- `rcvTime` is **not** monotonic (25202 → 54198 with reversals)

**Missing:** there is no sender/node identifier — it was dropped during cleaning.
This is why the Month-4 windowed formulation failed: consecutive rows are beacons
from *different* senders, so windowing averaged kinematics across unrelated
vehicles. Loaded per-beacon instead (defect D5).

To restore sender-grouped windowing, re-acquire raw VeReMi from
<https://github.com/josephkamel/VeReMi-Dataset> preserving the sender column;
`veremi_dataset.py` already implements `mode="windowed"` and will use it
automatically once the column is present.

---

## Regenerating from raw

The cleaning scripts that produced `Preprocessed_Dataset/` are in
`Complete Source Code/NewModel_active/data/` (per-dataset adapters) and
`Model_gen1_archived/scripts/clean_remaining_features.py`.

Raw sources:

| Dataset | Source |
|---|---|
| Car-Hacking | HCRL, Korea University — <https://ocslab.hksecurity.net/Datasets/car-hacking-dataset> |
| IEEE VTC-CAN | HCRL survival-analysis dataset |
| CICIDS-2017 | Canadian Institute for Cybersecurity — <https://www.unb.ca/cic/datasets/ids-2017.html> |
| VeReMi | <https://github.com/josephkamel/VeReMi-Dataset> |

---

## Integrity check

```bash
python tests/test_data_pipeline.py
```

Verifies that labels come from per-message ground truth, that no window crosses
a block boundary, that splits share no blocks, and that the VeReMi attack share
is preserved. 25 assertions; all must pass before any result is reported.

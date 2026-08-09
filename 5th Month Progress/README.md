# 5th Month Progress — Complete Project Snapshot

**Privacy-Preserving Collaborative Intrusion Detection for the Internet of Vehicles**
Federated learning with multi-key CKKS homomorphic encryption

LG Soft India · 12-month industry project · **snapshot at end of Month 5** · 2026-08-08

---

## What this folder is

The **complete project from Month 1 through Month 5** — source code,
documentation, decks, results, models, diagrams and experiments — organised so
that someone who has never seen the project can read it, run it, and understand
exactly where it stands.

It is not a Month-5-only folder. Everything needed to understand or run the
system is here.

---

## Start here

1. **`Documentation/00_MASTER_DOCUMENTATION.pdf`** — the primary document. Explains
   the project from zero, defines every technical term where it first appears,
   walks through months 1–5, presents the results, and states what remains.
2. `Documentation/11_current_status.md` — where the project stands today.
3. `Documentation/12_next_steps.md` — what to do next, in priority order.

---

## Layout

```
5th Month Progress/
├── README.md                          ← you are here
│
├── Documentation/                     ← 2 PDFs + 16 markdown documents
│   ├── 00_MASTER_DOCUMENTATION.pdf    ← START HERE
│   ├── 00_README_documentation_index.md
│   ├── 01-07  audit trail (written during the Month-5 audit)
│   ├── 08_threat_model.md             ← overdue LG deliverable, now delivered
│   ├── 09_security_specification.md   ← overdue LG deliverable, now delivered
│   ├── 10_library_evaluation.md       ← overdue LG deliverable, now delivered
│   ├── 11_current_status.md
│   ├── 12_next_steps.md
│   ├── 13_why_AES_with_FHE.pdf        ← design note: why both layers are needed
│   ├── 14_packing_and_encoding.md     ← overdue LG deliverable, now delivered
│   ├── 15_ntt_implementation.md       ← overdue LG deliverable, reference done
│   └── 16_hardware_baseline.md        ← overdue LG deliverable, harness done
│
├── Complete Source Code/
│   ├── NewModel_active/               ← THE CURRENT SYSTEM — run this
│   ├── Model_gen1_archived/           ← generation 1 (KANConvNet), reference only
│   └── ArchitectureViewer_web/        ← React architecture visualiser
│
├── Newly Added - Month 5/             ← ONLY what changed in Month 5
│   ├── CHANGELOG.md                   ← new / rewritten / removed, defect by defect
│   └── code/                          ← the 24 new and rewritten files
│
├── Month 1-2 Foundation/              ← decks, reports, Phase-1 checkpoints
├── Month 3-4 FHE and Architecture/    ← FHE study, CKKS mathematics, ChebyKAN pivot
│
├── Dataset/README.md                  ← manifest + provenance (8.6 GB referenced, not copied)
├── Models/                            ← trained checkpoints
├── Experiments/                       ← benchmark + sweep scripts, test suites
├── Results/                           ← Month-5 results; Month-4 marked INVALID
└── Diagrams/                          ← all figures, PNG + SVG
```

**Why the dataset is referenced rather than copied:** the corpus is 8.6 GB
(VeReMi alone is 6.9 GB). Copying it would make this folder unusable for review
or Git. The canonical copy is at `Team/LG_IoV/Preprocessed_Dataset/` and the code
resolves it automatically. Full inventory and re-acquisition instructions are in
`Dataset/README.md`.

---

## Running it

```bash
cd "Complete Source Code/NewModel_active"
```

Verify the experimental setup is sound (105 assertions — run these first):

```bash
python tests/test_data_pipeline.py
```

```bash
python tests/test_crypto.py
```

```bash
python tests/test_ntt.py
```

Train with real CKKS encryption, three seeds:

```bash
python train_federated.py --dataset car_hack --backend ckks --seeds 2025 2026 2027
```

The plaintext baseline for comparison:

```bash
python train_federated.py --dataset car_hack --backend none --seeds 2025 2026 2027
```

Full sweep, benchmarks, diagrams and this PDF:

```bash
python scripts/run_all_experiments.py
```

---

## Month 5 in one paragraph

Month 5 began as an investigation into multi-key CKKS and became an audit-then-fix
month. The audit found that the "encryption" used during training was numpy plus
1e-9 noise; that the Byzantine filter decrypted every individual client update,
voiding the central privacy claim; that CAN datasets were labelled by filename
rather than ground truth, which is why CAN-VTC reported 100 % accuracy; that
overlapping windows were split randomly across train and test; that VeReMi was at
chance level; and that transport security had been deleted. **All seven defects
are fixed and machine-verified.** On top of that, real CKKS encryption, FheFL
encrypted-domain robust aggregation, and distributed multi-key key sharing with a
fix for the paper's dropout failure were implemented, and the three overdue LG
documentation deliverables were written.

---

## Honest boundaries

Stated up front so nothing downstream reads as an overclaim:

- **This is not full multi-key CKKS.** The homomorphic arithmetic is real; the
  multi-key *key management* is an algebraic model, because TenSEAL exposes no
  multi-key API. Migrating to OpenFHE closes this and is the Month-6 priority.
- **Nothing has run on target hardware.** The NTT reference, the packing module
  and the benchmark harness are built and validated, but every number was
  measured on a development laptop. No board has been ordered — and both
  remaining partial deliverables are blocked on exactly that and nothing else.
- **Byzantine robustness is unproven against patient attackers.** The scoring
  function rewards staying close to consensus, so a low-magnitude persistent
  attacker is an open blind spot.
- **CAN-VTC results measure flood detection, not generalisation** — its DoS
  injection runs at 51.1 % density, saturating every window. Car-Hacking is the
  meaningful CAN benchmark.
- **VeReMi results are a near-chance lower bound.** Its attack types are defined
  by how a sender's claims evolve over time, and the cleaned export has no sender
  ID — so neither windowing (mixes senders) nor per-beacon (loses the temporal
  signal) can express the task. Measured best single-feature separation is 0.046σ.
  The dataset must be re-acquired with sender IDs.
- **The Month-4 results in `Results/month4_legacy_INVALID/` must not be
  re-reported.** They are kept for provenance only.

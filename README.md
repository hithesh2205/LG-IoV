# LG-IoV — Privacy-Preserving Collaborative IDS for the Internet of Vehicles

Federated learning with CKKS homomorphic encryption and Byzantine-robust
aggregation performed **inside the encrypted domain**.

LG Soft India · 12-month industry project · **snapshot: end of Month 5**

---

## Start here

**[`5th Month Progress/Documentation/00_MASTER_DOCUMENTATION.pdf`](5th%20Month%20Progress/Documentation/)** —
27 pages, written to be read start to finish by someone who has never seen the
project. Every technical term is explained where it first appears.

| Then | For |
|---|---|
| [`5th Month Progress/README.md`](5th%20Month%20Progress/) | The complete Month 1–5 snapshot |
| `Documentation/11_current_status.md` | Where the project stands today |
| `Documentation/12_next_steps.md` | Prioritised roadmap |
| `Complete Source Code/NewModel_active/` | **The runnable system** |

---

## What the system does

Vehicles train an intrusion detector on their own CAN/V2X logs and upload only
**encrypted** model updates. The aggregation server measures how far each
encrypted update sits from the consensus — *without decrypting it* — down-weights
the outliers, sums everything homomorphically, and decrypts only the total.

The decryption key is split across vehicles so no single party, including the
server, can decrypt any individual contribution.

```
Vehicle ──[encrypted update]──▶ RSU ──▶ Server
   ▲                                      │
   └──────[plaintext global model]────────┘
```

---

## Results

3 seeds, 10 simulated vehicles, 5 federated rounds, Dirichlet α = 0.3.

| Dataset | CKKS encrypted | Plaintext baseline | Difference |
|---|---|---|---|
| CAN-VTC | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 0.0000 |
| **Car-Hacking** | **0.9977 ± 0.0012** | **0.9981 ± 0.0006** | −0.0004 |
| CICIDS-2017 | 0.9555 ± 0.0079 | 0.9542 ± 0.0098 | +0.0013 |
| VeReMi | 0.4839 ± 0.0433 | 0.4851 ± 0.0424 | −0.0012 |

**Encryption costs no accuracy** — every difference sits inside seed variance,
and the audit counter records **zero** individual-update decryptions across all
runs.

---

## Read the numbers honestly

- **Car-Hacking is the meaningful CAN benchmark.** Its 12–24 % injection density
  means each capture yields both normal and attack windows.
- **CAN-VTC measures flood detection, not generalisation.** Its DoS runs at 51 %
  density, and one feature (dominant-ID frequency) separates it perfectly on its own.
- **VeReMi is a near-chance lower bound.** Its attacks are defined by how a
  sender's claims evolve over time, and the cleaned export has no sender ID.
  Measured best single-feature separation: 0.046σ. Needs re-acquisition.

---

## Running it

```bash
cd "5th Month Progress/Complete Source Code/NewModel_active"
```

Verify the experimental setup first — 105 assertions across three suites:

```bash
python tests/test_data_pipeline.py && python tests/test_crypto.py && python tests/test_ntt.py
```

Then train:

```bash
python train_federated.py --dataset car_hack --backend ckks --seeds 2025 2026 2027
```

---

## Datasets are not in this repository

The corpus is **8.6 GB** (VeReMi alone is 6.9 GB) and eleven files exceed
GitHub's 100 MB limit. Full inventory, measured properties and re-acquisition
instructions: [`5th Month Progress/Dataset/README.md`](5th%20Month%20Progress/Dataset/).

---

## Honest boundaries

Stated up front so nothing below reads as an overclaim:

- **This is not full multi-key CKKS.** The homomorphic arithmetic is real
  (TenSEAL); the multi-key *key management* is an algebraic model, because
  TenSEAL exposes no multi-key API. Migrating to OpenFHE closes this.
- **Nothing has run on target hardware.** The NTT reference, packing module and
  benchmark harness are built and validated, but every number was measured on a
  development laptop.
- **Byzantine robustness is unproven against patient attackers.** The scoring
  function rewards staying close to consensus, so a low-magnitude persistent
  attacker is an open blind spot.
- **Month-4 results in `Results/month4_legacy_INVALID/` must not be re-reported.**
  They were produced with filename labels, a leaky split and simulated
  encryption, and are kept for provenance only.

---

## Repository layout

```
5th Month Progress/     ← the complete Month 1–5 snapshot (start here)
Team/LG_IoV/            ← working tree: NewModel (live), Model (gen 1 archived)
FHE_Comparison/         ← FHE vs no-FHE comparison results and HTML explainers
Base line/              ← React architecture visualiser
compare/                ← deck extraction utilities
*.pdf, *.pptx           ← meeting decks and reference papers
```

## Licence

Internal LGSI project deliverable. Third-party datasets remain under their
original licences — see the dataset manifest.

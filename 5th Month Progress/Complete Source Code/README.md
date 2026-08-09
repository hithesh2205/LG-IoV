# Complete Source Code

Four code trees are present. **Only one is live.**

| Folder | Generation | Status | Use it for |
|---|---|---|---|
| **`NewModel_active/`** | Gen 3 (current) | ✅ **LIVE — run this** | All development and all reported results |
| `Model_gen1_archived/` | Gen 1, Month 1–2 | 📦 Archived | Reference: KANConvNet, TOPSIS + Multi-Krum, GA search, Phase-1 setup |
| `_archived_prototypes/ChebyKAN_FHE/` | Gen 2 prototype, Month 3–4 | 📦 Archived | Reference: first standalone ChebyKAN + FHE experiment |
| `_archived_prototypes/CHEBYKANDEMO/` | Gen 2 prototype, Month 3–4 | 📦 Archived | Reference: the demo variant of the same |
| `ArchitectureViewer_web/` | — | 🔧 Tool, **content is Month 3–4** | React/xyflow interactive architecture diagram |

> ⚠️ **`ArchitectureViewer_web/` shows the Month 3–4 architecture**, including the
> MamKANformer trunk and the layer-wise simulated-FHE flow. It has not been
> updated for the Month-5 design (ChebyKAN, real CKKS, FheFL aggregation,
> multi-key sharing). For the current architecture use the figures in
> `../Diagrams/` or the master PDF. Refreshing the viewer is a small task and is
> not on the critical path.

---

## Why the archives are kept

They are the record of how the design arrived where it is, and several decisions
only make sense against them:

- `Model_gen1_archived/` contains `federated/secure_channel.py`, which was
  deleted from the active tree in Month 4 and **restored from here** in Month 5.
- It also contains the TOPSIS + Multi-Krum aggregator and GA search described in
  `ROADMAP.md` but deliberately not carried forward — see the scope-reconciliation
  table at the top of that file.
- The Gen-2 prototypes show the ChebyKAN architecture before it was integrated
  into the unified pipeline.

**Do not extend the archives.** They use the old dataset adapters with filename
labelling (defect D1) and the old random splitter (defect D2), so any result they
produce is invalid. They are frozen deliberately.

---

## Running the live tree

```bash
cd NewModel_active
```

Verify the experimental setup first — 105 assertions:

```bash
python tests/test_data_pipeline.py
```

```bash
python tests/test_crypto.py
```

```bash
python tests/test_ntt.py
```

Then train:

```bash
python train_federated.py --dataset car_hack --backend ckks --seeds 2025 2026 2027
```

---

## Layout of `NewModel_active/`

```
NewModel_active/
├── config.yaml                  model / data / federated / crypto settings
├── train.py                     centralized training
├── train_federated.py           federated training  ← main entry point
├── evaluate.py                  standalone evaluation
├── data/
│   ├── can_features.py          46-D extractor + block-safe windowing
│   ├── can_vtc_dataset.py       signature-derived DoS labels
│   ├── car_hack_dataset.py      R/T ground-truth labels
│   ├── cicids_dataset.py        flow records
│   ├── veremi_dataset.py        per-beacon plausibility features
│   ├── preprocess.py            group-aware split + scaling
│   ├── build_dataset.py         thin wrapper over preprocess
│   └── loader.py                Dataset / DataLoader
├── models/
│   ├── cheby_kan.py             ChebyshevKAN — the live model
│   └── mamkanformer*.py         archived Month-3 branch, unused
├── federated/
│   ├── client.py                vehicle: train, encrypt, upload
│   ├── server.py                FheFL aggregation + audit invariant
│   ├── fhe_adapter.py           ckks / exact / none backends
│   ├── multikey_ckks.py         FheFL key sharing + dropout fix
│   ├── secure_channel.py        ECDH + AES-256-GCM + Ed25519
│   └── partition.py             Dirichlet non-IID sharding
├── crypto/ntt.py                negacyclic NTT reference + test vectors
├── tests/                       105 correctness assertions
└── scripts/                     benchmarks, sweep, diagrams, PDF build
```

---

## The four invariants

Any change that breaks one of these invalidates every metric the pipeline
produces. They are enforced by the test suites, not by convention.

1. **Labels come from per-message ground truth, never a filename.**
2. **Whole blocks go to exactly one split** — windows overlap 75 %.
3. **The server never decrypts an individual client update.**
4. **The `exact` and `none` backends stay bitwise identical.**

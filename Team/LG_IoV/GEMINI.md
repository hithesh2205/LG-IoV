# LG-IoV — Project Instructions

Privacy-preserving collaborative intrusion detection for the Internet of
Vehicles: federated learning over vehicular datasets, with model updates
protected by CKKS homomorphic encryption and robust aggregation that runs in the
encrypted domain.

> **Currency:** rewritten 2026-08-08 (Month 5). The previous version of this file
> described the Month-1 generation (KANConvNet, Fourier basis, `Model/`) and had
> been stale for roughly three months. If anything below disagrees with the code,
> the code is right — file an issue.

## Current architecture

- **Classifier:** ChebyshevKAN — Kolmogorov–Arnold network with Chebyshev
  polynomial basis. 44,164 parameters (5-class configuration).
- **Federated aggregation:** FheFL non-poisoning-rate weighting
  (arXiv:2306.05112 eq. 6–12), computed on ciphertexts.
- **Encryption:** real CKKS via TenSEAL, plus an algebraic model of FheFL's
  distributed multi-key sharing. Migrating to OpenFHE — see
  `Documentation/10_library_evaluation.md`.
- **Transport:** ECDH-P256 + AES-256-GCM + Ed25519 mutual auth.
- **Data:** 46-feature vectors over four datasets (CAN-VTC, Car-Hacking,
  CICIDS-2017, VeReMi).

## Code layout

| Path | Contents |
|---|---|
| `NewModel/` | **Active generation.** All current work happens here |
| `NewModel/data/` | Dataset adapters + preprocessing + group-aware splitting |
| `NewModel/models/` | ChebyshevKAN (`cheby_kan.py`) and the archived MamKANformer branch |
| `NewModel/federated/` | Client, server, CKKS adapter, multi-key layer, secure channel |
| `NewModel/tests/` | Correctness tests for the data and crypto layers |
| `NewModel/scripts/` | Benchmarks and the experiment sweep |
| `Model/` | **Generation 1, archived.** KANConvNet + TOPSIS/Multi-Krum + GA. Kept for reference; do not extend |

## Workflows

Run everything from `NewModel/`.

```bash
python tests/test_data_pipeline.py
```

```bash
python tests/test_crypto.py
```

```bash
python train_federated.py --dataset car_hack --backend ckks --seeds 2025 2026 2027
```

```bash
python scripts/benchmark_ckks_profiles.py
```

**Always run both test scripts after touching the data or crypto layers.** They
assert the experimental setup is sound (no label leakage, no window leakage, no
individual-update decryption); if they fail, every metric the pipeline produces
is meaningless.

## Invariants — do not break these

1. **Labels come from per-message ground truth, never from a filename.** The
   Car-Hacking `R/T` flag and the CAN-VTC `0x000` DoS signature are the sources
   of truth. Filename labelling turns intrusion detection into capture-file
   identification.
2. **Whole blocks go to exactly one split.** Windows overlap by 75 %, so a random
   per-window split leaks. `assert_no_group_overlap` enforces this.
3. **The server never decrypts an individual client update.**
   `assert_no_individual_decryption` runs every round.
4. **`exact` and `none` backends must stay bitwise identical.** That is what
   makes the FHE comparison controlled. Never inject noise into a backend to
   "simulate" encryption.

## Conventions

- Python ≥ 3.12, PEP 8, `torch >= 2.3`.
- Model/training hyperparameters in `NewModel/config.yaml`.
- Results are written to `NewModel/results/` as JSON; checkpoints to
  `NewModel/checkpoints/`.
- Multi-seed runs are the default for anything reported. Single-seed numbers are
  for debugging only.

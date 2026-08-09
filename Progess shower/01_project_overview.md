# 01 — Project Overview

## Problem

Vehicles in an IoV fleet observe attack traffic that other vehicles have not
seen. Pooling raw CAN/V2X logs to a central server would give a much stronger
intrusion detector, but the logs are privacy-sensitive (location, driving
behaviour, vehicle identity) and cannot leave the vehicle.

Federated learning solves the raw-data problem but not the gradient problem: a
semi-honest aggregation server can invert model updates to recover training
data. Encrypting the updates fixes that but blinds the server to poisoning
attacks. The project's goal is a system that resists **both** at once.

## Target architecture

```
Vehicle i                          Aggregation server
─────────                          ──────────────────
local CAN/V2X log
   │
   ├─ 46-D window features
   ├─ local ChebyKAN training
   ├─ encrypt update under CKKS  ──────►  robust filter (encrypted domain)
   │                                       homomorphic weighted aggregation
   └─ decrypt new global model  ◄──────  aggregate only, never individuals
```

## Component status

| Component | Where | Status |
|---|---|---|
| Dataset adapters (4 sources → 46-D) | `NewModel/data/` | Working, **labelling defect** (see 05) |
| Preprocessing (clip, z-score, split) | `NewModel/data/preprocess.py` | Working, **split defect** (see 05) |
| ChebyKAN classifier (44,164 params) | `NewModel/models/cheby_kan.py` | Working |
| Non-IID Dirichlet sharding (α=0.3) | `NewModel/federated/partition.py` | Working |
| FL client loop | `NewModel/federated/client.py` | Working |
| Multi-Krum robust filter | `NewModel/federated/server.py` | Working but **not FHE-compatible** |
| Homomorphic aggregation | `NewModel/federated/fhe_adapter.py` | **Simulated only** (numpy) |
| Real CKKS cost benchmark | `NewModel/benchmark_real_ckks.py` | Working, genuine TenSEAL |
| Secure transport (ECDH + AES-GCM) | `Model/federated/secure_channel.py` | **Built then dropped** |
| Multi-key / threshold CKKS | — | Not started (this is the current work) |
| Embedded port, quantization, NTT | — | Not started |

## Datasets

| Dataset | Task | Windows | Classes |
|---|---|---|---|
| IEEE VTC-CAN | CAN bus intrusion | — | 4 (free, DoS, fuzzy, impersonation) |
| Car-Hacking (HCRL) | CAN bus intrusion | — | 5 (normal, DoS, fuzzy, RPM, gear) |
| CICIDS-2017 | IP flow intrusion | — | binary |
| VeReMi | V2X misbehaviour | 1,385,281 | binary |

All four are mapped into a shared 46-dimension "timeless" feature vector
(`NewModel/data/can_features.py`) so one model architecture serves every source.

## Two code generations

The repository contains two model generations. This is a source of confusion and
should be resolved before the GitHub push.

- **`Team/LG_IoV/Model/`** — first generation. KANConvNet classifier, TOPSIS +
  Multi-Krum aggregation, GA hyperparameter search, ECDH/AES secure channels,
  designed for N ∈ {50,100,200} clients and 200–300 rounds
  (`Team/LG_IoV/Reports/ROADMAP.md`).
- **`Team/LG_IoV/NewModel/`** — current generation. MamKANformer, then narrowed
  to ChebyKAN. 10 clients, 5 rounds, no secure channel, no TOPSIS, no GA.

The second generation is the one being demonstrated, but it implements *less* of
the roadmap than the first. `Team/LG_IoV/GEMINI.md` still describes generation 1
(KANConvNet, Fourier basis, `Model/` layout) and is stale.

## Reference material in-repo

- `LG_Expectations_IDS.pdf` — the contractual 12-month deliverable schedule
- `Fed-Iov.pdf`, `FedIoV_Paper_Analysis.pdf` — source paper for generation 1
- `MamKanformer_...pdf` — source paper for the MamKANformer trunk
- `Math Behinf the CKKS Homomorphic encryption.PDF` — CKKS background
- `2306.05112v1.pdf` (FheFL) — the multi-key CKKS paper now being adopted

# FedIoV — Implementation Roadmap

> ## ⚠️ Scope reconciliation (added Month 5, 2026-08-08)
> **This document describes the Month-1 *target* design, not what currently
> runs.** It was written for the first-generation KANConvNet system and has not
> been amended since. The gap is recorded here rather than left for a reviewer
> to discover.
>
> | Item | This roadmap | Actually implemented (Month 5) |
> |---|---|---|
> | Classifier | KANConvNet | **ChebyshevKAN** (44,164 params) |
> | Clients N | 50 / 100 / 200 | **10** |
> | Rounds R | 200 (N≤100), 300 (N=200) | **5** |
> | Aggregation | TOPSIS → Multi-Krum, m=5 | **FheFL non-poisoning rate** (Multi-Krum was removed — it required decrypting individual updates, defect D4) |
> | GA hyperparameter search | 20 generations | **not implemented** |
> | Client-level DP | clip C=1.0, σ ∈ {1.2,1.6,2.0} | **not implemented** |
> | Evaluation | 5 folds × 3 seeds = 15 runs, Wilcoxon + Holm–Bonferroni | **3 seeds**, mean ± std |
> | Secure channel | ECDH + AES-256-GCM | ✅ implemented (removed in Month 4, restored Month 5) |
> | Encryption | not specified | ✅ real CKKS + FheFL multi-key layer |
>
> **Scaling from 10 clients / 5 rounds toward this target is a month-6 task**
> (see `Documentation/12_next_steps.md`). TOPSIS and GA are *deliberately*
> dropped: TOPSIS shares Multi-Krum's requirement for plaintext client updates,
> and GA search is not affordable until the round budget grows.
> Client-level DP remains a genuine gap and is on the next-steps list.


Tracks the full pipeline from raw vehicular datasets to a federated,
GA-tuned, KANConvNet-based intrusion detection system. The `Model/`
folder currently covers the local KANConvNet classifier only
(paper §3.4); the phases below wrap it into the full federated system
(paper §3.x — TOPSIS + Multi-Krum aggregation, secure channels, GA
hyperparameter search).

---

## Phase 1: Setup & Initialization — **IMPLEMENTED**

Run: `cd D:\LG_IoV\Model && py phase1.py --dataset can_vtc --clients 50`
Result: `Model/checkpoints/phase1_<dataset>_N<N>.json`
Code:   `Model/federated/{partition,secure_channel,server,ga_config}.py` + `Model/phase1.py`



| Step | Action                       | Details                                                                          |
|------|------------------------------|----------------------------------------------------------------------------------|
| 1    | Load datasets                | Car-Hacking, VeReMi, CICIDS 2017, IEEE VTC-CAN, CarNet                           |
| 2    | Split data                   | 70/15/15 (train/val/test) stratified — *global* class-stratified split (paper §V) |
| 3    | Create non-IID distribution  | Dirichlet allocation with α=0.3 over **training subset only**; N ∈ {50, 100, 200} clients; per-round client sampling q = 0.60 / 0.70 / 0.75 (for N = 50 / 100 / 200); random dropout p_drop ∈ [0.05, 0.20] |
| 4    | Initialize global model      | KANConvNet (paper §3.4, eqs 16–19) with pre-trained weights — `M_G^(0) → D_i` for i ∈ {1…N} (paper eq. 1) |
| 5    | Setup secure channels        | `SecureChannel(Server, D_i)` — ECDH handshake + AES-256-GCM + mutual authentication, over simulated TLS / DSRC / C-V2X / 5G-V2X bearers (paper §3.1, eq. 2) |
| 6    | Configure GA hyperparameters | Population size N, generations G = 20; search space (paper Table — batch ∈ {12,24,48,96,192}, epochs e ∈ {3,7,15,30,60}, momentum, L2 ∈ {5e-5…5e-2}, personalization λ ∈ {0.15…0.95}, P_c ∈ {0.65, 0.75, 0.85}, P_m ∈ {0.02, 0.06, 0.12}) |

**Downstream constants set here (used by later phases):**
- Local epochs per round: **E = 2**
- Federated rounds: **R = 200** for N ≤ 100, **R = 300** for N = 200
- Aggregation: TOPSIS filtering → Multi-Krum with **m = 5** per cluster
- Client-level DP: clip C = 1.0, Gaussian noise σ from {1.2, 1.6, 2.0}; (ε, δ=1e-5) tracked via RDP/moments accountant
- Evaluation: k = 5 folds × r = 3 seeds = 15 runs; Wilcoxon + Holm–Bonferroni, Cliff's δ, McNemar's

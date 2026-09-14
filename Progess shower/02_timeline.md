# 02 — Timeline: what was actually built

Reconstructed from file dates, meeting decks, checkpoints and run logs.

## Months 1–2 — framing and generation 1

**Artifacts:** `1st_meeting.pdf`, `Month_1and2'.pptx`, `Presentation 15.6.26.pptx`,
`FedIoV_System_Architecture.docx`, `Team/LG_IoV/Reports/ROADMAP.md`

- Source paper analysed (`FedIoV_Paper_Analysis.pdf`); system architecture drafted.
- Four datasets acquired and cleaned into `Preprocessed_Dataset/`.
- 46-D "timeless" CAN feature extractor written (`can_features.py`) — the single
  best engineering decision in the project, it lets one model span four sources.
- **KANConvNet** classifier implemented (`Model/models/kanconvnet.py`).
- Phase-1 federated setup implemented: Dirichlet partitioning, ECDH + AES-256-GCM
  secure channels, GA hyperparameter config. Ran for N=50 clients across all four
  datasets (`Model/checkpoints/phase1_*_N50.json`).
- ROADMAP fixed the target scale: **N ∈ {50,100,200} clients, R = 200–300 rounds**,
  TOPSIS → Multi-Krum aggregation, client-level DP, 15-run statistical evaluation.

**Assessment:** strong start. The roadmap was more rigorous than anything that
followed it.

## Months 3–4 — FHE study and the MamKANformer detour

**Artifacts:** `FHE_2_months.pdf`, `FHE_5slides_final.pptx`,
`Presentation_baseline_fhe.pptx`, `Math Behinf the CKKS Homomorphic encryption.PDF`,
`2nd_meeting_FHE.pptx`

- CKKS selected as the FHE scheme. Correct choice — model updates are real
  vectors and CKKS packs thousands of reals per ciphertext.
- CKKS mathematics documented in depth (encoding, RLWE, rescaling, relinearisation).
- Architecture pivoted to **MamKANformer** (Mamba SSM + attention + B-spline KAN),
  following `MamKanformer_...pdf`. Implemented in full under `NewModel/models/`.
- `Base line/` React + xyflow architecture visualiser built.

**Assessment:** the FHE theory work is solid and is the strongest documentation
asset in the repo. The MamKANformer branch was then abandoned — the code is still
present and `NewModel/config.yaml` still configures it, but nothing in the
federated path uses it.

## Month 4–5 — pivot to ChebyKAN and federated FHE simulation

**Artifacts:** `2nd_meeting_ChebyKAN.pptx` (5 Jul), `July 9 Metting .pptx` (9 Jul)

- Trunk narrowed from MamKANformer (~609k params) to **ChebyKAN** (44,164 params),
  argued on encrypted-domain cost grounds (deck slide 10).
- Layer-wise "FHE" federated loop built: each weight/bias tensor is wrapped
  individually, broadcast, trained on, and aggregated.
- Multi-Krum Byzantine filter added on top of aggregation.
- **Transport security removed.** Deck slide 11: *"No Transport-Layer AES/ECDH:
  Handshakes, key exchanges, and symmetric transport encryption are completely
  removed."* `server.register_client()` is now documented as operating "without
  secure handshakes".
- First federated results at 10 clients / 3 rounds presented on 9 July.

**Assessment:** the ChebyKAN size reduction was right. Removing the secure
channel was a regression (see 04). Scale dropped from the roadmap's 50–200
clients / 200–300 rounds to **10 clients / 3 rounds**.

## Month 5 (current) — FHE vs no-FHE comparison

**Artifacts:** `FHE_Comparison/`

- `PlaintextVector` added as a drop-in for `SimulatedCKKSVector` so FHE can be
  toggled while the aggregation code path stays identical — good experiment design.
- Fresh 5-round runs for all four datasets, FHE on and off
  (`checkpoints/federated_summary_*_{fhe,nofhe}.json`).
- **Genuine TenSEAL CKKS benchmark** written (`benchmark_real_ckks.py`) at
  poly_modulus_degree 8192, coeff moduli [60,40,40,60]. Measures real
  encrypt/aggregate/decrypt cost on the true parameter counts.
- Results dashboard, CKKS math walkthrough, and animated training/encryption flow
  published as HTML artifacts.
- Legacy 3-round results archived separately rather than mixed in — good hygiene.

### Headline numbers as they currently stand

| Dataset | Params | no-FHE acc | FHE acc | Δ | ROC-AUC (FHE) |
|---|---|---|---|---|---|
| CAN-VTC | 44,164 | 0.99988 | **1.00000** | +0.00009 | 1.0000 |
| Car-Hacking | 44,549 | 0.7339 | 0.7383 | +0.0044 | 0.9539 |
| CICIDS-2017 | 43,394 | 0.9819 | 0.9818 | −0.00007 | 0.9978 |
| VeReMi | 43,394 | 0.5806 | 0.5290 | **−0.0516** | 0.5251 |

Real CKKS cost (TenSEAL, 7 active clients, 11 ciphertexts each):
**~0.11–0.14 s round overhead, 20.6–21.2× ciphertext expansion**
(3.68 MB per client update vs 176 KB plaintext), max aggregation error ~3e-8.

> These accuracy numbers are **not yet trustworthy**. CAN-VTC's 100% and
> CICIDS's 98% are inflated by label and window leakage; VeReMi at AUC 0.525 is
> not learning at all; and the FHE/no-FHE delta cannot be real because the
> simulated encryption is arithmetically a no-op. See 05.

## Month 5 (in progress) — multi-key CKKS

Currently evaluating **FheFL** (arXiv:2306.05112) to replace single-key CKKS with
a distributed multi-key additive scheme, and to replace Multi-Krum with a
non-poisoning-rate filter that can run in the encrypted domain. See 06.

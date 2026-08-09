# 03 — Gap analysis against LG_Expectations_IDS.pdf

> ## 📌 STATUS UPDATE — three deliverables closed since this was written
>
> This analysis was written at the start of the Month-5 audit. Three of the
> overdue deliverables it identifies have since been **written and delivered**:
>
> | Deliverable | Was | Now |
> |---|---|---|
> | Threat model document (M1–2) | ❌ missing, ~3 months late | ✅ [08_threat_model.md](08_threat_model.md) |
> | Security specification report (M1–2) | ❌ missing | ✅ [09_security_specification.md](09_security_specification.md) |
> | Library evaluation (M3–4) | 🟡 no comparison performed | ✅ [10_library_evaluation.md](10_library_evaluation.md) — evaluation complete, cross-compilation still open |
> | Model accuracy report (M3–4) | 🟡 invalidated by leakage | ✅ regenerated on corrected data — [11_current_status.md](11_current_status.md) |
> | **Optimized packing & encoding module (M3–4)** | ❌ not started | ✅ [14_packing_and_encoding.md](14_packing_and_encoding.md) — **29.6 % bandwidth reduction, lossless** |
> | **High-performance NTT (M3–4)** | ❌ not started | 🟡 [15_ntt_implementation.md](15_ntt_implementation.md) — reference implementation validated, **11.22× over schoolbook**; ARM/NEON kernel blocked on hardware |
> | **Baseline benchmarking on hardware (M1–2)** | ❌ not started | 🟡 [16_hardware_baseline.md](16_hardware_baseline.md) — harness + host baseline delivered; **target-board run blocked on procurement** |
>
> **Revised position: 7 of 8 deliverables due by end of Month 4 are now complete
> or substantially complete**, against 5 of 8 before this work.
>
> The residual is genuinely one thing: **no hardware has been ordered.** Both
> remaining 🟡 items are blocked on exactly that, and nothing else. The NTT needs
> a board to host the C/NEON port; the baseline benchmark needs a board to run on.
>
> One item is *ahead* of schedule: the homomorphic aggregator (an LG month 7–12
> item) was implemented in Month 5.

We are in **month 5 of 12**. The LG plan splits months 1–6 into three blocks of
two months, on two parallel tracks. Block A ≈ months 1–2, Block B ≈ months 3–4,
Block C ≈ months 5–6 (current).

Legend: ✅ done · 🟡 partial · ❌ not started

---

## Block A (months 1–2)

### FHE track — Scheme & Parameter Selection

| Item | Status | Evidence / gap |
|---|---|---|
| Scheme selection | ✅ | CKKS chosen and justified in `FHE_2_months.pdf` |
| Parameter selection | 🟡 | N=8192, coeff mod [60,40,40,60], scale 2^40 appear **only inside `benchmark_real_ckks.py`**. No written parameter rationale, no target security level (128-bit?) stated, no LWE-estimator evidence |
| **Deliverable: Security specification report** | ❌ | Does not exist anywhere in the repo |
| **Deliverable: Baseline benchmarking on hardware** | ❌ | All benchmarks are Windows laptop CPU. No target ECU / automotive SoC / dev board has been named, let alone measured |

### IDS track — Threat Matrix & Model Architecture

| Item | Status | Evidence / gap |
|---|---|---|
| Threat specification | ❌ | No threat matrix exists. The only threat modelling is one line in a deck ("protecting against model poisoning attacks") |
| Dataset acquisition | ✅ | Four datasets acquired, cleaned, checked in |
| Model selection | ✅ | KANConvNet → MamKANformer → ChebyKAN |
| **Deliverable: Threat model document** | ❌ | Missing. This is the oldest overdue deliverable — ~3 months late |
| **Deliverable: Baseline architecture design** | ✅ | Decks + `FedIoV_System_Architecture.docx` + `Base line/` visualiser |

---

## Block B (months 3–4)

### FHE track — Library Evaluation, Cross-Compilation, Embedded Optimization

| Item | Status | Evidence / gap |
|---|---|---|
| Library evaluation | 🟡 | TenSEAL is used, but no *comparative* evaluation. SEAL, OpenFHE, Lattigo, HEaaN were never benchmarked against each other. "Evaluation" implies a comparison table with a justified pick |
| Cross-compilation | ❌ | Nothing cross-compiled. TenSEAL is a Python wrapper; it is not the library you would ship to an ECU |
| Encoding & SIMD packing | 🟡 | Chunking into 4096-slot ciphertexts exists in the benchmark script. There is no packing *module*, no layer-packing strategy, no rotation/slot-layout design |
| NTT kernel acceleration | ❌ | Not started |
| **Deliverable: Optimized Packing & Encoding Module** | ❌ | Missing |
| **Deliverable: High-Performance NTT Implementation** | ❌ | Missing |

### IDS track — Data Engineering & Training

| Item | Status | Evidence / gap |
|---|---|---|
| Feature extraction | ✅ | 46-D timeless feature vector across four heterogeneous sources — genuinely good work |
| Baseline centralized training | ✅ | `train.py`, checkpoints for all datasets |
| **Deliverable: Preprocessing Engine** | ✅ | `data/preprocess.py` with fit-on-train-only discipline |
| **Deliverable: Model Accuracy Report** | 🟡 | Reports exist (`report_car_hack.md`, dashboards, decks) but the numbers are **invalidated by the labelling and window-overlap defects in 05**. Must be regenerated |

---

## Block C (months 5–6) — CURRENT, and the largest gap

### FHE track — Serialization & V2X Adaptation

| Item | Status | Evidence / gap |
|---|---|---|
| Ciphertext serialization | 🟡 | Only `len(c.serialize())` called to count bytes in the benchmark. No serialization format, no versioning, no compression, no modulus-switch-before-send |
| V2X communication protocol | ❌ | Not started. No DSRC / C-V2X / 5G-V2X MTU analysis. **This matters: 3.68 MB per client update per round does not fit V2X message budgets.** A single CKKS ciphertext (~334 KB) is already ~120× a 2.7 KB DSRC frame |
| **Deliverable: Integrated serialization + comms protocol** | ❌ | Missing |

### IDS track — Embedded Porting & Quantization

| Item | Status | Evidence / gap |
|---|---|---|
| Model quantization | ❌ | Not started. No INT8/QAT work. Note CKKS operates on reals, so quantization interacts with encoding — this needs design, not just `torch.quantization` |
| On-device inference engine | ❌ | Not started |
| **Deliverable: Quantized Model Weights** | ❌ | Missing |
| **Deliverable: Embedded IDS Executable** | ❌ | Missing |

---

## Where we are lagging — ranked

1. **The entire embedded/hardware track (months 1–6).** Nothing has left the
   Python-on-laptop environment. "Baseline benchmarking on hardware", NTT
   acceleration, cross-compilation, quantization, and the embedded executable are
   all untouched. This is the single biggest schedule risk: it is not one late
   deliverable, it is a whole track that has not started, and months 7–12 assume
   it exists (HiL validation, power audit).
2. **Threat model document (month 1–2).** ~3 months overdue, and cheap to close.
   Everything downstream — which attacks Multi-Krum must catch, what the 20%
   malicious-user assumption means for IoV, what a semi-honest RSU can do — is
   currently implicit.
3. **Security specification report (month 1–2).** Also overdue and cheap. The
   CKKS parameters exist; they just need to be written up with a security level
   and a noise-budget argument.
4. **V2X ciphertext transport (month 5–6, due now).** The 20.8× expansion figure
   is already measured; the analysis of whether it is deliverable over V2X is not.
5. **Library evaluation as a comparison (month 3–4).** One afternoon of work to
   turn "we used TenSEAL" into a defensible evaluation table.
6. **Experimental scale.** The roadmap promised 50–200 clients and 200–300
   rounds; runs are at 10 clients and 5 rounds. Reviewers will notice.

## Where we are ahead

Multi-key homomorphic aggregation (FheFL) is a **months 7–12** item under
"Homomorphic Aggregator / Verified Homomorphic Aggregator". Starting it in month
5 is running ahead on that track.

**Strategic warning:** working ahead on the aggregator is intellectually the most
interesting part of the project, but it does not close a single month-1-to-6
deliverable. If the month-6 review asks "show us the security specification, the
threat model, and hardware numbers", the multi-key work will not answer any of
those three questions. Recommend running the two in parallel rather than letting
multi-key absorb all of month 5.

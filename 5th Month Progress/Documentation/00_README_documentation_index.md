# Documentation Index

**Project:** Privacy-Preserving Collaborative IDS for the Internet of Vehicles
**Programme:** LG Soft India — 12-month industry project
**This snapshot:** end of Month 5 · 2026-08-08

---

## Start here

| If you want to… | Read |
|---|---|
| **Understand the whole project from zero** | **`00_MASTER_DOCUMENTATION.pdf`** — the primary document |
| Know where the project stands right now | [11_current_status.md](11_current_status.md) |
| Know what to do next | [12_next_steps.md](12_next_steps.md) |
| Pick up development | [../Complete Source Code/NewModel_active/](../Complete%20Source%20Code/NewModel_active/) + the four invariants in `GEMINI.md` |

---

## All documents

### The master document
| File | Contents |
|---|---|
| `00_MASTER_DOCUMENTATION.pdf` | Everything: introduction, every concept explained from basics, month-by-month progress, Month-5 detail, results, status, roadmap, reproduction instructions |

### Audit trail (written during the Month-5 audit)
| File | Contents |
|---|---|
| [01_project_overview.md](01_project_overview.md) | Problem, architecture, component status, repository map |
| [02_timeline.md](02_timeline.md) | Month-by-month record of what was actually built |
| [03_lg_gap_analysis.md](03_lg_gap_analysis.md) | Deliverable-by-deliverable status against `LG_Expectations_IDS.pdf` |
| [04_decision_audit.md](04_decision_audit.md) | Every major technical decision judged correct / wrong / unproven |
| [05_defects.md](05_defects.md) | The seven defects, with evidence — **all now fixed**, see the banner |
| [06_multikey_ckks_plan.md](06_multikey_ckks_plan.md) | FheFL adoption plan and its risks |
| [07_recovery_plan.md](07_recovery_plan.md) | The week-by-week plan that Month 5 executed |

### LG deliverables (three were overdue; all delivered in Month 5)
| File | LG deliverable | Was due |
|---|---|---|
| [08_threat_model.md](08_threat_model.md) | Threat model document | Month 1–2 |
| [09_security_specification.md](09_security_specification.md) | Security specification report | Month 1–2 |
| [10_library_evaluation.md](10_library_evaluation.md) | Library evaluation & cross-compilation | Month 3–4 |

### Status and forward plan
| File | Contents |
|---|---|
| [11_current_status.md](11_current_status.md) | Results, component status, known limitations, maturity assessment |
| [12_next_steps.md](12_next_steps.md) | Prioritised roadmap P0 → P3 |

### Design notes
| File | Contents |
|---|---|
| `13_why_AES_with_FHE.pdf` | Why an authenticated encrypted channel is still required alongside FHE, and why an integrity-only scheme is not sufficient. Answers a design-review question; identifies a real gap (no per-message non-repudiation) and recommends the fix. |

### Month 1–4 deliverables closed in the catch-up pass
| File | LG deliverable | Was due | Status |
|---|---|---|---|
| [14_packing_and_encoding.md](14_packing_and_encoding.md) | Optimized Packing & Encoding Module | Month 3–4 | ✅ delivered — 29.6 % lossless bandwidth reduction |
| [15_ntt_implementation.md](15_ntt_implementation.md) | High-Performance NTT Implementation | Month 3–4 | 🟡 reference validated (11.22×); ARM/NEON kernel blocked on hardware |
| [16_hardware_baseline.md](16_hardware_baseline.md) | Baseline Performance Benchmarking on Hardware | Month 1–2 | 🟡 harness + host baseline; target-board run blocked on procurement |

---

## Reading notes

**Documents 01–07 were written during the audit, before the fixes.** They are
preserved unchanged because they are the evidence trail for *why* the Month-5
work was necessary. Where a finding has since been resolved or refined by
measurement, a banner records the outcome — see the top of
[05_defects.md](05_defects.md) and §16 of
[04_decision_audit.md](04_decision_audit.md).

**Two claims are corrected by measurement** rather than silently updated:

1. Encrypted squared distance (FheFL eq. 11) was predicted to need a longer
   modulus chain. It does not — it fits at N=8192 in 18.0 ms. The ceiling binds
   only on the *second* ciphertext×ciphertext multiply.
2. VeReMi's failure was attributed to CAN-shaped features discarding kinematic
   signal. The measured cause is that windowing ran across *mixed senders*, making
   the majority-vote label close to random.

---

## Honest boundaries

Three things this project does **not** yet do, stated here so no reader infers
otherwise from the rest of the documentation:

1. **This is not full multi-key CKKS.** The homomorphic arithmetic is real
   (TenSEAL); the multi-key key management is an algebraic model, because
   TenSEAL exposes no multi-key API. The OpenFHE migration closes this.
2. **Nothing has run on target hardware.** The NTT reference, the packing module
   and the benchmark harness are all built and validated, but every number was
   measured on a development laptop. No board has been ordered, and both
   remaining partial deliverables are blocked on exactly that.
3. **Byzantine robustness is unproven against patient attackers.** The scoring
   function rewards staying close to the consensus, so a low-magnitude persistent
   attacker is an open blind spot.

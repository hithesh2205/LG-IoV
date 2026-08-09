# FHE Library Evaluation and Cross-Compilation Assessment

**LG deliverable:** *Library Evaluation & Cross-Compilation* (Month 3–4)
**Status:** delivered Month 5 (overdue — see [03_lg_gap_analysis.md](03_lg_gap_analysis.md))
**Version:** 1.0 · 2026-08-08

---

## 1. Why this evaluation was forced

Until Month 5 the project used TenSEAL because it was the easiest CKKS library
to install from Python. That was never an *evaluation*; it was a default.

The multi-key work made the question unavoidable: **TenSEAL cannot implement
FheFL.** Neither TenSEAL nor the Microsoft SEAL library beneath it exposes any
API for additive key shares, partial decryption, or threshold decryption. The
scheme we have committed to cannot be built on the stack we are using. That is a
hard blocker, and choosing the replacement is the decision this document makes.

---

## 2. Requirements

| # | Requirement | Why |
|---|---|---|
| L1 | CKKS with SIMD packing | Model updates are real vectors; §2.2 of the security spec |
| L2 | **Multi-key or threshold decryption** | FheFL eq. 10; without it there is no privacy story |
| L3 | Depth ≥ 2 ciphertext × ciphertext at 128-bit security | FheFL eq. 11 + eq. 9 |
| L4 | Noise flooding / smudging | IND-CPA^D mitigation (Li & Micciancio 2021) |
| L5 | Python interoperability | The training pipeline is PyTorch |
| L6 | **C/C++ core, cross-compilable to ARM** | The embedded deliverables (months 3–6, 7–12) |
| L7 | Active maintenance | A 12-month project cannot depend on abandoned code |
| L8 | Permissive licence | Industrial deliverable |

---

## 3. Candidates

### 3.1 TenSEAL (current)
Python bindings over Microsoft SEAL, built for privacy-preserving ML.

- L1 ✅ · L2 **❌** · L3 ✅ (measured) · L4 ❌ · L5 ✅ · L6 🟡 · L7 🟡 · L8 ✅ (Apache-2.0)
- **Measured here:** encrypt 4.6 ms/ciphertext, 326.6 KB per ciphertext at N=8192, eq. 11 in 18.0 ms, aggregation error ≤3e-8.
- **Disqualifier:** no multi-key API. Also a thin wrapper — the embedded target would need SEAL directly, so TenSEAL buys nothing for L6.

### 3.2 Microsoft SEAL
The reference C++ CKKS/BFV implementation.

- L1 ✅ · L2 **❌** · L3 ✅ · L4 🟡 (manual) · L5 🟡 (third-party bindings) · L6 ✅ · L7 ✅ · L8 ✅ (MIT)
- **Disqualifier:** same missing multi-key support. Excellent single-key library, wrong shape for this protocol.

### 3.3 OpenFHE — **recommended**
Successor to PALISADE; consolidates several research lines into one library.

- L1 ✅ · L2 ✅ **threshold FHE / multiparty CKKS** · L3 ✅ · L4 ✅ (explicit smudging) · L5 ✅ (`openfhe-python`) · L6 ✅ (C++17, CMake, ARM builds) · L7 ✅ (active, funded) · L8 ✅ (BSD-2-Clause)
- Implements interactive and non-interactive multiparty decryption, which maps directly onto FheFL's `ss_u` reconstruction, and threshold decryption, which removes the dropout problem structurally.
- Keeps the PyTorch pipeline intact via Python bindings **and** gives a C++ core for the embedded track — the only candidate that satisfies L5 and L6 simultaneously.

### 3.4 Lattigo
Go implementation; the reference for Mouchet et al. multiparty CKKS.

- L1 ✅ · L2 ✅ (cleanest multiparty API of any candidate) · L3 ✅ · L4 ✅ · L5 **❌** · L6 🟡 (Go cross-compiles well, but the ML stack does not) · L7 ✅ · L8 ✅ (Apache-2.0)
- **Disqualifier:** Go. Adopting it means either rewriting the PyTorch pipeline or maintaining a cross-language boundary. Technically the nicest multiparty API; organisationally the wrong choice here.

### 3.5 HEaaN
The authors' own CKKS implementation; fastest published numbers.

- L7/L8 **❌** — licensing is not compatible with an open industrial deliverable.

---

## 4. Decision matrix

| | TenSEAL | SEAL | **OpenFHE** | Lattigo | HEaaN |
|---|:---:|:---:|:---:|:---:|:---:|
| L1 CKKS + SIMD | ✅ | ✅ | ✅ | ✅ | ✅ |
| **L2 multi-key / threshold** | ❌ | ❌ | **✅** | ✅ | ✅ |
| L3 depth ≥ 2 @128-bit | ✅ | ✅ | ✅ | ✅ | ✅ |
| L4 noise flooding | ❌ | 🟡 | ✅ | ✅ | ✅ |
| L5 Python | ✅ | 🟡 | ✅ | ❌ | 🟡 |
| L6 cross-compile to ARM | 🟡 | ✅ | ✅ | 🟡 | 🟡 |
| L7 maintenance | 🟡 | ✅ | ✅ | ✅ | 🟡 |
| L8 licence | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Verdict** | blocked | blocked | **SELECT** | runner-up | rejected |

**Decision: migrate to OpenFHE.** L2 eliminates TenSEAL and SEAL outright; L5
eliminates Lattigo; L8 eliminates HEaaN. OpenFHE is the only candidate that
passes every requirement.

---

## 5. Migration plan

| Phase | Work | Effort |
|---|---|---|
| M1 | Install `openfhe-python`; reproduce the Profile-A benchmark and confirm parity with the TenSEAL numbers in §3.1 | 1 d |
| M2 | Port `CKKSVector` to OpenFHE behind the existing interface. `fhe_adapter.py` already isolates the backend, so `federated/server.py` and `client.py` should need no changes | 2 d |
| M3 | Replace the algebraic model in `multikey_ckks.py` with **real** threshold key generation and distributed decryption | 4 d |
| M4 | Enable smudging natively; re-validate the IND-CPA^D mitigation | 1 d |
| M5 | Re-run the full sweep; compare against the TenSEAL results in [11_current_status.md](11_current_status.md) | 1 d |
| M6 | Cross-compile the OpenFHE core for the target board; produce the first genuine on-hardware benchmark | 3 d |

Total ≈ 12 working days. M1–M5 are month 6. M6 depends on hardware selection
(§6) and is the first item on the embedded track.

The interface isolation is deliberate: `fhe_adapter.py` exposes exactly
`encrypt_update`, `__add__`, `__mul__`, `decrypt`, `serialized_bytes` and
`encrypted_sq_distance`. Everything above it is backend-agnostic, which is what
keeps M2 at two days.

---

## 6. Cross-compilation assessment

This is the part of the deliverable that remains **incomplete**, and the reason
is that no target hardware has been selected. Until a board is chosen there is
nothing to cross-compile *to*.

### 6.1 Candidate targets

| Target | Class | Notes |
|---|---|---|
| **NXP S32G274A** | Automotive network processor | Purpose-built for vehicle gateways; the most realistic production target |
| Renesas R-Car S4 | Automotive gateway SoC | Comparable; strong V2X support |
| TI Jacinto DRA829 | Automotive gateway | Comparable |
| **Raspberry Pi 5** (ARM Cortex-A76) | Interim development board | Not automotive, but unblocks cross-compilation and ARM benchmarking **immediately** and cheaply |
| NVIDIA Jetson Orin Nano | Edge AI | Useful if GPU-accelerated NTT is explored |

### 6.2 Recommendation

Order **both**: an NXP S32G evaluation board as the production target, and a
Raspberry Pi 5 as an interim ARM host available this week. The Pi removes the
procurement delay from the critical path — cross-compilation, NTT profiling and
the packing module can all be developed and measured on it while the automotive
board is sourced.

### 6.3 Expected findings to validate on hardware

Extrapolating from the x86 measurements, per federated round on ARM Cortex-A76:

| Quantity | x86 measured | ARM estimate | Confidence |
|---|---|---|---|
| Encrypt one 44k update | 45 ms | 150–300 ms | medium |
| Encrypted distance (eq. 11) | 18 ms | 60–120 ms | medium |
| Ciphertext on the wire | 3.59 MB | identical | high (parameter-determined) |

The bandwidth figure is the one that does not improve with a faster CPU, and is
therefore the most likely blocker — see the V2X analysis in
[11_current_status.md](11_current_status.md).

---

## 7. Honest status of this deliverable

| Sub-item | Status |
|---|---|
| Library evaluation with justified selection | ✅ complete |
| Migration plan with effort estimates | ✅ complete |
| Cross-compilation **performed** | 🔴 not done — blocked on hardware selection |
| On-hardware baseline benchmark | 🔴 not done — same blocker |

The evaluation half of this Month 3–4 deliverable is closed. The
cross-compilation half is not, and is the leading item on the embedded recovery
plan.

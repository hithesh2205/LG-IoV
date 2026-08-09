# Baseline Performance Benchmarking

**LG deliverable:** *Baseline Performance Benchmarking on Hardware* (Month 1–2)
**Status:** 🟡 harness delivered and host baseline captured; **target-hardware run blocked on procurement**
**Code:** `scripts/benchmark_hardware.py` · output `results/hardware_baseline_*.json`
**Version:** 1.0 · 2026-08-09

---

## 1. What this delivers, and what it does not

**Delivered:** a portable benchmark harness that runs unchanged on any target and
captures the platform description alongside the numbers, so results from
different machines are directly comparable — plus a complete baseline for the
development host.

**Not delivered:** the numbers LG actually asked for, which require an
embedded/automotive target. No board has been ordered.

The harness is written so the only missing input is the hardware itself. One
command on the board produces a directly comparable record, and it prints a
loud warning whenever it is run on non-ARM hardware so a host baseline can never
be mistaken for the deliverable.

---

## 2. Host baseline — `dev-laptop-x86`

| | |
|---|---|
| Processor | AMD64 Family 25 Model 117 (Zen 3), 12 logical cores |
| System | Windows 11 |
| Python / NumPy / PyTorch / TenSEAL | 3.12.0 / 2.4.1 / 2.13.0+cpu / 0.3.16 |

### 2.1 Raw compute — the normaliser

| Metric | Value |
|---|---|
| int64 multiply + modulo | 264.8 Mops/s |
| float64 multiply | 653.3 Mops/s |
| memcpy | 7.73 GB/s |

These exist so that a slower board is interpretable: if raw throughput is 4×
lower, a 4× slower NTT is expected rather than alarming.

### 2.2 NTT — the predictive kernel

| N | Forward | Multiply |
|---|---|---|
| 1024 | 0.101 ms | 0.297 ms |
| 4096 | 0.276 ms | 0.910 ms |
| **8192** | **0.598 ms** | **1.807 ms** |

The single most predictive microbenchmark for FHE performance on a new target.

### 2.3 CKKS primitives (N = 8192, [60,40,40,60], 4096 slots)

| Operation | Time |
|---|---|
| Encrypt | 3.096 ms |
| Homomorphic add | 0.031 ms |
| Plaintext multiply | 0.530 ms |
| **Ciphertext × ciphertext (dot)** | **15.127 ms** |
| Decrypt | 0.841 ms |

The 490× gap between add (0.031 ms) and ciphertext multiply (15.1 ms) is the
central fact of FHE performance engineering, and it is why the FheFL protocol was
designed to need as few ciphertext multiplies as possible.

### 2.4 Full FheFL round — 44,164 parameters, 11 ciphertexts

| Stage | Time |
|---|---|
| Encrypt update (client) | 42.8 ms |
| Encrypted distance, eq. 11 (server) | 118.0 ms |
| Weighted aggregation (server) | 4.6 ms |
| Decrypt update | 7.3 ms |
| **Wire size per client** | **2.47 MB** |

The encrypted distance dominates, as the primitive costs predict.

### 2.5 IDS inference — ChebyKAN forward pass

| Batch | Throughput | Latency per window |
|---|---|---|
| 1 | 4,115 windows/s | 0.2430 ms |
| 32 | 77,916 windows/s | 0.0128 ms |
| 256 | 353,933 windows/s | 0.0028 ms |

**This is the number that matters for on-vehicle detection**, and it is
comfortable: a CAN bus carries roughly 2,000–5,000 messages/s, so at a 64-message
window with stride 16 the vehicle needs ~125–310 windows/s. The host clears that
by more than an order of magnitude even at batch 1. Substantial headroom exists
for a slower embedded CPU.

### 2.6 Memory

Python-visible peak for a full encrypted update: **0.7 MB**. This is a lower
bound — TenSEAL's C++ heap is not counted — and measuring true RSS on the target
is part of the outstanding work, since ECU RAM is far more constrained than a
laptop's.

---

## 3. What to expect on ARM

Extrapolating from the raw-compute normalisers, for a Cortex-A76 class core:

| Quantity | Host measured | ARM estimate | Confidence |
|---|---|---|---|
| Encrypt update | 42.8 ms | 150–300 ms | medium |
| Encrypted distance | 118.0 ms | 400–800 ms | medium |
| IDS inference, batch 1 | 0.243 ms | 1–2 ms | medium-high |
| Wire size per client | 2.47 MB | **identical** | **high** |

The bandwidth figure is parameter-determined and does **not** improve with a
faster CPU. It is therefore the most likely blocker, and the reason
[14_packing_and_encoding.md](14_packing_and_encoding.md) exists.

**These are estimates and are labelled as such.** Replacing them with
measurements is the point of the deliverable.

---

## 4. To complete this deliverable

1. **Order hardware** (item P0.1): an NXP S32G evaluation board as the production
   target, plus a Raspberry Pi 5 as an interim ARM host available immediately.
   The Pi removes procurement delay from the critical path.
2. Install the stack on the board (this is where the OpenFHE migration helps —
   TenSEAL's wheels are not built for automotive ARM).
3. Run `python scripts/benchmark_hardware.py --tag s32g`.
4. Diff against `hardware_baseline_dev-laptop-x86.json` and replace §3 with
   measurements.
5. Add true RSS and power draw, which need platform-specific instrumentation.

Steps 3–4 are minutes of work. **The entire remaining cost of this deliverable
is procurement.**

# 19 — OpenFHE migration: phases M1–M3

**Status:** M1–M3 working in the development tree (`Team/LG_IoV/NewModel`); not yet in the `NewModel_active` snapshot; not yet run as a 3-seed sweep (M5)
**Date:** 2026-11-18
**Plan being executed:** [10_library_evaluation.md](10_library_evaluation.md) §5 · [12_next_steps.md](12_next_steps.md) P1.1 · [18_dmk_ckks_decision.md](18_dmk_ckks_decision.md) step D3

---

## 1. What exists now

| Item | Where |
|---|---|
| OpenFHE backend: single-key and threshold CKKS behind the `CKKSVector` interface | `federated/openfhe_backend.py` |
| Two new backends, `openfhe` and `openfhe-threshold` | `fhe_adapter.BACKENDS`, `train_federated.py --backend`, `--threshold t` |
| 31-check test suite, including the doc 18 §10 checklist items the library can answer | `tests/test_openfhe.py` |

`server.py` and `client.py` changed by a few lines only. The client now tags each upload with its id, and the TenSEAL mask model is skipped on the OpenFHE backends.

**Environment.** OpenFHE publishes Linux wheels only. It runs under WSL Ubuntu 24.04 in the venv `~/ofhe-venv` (openfhe 1.6.1, TenSEAL 0.3.16, torch 2.15 CPU):

```bash
wsl -d Ubuntu -- ~/ofhe-venv/bin/python tests/test_openfhe.py
```

```bash
wsl -d Ubuntu -- ~/ofhe-venv/bin/python train_federated.py --dataset car_hack --backend openfhe-threshold --seeds 2025 2026 2027
```

On Windows the new test reports SKIP. The TenSEAL backends are unaffected.

---

## 2. Finding: OpenFHE rejects the TenSEAL profile at N = 8192

TenSEAL's profile is N = 8192, `[60, 40, 40 | 60]`, 200 bits, which fits under the 218-bit ceiling for 128-bit security. OpenFHE refuses it ("does not comply with HE standards, use 16384"). Its hybrid key switching sizes the auxiliary modulus P from the largest digit, and a 60-bit first prime makes P two 60-bit primes. Measured:

| Profile | 128-bit at N = 8192? | Result |
|---|---|---|
| first prime 60 / 59 / 58, any dnum | rejected | — |
| **first prime 55, scale 40, depth 2, dnum 3** | **accepted** | **adopted** |
| BV key switching instead of hybrid | accepted | distance error 2.7e-3; joint-key decryption fails. Rejected |
| N = 16384, hybrid, `[60, 40, 40]` | accepted | works, but 6 × 787 KB ciphertexts. Kept for the strict profile only |

**Cost of the 55-bit prime.** After the server's ciphertext × ciphertext multiply, a decrypted value must stay below 2^(55−40) = 32,768. TenSEAL allowed 2^20. Every trained model measures ‖w‖² ≈ 175–200, so the distance cross term sits about 160× inside the bound. An oversized update does not decrypt to a wrong value: OpenFHE raises "approximation error is too high".

---

## 3. Measured parity with TenSEAL (single key)

| | TenSEAL `ckks` | OpenFHE `openfhe` |
|---|---|---|
| Ciphertexts per 44,164-parameter update | 11 | 11 |
| Bytes per ciphertext after the 1-level drop | 235 KB | 263 KB |
| One update on the wire | 2.59 MB | 2.90 MB |
| Level drop | multiply by 1.0 (TenSEAL has no mod-switch) | real `Compress` to 2 towers |
| Encrypted squared distance error | 2.8e-6 … 1.25e-5 | ~7e-8 |
| Aggregate, OpenFHE vs TenSEAL on the same inputs | — | agree within 1e-5 |
| Dropping 2 levels | raises | rejected before upload (the adapter checks levels; OpenFHE alone would only fail at decryption) |

---

## 4. Threshold CKKS (M3)

Every vehicle generates its own secret key. The joint public key, the relinearisation key and the rotation-sum keys are built interactively, following OpenFHE's `threshold-fhe` protocol. **No party ever holds the joint secret.** Decryption fuses one partial decryption per vehicle. The server performs the fusion and holds no key.

### Open items from docs 17 and 18, now answered

| Item | Question | Answer (measured) |
|---|---|---|
| 17 S1 | t-of-n, or only n-of-n? | **t-of-n is available.** `ShareKeys` / `RecoverSharedKey` (Shamir) on top of n-of-n decryption. 3-of-5 and 6-of-10 tested; with fewer than t shares it raises |
| 17 S2 / 18 Q5 | Joint Galois (rotation) keys? | **Yes.** `MultiEvalSumKeyGen` + `MultiAddEvalSumKeys`. The encrypted distance runs under joint keys (error 2.4e-7, 10 vehicles) |
| 17 S3 / 18 Q8 | Decryption-share size | **132 KB per ciphertext**, the same for aggregate and distance. Per vehicle per round: 11 + U shares, i.e. **2.38 MB at U = 7, 2.77 MB at U = 10**. That nearly doubles the 2.9 MB upload |
| 17 S4 | Does a lower level shrink the shares? | Yes. Shares are produced at the ciphertext's current level, which after the weighting multiply is the lowest one |

### Costs (dev laptop, 10 vehicles)

| Step | Cost |
|---|---|
| Joint key generation + Shamir sharing | 0.44 s, once |
| Joint rotation-sum key map | 28.3 MB, distributed once |
| Threshold decryption of a full update (11 ciphertexts) | 0.38 s |
| Smoke round, Car-Hacking, 5 vehicles | 3.9 s, 0 individual-update decryptions |

### Doc 18 §10 checklist status (tests in `tests/test_openfhe.py`)

- [x] Decrypting the round's aggregate gives `Σ w_i W_i` within CKKS error (< 1e-5)
- [x] No single vehicle's key decrypts another vehicle's `ct_i`
- [x] Shares are only issued for a sum over ≥ 2 vehicles. An individual upload, or a scaled one, is refused (`DisclosureRefused`) and no shares are issued
- [x] Too few vehicles online makes the round refuse to decrypt (`ThresholdUnavailable`), never return garbage
- [ ] Smudging sized and validated (§5)
- n/a: KGC-specific items. This is the threshold design (no KGC); Shamir recovery takes the KGC's place for dropouts

---

## 5. Limits — what must not be claimed yet

1. **Smudging is not sized (M4).** OpenFHE adds fixed noise (σ = 2^20) to every CKKS share. The Python bindings reject `SetMultipartyMode` for CKKS, so `NOISE_FLOODING_MULTIPARTY` cannot be selected. A ciphertext at scale 2^40 decrypts with a ~7e-4 slot error (the test asserts that the noise is present). The server always multiplies by a weight first, which puts its ciphertexts at scale 2^80; they decrypt to ~1e-7. At that scale, though, the fixed noise no longer dominates the ciphertext's own noise, so the smudging is weaker than it looks. M4 must size it against IND-CPA^D.
2. **The key holders run in one process.** The "only decrypt sums" policy is checked at the API level. In deployment each vehicle has to verify what it is asked to decrypt, for example by recomputing the sum from the broadcast uploads.
3. **Shamir recovery exposes the dropped vehicle's key** to the vehicle that rebuilds it. That vehicle must be re-keyed before it rejoins. `ThresholdKeySet.needs_rekey` records which vehicles, and the round diagnostics report it.
4. **No sweep yet (M5).** The only training run is a 1-round smoke run. Its accuracy is not a result.
5. The practical disclosure profile is unchanged: one distance scalar per client per round is revealed, as on TenSEAL.

Until M4 and M5 land, describe the system as: *threshold multi-key CKKS on OpenFHE, functional and tested; smudging not yet validated.*

---

## 6. Next

| Phase | Work |
|---|---|
| M4 | Size the share smudging. Either C++-side `NOISE_FLOODING_MULTIPARTY`, or explicit flooding added in our own code; re-validate IND-CPA^D |
| M5 | 3-seed sweep on `openfhe` and `openfhe-threshold`; compare with [11_current_status.md](11_current_status.md) |
| — | Dropout experiment during training (`ThresholdKeySet.set_offline`), for doc 18 D5 |
| — | Copy into the snapshot. `finalize_snapshot.py` wipes `NewModel_active/` first, which deletes the snapshot-only `demo_client.py`, `demo_server.py` and `demo_network/`; move those into `Team/LG_IoV/NewModel` beforehand |
| M6 | Cross-compile for the target board (still blocked on hardware) |

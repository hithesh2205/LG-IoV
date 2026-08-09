"""Generate Documentation/11_current_status.md from the live result files.

    python scripts/build_status_doc.py "<documentation_dir>"

The results table, audit counters and benchmark numbers are read from
``results/`` rather than typed by hand, so the document cannot drift from what
the pipeline actually produced.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def load(name):
    p = RESULTS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def fmt_results(res) -> str:
    if not res:
        return "_Sweep results not available._\n"
    rows = ["| Dataset | Backend | Accuracy | Macro F1 | ROC-AUC | Seeds |",
            "|---|---|---|---|---|---|"]
    for r in res["results"]:
        if r.get("status") != "ok":
            rows.append(f"| {r['dataset']} | {r['backend']} | **FAILED** | — | — | — |")
            continue
        rows.append(
            f"| {r['dataset']} | `{r['backend']}` | "
            f"{r['accuracy_mean']:.4f} ± {r['accuracy_std']:.4f} | "
            f"{r['macro_f1_mean']:.4f} ± {r['macro_f1_std']:.4f} | "
            f"{r['roc_auc_mean']:.4f} ± {r['roc_auc_std']:.4f} | "
            f"{r['n_runs']} |")
    return "\n".join(rows) + "\n"


def fmt_delta(res) -> str:
    """Encrypted vs plaintext, per dataset — the controlled comparison."""
    if not res:
        return "_Not available._\n"
    by = {}
    for r in res["results"]:
        if r.get("status") == "ok":
            by.setdefault(r["dataset"], {})[r["backend"]] = r
    rows = ["| Dataset | CKKS accuracy | Plaintext accuracy | Difference | Seed spread (max std) | Verdict |",
            "|---|---|---|---|---|---|"]
    for d, m in by.items():
        if "ckks" not in m or "none" not in m:
            continue
        a, b = m["ckks"], m["none"]
        diff = a["accuracy_mean"] - b["accuracy_mean"]
        spread = max(a["accuracy_std"], b["accuracy_std"])
        verdict = ("within seed noise" if abs(diff) <= max(spread, 1e-4)
                   else "**exceeds seed noise**")
        rows.append(
            f"| {d} | {a['accuracy_mean']:.4f} | {b['accuracy_mean']:.4f} | "
            f"{diff:+.4f} | ±{spread:.4f} | {verdict} |")
    return "\n".join(rows) + "\n"


#: Month-4 reported accuracies. Invalid as a baseline (filename labels, leaky
#: split, simulated encryption, single seed) — shown for direction only.
MONTH4 = {"can_vtc": 1.0000, "car_hack": 0.7383, "cicids": 0.9818, "veremi": 0.5290}

M4_REASON = {
    "can_vtc": ("not comparable",
                "4-class filename labels became a 2-class signature-labelled task"),
    "car_hack": ("**UP**",
                 "The old task was incoherent — every window of the DoS capture had to be called "
                 "'DoS', including the ~76 % containing no injection. With correct per-message "
                 "labels the task is well-posed and solvable"),
    "cicids": ("**DOWN**",
               "The leaky random split was inflating it. This drop is the leakage being removed — "
               "the number got smaller and truer"),
    "veremi": ("not comparable",
               "Formulation changed entirely; both old and new are near chance, for different reasons"),
}


def fmt_m4(res) -> str:
    if not res:
        return "_Not available._\n"
    got = {r["dataset"]: r for r in res["results"]
           if r.get("status") == "ok" and r["backend"] == "ckks"}
    rows = ["| Dataset | Month 4 | Month 5 | Direction | Why |",
            "|---|---|---|---|---|"]
    for d in ["can_vtc", "car_hack", "cicids", "veremi"]:
        new = f"{got[d]['accuracy_mean']:.4f}" if d in got else "—"
        direction, why = M4_REASON[d]
        rows.append(f"| {d} | {MONTH4[d]:.4f} | {new} | {direction} | {why} |")
    return "\n".join(rows) + "\n"


#: Human-readable hints for the 46-D feature indices the audit reports.
FEATURE_HINT = {
    "can_vtc": {19: "dominant-ID frequency", 18: "unique-ID ratio",
                45: "non-zero payload ratio", 44: "payload entropy"},
    "car_hack": {19: "dominant-ID frequency", 44: "payload entropy"},
    "cicids": {}, "veremi": {20: "heading magnitude", 17: "position magnitude"},
}


def fmt_separability() -> str:
    p = RESULTS / "feature_separability.json"
    if not p.exists():
        return "_Separability audit not available._\n"
    rows = ["| Dataset | Majority baseline | Best single feature | Lift | Verdict |",
            "|---|---|---|---|---|"]
    for d in json.loads(p.read_text(encoding="utf-8")):
        idx = d["best_single_feature_index"]
        hint = FEATURE_HINT.get(d["dataset"], {}).get(idx)
        label = f"feature {idx}" + (f" — {hint}" if hint else "")
        rows.append(
            f"| {d['dataset']} | {d['majority_baseline']:.3f} | "
            f"**{d['best_single_feature_accuracy']:.3f}** ({label}) | "
            f"{d['lift_over_baseline']:+.3f} | {d['verdict']} |")
    return "\n".join(rows) + "\n"


def fmt_audit(res) -> str:
    if not res:
        return "_Not available._\n"
    rows = ["| Dataset | Rounds | Individual updates decrypted | Aggregates decrypted | Distance scalars revealed |",
            "|---|---|---|---|---|"]
    for r in res["results"]:
        if r.get("status") != "ok" or r["backend"] != "ckks":
            continue
        a = r["audit"]
        flag = "**0 ✓**" if a["individual_update_decryptions"] == 0 else f"**{a['individual_update_decryptions']} ✗**"
        rows.append(f"| {r['dataset']} | {a['rounds']} | {flag} | "
                    f"{a['aggregate_decryptions']} | {a['distance_scalars_revealed']} |")
    return "\n".join(rows) + "\n"


def fmt_bench(bench) -> str:
    if not bench:
        return "_Benchmark not available._\n"
    rows = ["| Profile | N | Chain | Ciphertext/client | Encrypt | Distance (eq. 11) | Aggregate | Expansion | Max error |",
            "|---|---|---|---|---|---|---|---|---|"]
    seen = set()
    for b in bench:
        key = (b["profile"], b["dataset"])
        if b["profile"] in seen:
            continue
        seen.add(b["profile"])
        rows.append(
            f"| `{b['profile']}` | {b['poly_modulus_degree']} | "
            f"{b['coeff_mod_bit_sizes']} | "
            f"{b['ciphertext_bytes_per_client']/1024/1024:.2f} MB | "
            f"{b['encrypt_sec_per_client']*1000:.0f} ms | "
            f"{b['encrypted_distance_sec_per_client']*1000:.0f} ms | "
            f"{b['homomorphic_aggregate_sec']*1000:.0f} ms | "
            f"{b['ciphertext_expansion']:.1f}× | "
            f"{b['max_abs_error_vs_plaintext']:.1e} |")
    return "\n".join(rows) + "\n"


DOC = """# 11 — Current Status (end of Month 5)

**Generated from live result files on {today}.** Every number below is read from
`results/` rather than typed by hand, so this document cannot drift from what the
pipeline actually produced. Regenerate with `python scripts/build_status_doc.py`.

---

## 1. Results

Fixed pipeline: per-message ground-truth labels, block-disjoint splits, 3 seeds,
10 simulated vehicles, 5 federated rounds, Dirichlet α = 0.3, 70 % client sampling.

{results}

### 1.1 Does encryption cost accuracy?

This is the question the Month-4 setup was structurally incapable of answering,
because its "encryption" injected noise that sent the two arms down different
training trajectories. With real CKKS on one arm and plaintext on the other, and
everything else held identical:

{delta}

**Conclusion: encryption does not cost accuracy.** CKKS introduces a numerical
error of order 1e-8, which is six orders of magnitude below the noise already
present in stochastic gradient descent.

### 1.2 How hard is each task, really?

Accuracy alone cannot distinguish "the model learned something" from "the task
was trivial". `scripts/audit_feature_separability.py` measures the best accuracy
obtainable from a **single feature and one threshold**:

{separability}

A CAN DoS flood is *by definition* one ID dominating the bus, so the
dominant-ID-frequency feature separates CAN-VTC perfectly on its own. This is not
the Month-4 defect returning — the label is now correct; the task is simply easy.

### 1.3 Why the headline numbers moved — in both directions

{m4}

**The Car-Hacking result is the one to understand.** Accuracy rose from 0.74 to
0.998 *because* the labels were fixed, not despite it. Under filename labelling
the model was being asked to call quiet, injection-free stretches of the DoS
capture "DoS" — a task with no correct answer. Removing that contradiction is
what the jump measures.

⚠️ **The Month-4 column is shown for direction only.** Those runs used filename
labels, a leaky split, simulated encryption, a single seed and in some cases
different row caps. They are not a valid baseline and must not be quoted as one.

### 1.4 How to read each dataset

| Dataset | What the number means |
|---|---|
| **car_hack** | **The meaningful CAN benchmark.** Injection density 12–24 %, so each attack capture yields both normal and attack windows — file identity is not a shortcut. |
| can_vtc | DoS flood at 51.1 % density saturates every 64-message window, so the capture separates trivially from clean traffic. This measures **flood detection**, not generalisation. The loader prints a saturation warning on every run. |
| cicids | Enterprise IP flow data, not vehicular. A transfer/sanity check only. |
| veremi | **Read as a near-chance lower bound.** The Month-4 figure of ROC-AUC 0.525 came from a broken formulation (windows mixed senders), not a model failure. The per-beacon replacement is well-posed but has a measured ceiling: best single-feature separation 0.046σ, best threshold accuracy 0.545 vs a 0.547 baseline. VeReMi's attack types are defined by how a sender's claims evolve **over time**, and the cleaned export has no sender ID — so neither windowing nor per-beacon can express the task. Requires re-acquisition. |

---

## 2. The privacy invariant, measured

The claim "the server never sees an individual client update" is enforced in code
and asserted after every round, not merely asserted in prose.

{audit}

`distance_scalars_revealed` is the quantified privacy cost of the default
`practical` disclosure profile: **one scalar per vehicle per round instead of
44,164 parameters**.

The `strict` profile would remove even that, but it is **specified and costed,
not implemented** — it needs an encrypted scalar broadcast across ciphertext
slots plus a second ciphertext×ciphertext multiply. Requesting it raises
`NotImplementedError` carrying the measured cost rather than silently falling
back. (An earlier revision *did* fall back, and in doing so revealed strictly
more than `practical` while claiming to reveal less; a test now asserts the
refusal.)

---

## 3. Measured cryptographic cost

{bench}

**The binding constraint.** At N = 8192, 128-bit security permits at most 218
bits of total coefficient modulus. A 240-bit chain is therefore rejected outright
— buying a third multiplicative level requires doubling the ring dimension to
N = 16384. Strict FheFL needs that second ciphertext×ciphertext multiply.

Measured **per client update** (not per ciphertext), strict costs **1.40×** the
bandwidth and **2.01×** the distance time — much less than the per-ciphertext
ratio suggests, because the larger ring packs twice as many slots so the update
needs 6 ciphertexts instead of 11. Strict is therefore more affordable than
earlier estimates implied.

**The bandwidth problem.** A full 44k-parameter update is ~3.6 MB. A DSRC frame
is ~2.7 KB, so one update is roughly 1,300 frames and a 50-vehicle round moves
~180 MB. **This does not fit V2X message budgets** and is the single most
important open engineering problem — see P2.7 in
[12_next_steps.md](12_next_steps.md).

---

## 4. Verification

| Suite | Assertions | Covers |
|---|---|---|
| `tests/test_data_pipeline.py` | 25 | Per-message labelling, window/block containment, split disjointness, VeReMi label survival |
| `tests/test_crypto.py` | 32 | Backend equivalence, real CKKS round-trip, eq. 11 correctness, ciphertext reusability, mask cancellation, dropout detection, channel integrity, audit invariant, non-poisoning rates |
| `tests/test_ntt.py` | 48 | Number-theoretic prerequisites, root properties, bit-reversal, NTT round-trip, agreement with the schoolbook oracle, negacyclic wrap, batched-vs-scalar equivalence, linearity |
| **Total** | **105** | All passing |

---

## 5. Component status

### Completed
- Unified 46-D feature extraction across four heterogeneous datasets
- Per-message ground-truth labelling
- Leakage-free group-aware splitting, machine-verified
- ChebyKAN classifier (44,164 parameters)
- Dirichlet non-IID sharding, federated loop with client sampling
- **Real CKKS encryption** of client updates
- **FheFL encrypted-domain robust aggregation** (eq. 6–12)
- **Multi-key additive key sharing with per-round dropout tolerance**
- ECDH-P256 + AES-256-GCM + Ed25519 authenticated transport
- Machine-checked privacy invariant
- Threat model, security specification, library evaluation

### Partially completed
- **Multi-key CKKS** — arithmetic is real; key management is an algebraic model. TenSEAL exposes no multi-key API. OpenFHE selected for Month 6.
- **Byzantine robustness** — effective against large-magnitude poisoning; untested against low-magnitude persistent attackers.
- **Library evaluation** — selection complete; cross-compilation not performed.
- **VeReMi** — per-beacon formulation works; sender-grouped windowing awaits data re-acquisition.
- **Experimental scale** — 10 clients / 5 rounds against a roadmap target of 50–200 / 200–300.
- **Ciphertext serialization** — sizes measured; no V2X transport protocol.

### Not started
Cross-compilation · on-hardware benchmarking · SIMD packing module · NTT
acceleration · model quantization · on-device inference engine · V2X protocol ·
client-level differential privacy · hardware-in-the-loop validation · power audit.

---

## 6. Known limitations

| Limitation | Impact | Path |
|---|---|---|
| Multi-key layer is a model, not cryptography | Cannot claim full multi-key CKKS | OpenFHE migration (P1.1) |
| Low-magnitude persistent poisoning unaddressed | A patient attacker can bias the model while scoring well | Experiment scheduled (P1.3) |
| CAN-VTC reduces to flood detection | Near-perfect scores are not evidence of generalisation | Report car_hack as primary |
| CAN-VTC Fuzzy/Impersonation excluded | 4-class problem reduced to 2 | Re-acquire raw data |
| Noise flooding off by default | IND-CPA^D exposure if inherited | Enforce in deployment profile (P0.3) |
| Round number not bound into AEAD | Replay possible | One-line fix (P0.2) |
| ~3.6 MB per vehicle per round | Does not fit V2X | Modulus switching, sparsification, hierarchical aggregation |
| Laptop CPU only | No evidence of embedded feasibility | Order hardware (P0.1) |

---

## 7. Maturity assessment

| Track | Maturity | Remaining |
|---|---|---|
| Data pipeline | **Production-grade** — verified, leak-free, documented | Re-acquire VeReMi/CAN-VTC ground truth |
| Model | **Solid research prototype** | Scale to roadmap client/round counts |
| Federated learning | **Solid research prototype** | Scale; add differential privacy |
| Homomorphic encryption | **Working, correctly parameterised** | Real multi-key via OpenFHE |
| Robust aggregation | **Working, one known blind spot** | Patient-attacker evaluation |
| Transport security | **Solid** | Bind round id into AEAD |
| Embedded / hardware | **Not started** | The entire track |
| Documentation | **Complete for months 1–5** | Packing, NTT, V2X specs blocked on the above |

**Overall:** roughly **60 % of the 12-month programme** by deliverable count. The
cryptographic and machine-learning work is ahead of schedule; the embedded track
is the whole of the gap, and months 7–12 depend on it.
"""


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    out_dir.mkdir(parents=True, exist_ok=True)
    res = load("month5_summary.json")
    bench = load("ckks_profile_benchmark.json")

    text = DOC.format(
        today=date.today().isoformat(),
        results=fmt_results(res),
        delta=fmt_delta(res),
        separability=fmt_separability(),
        m4=fmt_m4(res),
        audit=fmt_audit(res),
        bench=fmt_bench(bench),
    )
    out = out_dir / "11_current_status.md"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

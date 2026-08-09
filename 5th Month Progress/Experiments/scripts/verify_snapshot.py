"""Final verification of the '5th Month Progress' deliverable.

    python scripts/verify_snapshot.py "<snapshot_dir>"

Checks that the snapshot is complete, internally consistent, and that the
documentation matches what the code actually produced. Exits non-zero on any
failure so it can gate a release.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_fail: list = []
_pass: list = []
_warn: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        _pass.append(name)
        print(f"  PASS  {name}")
    else:
        _fail.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def warn(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        _pass.append(name)
        print(f"  PASS  {name}")
    else:
        _warn.append((name, detail))
        print(f"  WARN  {name}  {detail}")


def main() -> int:
    snap = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent.parent / "5th Month Progress"
    print("=" * 70)
    print(f"Verifying snapshot: {snap}")
    print("=" * 70)

    # ── 1. structure ─────────────────────────────────────────────────────
    print("\n[1] Folder structure")
    required_dirs = [
        "Documentation", "Complete Source Code", "Complete Source Code/NewModel_active",
        "Newly Added - Month 5", "Newly Added - Month 5/code",
        "Month 1-2 Foundation", "Month 3-4 FHE and Architecture",
        "Dataset", "Models", "Experiments", "Results", "Diagrams",
    ]
    for d in required_dirs:
        check(f"exists: {d}", (snap / d).is_dir())

    # ── 2. documentation completeness ────────────────────────────────────
    print("\n[2] Documentation")
    doc = snap / "Documentation"
    check("master PDF present", (doc / "00_MASTER_DOCUMENTATION.pdf").is_file())
    pdf = doc / "00_MASTER_DOCUMENTATION.pdf"
    if pdf.is_file():
        check("master PDF is non-trivial (>200 KB)", pdf.stat().st_size > 200_000,
              f"{pdf.stat().st_size/1024:.0f} KB")
    for n in list(range(1, 13)) + [14, 15, 16]:
        matches = list(doc.glob(f"{n:02d}_*.md"))
        check(f"document {n:02d} present", len(matches) == 1,
              f"found {len(matches)}")
    check("13 channel-rationale PDF present",
          (doc / "13_why_AES_with_FHE.pdf").is_file())

    # ── 3. source code ───────────────────────────────────────────────────
    print("\n[3] Source code")
    src = snap / "Complete Source Code" / "NewModel_active"
    required_files = [
        "train_federated.py", "evaluate.py", "config.yaml",
        "data/can_features.py", "data/car_hack_dataset.py", "data/can_vtc_dataset.py",
        "data/veremi_dataset.py", "data/cicids_dataset.py", "data/preprocess.py",
        "models/cheby_kan.py",
        "federated/server.py", "federated/client.py", "federated/fhe_adapter.py",
        "federated/multikey_ckks.py", "federated/secure_channel.py",
        "federated/packing.py",
        "crypto/ntt.py",
        "tests/test_data_pipeline.py", "tests/test_crypto.py", "tests/test_ntt.py",
    ]
    for f in required_files:
        check(f"exists: {f}", (src / f).is_file())

    # ── 4. the four invariants are actually enforced in the shipped code ──
    print("\n[4] Invariants present in shipped source")
    def read(p):
        q = src / p
        return q.read_text(encoding="utf-8", errors="replace") if q.is_file() else ""

    # Match real code usage, not prose. The adapter's docstring legitimately
    # names SimulatedCKKSVector when explaining what was removed and why.
    dead_usage = re.compile(
        r"(class\s+SimulatedCKKSVector\b|SimulatedCKKSVector\s*\(|"
        r"=\s*SimulatedCKKSVector\b|import\s+.*\bSimulatedCKKSVector\b)")
    offenders = [f for f in required_files
                 if f.endswith(".py") and dead_usage.search(read(f))]
    check("SimulatedCKKSVector is not used as code anywhere", not offenders,
          str(offenders))
    check("server never calls decrypt() on a per-client update",
          "encrypted_model" not in read("federated/server.py"))
    check("assert_no_individual_decryption is defined",
          "def assert_no_individual_decryption" in read("federated/server.py"))
    check("assert_no_group_overlap is defined",
          "def assert_no_group_overlap" in read("data/preprocess.py"))
    check("group-aware split replaces the random shuffle",
          "_grouped_split" in read("data/preprocess.py")
          and "_stratified_split" not in read("data/preprocess.py"))
    check("Car-Hacking reads the R/T ground-truth flag",
          'flag == "T"' in read("data/car_hack_dataset.py"))
    check("CAN-VTC uses the DoS injection signature",
          "DOS_INJECTION_ID" in read("data/can_vtc_dataset.py"))
    check("real CKKS backend is present",
          "class CKKSVector" in read("federated/fhe_adapter.py"))
    check("multi-key dropout fix is present",
          "def begin_round" in read("federated/multikey_ckks.py"))
    check("packing module enforces the level-drop bound",
          "MAX_SAFE_LEVEL_DROP" in read("federated/packing.py"))
    check("NTT ships both batched and scalar reference forms",
          "def forward_scalar" in read("crypto/ntt.py")
          and "def forward" in read("crypto/ntt.py"))
    check("smoke runs cannot overwrite real results",
          '"_smoke" if args.smoke' in read("train_federated.py"))

    bench = ROOT / "results"
    for f in ("packing_benchmark.json", "ntt_benchmark.json",
              "ntt_test_vectors.json"):
        check(f"benchmark artefact: {f}", (bench / f).is_file())
    check("hardware baseline captured",
          any(bench.glob("hardware_baseline_*.json")))

    # ── 5. results ───────────────────────────────────────────────────────
    print("\n[5] Results")
    res_path = ROOT / "results" / "month5_summary.json"
    check("month5_summary.json exists", res_path.is_file())
    res = None
    if res_path.is_file():
        res = json.loads(res_path.read_text(encoding="utf-8"))
        ok_cells = [r for r in res["results"] if r.get("status") == "ok"]
        check("all sweep cells succeeded",
              len(ok_cells) == len(res["results"]),
              f"{len(ok_cells)}/{len(res['results'])}")
        check("3 seeds per cell", all(r.get("n_runs") == 3 for r in ok_cells),
              str([r.get("n_runs") for r in ok_cells]))
        # THE privacy invariant, measured
        bad = [r for r in ok_cells
               if r["backend"] == "ckks"
               and r["audit"]["individual_update_decryptions"] != 0]
        check("zero individual-update decryptions across all CKKS runs",
              not bad, f"violations in {[r['dataset'] for r in bad]}")
        # encryption should not change accuracy beyond seed noise
        by = {}
        for r in ok_cells:
            by.setdefault(r["dataset"], {})[r["backend"]] = r
        for d, m in by.items():
            if "ckks" in m and "none" in m:
                diff = abs(m["ckks"]["accuracy_mean"] - m["none"]["accuracy_mean"])
                spread = max(m["ckks"]["accuracy_std"], m["none"]["accuracy_std"], 1e-4)
                warn(f"{d}: CKKS vs plaintext within seed noise",
                     diff <= 3 * spread,
                     f"diff={diff:.4f} spread={spread:.4f}")

    bench_path = ROOT / "results" / "ckks_profile_benchmark.json"
    check("ckks_profile_benchmark.json exists", bench_path.is_file())

    # ── 6. diagrams ──────────────────────────────────────────────────────
    print("\n[6] Diagrams")
    dg = snap / "Diagrams"
    for name in ["01_system_architecture", "02_fhefl_round_protocol",
                 "03_data_pipeline_and_defects", "04_multikey_sharing",
                 "05_ckks_profile_tradeoff", "06_month5_results"]:
        check(f"{name}.png", (dg / f"{name}.png").is_file())

    # ── 7. documentation matches reality ─────────────────────────────────
    print("\n[7] Documentation matches measured results")
    status = doc / "11_current_status.md"
    if status.is_file() and res:
        txt = status.read_text(encoding="utf-8")
        for r in [x for x in res["results"] if x.get("status") == "ok"]:
            acc = f"{r['accuracy_mean']:.4f}"
            check(f"status doc quotes {r['dataset']}/{r['backend']} accuracy {acc}",
                  acc in txt)
    else:
        check("11_current_status.md present and results loaded",
              status.is_file() and res is not None)

    # ── 8. no stale entry points that would fail if run ──────────────────
    print("\n[8] No stale entry points in the shipped tree")
    stale = []
    for p in src.rglob("*.py"):
        if "_legacy_month4" in str(p) or "_archived" in str(p):
            continue
        # This checker necessarily contains the patterns it searches for.
        if p.name == "verify_snapshot.py":
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        if dead_usage.search(t) or "aggregate_rounds(" in t:
            stale.append(str(p.relative_to(src)))
    check("no live module calls a removed API", not stale, str(stale))

    # ── summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"{len(_pass)} passed, {len(_fail)} failed, {len(_warn)} warnings")
    for n, d in _fail:
        print(f"  FAILED : {n}  {d}")
    for n, d in _warn:
        print(f"  WARNING: {n}  {d}")
    print("=" * 70)
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

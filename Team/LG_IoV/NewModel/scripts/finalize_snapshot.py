"""Finalise the '5th Month Progress' deliverable in one pass.

    python scripts/finalize_snapshot.py "<snapshot_dir>"

Order matters: benchmark -> status doc -> diagrams -> PDF -> sync -> verify.
Each step depends on the outputs of the previous one, so this script is the
single reproducible way to rebuild the deliverable from the current code and
results.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
RESULTS = ROOT / "results"
PY = sys.executable

# Files that were created or substantially rewritten in Month 5.
MONTH5_FILES = [
    "federated/multikey_ckks.py", "federated/secure_channel.py",
    "federated/fhe_adapter.py", "federated/server.py", "federated/client.py",
    "federated/__init__.py",
    "data/car_hack_dataset.py", "data/can_vtc_dataset.py",
    "data/veremi_dataset.py", "data/can_features.py",
    "data/cicids_dataset.py", "data/preprocess.py",
    "data/build_dataset.py", "data/loader.py",
    "tests/test_data_pipeline.py", "tests/test_crypto.py",
    "scripts/benchmark_ckks_profiles.py", "scripts/run_all_experiments.py",
    "scripts/generate_diagrams.py", "scripts/build_master_pdf.py",
    "scripts/content.py", "scripts/build_status_doc.py",
    "scripts/verify_snapshot.py", "scripts/finalize_snapshot.py",
    "scripts/audit_feature_separability.py",
    "scripts/build_channel_rationale_pdf.py",
    "scripts/benchmark_packing.py", "scripts/benchmark_ntt.py",
    "scripts/benchmark_hardware.py",
    "federated/packing.py", "crypto/__init__.py", "crypto/ntt.py",
    "tests/test_ntt.py",
    "train_federated.py", "evaluate.py", "config.yaml",
]

EXCLUDE_DIRS = {"__pycache__", ".venv", ".pytest_cache", "node_modules", ".git"}


def step(n, title):
    print(f"\n{'=' * 70}\n[{n}] {title}\n{'=' * 70}", flush=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=str(ROOT), text=True, **kw)
    if r.returncode != 0:
        print(f"  !! step failed (rc={r.returncode})")
    return r.returncode


def copytree(src: Path, dst: Path, clean: bool = False):
    """Copy a tree, optionally wiping the destination first.

    ``clean=True`` matters: a plain additive copy leaves behind files that were
    since deleted or relocated in the source. That is how stale Month-4 scripts
    survived at the top level of the snapshot after being moved into
    ``_legacy_month4/`` — the snapshot then shipped modules that reference
    removed APIs and would fail if run.
    """
    if not src.exists():
        return 0
    if clean and dst.exists():
        shutil.rmtree(dst)
    n = 0
    for p in src.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix != ".pyc":
            rel = p.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            n += 1
    return n


def main() -> int:
    snap = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent.parent / "5th Month Progress"
    doc = snap / "Documentation"
    doc.mkdir(parents=True, exist_ok=True)

    # 0. Correctness gates. If these fail, nothing downstream is worth building.
    step(0, "Verification suites")
    rc_data = run([PY, str(ROOT / "tests" / "test_data_pipeline.py")])
    rc_crypto = run([PY, str(ROOT / "tests" / "test_crypto.py")])
    rc_ntt = run([PY, str(ROOT / "tests" / "test_ntt.py")])
    if rc_data or rc_crypto or rc_ntt:
        print("\n!! Correctness gates FAILED. Refusing to build the deliverable on\n"
              "   a pipeline whose experimental setup is not sound.")
        return 1

    # 0b. Rebuild the combined summary from whatever per-cell results exist.
    #     Cells with a result JSON are reused, so this is near-instant once the
    #     sweep has run — and it repairs a summary left stale by an interrupted
    #     sweep (both earlier runs were killed by process teardown).
    step("0b", "Rebuild month5_summary.json from per-cell results")
    run([PY, str(SCRIPTS / "run_all_experiments.py")])

    # 1a. Feature separability audit — catches both leakage and unusable
    #     formulations before any accuracy number is believed.
    step("1a", "Feature separability audit")
    run([PY, str(SCRIPTS / "audit_feature_separability.py")])

    # 1b. CKKS benchmark — must run alone; timings are contended otherwise.
    step("1b", "CKKS profile benchmark")
    run([PY, str(SCRIPTS / "benchmark_ckks_profiles.py")])

    # 1c-1e. Month 1-4 deliverable benchmarks (also timing-sensitive).
    step("1c", "Packing & encoding benchmark")
    run([PY, str(SCRIPTS / "benchmark_packing.py")])
    step("1d", "NTT benchmark + test-vector export")
    run([PY, str(SCRIPTS / "benchmark_ntt.py")])
    step("1e", "Hardware baseline")
    run([PY, str(SCRIPTS / "benchmark_hardware.py"), "--tag", "dev-laptop-x86"])

    # 2. Status document, generated from the result JSONs.
    step(2, "Generate 11_current_status.md from live results")
    run([PY, str(SCRIPTS / "build_status_doc.py"), str(doc)])

    # 3. Diagrams (now including the results chart).
    step(3, "Generate diagrams")
    run([PY, str(SCRIPTS / "generate_diagrams.py"), str(snap / "Diagrams")])

    # 4. PDFs.
    step(4, "Build master documentation PDF")
    run([PY, str(SCRIPTS / "build_master_pdf.py"), str(doc)])
    step("4b", "Build channel-rationale design note")
    run([PY, str(SCRIPTS / "build_channel_rationale_pdf.py"), str(doc)])

    # 5. Sync code + results into the snapshot.
    step(5, "Sync source, results and experiments into the snapshot")
    n = copytree(ROOT, snap / "Complete Source Code" / "NewModel_active", clean=True)
    print(f"  NewModel_active: {n} files (destination wiped first)")

    m5 = snap / "Newly Added - Month 5" / "code"
    if m5.exists():
        shutil.rmtree(m5)
    cnt = 0
    for rel in MONTH5_FILES:
        s = ROOT / rel
        if s.is_file():
            t = m5 / rel
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, t)
            cnt += 1
    print(f"  Newly Added - Month 5/code: {cnt} files")

    res_dst = snap / "Results" / "month5"
    res_dst.mkdir(parents=True, exist_ok=True)
    rc = 0
    for p in RESULTS.glob("*.json"):
        shutil.copy2(p, res_dst / p.name)
        rc += 1
    print(f"  Results/month5: {rc} files")

    m5res = snap / "Newly Added - Month 5" / "results"
    m5res.mkdir(parents=True, exist_ok=True)
    for p in RESULTS.glob("*.json"):
        shutil.copy2(p, m5res / p.name)

    m5dia = snap / "Newly Added - Month 5" / "diagrams"
    m5dia.mkdir(parents=True, exist_ok=True)
    for p in (snap / "Diagrams").glob("*.png"):
        shutil.copy2(p, m5dia / p.name)

    exp = snap / "Experiments"
    (exp / "scripts").mkdir(parents=True, exist_ok=True)
    (exp / "tests").mkdir(parents=True, exist_ok=True)
    (exp / "run_logs").mkdir(parents=True, exist_ok=True)
    for p in SCRIPTS.glob("*.py"):
        shutil.copy2(p, exp / "scripts" / p.name)
    for p in (ROOT / "tests").glob("*.py"):
        shutil.copy2(p, exp / "tests" / p.name)
    for p in (ROOT / "run_logs").glob("*.log"):
        shutil.copy2(p, exp / "run_logs" / p.name)
    print("  Experiments: scripts, tests and run logs synced")

    mdl = snap / "Models" / "month5_ckks"
    mdl.mkdir(parents=True, exist_ok=True)
    for p in (ROOT / "checkpoints").glob("federated_*_s*.pt"):
        shutil.copy2(p, mdl / p.name)
    print(f"  Models: {len(list(mdl.glob('*.pt')))} checkpoints")

    # 6. Verify.
    step(6, "Verify the snapshot")
    rc = run([PY, str(SCRIPTS / "verify_snapshot.py"), str(snap)])

    print(f"\n{'=' * 70}")
    print("FINALISE COMPLETE" if rc == 0 else "FINALISE COMPLETE — verification reported failures")
    print(f"{'=' * 70}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate the architecture and results diagrams used in the documentation.

Writes PNG (for the PDF) and SVG (for the web/repo) into ``../Diagrams`` or a
directory given as argv[1].

    python scripts/generate_diagrams.py "<out_dir>"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

INK = "#1a1a2e"
BLUE = "#2d6cdf"
GREEN = "#1e9e6a"
RED = "#d64545"
AMBER = "#d98324"
GREY = "#8a8f98"
LIGHT = "#eef2f8"


def _box(ax, x, y, w, h, text, fc=LIGHT, ec=BLUE, fs=9, weight="normal", tc=INK):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor=fc, edgecolor=ec, linewidth=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, weight=weight, linespacing=1.45)


def _arrow(ax, xy1, xy2, color=INK, style="-|>", lw=1.5, ls="-"):
    ax.add_patch(FancyArrowPatch(
        xy1, xy2, arrowstyle=style, mutation_scale=13,
        color=color, linewidth=lw, linestyle=ls,
        shrinkA=2, shrinkB=2))


def _canvas(w=12, h=7):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def _save(fig, out_dir: Path, name: str):
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"{name}.{ext}", dpi=170,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {name}.png / .svg")


# ── 1. system architecture ───────────────────────────────────────────────
def diagram_system(out: Path):
    fig, ax = _canvas(12, 7.2)
    ax.text(0.5, 0.965, "System Architecture — Privacy-Preserving Collaborative IDS for IoV",
            ha="center", fontsize=14, weight="bold", color=INK)

    for i, x in enumerate([0.03, 0.245, 0.46]):
        _box(ax, x, 0.60, 0.185, 0.26,
             f"Vehicle {i+1}\n\nCAN bus + V2X\nlocal ChebyKAN\nkey share $s_{i+1}$",
             fc="#f2f7ff", ec=BLUE, fs=8.5)
    ax.text(0.735, 0.73, ". . .", fontsize=17, color=GREY, ha="center")

    _box(ax, 0.79, 0.60, 0.185, 0.26,
         "Vehicle N\n\nCAN bus + V2X\nlocal ChebyKAN\nkey share $s_N$",
         fc="#f2f7ff", ec=BLUE, fs=8.5)

    ax.text(0.5, 0.545, "TRUST BOUNDARY 1 — V2X radio link  ·  ECDH-P256 + AES-256-GCM + Ed25519 mutual auth",
            ha="center", fontsize=8.5, color=RED, weight="bold")
    ax.plot([0.02, 0.98], [0.522, 0.522], ls="--", color=RED, lw=1.2)

    _box(ax, 0.30, 0.375, 0.40, 0.10,
         "RSU / Edge relay — forwards ciphertext, learns nothing",
         fc="#fff8ec", ec=AMBER, fs=9)

    ax.text(0.5, 0.335, "TRUST BOUNDARY 2 — aggregation interface  ·  adversary: semi-honest server operator",
            ha="center", fontsize=8.5, color=RED, weight="bold")
    ax.plot([0.02, 0.98], [0.312, 0.312], ls="--", color=RED, lw=1.2)

    _box(ax, 0.135, 0.07, 0.73, 0.215,
         "AGGREGATION SERVER  (semi-honest)\n\n"
         "holds plaintext GLOBAL model only\n"
         "encrypted squared distance  $[d^u] = g^Tg + [(f^u-2g)^T f^u]$   (eq. 11)\n"
         "non-poisoning rate  $p^u = 1 - d^u / \\Sigma_j d^j$   (eq. 7)\n"
         "homomorphic weighted sum  $\\Sigma_u\\, p^u f^u$   (eq. 9)  →  decrypt AGGREGATE ONLY",
         fc="#eefaf4", ec=GREEN, fs=8.8)

    for x in [0.1225, 0.3375, 0.5525, 0.8825]:
        _arrow(ax, (x, 0.60), (x, 0.478), color=BLUE)
        _arrow(ax, (x + 0.012, 0.478), (x + 0.012, 0.60), color=GREEN, ls=":")
    _arrow(ax, (0.5, 0.375), (0.5, 0.288), color=BLUE)

    ax.text(0.055, 0.023, "→ encrypted update (client→server)", fontsize=8, color=BLUE)
    ax.text(0.60, 0.023, "⇢ plaintext global model (broadcast, not secret)",
            fontsize=8, color=GREEN)
    _save(fig, out, "01_system_architecture")


# ── 2. one FheFL round ───────────────────────────────────────────────────
def diagram_round(out: Path):
    fig, ax = _canvas(12, 7.6)
    ax.text(0.5, 0.965, "One Federated Round — FheFL Multi-Key CKKS Protocol",
            ha="center", fontsize=14, weight="bold", color=INK)

    steps = [
        ("1", "Server broadcasts the plaintext global model $g_{i-1}$\n"
              "over the authenticated channel", GREEN),
        ("2", "Each vehicle trains locally on its non-IID shard\n"
              "(Dirichlet $\\alpha=0.3$), producing $f^u$", BLUE),
        ("3", "Vehicle encrypts: $[f^u] \\leftarrow \\mathrm{CKKS.Enc}(f^u)$\n"
              "and uploads the masked key share $ss_u = s_u + \\Sigma_{j\\neq u} s_{u,j}$", BLUE),
        ("4", "Server re-scopes pairwise masks to THIS round's participants,\n"
              "then reconstructs $s = \\Sigma_u ss_u$   (eq. 10 — the dropout fix)", AMBER),
        ("5", "Server computes $[d^u]$ homomorphically — one ciphertext×ciphertext\n"
              "multiply; individual updates stay encrypted   (eq. 11)", AMBER),
        ("6", "Non-poisoning rates $p^u$: outliers down-weighted, not excluded\n"
              "$\\Sigma_u p^u = U-1$   (eq. 7, 8)", AMBER),
        ("7", "Homomorphic weighted aggregation $\\Sigma_u p^u [f^u]$,\n"
              "then decrypt the AGGREGATE ONLY   (eq. 9)", GREEN),
    ]
    y = 0.875
    for num, text, col in steps:
        _box(ax, 0.055, y - 0.088, 0.052, 0.078, num, fc=col, ec=col,
             fs=13, weight="bold", tc="white")
        _box(ax, 0.125, y - 0.088, 0.82, 0.078, text, fc=LIGHT, ec=col, fs=9)
        if y > 0.30:
            _arrow(ax, (0.081, y - 0.088), (0.081, y - 0.118), color=GREY)
        y -= 0.118

    _box(ax, 0.125, 0.022, 0.82, 0.062,
         "INVARIANT (asserted every round):  individual_update_decryptions == 0",
         fc="#eefaf4", ec=GREEN, fs=10, weight="bold")
    _save(fig, out, "02_fhefl_round_protocol")


# ── 3. data pipeline + the two defects it fixes ──────────────────────────
def diagram_pipeline(out: Path):
    fig, ax = _canvas(12, 7.4)
    ax.text(0.5, 0.965, "Data Pipeline — and the Two Defects Fixed in Month 5",
            ha="center", fontsize=14, weight="bold", color=INK)

    _box(ax, 0.03, 0.78, 0.17, 0.115, "Raw captures\nCAN / flow / V2X", fc=LIGHT, ec=GREY, fs=9)
    _arrow(ax, (0.20, 0.838), (0.245, 0.838))
    _box(ax, 0.245, 0.78, 0.20, 0.115,
         "Per-MESSAGE labels\nR/T flag · 0x000 · attack col", fc="#eefaf4", ec=GREEN, fs=8.5)
    _arrow(ax, (0.445, 0.838), (0.49, 0.838))
    _box(ax, 0.49, 0.78, 0.20, 0.115,
         "46-D feature vector\nwindow=64, stride=16", fc=LIGHT, ec=BLUE, fs=8.8)
    _arrow(ax, (0.69, 0.838), (0.735, 0.838))
    _box(ax, 0.735, 0.78, 0.235, 0.115,
         "Contiguous BLOCKS\nno window crosses a boundary", fc="#eefaf4", ec=GREEN, fs=8.5)

    _arrow(ax, (0.85, 0.78), (0.85, 0.715))
    _box(ax, 0.60, 0.60, 0.37, 0.108,
         "Group-aware split — whole blocks to one split\n70 / 15 / 15,  assert_no_group_overlap",
         fc="#eefaf4", ec=GREEN, fs=8.8)
    _arrow(ax, (0.60, 0.654), (0.50, 0.654))
    _box(ax, 0.28, 0.60, 0.21, 0.108,
         "Dirichlet non-IID\nsharding  $\\alpha=0.3$", fc=LIGHT, ec=BLUE, fs=8.8)

    # D1
    ax.text(0.255, 0.505, "Defect D1 — labelling", fontsize=11, weight="bold", color=INK, ha="center")
    _box(ax, 0.03, 0.30, 0.45, 0.185,
         "BEFORE   label = source filename\n\n"
         "every window of DoS_dataset.csv → 'DoS'\n"
         "→ learns WHICH FILE, not whether an\n"
         "   intrusion is present\n"
         "→ CAN-VTC reported 100.0 % accuracy",
         fc="#fdeeee", ec=RED, fs=8.5)
    _box(ax, 0.52, 0.30, 0.45, 0.185,
         "AFTER   label = injected messages\n\n"
         "attack captures yield BOTH classes\n"
         "Car-Hacking DoS: 3,339 attack / 4,049 normal\n"
         "→ file identity is no longer a shortcut\n"
         "→ measures intrusion detection",
         fc="#eefaf4", ec=GREEN, fs=8.5)

    # D2
    ax.text(0.255, 0.245, "Defect D2 — split leakage", fontsize=11, weight="bold", color=INK, ha="center")
    _box(ax, 0.03, 0.035, 0.45, 0.185,
         "BEFORE   random per-window shuffle\n\n"
         "windows overlap 75 % (48 of 64 messages)\n"
         "near-duplicates land on both sides of\n"
         "   the train/test boundary\n"
         "→ test accuracy measured memorisation",
         fc="#fdeeee", ec=RED, fs=8.5)
    _box(ax, 0.52, 0.035, 0.45, 0.185,
         "AFTER   whole contiguous blocks\n\n"
         "a block is never split across sets\n"
         "overlapping windows always land together\n"
         "assert_no_group_overlap enforces it\n"
         "→ test accuracy measures generalisation",
         fc="#eefaf4", ec=GREEN, fs=8.5)
    _save(fig, out, "03_data_pipeline_and_defects")


# ── 4. multi-key mask cancellation ───────────────────────────────────────
def diagram_multikey(out: Path):
    fig, ax = _canvas(12, 6.8)
    ax.text(0.5, 0.955, "FheFL Distributed Multi-Key Sharing — and the Dropout Fix",
            ha="center", fontsize=14, weight="bold", color=INK)

    ax.text(0.5, 0.885,
            "The secret key is never assembled anywhere:   $s = \\Sigma_u s_u$   (eq. 10)",
            ha="center", fontsize=10.5, color=INK)

    for i, x in enumerate([0.05, 0.28, 0.51, 0.74]):
        _box(ax, x, 0.665, 0.185, 0.155,
             f"Vehicle {i+1}\nholds $s_{i+1}$\nuploads $ss_{i+1}$",
             fc="#f2f7ff", ec=BLUE, fs=8.5)

    _box(ax, 0.10, 0.455, 0.80, 0.16,
         "$ss_u = s_u + \\Sigma_{j \\neq u}\\, s_{u,j}$      with      $s_{i,j} = -s_{j,i}$\n\n"
         "$\\Sigma_u ss_u \\;=\\; \\Sigma_u s_u \\;+\\; [\\, \\Sigma_u \\Sigma_{j \\neq u} s_{u,j} = 0 \\,] \\;=\\; s$",
         fc=LIGHT, ec=INK, fs=11)

    _box(ax, 0.05, 0.245, 0.42, 0.175,
         "THE GAP IN THE PAPER\n\n"
         "pairwise secrets are fixed at enrolment,\n"
         "but a random subset participates each round\n"
         "→ one vehicle offline ⇒ masks do not cancel\n"
         "→ decryption returns GARBAGE, silently",
         fc="#fdeeee", ec=RED, fs=8.5)

    _box(ax, 0.53, 0.245, 0.42, 0.175,
         "OUR FIX\n\n"
         "begin_round(participants) re-derives the\n"
         "pairwise masks for exactly this round's set\n"
         "(HMAC-SHA256 from a per-round nonce)\n"
         "→ cancellation holds by construction\n"
         "→ strict_dropout_check raises, never corrupts",
         fc="#eefaf4", ec=GREEN, fs=8.5)

    _box(ax, 0.10, 0.045, 0.80, 0.155,
         "Security (FheFL Theorem 1): to recover one honest vehicle's update the server\n"
         "must collude with U−1 vehicles.   Requires ≥2 non-colluding vehicles — enforced in code.\n"
         "Verified: masks cancel for U ∈ {2,5,10,25} and for the surviving subset {0,1,2,5,7} of 8.",
         fc="#eefaf4", ec=GREEN, fs=9)
    _save(fig, out, "04_multikey_sharing")


# ── 5. measured CKKS profile trade-off ───────────────────────────────────
def diagram_profiles(out: Path):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.1))
    fig.suptitle("Measured CKKS Profile Trade-off — why strict FheFL costs a larger ring",
                 fontsize=13, weight="bold", color=INK, y=1.02)
    names = ["practical\nN=8192\n[60,40,40,60]", "strict\nN=16384\n[60,40,40,40,60]"]
    cols = [BLUE, AMBER]

    for ax, (vals, title, unit) in zip(axes, [
        ([326.6, 836.1], "Ciphertext size", "KB"),
        ([18.0, 67.7], "Encrypted distance (eq. 11)", "ms"),
        ([2, 3], "Multiplicative levels", "levels"),
    ]):
        bars = ax.bar(names, vals, color=cols, width=0.55)
        ax.set_title(title, fontsize=10.5, color=INK)
        ax.set_ylabel(unit, fontsize=9)
        ax.tick_params(labelsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(0, max(vals) * 1.25)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.03, f"{v:g}",
                    ha="center", fontsize=9, weight="bold", color=INK)

    axes[2].text(0.5, -0.36,
                 "N=8192 with a 3-level chain (240 bits) is REJECTED — exceeds the 218-bit\n"
                 "ceiling for 128-bit security. Buying a level requires doubling the ring.",
                 transform=axes[2].transAxes, ha="center", fontsize=8.5, color=RED)
    fig.tight_layout()
    _save(fig, out, "05_ckks_profile_tradeoff")


# ── 6. results, from the actual sweep ────────────────────────────────────
def diagram_results(out: Path):
    path = RESULTS / "month5_summary.json"
    if not path.exists():
        print("  (skipping results diagram — sweep output not present yet)")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [r for r in data["results"] if r.get("status") == "ok"]
    if not rows:
        print("  (skipping results diagram — no successful runs)")
        return

    datasets = sorted({r["dataset"] for r in rows})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    fig.suptitle("Month-5 Results — encryption on vs off (3 seeds, mean ± std)",
                 fontsize=13, weight="bold", color=INK, y=1.02)

    for ax, (key, err, title) in zip(axes, [
        ("accuracy_mean", "accuracy_std", "Accuracy"),
        ("roc_auc_mean", "roc_auc_std", "ROC-AUC"),
    ]):
        w = 0.36
        xs = range(len(datasets))
        for off, backend, col in [(-w/2, "ckks", BLUE), (w/2, "none", GREY)]:
            vals, errs = [], []
            for d in datasets:
                m = [r for r in rows if r["dataset"] == d and r["backend"] == backend]
                vals.append(m[0][key] if m else 0.0)
                errs.append(m[0][err] if m else 0.0)
            ax.bar([x + off for x in xs], vals, w, yerr=errs, capsize=3,
                   label=("CKKS encrypted" if backend == "ckks" else "plaintext baseline"),
                   color=col)
        ax.set_xticks(list(xs)); ax.set_xticklabels(datasets, fontsize=9)
        ax.set_ylim(0, 1.08); ax.set_title(title, fontsize=11, color=INK)
        ax.axhline(0.5, ls=":", color=RED, lw=1)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=8.5, frameon=False)
    fig.tight_layout()
    _save(fig, out, "06_month5_results")


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent.parent / "5th Month Progress" / "Diagrams"
    out.mkdir(parents=True, exist_ok=True)
    print(f"writing diagrams to {out}")
    diagram_system(out)
    diagram_round(out)
    diagram_pipeline(out)
    diagram_multikey(out)
    diagram_profiles(out)
    diagram_results(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

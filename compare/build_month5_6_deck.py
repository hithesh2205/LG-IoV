"""Build Month_5_6_Progress_Update.pptx in the style of ChebyKAN_updated.pptx.

Starts from a copy of ChebyKAN_updated.pptx (to inherit its theme, fonts and
16:9 slide size), strips every existing slide, then writes the Month 5-6 deck.

Run from the repo root with the Windows Python that has python-pptx:
    "/c/Users/Thrish_Sudha/AppData/Local/Programs/Python/Python312/python.exe" \
        compare/build_month5_6_deck.py
"""
from __future__ import annotations

import copy
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.enum.text import PP_ALIGN

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "ChebyKAN_updated.pptx"
OUTPUT = REPO / "Month_5_6_Progress_Update.pptx"

BODY_L0 = Pt(16)
BODY_L1 = Pt(13)
TABLE_FONT = Pt(12)
TABLE_HEAD = Pt(12)


# --------------------------------------------------------------------------- #
# template plumbing
# --------------------------------------------------------------------------- #
def delete_all_slides(prs: Presentation) -> None:
    xml_slides = prs.slides._sldIdLst
    for sld_id in list(xml_slides):
        rId = sld_id.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/"
            "relationships}id"
        )
        prs.part.drop_rel(rId)
        xml_slides.remove(sld_id)


def layout_by_name(prs: Presentation, *names, fallback_idx: int):
    for lay in prs.slide_layouts:
        if lay.name in names:
            return lay
    return prs.slide_layouts[fallback_idx]


def body_placeholder(slide):
    """Return the first non-title placeholder on the slide, else None."""
    title = slide.shapes.title
    for ph in slide.placeholders:
        if title is not None and ph._element is title._element:
            continue
        return ph
    return None


# --------------------------------------------------------------------------- #
# slide builders
# --------------------------------------------------------------------------- #
def add_title_slide(prs, title, subtitle_lines):
    slide = prs.slides.add_slide(
        layout_by_name(prs, "Title Slide", fallback_idx=0)
    )
    if slide.shapes.title is not None:
        slide.shapes.title.text = title
    sub = body_placeholder(slide)
    if sub is not None:
        tf = sub.text_frame
    else:
        box = slide.shapes.add_textbox(
            Emu(1524000), Emu(4400000), Emu(9144000), Emu(1800000)
        )
        tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(subtitle_lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = PP_ALIGN.CENTER
        for run in p.runs:
            run.font.size = Pt(18)
    return slide


def add_content_slide(prs, title, bullets):
    """bullets: list of (level:int, text:str)."""
    slide = prs.slides.add_slide(
        layout_by_name(prs, "Title and Content", fallback_idx=1)
    )
    slide.shapes.title.text = title
    body = body_placeholder(slide)
    tf = body.text_frame
    tf.word_wrap = True
    for i, (level, text) in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.level = level
        for run in p.runs:
            run.font.size = BODY_L0 if level == 0 else BODY_L1
    return slide


def add_table_slide(prs, title, col_widths_emu, header, rows, notes,
                    table_top_emu=Emu(1500000), table_height_emu=Emu(2600000)):
    slide = prs.slides.add_slide(
        layout_by_name(prs, "Title and Content", fallback_idx=1)
    )
    slide.shapes.title.text = title

    n_rows = len(rows) + 1
    n_cols = len(header)
    left = Emu(685800)
    width = Emu(sum(col_widths_emu))
    gfx = slide.shapes.add_table(
        n_rows, n_cols, left, table_top_emu, width, table_height_emu
    )
    table = gfx.table
    for c, w in enumerate(col_widths_emu):
        table.columns[c].width = Emu(w)

    for c, text in enumerate(header):
        cell = table.cell(0, c)
        cell.text = text
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                run.font.bold = True
                run.font.size = TABLE_HEAD
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(text)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = TABLE_FONT

    # notes below the table
    note_top = Emu(table_top_emu + table_height_emu + 250000)
    box = slide.shapes.add_textbox(
        left, note_top, width, Emu(6858000 - note_top - 300000)
    )
    tf = box.text_frame
    tf.word_wrap = True
    for i, (level, text) in enumerate(notes):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.level = level
        for run in p.runs:
            run.font.size = BODY_L0 if level == 0 else BODY_L1
    return slide


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #
def build():
    prs = Presentation(str(TEMPLATE))
    delete_all_slides(prs)

    # 1
    add_title_slide(
        prs,
        "Privacy-Preserving Collaborative IDS for "
        "Internet-of-Vehicle Networks",
        [
            "Month 5–6 Progress Update",
            "[Presenter names]",
            "With thanks to Dr. Durga, Dr. Uma, Dr. Anusuya, Dr. Praveen",
        ],
    )

    # 2
    add_content_slide(prs, "Recap from Last Meeting", [
        (0, "ChebyKAN adopted as the IDS trunk — 44,164 parameters, "
            "14× smaller than the MamKANformer trunk"),
        (0, "Layer-wise homomorphic federated aggregation demonstrated "
            "across all four datasets"),
        (0, "Committed to multi-key CKKS (FheFL, arXiv:2306.05112) so the "
            "server never sees an individual plaintext update"),
        (0, "Review action item: present the mathematical foundations of "
            "CKKS — addressed in this deck"),
    ])

    # 3
    add_content_slide(prs, "Contents", [
        (0, "Mathematical foundations of CKKS"),
        (0, "Baseline: FHE vs No-FHE — the control established before "
            "model quantization"),
        (0, "System validation — proactive data-engineering validation"),
        (0, "V2X communication protocol — FHE with AES / ECDH"),
        (0, "Embedded porting and multi-key CKKS — the OpenFHE / C++ "
            "pathway"),
        (0, "Status against LG Month 5–6 expectations and the Month 6 "
            "plan"),
    ])

    # 4
    add_content_slide(prs, "Where We Stand (Month 5–6)", [
        (0, "Month 5 of 12"),
        (0, "Overdue Month 1–4 deliverables closed this month: threat "
            "model, security specification, library evaluation, packing & "
            "encoding module, NTT reference implementation"),
        (0, "105 automated tests guarding data integrity, cryptographic "
            "correctness, and the privacy invariant — all passing"),
        (0, "Real CKKS now replaces the Month-4 placeholder throughout the "
            "federated loop"),
        (0, "Ahead of schedule: the homomorphic aggregator (an LG Month "
            "7–12 item) is implemented now"),
    ])

    # 5
    add_content_slide(prs, "Mathematical Foundations I — The CKKS Scheme", [
        (0, "Operates natively on vectors of real numbers — "
            "neural-network weights are exactly that"),
        (0, "Ring: R_q = Z_q[x] / (x^N + 1); secret key s is a small "
            "polynomial; modulus q; scaling factor Δ"),
        (0, "Encode: real vector → integer polynomial by scaling "
            "×Δ"),
        (0, "Encrypt with public key (a, b), b = −a·s + e:  "
            "c = (c0, c1),  c0 = b·u + e1 + m,  c1 = a·u + e2"),
        (0, "Decrypt:  m' = c0 + c1·s (mod q),  then divide by Δ"),
        (0, "Security rests on Ring-LWE: recovering s from b = a·s + e "
            "is believed hard even for quantum adversaries"),
    ])

    # 6
    add_table_slide(
        prs,
        "Mathematical Foundations II — Homomorphic Aggregation "
        "(worked example)",
        col_widths_emu=[4300000, 6500000],
        header=["Step", "Value"],
        rows=[
            ["Client plaintext weights",
             "0.10, 0.12, 0.09   (scaling factor Δ = 1000)"],
            ["Server step",
             "Add the three ciphertexts componentwise — no individual "
             "value is decrypted"],
            ["Decrypt aggregate, ÷ Δ, ÷ 3", "0.10733"],
            ["True mean (no encryption)", "0.10330"],
            ["Error at this toy modulus", "≈ 4 × 10⁻³"],
            ["Error at real CKKS parameters",
             "≤ 3 × 10⁻⁸"],
        ],
        notes=[
            (0, "This is federated averaging in the encrypted domain:  "
                "Enc(W_global) = Σ w_i · Enc(W_i)"),
        ],
        table_height_emu=Emu(3000000),
    )

    # 7
    add_content_slide(
        prs,
        "Mathematical Foundations III — Noise, Depth, and Why It Shapes "
        "the Design", [
            (0, "Every ciphertext carries growing noise; every ciphertext "
                "× ciphertext multiply consumes one prime (\"level\") "
                "from the modulus chain via rescaling"),
            (0, "A chain of L primes supports L − 2 multiplications "
                "— the depth budget is the binding design constraint"),
            (0, "Security is set by ring dimension N vs total modulus bits: "
                "at N = 8192, 128-bit security allows ≤ 218 bits "
                "→ 2 multiplicative levels"),
            (0, "Homomorphic addition is about 490× cheaper than "
                "ciphertext multiplication (measured)"),
            (0, "Consequence: the FheFL protocol is engineered to need as "
                "few ciphertext × ciphertext multiplies as possible"),
        ])

    # 8
    add_content_slide(prs, "Baseline: FHE vs No-FHE — Setup", [
        (0, "Purpose: the mandatory control before Month 5–6 model "
            "quantization — measure what encryption costs before "
            "adding a second approximation"),
        (0, "Real TenSEAL CKKS on one arm, exact plaintext on the other, "
            "everything else held identical"),
        (0, "3 seeds · 10 simulated vehicles · 5 federated rounds "
            "· Dirichlet α = 0.3 · 70% client sampling"),
        (0, "The two backends are asserted bitwise-identical on the "
            "aggregation path (test_backend_equivalence)"),
    ])

    # 9
    add_table_slide(
        prs,
        "Baseline: FHE vs No-FHE — Results",
        col_widths_emu=[2450000, 1950000, 2050000, 1500000, 2850000],
        header=["Dataset", "CKKS acc", "Plaintext acc", "Δ", "Verdict"],
        rows=[
            ["CAN-VTC", "1.0000", "1.0000", "+0.0000", "within seed noise"],
            ["Car-Hacking", "0.9977", "0.9981", "−0.0004",
             "within seed noise"],
            ["CICIDS-2017", "0.9555", "0.9542", "+0.0012",
             "within seed noise"],
            ["VeReMi", "0.4839", "0.4851", "−0.0012",
             "within seed noise"],
        ],
        notes=[
            (0, "Finding: encryption costs no accuracy — the "
                "CKKS/plaintext gap is smaller than seed-to-seed variance "
                "on every dataset"),
            (0, "CAN-VTC = 100% is flood detection, not generalisation: the "
                "DoS attack floods one novel CAN ID (51% of traffic), "
                "separable by a single feature at 13σ. Split verified "
                "clean — the task is simply easy, not the earlier "
                "filename-label defect."),
            (0, "Car-Hacking is the CAN benchmark we stand behind: 5 real "
                "classes, best single feature only 0.94, injection density "
                "12–24%"),
            (0, "VeReMi is a near-chance lower bound: the cleaned export "
                "dropped sender IDs, so the misbehaviour signal cannot be "
                "expressed — re-acquisition required"),
        ],
        table_top_emu=Emu(1350000),
        table_height_emu=Emu(2100000),
    )

    # 10
    add_content_slide(prs, "What This Baseline Establishes", [
        (0, "Real CKKS now replaces the Month-4 placeholder "
            "(SimulatedCKKSVector), so this is a controlled experiment for "
            "the first time"),
        (0, "Accuracy is encryption-invariant → any accuracy change "
            "under INT8 quantization in Month 5–6 is attributable to "
            "quantization alone"),
        (0, "Measured cryptographic cost per client update (44k parameters): "
            "encrypt ~42 ms · encrypted distance ~118–230 ms "
            "· aggregation ~5–52 ms · wire size 2.47 MB"),
    ])

    # 11
    add_content_slide(
        prs,
        "System Validation — Proactive Data-Engineering Validation", [
            (0, "Before building the multi-key layer, we ran a full "
                "validation pass over the existing pipeline: check the "
                "foundation before adding a floor"),
            (0, "Seven issues identified and all fixed, each now covered by "
                "a regression test:"),
            (1, "Ground-truth labels now per-message (HCRL R/T flag), not "
                "per-file"),
            (1, "Train/test split now group-aware by contiguous block "
                "— no window leakage"),
            (1, "FHE vs No-FHE now a controlled comparison (real CKKS, "
                "bitwise-checked)"),
            (1, "Server no longer decrypts individual client updates "
                "— FheFL scoring replaces Multi-Krum"),
            (1, "Transport security (AES / ECDH) restored"),
            (1, "VeReMi formulation diagnosed (needs sender IDs); "
                "documentation drift corrected"),
            (0, "105 assertions across the data, crypto, and NTT test "
                "suites — all passing"),
        ])

    # 12
    add_content_slide(
        prs,
        "System Validation — Effect on Results and the Privacy Invariant",
        [
            (0, "Headline accuracy figures were revised on the corrected "
                "pipeline: Car-Hacking 0.74 → 0.998 (fixed labels made "
                "the task well-posed); CICIDS 0.982 → 0.955 (leakage "
                "removed); CAN-VTC and VeReMi not comparable across "
                "formulations"),
            (0, "These movements are the experiment starting to measure the "
                "right thing"),
            (0, "Privacy invariant, machine-checked every round: individual "
                "client updates decrypted = 0 on all four datasets across 5 "
                "rounds each; only the aggregate is decrypted"),
        ])

    # 13
    add_content_slide(
        prs,
        "V2X Communication Protocol — FHE with AES / ECDH", [
            (0, "Maps to LG Month 5–6: Ciphertext Serialization & "
                "Communication Protocol"),
            (0, "Two complementary layers, not alternatives:"),
            (1, "FHE → payload confidentiality from the aggregation "
                "server"),
            (1, "AES-256-GCM / ECDH-P256 / Ed25519 → authentication, "
                "integrity, replay resistance, Sybil resistance on the "
                "radio link"),
            (0, "FHE provides none of the second list; removing the channel "
                "in Month 4 traded a working control for a slogan"),
            (0, "Status: the transport channel is restored and integrated; "
                "mutual-auth handshake tested (test_secure_channel)"),
            (0, "Open Month 5–6 work: serialization format and "
                "versioning; fragmentation / reassembly over DSRC; the "
                "bandwidth problem"),
        ])

    # 14
    add_content_slide(prs, "V2X — The Bandwidth Problem", [
        (0, "One 44k-parameter update = 2.47 MB encrypted (~915 DSRC "
            "frames); a 50-vehicle round ≈ 180 MB — does not fit "
            "a V2X budget"),
        (0, "Delivered: Optimized Packing & Encoding module — 29.6% "
            "lossless reduction via level-dropped transmission, verified at "
            "zero accuracy cost"),
        (0, "Further levers: seed compression (~50%, needs OpenFHE) · "
            "sparsification (needs an accuracy study) · hierarchical "
            "RSU pre-aggregation"),
        (0, "Hierarchical aggregation is likely mandatory — an "
            "architecture decision to take early"),
    ])

    # 15
    add_content_slide(
        prs,
        "Embedded Porting and Multi-Key CKKS — The OpenFHE / C++ Pathway",
        [
            (0, "Maps to LG Month 5–6: Embedded Porting & Quantization"),
            (0, "Current multi-key layer: the homomorphic arithmetic is real "
                "CKKS; key management is an algebraic model — TenSEAL "
                "exposes no multi-key or threshold API"),
            (0, "Library evaluation delivered: OpenFHE selected — the "
                "only candidate with threshold / multiparty CKKS AND a "
                "cross-compilable C++17 core AND Python bindings"),
            (0, "The C++ core is the pathway to embedded: keeps the PyTorch "
                "training pipeline via Python bindings while giving a native "
                "core to port and quantize"),
            (0, "Migration plan (~12 working days): M1 install & verify "
                "· M2 port CKKSVector behind the existing interface "
                "· M3 real threshold key generation and distributed "
                "decryption · M4 native noise flooding · M5 re-run "
                "the full sweep"),
            (0, "Software groundwork already delivered: packing & encoding "
                "module (29.6% lossless); NTT reference implementation "
                "(11.22× over schoolbook, bit-exact test vectors "
                "exported)"),
        ])

    # 16
    add_content_slide(
        prs,
        "Status vs LG Month 5–6 Expectations, and the Month 6 Plan", [
            (0, "Ciphertext serialization & comms protocol: partial — "
                "authenticated transport channel complete; serialization + "
                "fragmentation spec open"),
            (0, "Model quantization: not started — encryption-neutral "
                "accuracy baseline now established as the control"),
            (0, "On-device inference engine / embedded executable: pathway "
                "defined via the OpenFHE + C++ core migration"),
            (0, "Homomorphic aggregator (LG Month 7–12): delivered "
                "early, in Month 5"),
            (0, "Month 6 plan:"),
            (1, "OpenFHE migration — makes multi-key CKKS real rather "
                "than modelled"),
            (1, "Two one-line security fixes: bind round number into the "
                "AEAD (replay); enforce noise flooding in the deployment "
                "profile"),
            (1, "Low-magnitude persistent-poisoning experiment — the "
                "known blind spot in the scoring function"),
            (1, "Scale from 10 to 50 clients toward the roadmap target"),
            (1, "Re-acquire raw VeReMi with sender IDs"),
        ])

    n_slides = len(prs.slides._sldIdLst)
    prs.save(str(OUTPUT))
    print(f"wrote {OUTPUT}  ({n_slides} slides)")


if __name__ == "__main__":
    build()

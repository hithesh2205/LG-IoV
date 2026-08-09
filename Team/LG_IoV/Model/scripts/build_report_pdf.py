"""Build the KANConvNet implementation report as a PDF.

Same content as scripts/build_report.js (the DOCX version), rendered via
reportlab's Platypus so no Word/LibreOffice install is required.

Output: D:\\LG_IoV\\Model\\KANConvNet_Report.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, PageBreak, ListFlowable, ListItem, Preformatted, KeepTogether,
)


OUT = Path(__file__).resolve().parent.parent / "KANConvNet_Report.pdf"


# ── Styles ───────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#1F3864")
BLUE = colors.HexColor("#2E5395")
GREY_LINE = colors.HexColor("#BFBFBF")
GREY_BG = colors.HexColor("#F4F4F4")
HEADER_BG = colors.HexColor("#D9E2F3")
MUTED = colors.HexColor("#808080")

styles = getSampleStyleSheet()
TITLE = ParagraphStyle("Title2", parent=styles["Title"],
                       fontName="Helvetica-Bold", fontSize=20,
                       textColor=NAVY, spaceAfter=4, alignment=1)
SUBTITLE = ParagraphStyle("Subtitle", parent=styles["Normal"],
                          fontName="Helvetica-Oblique", fontSize=11,
                          textColor=MUTED, alignment=1, spaceAfter=18)
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                    fontSize=16, textColor=NAVY, spaceBefore=18, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=13, textColor=BLUE, spaceBefore=12, spaceAfter=6)
H3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold",
                    fontSize=11, textColor=BLUE, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica",
                      fontSize=10.5, leading=14, spaceAfter=6, textColor=colors.black)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=18, bulletIndent=4,
                        spaceAfter=3)
CODE = ParagraphStyle("Code", parent=styles["Code"], fontName="Courier",
                      fontSize=9, leading=12, backColor=GREY_BG,
                      borderColor=GREY_LINE, borderPadding=4,
                      borderWidth=0.25, spaceBefore=4, spaceAfter=8,
                      textColor=colors.black, leftIndent=0)


# ── Helpers ──────────────────────────────────────────────────────────────
def P(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def bullets(items):
    return ListFlowable(
        [ListItem(P(t), leftIndent=12, bulletColor=NAVY) for t in items],
        bulletType="bullet", bulletFontSize=10, leftIndent=18,
        spaceAfter=8,
    )


def code_block(lines):
    return Preformatted("\n".join(lines), CODE)


def make_table(headers, rows, col_widths):
    data = [[P(h, ParagraphStyle("th", parent=BODY,
                                  fontName="Helvetica-Bold")) for h in headers]]
    for r in rows:
        data.append([P(str(c), BODY) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ── Document template with header + footer ──────────────────────────────
class ReportDoc(BaseDocTemplate):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        frame = Frame(self.leftMargin, self.bottomMargin,
                      self.width, self.height, id="main")
        tpl = PageTemplate(id="default", frames=[frame],
                           onPage=self._draw_decor)
        self.addPageTemplates([tpl])

    def _draw_decor(self, canvas, doc):
        canvas.saveState()
        # Header line.
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(
            self.pagesize[0] - self.rightMargin,
            self.pagesize[1] - 0.5 * inch,
            "KANConvNet Implementation Report — FedIoV (FGCS 2026)",
        )
        canvas.setStrokeColor(GREY_LINE)
        canvas.setLineWidth(0.4)
        canvas.line(self.leftMargin, self.pagesize[1] - 0.55 * inch,
                    self.pagesize[0] - self.rightMargin,
                    self.pagesize[1] - 0.55 * inch)
        # Footer.
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(self.pagesize[0] / 2.0, 0.4 * inch,
                                 f"Page {canvas.getPageNumber()}")
        canvas.restoreState()


# ── Content ──────────────────────────────────────────────────────────────
story = []
story += [P("KANConvNet Classifier on Unified IoV Datasets", TITLE)]
story += [P("Implementation report — FedIoV (Heidari et al., FGCS 2026)", SUBTITLE)]

# 1. CONTEXT
story += [P("1. Project context and scope", H1)]
story += [P(
    "This report documents the classifier-side implementation of the FedIoV "
    "framework proposed by Heidari, Rastegar and Khonsari in <i>FedIoV: A secure "
    "and adaptive federated framework for real-time intrusion detection in "
    "vehicular networks</i> (Future Generation Computer Systems 181, 2026, 108448). "
    "FedIoV combines four components: secure model initialisation and encrypted "
    "communication, a two-stage robust aggregation pipeline (TOPSIS + Multi-Krum), "
    "a Kolmogorov–Arnold convolutional classifier (KANConvNet, paper §3.4), and "
    "genetic algorithm-based hyperparameter optimisation."
)]
story += [P(
    "The work covered here is the <b>second</b> of those four components — the local "
    "KANConvNet classifier that each vehicle would train on its own data before "
    "sending updates to the aggregator. The federation, the robust aggregation, "
    "and the GA-based hyperparameter search are not implemented yet and are scoped "
    "for the next milestone."
)]

story += [P("1.1 What is in the deliverable", H2)]
story += [bullets([
    "A from-scratch PyTorch implementation of KANConvNet matching paper equations 16–19.",
    "Per-dataset adapters for four benchmark IoV datasets: IEEE VTC–CAN, Car-Hacking, CICIDS-2017, VeReMi.",
    "A unified data pipeline that reduces every dataset to a common 46-dimensional input vector, so the same classifier definition trains on each.",
    "Cleanup scripts that strip the features the paper marks as identifier-leaking or unstable (absolute timestamps, port identifiers, raw node IDs, RSSI).",
    "A training/evaluation loop with per-dataset hyperparameters drawn from paper Table 4.",
])]

# 2. DATASETS
story += [P("2. Datasets and cleanup", H1)]
story += [P(
    "Four benchmark IoV datasets are used. Each is preprocessed twice: an initial "
    "cleanup pass produced the <font face='Courier'>cleaned_*</font> CSVs in "
    "<font face='Courier'>Preprocessed_Dataset</font>; a second pass "
    "(<font face='Courier'>scripts/clean_remaining_features.py</font>) removed the "
    "identifier-leaking or unstable columns that survived the first pass. The "
    "script is idempotent — re-running it is a no-op once each file has been cleaned."
)]
story += [make_table(
    ["Dataset", "Native format", "Native classes", "Columns dropped this pass"],
    [
        ["IEEE VTC–CAN", "HCRL CAN log", "4 (Attack-free, DoS, Fuzzy, Impersonation)",
         "“Timestamp: &lt;x&gt;” prefix on every line"],
        ["Car-Hacking",  "HCRL CAN (flat CSV + log)", "5 (normal, DoS, Fuzzy, RPM, gear)",
         "AbsoluteTimestamp (col 0) on flat CSVs; “Timestamp: &lt;x&gt;” on log"],
        ["CICIDS-2017",  "Flow-level CSV (78 numeric + Label)", "15 attack families + BENIGN",
         "Destination Port (col 0)"],
        ["VeReMi",       "Per-beacon CSV (kinematics + noise)", "18 attack types + BENIGN",
         "Unnamed: 0 (pandas index). Raw Node IDs / RSSI were not present — already removed in your earlier preprocessing pass."],
    ],
    [1.1 * inch, 1.5 * inch, 1.7 * inch, 2.2 * inch],
)]
story += [Spacer(1, 6)]
story += [P(
    "Sizes shrank after cleanup. For VeReMi the savings were modest "
    "(7.44 GB → 7.26 GB, ~70 s on disk). For the CAN datasets the Timestamp prefix "
    "accounted for roughly 40% of each line, so e.g. CAN-VTC Attack_free dropped "
    "from 206.7 MB to 121.4 MB."
)]

# 3. UNIFIED 46
story += [PageBreak()]
story += [P("3. The unified 46-feature representation", H1)]
story += [P(
    "The paper’s KANConvNet eq. (16) takes x ∈ ℝ<super>46</super> as input. To "
    "run the same classifier on four datasets with very different native schemas "
    "we enforce a 46-dim contract at the adapter layer. The shape is unified; the "
    "per-slot semantics are not — slot 0 is a different quantity in each dataset, "
    "so we train one model per dataset rather than a single shared model."
)]

story += [P("3.1 CAN-style datasets (IEEE VTC–CAN, Car-Hacking)", H2)]
story += [P(
    "Both share <font face='Courier'>data/can_features.py</font>. We slide a "
    "length-W = 64 window with stride 16 over the message stream and compute the "
    "timeless statistics below. Because timestamps were stripped, classical "
    "inter-arrival-time features were replaced with entropy and ID-diversity "
    "descriptors."
)]
story += [make_table(
    ["Slots", "Feature", "Count"],
    [
        ["0–7",   "Payload byte means (b0..b7), normalised /255",   "8"],
        ["8–15",  "Payload byte standard deviations",               "8"],
        ["16",    "DLC mean",                                       "1"],
        ["17",    "DLC standard deviation",                         "1"],
        ["18",    "Unique CAN-ID ratio (uniq / W)",                 "1"],
        ["19",    "Dominant-ID frequency",                          "1"],
        ["20–43", "CAN-ID histogram over 24 hash buckets",          "24"],
        ["44",    "Mean Shannon entropy across the 8 byte slots",   "1"],
        ["45",    "Non-zero payload byte ratio",                    "1"],
        ["",      "Total",                                          "46"],
    ],
    [0.8 * inch, 4.6 * inch, 0.8 * inch],
)]

story += [P("3.2 CICIDS-2017", H2)]
story += [P(
    "Rows are already flow-level feature vectors (78 numeric columns after "
    "Destination Port removal). No windowing is needed; we select 46 stable "
    "columns spanning the main feature families:"
)]
story += [bullets([
    "Flow duration, total forward/backward packets, total lengths",
    "Per-direction packet length max/min/mean/std (8 columns)",
    "Flow bytes/sec, packets/sec, flow IAT mean/std/max/min",
    "Forward IAT total/mean/std/max/min and Backward IAT total/mean/std/max/min",
    "Forward/backward header length and packet rate",
    "Min/max/mean/std/variance of packet length",
    "FIN/SYN/RST/PSH/ACK/URG flag counts",
    "Down/Up ratio, average packet size",
])]
story += [P(
    "The full list is in <font face='Courier'>data/cicids_dataset.py</font> "
    "(<font face='Courier'>SELECTED_COLUMNS_46</font>). Labels default to "
    "binary BENIGN vs ATTACK; passing <font face='Courier'>--multi-class</font> "
    "on the CLI enables the 15-attack-family taxonomy."
)]

story += [P("3.3 VeReMi", H2)]
story += [P(
    "Per-beacon CSV with 18 kinematic columns (type, rcvTime, pos × 2, spd × 2, "
    "acl × 2, hed × 2, each with a noise channel) plus two label columns. We "
    "slide W = 64 windows with stride 16 over the rows (streaming in 1-million-row "
    "chunks so the 7 GB file fits in memory)."
)]
story += [make_table(
    ["Slots", "Feature", "Count"],
    [
        ["0–17",  "Mean of each of the 18 kinematic columns",         "18"],
        ["18–35", "Standard deviation of each of the 18 columns",     "18"],
        ["36–37", "Speed magnitude mean and std (√(spd_0² + spd_1²))", "2"],
        ["38–39", "Acceleration magnitude mean and std",              "2"],
        ["40–41", "Position spread x and y (max − min)",              "2"],
        ["42",    "Mean heading magnitude",                           "1"],
        ["43–44", "rcvTime delta mean and std",                       "2"],
        ["45",    "Fraction of position-broadcast messages (type == 3)", "1"],
        ["",      "Total",                                            "46"],
    ],
    [0.8 * inch, 4.6 * inch, 0.8 * inch],
)]

# 4. INTERNALS
story += [PageBreak()]
story += [P("4. What KANConvNet does internally", H1)]
story += [P(
    "The Kolmogorov–Arnold representation theorem states that any continuous "
    "multivariate function on a bounded domain can be written as a finite "
    "composition of continuous univariate functions plus addition. KAN networks "
    "operationalise this by moving the learnable nonlinearity from the nodes "
    "(as in a standard MLP) to the edges. Every (input, output) edge carries "
    "its own learnable univariate function φ, and each output neuron is the "
    "sum of its incoming φ values. Two practical benefits the paper claims: "
    "fewer parameters than an equally expressive MLP, and per-edge functions "
    "are plottable, so the model is more interpretable than a black-box deep net."
)]

story += [P("4.1 Fourier KAN Linear layer", H2)]
story += [P("We realise each per-edge φ with a truncated Fourier basis of K modes:")]
story += [code_block([
    "phi_{i,j}(x_i) = sum_{k=1..K} [ a_{i,j,k} * sin(k * x_i) + b_{i,j,k} * cos(k * x_i) ]",
    "",
    "y_j = bias_j + sum_i phi_{i,j}(x_i)",
])]
story += [P(
    "Implementation lives in <font face='Courier'>models/kan_layers.py</font> "
    "(<font face='Courier'>FourierKANLinear</font>). The operation is vectorised "
    "with <font face='Courier'>torch.einsum</font>; there are no Python loops "
    "over input or output features."
)]

story += [P("4.2 Kolmogorov activation", H2)]
story += [P(
    "Between the KAN layer and the readout, the paper applies a custom "
    "σ<sub>Kolmogorov</sub> nonlinearity. We implement it as a smooth gated "
    "composition with per-channel learnable parameters "
    "(<font face='Courier'>models/kan_layers.py</font>, "
    "<font face='Courier'>KolmogorovActivation</font>):"
)]
story += [code_block([
    "sigma_K(x) = alpha * tanh(beta * x) + gamma * SiLU(delta * x) + eps",
])]
story += [P(
    "At initialisation (α=1, β=1, γ=0, ε=0) the layer collapses to plain tanh, "
    "so training starts in a well-behaved regime."
)]

story += [P("4.3 The full forward pass (paper eqs. 16–19)", H2)]
story += [code_block([
    "x  in R^46                              # 46-dim window feature vector",
    "z0 = Preprocess(x)                      # z-score + percentile clip (DataLoader)",
    "z1 = W1 . F(z0) + b1                    # FourierKANLinear            (eq. 16)",
    "z2 = sigma_Kolmogorov(z1)               # KolmogorovActivation        (eq. 17)",
    "z3, z4, z5 = Linear+ReLU stack          # hidden refinement",
    "z6 = W5 . sigma_Kolmogorov(z5) + b5     # KAN-style head              (eq. 18)",
    "y_hat = softmax(z6) -> argmax           # SGD-trained classifier      (eq. 19)",
])]
story += [P(
    "An optional <font face='Courier'>KANConv1d</font> backbone "
    "(<font face='Courier'>models/kan_conv.py</font>) is available for the case "
    "where the adapter emits raw windowed sequences (B, 46, W) rather than "
    "collapsed summary vectors (B, 46). It uses the same Fourier-KAN "
    "parameterisation but with weight-sharing across time via "
    "<font face='Courier'>torch.nn.functional.unfold</font>. The current "
    "adapters emit (B, 46), so the backbone is off by default."
)]

# 5. DATA FLOW
story += [PageBreak()]
story += [P("5. End-to-end data flow", H1)]
story += [P("Tracing a single sample from raw bytes on disk to a class prediction:")]
story += [code_block([
    "[1] Raw CSV / CAN log on disk",
    "    e.g. Can_vtc_pro/cleaned_DoS_attack_dataset.csv",
    "         line:  ID: 0220  000  DLC: 8  29 c5 26 55 6a 67 02 5d",
    "         |",
    "         v",
    "[2] Per-dataset parser (data/can_vtc_dataset.py, etc.)",
    "    Stream-reads the file row by row, decodes hex bytes,",
    "    yields arrays:  can_ids (W,), dlc (W,), payload (W, 8)",
    "         |",
    "         v",
    "[3] Feature extractor (data/can_features.py)",
    "    Slides a W=64 window with stride 16,",
    "    computes the 46 statistics described in section 3.1",
    "         |",
    "         v",
    "[4] Builder (data/build_dataset.py)",
    "    Stratified 70/15/15 split, percentile-clip + z-score on train only",
    "    Returns three Dataset objects with shape (N, 46)",
    "         |",
    "         v",
    "[5] DataLoader -> batched tensor (B, 46)",
    "         |",
    "         v",
    "[6] KANConvNet (models/kanconvnet.py)",
    "    z1 = FourierKANLinear(46 -> 128)",
    "    z2 = KolmogorovActivation(128)",
    "    hidden = 3 x (Linear 128 -> 128 + ReLU + Dropout)",
    "    z6 = KolmogorovActivation(128) -> Linear(128 -> n_classes)",
    "         |",
    "         v",
    "[7] CrossEntropyLoss with class-balanced weights",
    "    Optimiser step (per-dataset choice from Table 4)",
    "         |",
    "         v",
    "[8] Best checkpoint saved to",
    "    checkpoints/kanconvnet_best_<dataset>.pt",
])]

# 6. HYPERPARAMS
story += [P("6. Per-dataset hyperparameters (paper Table 4)", H1)]
story += [P(
    "<font face='Courier'>config.DATASET_HPARAMS</font> exposes the best-found "
    "hyperparameter set per dataset. "
    "<font face='Courier'>cfg.apply_dataset_defaults()</font> applies the right "
    "row automatically when <font face='Courier'>--dataset</font> is passed on "
    "the CLI."
)]
story += [make_table(
    ["Dataset", "Optimiser", "Epochs", "Momentum", "Dropout", "Layer size"],
    [
        ["can_vtc",  "RMSprop", "40", "0.90", "0.20", "128"],
        ["car_hack", "AdamW",   "30", "0.85", "0.25", "64"],
        ["cicids",   "SGD",     "60", "0.80", "0.30", "256"],
        ["veremi",   "Nadam",   "25", "0.95", "0.45", "128"],
    ],
    [1.0 * inch, 1.0 * inch, 0.7 * inch, 1.0 * inch, 0.9 * inch, 0.9 * inch],
)]
story += [Spacer(1, 6)]
story += [P(
    "Common hyperparameters are in dataclass "
    "<font face='Courier'>TrainConfig</font>: batch size 96, learning rate 5e-4, "
    "L2 weight decay 5e-4, 70/15/15 stratified split, seed 2025. These match the "
    "value sets in paper Table 3."
)]

# 7. LAYOUT
story += [P("7. Project layout", H1)]
story += [code_block([
    "D:\\LG_IoV\\",
    "|-- Preprocessed_Dataset\\               # cleaned source CSVs (input)",
    "|   |-- Can_vtc_pro\\cleaned_*.csv",
    "|   |-- Car_hack_pro\\Car_hack_pro\\cleaned_*.csv",
    "|   |-- CICIDS_pro\\CICIDS_pro\\cleaned_*.csv",
    "|   `-- VeReMi_pro\\cleaned_Veremi_final_dataset.csv",
    "`-- Model\\",
    "    |-- README.md",
    "    |-- requirements.txt",
    "    |-- config.py                        # all hyperparameters",
    "    |-- train.py                         # training + eval entry point",
    "    |-- models\\",
    "    |   |-- kan_layers.py                # FourierKANLinear, KolmogorovActivation",
    "    |   |-- kan_conv.py                  # KANConv1d (optional backbone)",
    "    |   `-- kanconvnet.py                # full classifier (eqs 16-19)",
    "    |-- data\\",
    "    |   |-- can_features.py              # timeless 46-feature extractor",
    "    |   |-- can_vtc_dataset.py           # IEEE VTC-CAN adapter",
    "    |   |-- car_hack_dataset.py          # Car-Hacking adapter",
    "    |   |-- cicids_dataset.py            # CICIDS-2017 adapter",
    "    |   |-- veremi_dataset.py            # VeReMi adapter (streamed)",
    "    |   `-- build_dataset.py             # unified dispatcher + split",
    "    |-- scripts\\",
    "    |   |-- clean_remaining_features.py  # second-pass column scrubber",
    "    |   |-- build_report.js              # DOCX report",
    "    |   `-- build_report_pdf.py          # this PDF",
    "    `-- checkpoints\\                    # written by train.py",
    "        |-- kanconvnet_best_<dataset>.pt",
    "        `-- training_log_<dataset>.json",
])]

# 8. HOW TO RUN
story += [P("8. How to run training", H1)]
story += [P("Install once:")]
story += [code_block([
    "cd D:\\LG_IoV\\Model",
    "py -m pip install -r requirements.txt",
])]
story += [P("Smoke test (1 epoch, capped row count, validates wiring end-to-end):")]
story += [code_block([
    "py train.py --dataset can_vtc  --smoke",
    "py train.py --dataset car_hack --smoke",
    "py train.py --dataset cicids   --smoke",
    "py train.py --dataset veremi   --smoke",
])]
story += [P("Full training run with the paper’s Table-4 hyperparameters:")]
story += [code_block([
    "py train.py --dataset can_vtc",
    "py train.py --dataset car_hack",
    "py train.py --dataset cicids",
    "py train.py --dataset cicids --multi-class    # 15-class taxonomy",
    "py train.py --dataset veremi",
    "py train.py --dataset veremi --multi-class    # 18-attack-type taxonomy",
])]
story += [P("Per-run outputs land in <font face='Courier'>Model/checkpoints/</font>:")]
story += [bullets([
    "<font face='Courier'>kanconvnet_best_&lt;dataset&gt;.pt</font> — best-validation-loss weights, normalisation statistics, class list.",
    "<font face='Courier'>training_log_&lt;dataset&gt;.json</font> — per-epoch train loss, validation loss, accuracy and macro-F1.",
])]
story += [P(
    "After training, the script reloads the best checkpoint and runs the test "
    "split, printing accuracy, macro-F1 and a per-class precision/recall/F1 breakdown."
)]

# 9. OUTSTANDING
story += [P("9. Outstanding work", H1)]
story += [bullets([
    "Federated wrapper: spawn N local clients, each with a KANConvNet instance trained on a non-IID slice of one dataset (Dirichlet α=0.3 per paper §5.2).",
    "Robust aggregation: TOPSIS-based dimensionality reduction followed by Multi-Krum filtering of client updates (paper §3.x).",
    "Differential privacy: client-level update clipping (||Δθ||₂ ≤ 1.0) and Gaussian noise σ ∈ {1.2, 1.6, 2.0} before transmission (paper §5.3).",
    "GA-based hyperparameter optimisation across heterogeneous clients (paper §4).",
    "Reporting: end-to-end latency and energy-per-round measurements against the GROW / GPIDS / BCFL / REMD / CIDF baselines (paper §5.3.1 and §5.3.2).",
])]


# ── Build ────────────────────────────────────────────────────────────────
def main() -> int:
    doc = ReportDoc(
        str(OUT),
        pagesize=LETTER,
        leftMargin=1 * inch, rightMargin=1 * inch,
        topMargin=0.9 * inch, bottomMargin=0.7 * inch,
        title="KANConvNet Implementation Report",
        author="Saurabh Krishnan",
    )
    doc.build(story)
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

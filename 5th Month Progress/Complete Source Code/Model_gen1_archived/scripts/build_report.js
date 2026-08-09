// Build KANConvNet_Report.docx — technical report for project supervisor.
// Run from D:\LG_IoV\Model:  node scripts/build_report.js

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
} = require("docx");

// ---- helpers ------------------------------------------------------------
const FONT = "Arial";
const MONO = "Consolas";
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const cellBorders = { top: border, bottom: border, left: border, right: border };

const P = (text, opts = {}) =>
  new Paragraph({
    spacing: { after: 120 },
    ...opts,
    children: [new TextRun({ text, font: FONT, size: 22, ...(opts.runOpts || {}) })],
  });

const PB = (text) => P(text, { runOpts: { bold: true } });

const H1 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 180 },
    children: [new TextRun({ text, font: FONT, size: 32, bold: true })],
  });

const H2 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, font: FONT, size: 26, bold: true })],
  });

const H3 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 180, after: 100 },
    children: [new TextRun({ text, font: FONT, size: 22, bold: true })],
  });

// Multi-run paragraph (mix of bold/normal inline).
const Pmix = (runs, opts = {}) =>
  new Paragraph({
    spacing: { after: 120 },
    ...opts,
    children: runs.map((r) =>
      typeof r === "string"
        ? new TextRun({ text: r, font: FONT, size: 22 })
        : new TextRun({ text: r.text, font: FONT, size: 22, bold: !!r.bold, italics: !!r.italic })
    ),
  });

const Bullet = (text) =>
  new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });

const Code = (lines) =>
  lines.map(
    (ln) =>
      new Paragraph({
        spacing: { after: 0 },
        shading: { fill: "F4F4F4", type: ShadingType.CLEAR },
        children: [new TextRun({ text: ln, font: MONO, size: 20 })],
      })
  );

// Table builder with auto-sized cells (caller passes col widths in DXA).
function makeTable(headers, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  const headRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) =>
      new TableCell({
        borders: cellBorders,
        width: { size: colWidths[i], type: WidthType.DXA },
        shading: { fill: "D9E2F3", type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({
          children: [new TextRun({ text: h, font: FONT, size: 22, bold: true })],
        })],
      })
    ),
  });
  const dataRows = rows.map((r) =>
    new TableRow({
      children: r.map((cell, i) =>
        new TableCell({
          borders: cellBorders,
          width: { size: colWidths[i], type: WidthType.DXA },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            children: [new TextRun({ text: String(cell), font: FONT, size: 22 })],
          })],
        })
      ),
    })
  );
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headRow, ...dataRows],
  });
}

// ---- content ------------------------------------------------------------
const children = [];

children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({
    text: "KANConvNet Classifier on Unified IoV Datasets",
    font: FONT, size: 40, bold: true,
  })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 360 },
  children: [new TextRun({
    text: "Implementation report — FedIoV (Heidari et al., FGCS 2026)",
    font: FONT, size: 24, italics: true, color: "595959",
  })],
}));

// 1. INTRODUCTION ---------------------------------------------------------
children.push(H1("1. Project context and scope"));
children.push(P(
  "This report documents the classifier-side implementation of the FedIoV " +
  "framework proposed by Heidari, Rastegar and Khonsari in \"FedIoV: A " +
  "secure and adaptive federated framework for real-time intrusion " +
  "detection in vehicular networks\" (Future Generation Computer Systems " +
  "181, 2026, 108448). FedIoV combines four components: secure model " +
  "initialisation and encrypted communication, a two-stage robust " +
  "aggregation pipeline (TOPSIS + Multi-Krum), a Kolmogorov–Arnold " +
  "convolutional classifier (KANConvNet, paper §3.4), and genetic " +
  "algorithm-based hyperparameter optimisation."
));
children.push(P(
  "The work covered here is the second of those four components — the " +
  "local KANConvNet classifier that each vehicle would train on its own " +
  "data before sending updates to the aggregator. The federation, the " +
  "robust aggregation, and the GA-based hyperparameter search are not " +
  "implemented yet and are scoped for the next milestone."
));
children.push(H2("1.1 What is in the deliverable"));
children.push(Bullet("A from-scratch PyTorch implementation of KANConvNet matching paper equations 16–19."));
children.push(Bullet("Per-dataset adapters for four benchmark IoV datasets: IEEE VTC–CAN, Car-Hacking, CICIDS-2017, VeReMi."));
children.push(Bullet("A unified data pipeline that reduces every dataset to a common 46-dimensional input vector, so the same classifier definition trains on each."));
children.push(Bullet("Cleanup scripts that strip the features the paper marks as identifier-leaking or unstable (absolute timestamps, port identifiers, raw node IDs, RSSI)."));
children.push(Bullet("A training/evaluation loop with per-dataset hyperparameters drawn from paper Table 4."));

// 2. DATASETS & CLEANUP --------------------------------------------------
children.push(H1("2. Datasets and cleanup"));
children.push(P(
  "Four benchmark IoV datasets are used. Each is preprocessed twice: an " +
  "initial cleanup pass produced the `cleaned_*` CSVs in Preprocessed_" +
  "Dataset; a second pass (scripts/clean_remaining_features.py) removed " +
  "the identifier-leaking or unstable columns that survived the first " +
  "pass. The script is idempotent — re-running it is a no-op once each " +
  "file has been cleaned."
));
children.push(makeTable(
  ["Dataset", "Native format", "Native classes", "Columns dropped this pass"],
  [
    ["IEEE VTC–CAN", "HCRL CAN log", "4 (Attack-free, DoS, Fuzzy, Impersonation)", "\"Timestamp: <x>\" prefix on every line"],
    ["Car-Hacking",  "HCRL CAN (flat CSV + log)", "5 (normal, DoS, Fuzzy, RPM, gear)", "AbsoluteTimestamp (col 0) on flat CSVs; \"Timestamp: <x>\" on log"],
    ["CICIDS-2017",  "Flow-level CSV (78 numeric + Label)", "15 attack families + BENIGN", "Destination Port (col 0)"],
    ["VeReMi",       "Per-beacon CSV (kinematics + noise)", "18 attack types + BENIGN", "Unnamed: 0 (pandas index). Raw Node IDs / RSSI were not present — already removed in your earlier preprocessing pass."],
  ],
  [1700, 2300, 2500, 2860]
));
children.push(P(
  "Sizes shrank after cleanup. For VeReMi the savings were modest " +
  "(7.44 GB → 7.26 GB, ~70 s on disk). For the CAN datasets the " +
  "Timestamp prefix accounted for roughly 40% of each line, so e.g. " +
  "CAN-VTC Attack_free dropped from 206.7 MB to 121.4 MB."
));

// 3. UNIFIED 46-FEATURE VECTOR --------------------------------------------
children.push(H1("3. The unified 46-feature representation"));
children.push(P(
  "The paper's KANConvNet eq. (16) takes x ∈ ℝ^46 as input. To run the " +
  "same classifier on four datasets with very different native schemas " +
  "we enforce a 46-dim contract at the adapter layer. The shape is " +
  "unified; the per-slot semantics are not — slot 0 is a different " +
  "quantity in each dataset, so we train one model per dataset rather " +
  "than a single shared model."
));

children.push(H2("3.1 CAN-style datasets (IEEE VTC–CAN, Car-Hacking)"));
children.push(P(
  "Both share data/can_features.py. We slide a length-W = 64 window with " +
  "stride 16 over the message stream and compute the timeless statistics " +
  "below. Because timestamps were stripped, classical inter-arrival-time " +
  "features were replaced with entropy and ID-diversity descriptors."
));
children.push(makeTable(
  ["Slots", "Feature", "Count"],
  [
    ["0–7",   "Payload byte means (b0..b7), normalised /255",   "8"],
    ["8–15",  "Payload byte standard deviations",               "8"],
    ["16",    "DLC mean",                                       "1"],
    ["17",    "DLC standard deviation",                         "1"],
    ["18",    "Unique CAN-ID ratio (uniq/W)",                   "1"],
    ["19",    "Dominant-ID frequency",                          "1"],
    ["20–43", "CAN-ID histogram over 24 hash buckets",          "24"],
    ["44",    "Mean Shannon entropy across the 8 byte slots",   "1"],
    ["45",    "Non-zero payload byte ratio",                    "1"],
    ["",      "Total",                                          "46"],
  ],
  [1200, 5460, 1700]
));

children.push(H2("3.2 CICIDS-2017"));
children.push(P(
  "Rows are already flow-level feature vectors (78 numeric columns after " +
  "Destination Port removal). No windowing is needed; we select 46 " +
  "stable columns spanning the main feature families:"
));
children.push(Bullet("Flow duration, total forward/backward packets, total lengths"));
children.push(Bullet("Per-direction packet length max/min/mean/std (8 cols)"));
children.push(Bullet("Flow bytes/sec, packets/sec, flow IAT mean/std/max/min"));
children.push(Bullet("Forward IAT total/mean/std/max/min and Backward IAT total/mean/std/max/min"));
children.push(Bullet("Forward/backward header length and packet rate"));
children.push(Bullet("Min/max/mean/std/variance of packet length"));
children.push(Bullet("FIN/SYN/RST/PSH/ACK/URG flag counts"));
children.push(Bullet("Down/Up ratio, average packet size"));
children.push(P(
  "The full list is in data/cicids_dataset.py (SELECTED_COLUMNS_46). " +
  "Labels default to binary BENIGN vs ATTACK; passing --multi-class on " +
  "the CLI enables the 15-attack-family taxonomy."
));

children.push(H2("3.3 VeReMi"));
children.push(P(
  "Per-beacon CSV with 18 kinematic columns (type, rcvTime, pos × 2, " +
  "spd × 2, acl × 2, hed × 2, each with a noise channel) plus two label " +
  "columns. We slide W = 64 windows with stride 16 over the rows " +
  "(streaming in 1-million-row chunks so the 7 GB file fits in memory)."
));
children.push(makeTable(
  ["Slots", "Feature", "Count"],
  [
    ["0–17",  "Mean of each of the 18 kinematic columns", "18"],
    ["18–35", "Standard deviation of each of the 18 columns", "18"],
    ["36–37", "Speed magnitude mean and std  (√(spd_0² + spd_1²))", "2"],
    ["38–39", "Acceleration magnitude mean and std", "2"],
    ["40–41", "Position spread x and y (max − min)", "2"],
    ["42",    "Mean heading magnitude", "1"],
    ["43–44", "rcvTime delta mean and std", "2"],
    ["45",    "Fraction of position-broadcast messages (type == 3)", "1"],
    ["",      "Total", "46"],
  ],
  [1200, 5460, 1700]
));

// 4. KANConvNet INTERNALS -------------------------------------------------
children.push(H1("4. What KANConvNet does internally"));
children.push(P(
  "The Kolmogorov–Arnold representation theorem states that any " +
  "continuous multivariate function on a bounded domain can be written " +
  "as a finite composition of continuous univariate functions plus " +
  "addition. KAN networks operationalise this by moving the learnable " +
  "nonlinearity from the nodes (as in a standard MLP) to the edges. " +
  "Every (input, output) edge carries its own learnable univariate " +
  "function φ, and each output neuron is the sum of its incoming φ values. " +
  "Two practical benefits the paper claims: fewer parameters than an " +
  "equally expressive MLP, and per-edge functions are plottable, so the " +
  "model is more interpretable than a black-box deep net."
));

children.push(H2("4.1 Fourier KAN Linear layer"));
children.push(P(
  "We realise each per-edge φ with a truncated Fourier basis of K modes:"
));
children.push(...Code([
  "φ_{i,j}(x_i) = Σ_{k=1..K} [ a_{i,j,k} · sin(k · x_i) + b_{i,j,k} · cos(k · x_i) ]",
  "",
  "y_j = bias_j + Σ_i φ_{i,j}(x_i)",
]));
children.push(P(
  "Implementation lives in models/kan_layers.py (FourierKANLinear). The " +
  "operation is vectorised with torch.einsum; there are no Python loops " +
  "over input or output features."
));

children.push(H2("4.2 Kolmogorov activation"));
children.push(P(
  "Between the KAN layer and the readout, the paper applies a custom " +
  "σ_Kolmogorov nonlinearity. We implement it as a smooth gated " +
  "composition with per-channel learnable parameters (models/kan_layers.py, " +
  "KolmogorovActivation):"
));
children.push(...Code([
  "σ_K(x) = α · tanh(β · x) + γ · SiLU(δ · x) + ε",
]));
children.push(P(
  "At initialisation (α=1, β=1, γ=0, ε=0) the layer collapses to plain " +
  "tanh, so training starts in a well-behaved regime."
));

children.push(H2("4.3 The full forward pass (paper eqs. 16–19)"));
children.push(...Code([
  "x  ∈ R^46                                # 46-dim window feature vector",
  "z0 = Preprocess(x)                       # z-score + percentile clip (DataLoader)",
  "z1 = W1 · F(z0) + b1                     # FourierKANLinear            (eq. 16)",
  "z2 = σ_Kolmogorov(z1)                    # KolmogorovActivation        (eq. 17)",
  "z3, z4, z5 = Linear+ReLU stack           # hidden refinement",
  "z6 = W5 · σ_Kolmogorov(z5) + b5          # KAN-style head              (eq. 18)",
  "ŷ  = softmax(z6) → argmax                # SGD-trained classifier      (eq. 19)",
]));
children.push(P(
  "An optional KANConv1d backbone (models/kan_conv.py) is available for " +
  "the case where the adapter emits raw windowed sequences (B, 46, W) " +
  "rather than collapsed summary vectors (B, 46). It uses the same " +
  "Fourier-KAN parameterisation but with weight-sharing across time via " +
  "torch.nn.functional.unfold. The current adapters emit (B, 46), so the " +
  "backbone is off by default."
));

// 5. END-TO-END DATA FLOW -------------------------------------------------
children.push(H1("5. End-to-end data flow"));
children.push(P(
  "Tracing a single sample from raw bytes on disk to a class prediction:"
));
children.push(...Code([
  "[1] Raw CSV / CAN log on disk",
  "    e.g. Can_vtc_pro/cleaned_DoS_attack_dataset.csv",
  "         line:  ID: 0220  000  DLC: 8  29 c5 26 55 6a 67 02 5d",
  "         ↓",
  "[2] Per-dataset parser (data/can_vtc_dataset.py, etc.)",
  "    Stream-reads the file row by row, decodes hex bytes,",
  "    yields arrays:  can_ids (W,), dlc (W,), payload (W, 8)",
  "         ↓",
  "[3] Feature extractor (data/can_features.py)",
  "    Slides a W=64 window with stride 16,",
  "    computes the 46 statistics described in §3.1",
  "         ↓",
  "[4] Builder (data/build_dataset.py)",
  "    Stratified 70/15/15 split, percentile-clip + z-score on train only",
  "    Returns three Dataset objects with shape (N, 46)",
  "         ↓",
  "[5] DataLoader → batched tensor (B, 46)",
  "         ↓",
  "[6] KANConvNet (models/kanconvnet.py)",
  "    z1 = FourierKANLinear(46 → 128)",
  "    z2 = KolmogorovActivation(128)",
  "    hidden = 3 × (Linear 128 → 128 + ReLU + Dropout)",
  "    z6 = KolmogorovActivation(128) → Linear(128 → n_classes)",
  "         ↓",
  "[7] CrossEntropyLoss with class-balanced weights",
  "    Optimiser step (per-dataset choice from Table 4)",
  "         ↓",
  "[8] Best checkpoint saved to",
  "    checkpoints/kanconvnet_best_<dataset>.pt",
]));

// 6. HYPERPARAMETERS ------------------------------------------------------
children.push(H1("6. Per-dataset hyperparameters (paper Table 4)"));
children.push(P(
  "config.DATASET_HPARAMS exposes the best-found hyperparameter set per " +
  "dataset. cfg.apply_dataset_defaults() applies the right row " +
  "automatically when --dataset is passed on the CLI."
));
children.push(makeTable(
  ["Dataset", "Optimiser", "Epochs", "Momentum", "Dropout", "Layer size"],
  [
    ["can_vtc",  "RMSprop", "40", "0.90", "0.20", "128"],
    ["car_hack", "AdamW",   "30", "0.85", "0.25", "64"],
    ["cicids",   "SGD",     "60", "0.80", "0.30", "256"],
    ["veremi",   "Nadam",   "25", "0.95", "0.45", "128"],
  ],
  [1700, 1700, 1300, 1700, 1500, 1460]
));
children.push(P(
  "Common hyperparameters are in dataclass TrainConfig: batch size 96, " +
  "learning rate 5e-4, L2 weight decay 5e-4, 70/15/15 stratified split, " +
  "seed 2025. These match the value sets in paper Table 3."
));

// 7. PROJECT LAYOUT -------------------------------------------------------
children.push(H1("7. Project layout"));
children.push(...Code([
  "D:\\LG_IoV\\",
  "├── Preprocessed_Dataset\\               # cleaned source CSVs (input)",
  "│   ├── Can_vtc_pro\\cleaned_*.csv",
  "│   ├── Car_hack_pro\\Car_hack_pro\\cleaned_*.csv",
  "│   ├── CICIDS_pro\\CICIDS_pro\\cleaned_*.csv",
  "│   └── VeReMi_pro\\cleaned_Veremi_final_dataset.csv",
  "└── Model\\",
  "    ├── README.md",
  "    ├── requirements.txt",
  "    ├── config.py                        # all hyperparameters",
  "    ├── train.py                         # training + eval entry point",
  "    ├── models\\",
  "    │   ├── kan_layers.py                # FourierKANLinear, KolmogorovActivation",
  "    │   ├── kan_conv.py                  # KANConv1d (optional backbone)",
  "    │   └── kanconvnet.py                # full classifier (eqs 16-19)",
  "    ├── data\\",
  "    │   ├── can_features.py              # timeless 46-feature extractor",
  "    │   ├── can_vtc_dataset.py           # IEEE VTC-CAN adapter",
  "    │   ├── car_hack_dataset.py          # Car-Hacking adapter",
  "    │   ├── cicids_dataset.py            # CICIDS-2017 adapter",
  "    │   ├── veremi_dataset.py            # VeReMi adapter (streamed)",
  "    │   └── build_dataset.py             # unified dispatcher + split",
  "    ├── scripts\\",
  "    │   ├── clean_remaining_features.py  # second-pass column scrubber",
  "    │   └── build_report.js              # this report",
  "    └── checkpoints\\                    # written by train.py",
  "        ├── kanconvnet_best_<dataset>.pt",
  "        └── training_log_<dataset>.json",
]));

// 8. HOW TO RUN -----------------------------------------------------------
children.push(H1("8. How to run training"));
children.push(P("Install once:"));
children.push(...Code([
  "cd D:\\LG_IoV\\Model",
  "py -m pip install -r requirements.txt",
]));
children.push(P("Smoke test (1 epoch, capped row count, validates wiring end-to-end):"));
children.push(...Code([
  "py train.py --dataset can_vtc  --smoke",
  "py train.py --dataset car_hack --smoke",
  "py train.py --dataset cicids   --smoke",
  "py train.py --dataset veremi   --smoke",
]));
children.push(P("Full training run with the paper's Table-4 hyperparameters:"));
children.push(...Code([
  "py train.py --dataset can_vtc",
  "py train.py --dataset car_hack",
  "py train.py --dataset cicids",
  "py train.py --dataset cicids --multi-class    # 15-class taxonomy",
  "py train.py --dataset veremi",
  "py train.py --dataset veremi --multi-class    # 18-attack-type taxonomy",
]));
children.push(P("Per-run outputs land in Model/checkpoints/:"));
children.push(Bullet("kanconvnet_best_<dataset>.pt — best-validation-loss weights, normalisation statistics, class list."));
children.push(Bullet("training_log_<dataset>.json — per-epoch train loss, validation loss, accuracy and macro-F1."));
children.push(P("After training, the script reloads the best checkpoint and runs the test split, printing accuracy, macro-F1 and a per-class precision/recall/F1 breakdown."));

// 9. NEXT MILESTONE -------------------------------------------------------
children.push(H1("9. Outstanding work"));
children.push(Bullet("Federated wrapper: spawn N local clients, each with a KANConvNet instance trained on a non-IID slice of one dataset (Dirichlet α=0.3 per paper §5.2)."));
children.push(Bullet("Robust aggregation: TOPSIS-based dimensionality reduction followed by Multi-Krum filtering of client updates (paper §3.x)."));
children.push(Bullet("Differential privacy: client-level update clipping (||Δθ||₂ ≤ 1.0) and Gaussian noise σ ∈ {1.2, 1.6, 2.0} before transmission (paper §5.3)."));
children.push(Bullet("GA-based hyperparameter optimisation across heterogeneous clients (paper §4)."));
children.push(Bullet("Reporting: end-to-end latency and energy-per-round measurements against the GROW / GPIDS / BCFL / REMD / CIDF baselines (paper §5.3.1 and §5.3.2)."));

// build doc -------------------------------------------------------------
const doc = new Document({
  creator: "Saurabh Krishnan",
  title: "KANConvNet Implementation Report",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: "1F3864" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: "2E5395" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: FONT, color: "2E5395" },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({
            text: "KANConvNet Implementation Report — FedIoV (FGCS 2026)",
            font: FONT, size: 18, italics: true, color: "808080",
          })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Page ", font: FONT, size: 18, color: "808080" }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "808080" }),
            new TextRun({ text: " / ", font: FONT, size: 18, color: "808080" }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 18, color: "808080" }),
          ],
        })],
      }),
    },
    children,
  }],
});

const outPath = path.resolve("KANConvNet_Report.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log(`wrote ${outPath}  (${buf.length.toLocaleString()} bytes)`);
});

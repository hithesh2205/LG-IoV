const pptx = require("pptxgenjs");
const path = require("path");

const OUT = process.argv[2] || "Month5_Status_Update.pptx";
const DIAG = process.argv[3] || null;   // Diagrams folder

const p = new pptx();
p.layout = "LAYOUT_WIDE";               // 13.3 x 7.5
p.author = "LGSI IoV Project";
p.title = "Month 5 Status Update";

// ── palette ──────────────────────────────────────────────────────────────
const NAVY = "1E2761";
const NAVY_D = "141B45";
const ICE = "CADCFC";
const BLUE = "2D6CDF";
const GREEN = "1E9E6A";
const AMBER = "D98324";
const RED = "D64545";
const LIGHT = "F4F7FC";
const INK = "1A1A2E";
const GREY = "5A6472";
const WHITE = "FFFFFF";

const H = "Cambria";      // headers
const B = "Calibri";      // body

const W = 13.3, HT = 7.5;

// ── helpers ──────────────────────────────────────────────────────────────
function titleSlide(s, kicker, title, sub) {
  s.background = { color: NAVY };
  s.addText(kicker, { x: 0.9, y: 1.55, w: 11.5, h: 0.4, fontFace: B,
    fontSize: 14, color: ICE, charSpacing: 3, bold: true });
  s.addText(title, { x: 0.9, y: 2.05, w: 11.5, h: 1.9, fontFace: H,
    fontSize: 40, color: WHITE, bold: true, lineSpacing: 46 });
  s.addText(sub, { x: 0.9, y: 4.15, w: 11.5, h: 0.9, fontFace: B,
    fontSize: 16, color: ICE, lineSpacing: 24 });
}

function head(s, title, sub) {
  s.background = { color: WHITE };
  s.addText(title, { x: 0.7, y: 0.42, w: 12.0, h: 0.62, fontFace: H,
    fontSize: 30, color: NAVY, bold: true, margin: 0 });
  if (sub) {
    s.addText(sub, { x: 0.7, y: 1.06, w: 12.0, h: 0.4, fontFace: B,
      fontSize: 13.5, color: GREY, margin: 0 });
  }
}

// stat callout card
function stat(s, x, y, w, big, label, col) {
  s.addShape(p.ShapeType.roundRect, { x, y, w, h: 1.55, rectRadius: 0.09,
    fill: { color: LIGHT }, line: { color: "E1E8F2", width: 1 } });
  s.addText(big, { x, y: y + 0.16, w, h: 0.75, fontFace: H, fontSize: 34,
    color: col, bold: true, align: "center", margin: 0 });
  s.addText(label, { x: x + 0.12, y: y + 0.93, w: w - 0.24, h: 0.5,
    fontFace: B, fontSize: 11.5, color: GREY, align: "center", margin: 0 });
}

// icon-in-circle row
function row(s, x, y, w, num, title, body, col) {
  s.addShape(p.ShapeType.ellipse, { x, y, w: 0.46, h: 0.46,
    fill: { color: col } });
  s.addText(num, { x, y: y + 0.02, w: 0.46, h: 0.42, fontFace: H,
    fontSize: 15, color: WHITE, bold: true, align: "center", margin: 0 });
  s.addText(title, { x: x + 0.66, y: y - 0.03, w: w - 0.66, h: 0.34,
    fontFace: B, fontSize: 14.5, color: INK, bold: true, margin: 0 });
  s.addText(body, { x: x + 0.66, y: y + 0.29, w: w - 0.66, h: 0.72,
    fontFace: B, fontSize: 12, color: GREY, margin: 0, lineSpacing: 15 });
}

function tbl(s, rows, opts) {
  const o = Object.assign({
    x: 0.7, y: 1.6, w: 11.9, fontFace: B, fontSize: 12,
    color: INK, border: { type: "solid", color: "E1E8F2", pt: 1 },
    autoPage: false, valign: "middle",
  }, opts || {});
  s.addTable(rows, o);
}

function hdr(t) {
  return { text: t, options: { bold: true, color: WHITE, fill: { color: NAVY },
    fontSize: 12 } };
}

// ═════════════════════════════════════════════════════════════════════════
// 1 — title
// ═════════════════════════════════════════════════════════════════════════
let s = p.addSlide();
titleSlide(s,
  "LG SOFT INDIA  ·  12-MONTH INDUSTRY PROJECT",
  "Privacy-Preserving Collaborative\nIntrusion Detection for the IoV",
  "Federated learning with CKKS homomorphic encryption\nMonth 5 status update");
s.addShape(p.ShapeType.rect, { x: 0.9, y: 5.45, w: 1.1, h: 0.035,
  fill: { color: BLUE } });
s.addText("Federated Learning  ·  Homomorphic Encryption  ·  Byzantine Robustness",
  { x: 0.9, y: 5.68, w: 11.5, h: 0.4, fontFace: B, fontSize: 12.5,
    color: ICE, margin: 0 });
s.addNotes("Month 5 of 12. Headline: the month became an audit-then-rebuild. We found seven defects that invalidated earlier results, fixed all of them, and then went back and closed three deliverables from Months 1-4 that had never been started.");

// ═════════════════════════════════════════════════════════════════════════
// 2 — where we stand
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "Where we stand", "End of Month 5 of 12");
stat(s, 0.7, 1.75, 2.75, "5 / 12", "months elapsed", NAVY);
stat(s, 3.75, 1.75, 2.75, "7 / 8", "deliverables due by\nMonth 4 now closed", GREEN);
stat(s, 6.80, 1.75, 2.75, "105", "automated correctness\nassertions, all passing", BLUE);
stat(s, 9.85, 1.75, 2.75, "1", "blocker, and it is\nprocurement", AMBER);

s.addShape(p.ShapeType.roundRect, { x: 0.7, y: 3.66, w: 11.9, h: 1.32,
  rectRadius: 0.09, fill: { color: "EEF9F4" },
  line: { color: GREEN, width: 1.25 } });
s.addText("Headline", { x: 1.0, y: 3.82, w: 3.0, h: 0.3, fontFace: B,
  fontSize: 11.5, color: GREEN, bold: true, charSpacing: 1.5, margin: 0 });
s.addText("Encryption costs no accuracy. Across all four datasets the encrypted and plaintext runs agree to within seed variance — and the server never decrypted a single individual vehicle update.",
  { x: 1.0, y: 4.10, w: 11.3, h: 0.75, fontFace: B, fontSize: 14,
    color: INK, margin: 0, lineSpacing: 19 });

s.addText("Cryptography and machine-learning tracks are healthy and one item is ahead of schedule. The embedded/hardware track is the whole of the remaining gap.",
  { x: 0.7, y: 5.22, w: 11.9, h: 0.6, fontFace: B, fontSize: 13,
    color: GREY, margin: 0, lineSpacing: 18 });
s.addNotes("Lead with this slide. Four numbers, then the headline. The one blocker is that no hardware has been ordered - everything else on the embedded track is now software-complete and waiting on a board.");

// ═════════════════════════════════════════════════════════════════════════
// 3 — what month 5 became
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "What Month 5 became", "It started as multi-key CKKS research. An audit changed the plan.");
row(s, 0.7, 1.75, 11.9, "1",
  "We audited the whole project before building on it",
  "Standard practice before adopting a new cryptographic scheme: check the foundation first.", BLUE);
row(s, 0.7, 2.85, 11.9, "2",
  "The audit found seven defects — several invalidated our headline results",
  "The encryption in the training loop was not encryption. The Byzantine filter decrypted every vehicle's update. CAN labels came from filenames.", RED);
row(s, 0.7, 3.95, 11.9, "3",
  "So Month 5 became: fix the foundation, then build on it",
  "All seven fixed and machine-verified. Then real CKKS, FheFL aggregation and multi-key sharing on top.", AMBER);
row(s, 0.7, 5.05, 11.9, "4",
  "Then we went back and closed three Month 1–4 deliverables",
  "Packing module, NTT implementation and the hardware benchmark harness — none had been started.", GREEN);
s.addNotes("Be straightforward about this. Finding the defects was the valuable part - had we built multi-key CKKS on top of a leaky pipeline we would have produced a cryptographically elegant result about nothing.");

// ═════════════════════════════════════════════════════════════════════════
// 4 — the seven defects
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "The seven defects — all fixed and verified", "Each is now guarded by an automated test, so it cannot silently return");
tbl(s, [
  [hdr("#"), hdr("What was wrong"), hdr("Why it mattered"), hdr("Status")],
  ["D1", "Labels came from the source filename, not ground truth",
   "Trained a capture-file classifier, not an IDS. Caused the 100% accuracy", "Fixed"],
  ["D2", "75%-overlapping windows split randomly across train/test",
   "Test accuracy measured memorisation, not generalisation", "Fixed"],
  ["D3", "FHE-vs-plaintext was not a controlled experiment",
   "Produced a spurious 5-point accuracy gap that was pure divergence", "Fixed"],
  ["D4", "The server decrypted every individual client update",
   "Voided the central privacy claim of the entire project", "Fixed"],
  ["D5", "VeReMi windowed across mixed senders",
   "Label was near-random; model was fine. Needs data re-acquisition", "Diagnosed"],
  ["D6", "Transport security had been removed in Month 4",
   "FHE gives no authentication, integrity or replay protection", "Fixed"],
  ["D7", "Documentation contradicted the code", "Three months of drift", "Fixed"],
], { y: 1.62, colW: [0.62, 3.85, 5.63, 1.8], rowH: 0.44, fontSize: 11 });
s.addNotes("D4 is the one to emphasise: the deck said the server never sees plaintext, and the code decrypted every client's full 44,164-parameter update every round. That is now a machine-checked invariant, asserted after every round.");

// ═════════════════════════════════════════════════════════════════════════
// 5 — results table
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "Results — does encryption cost accuracy?",
  "3 seeds · 10 simulated vehicles · 5 federated rounds · Dirichlet alpha = 0.3");
tbl(s, [
  [hdr("Dataset"), hdr("CKKS encrypted"), hdr("Plaintext baseline"), hdr("Difference"), hdr("Verdict")],
  ["CAN-VTC", "1.0000 ± 0.0000", "1.0000 ± 0.0000", "0.0000", "within seed noise"],
  [{ text: "Car-Hacking", options: { bold: true } },
   { text: "0.9977 ± 0.0012", options: { bold: true } },
   { text: "0.9981 ± 0.0006", options: { bold: true } },
   { text: "−0.0004", options: { bold: true } },
   { text: "within seed noise", options: { bold: true } }],
  ["CICIDS-2017", "0.9555 ± 0.0079", "0.9542 ± 0.0098", "+0.0013", "within seed noise"],
  ["VeReMi", "0.4839 ± 0.0433", "0.4851 ± 0.0424", "−0.0012", "within seed noise"],
], { y: 1.62, colW: [2.3, 2.6, 2.6, 1.9, 2.5], rowH: 0.48, fontSize: 12.5 });

s.addShape(p.ShapeType.roundRect, { x: 0.7, y: 4.42, w: 5.8, h: 1.62,
  rectRadius: 0.09, fill: { color: "EEF9F4" }, line: { color: GREEN, width: 1.25 } });
s.addText("Conclusion", { x: 0.98, y: 4.58, w: 3.0, h: 0.28, fontFace: B,
  fontSize: 11, color: GREEN, bold: true, charSpacing: 1.5, margin: 0 });
s.addText("CKKS introduces ~1e-8 of numerical error — six orders of magnitude below the noise already in SGD. Encryption is free in accuracy terms.",
  { x: 0.98, y: 4.86, w: 5.25, h: 1.0, fontFace: B, fontSize: 12.5,
    color: INK, margin: 0, lineSpacing: 17 });

s.addShape(p.ShapeType.roundRect, { x: 6.8, y: 4.42, w: 5.8, h: 1.62,
  rectRadius: 0.09, fill: { color: "FDF3E8" }, line: { color: AMBER, width: 1.25 } });
s.addText("Read honestly", { x: 7.08, y: 4.58, w: 3.0, h: 0.28, fontFace: B,
  fontSize: 11, color: AMBER, bold: true, charSpacing: 1.5, margin: 0 });
s.addText("Car-Hacking is the meaningful benchmark. CAN-VTC is trivially separable (51% flood density). VeReMi is near-chance — its export lost the sender ID.",
  { x: 7.08, y: 4.86, w: 5.25, h: 1.0, fontFace: B, fontSize: 12.5,
    color: INK, margin: 0, lineSpacing: 17 });
s.addNotes("The Month-4 setup was structurally incapable of answering this question, because its simulated encryption injected noise that sent the two arms down different training trajectories. This is the first controlled version of the comparison.");

// ═════════════════════════════════════════════════════════════════════════
// 6 — chart
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "Encrypted versus plaintext, side by side",
  "Bars are indistinguishable on every dataset — that is the result");
s.addChart(p.ChartType.bar, [
  { name: "CKKS encrypted", labels: ["CAN-VTC", "Car-Hacking", "CICIDS-2017", "VeReMi"],
    values: [1.0000, 0.9977, 0.9555, 0.4839] },
  { name: "Plaintext baseline", labels: ["CAN-VTC", "Car-Hacking", "CICIDS-2017", "VeReMi"],
    values: [1.0000, 0.9981, 0.9542, 0.4851] },
], {
  x: 0.7, y: 1.66, w: 8.0, h: 4.9,
  barDir: "col", barGapWidthPct: 55,
  chartColors: [BLUE, "9FB3C8"],
  showTitle: false, showLegend: true, legendPos: "t", legendFontSize: 11,
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9.5,
  dataLabelFormatCode: "0.000", dataLabelColor: INK,
  valAxisMaxVal: 1.15, valAxisMinVal: 0,
  catAxisLabelColor: GREY, valAxisLabelColor: GREY,
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
  valGridLine: { color: "EDF1F7", size: 1 }, catGridLine: { style: "none" },
});

s.addShape(p.ShapeType.roundRect, { x: 9.0, y: 1.75, w: 3.6, h: 2.15,
  rectRadius: 0.09, fill: { color: LIGHT }, line: { color: "E1E8F2", width: 1 } });
s.addText("Privacy invariant", { x: 9.26, y: 1.92, w: 3.1, h: 0.3, fontFace: B,
  fontSize: 11, color: NAVY, bold: true, charSpacing: 1.2, margin: 0 });
s.addText("0", { x: 9.26, y: 2.22, w: 3.1, h: 0.72, fontFace: H, fontSize: 40,
  color: GREEN, bold: true, margin: 0 });
s.addText("individual vehicle updates decrypted by the server, across every run",
  { x: 9.26, y: 2.98, w: 3.1, h: 0.8, fontFace: B, fontSize: 11.5,
    color: GREY, margin: 0, lineSpacing: 15 });

s.addShape(p.ShapeType.roundRect, { x: 9.0, y: 4.12, w: 3.6, h: 2.44,
  rectRadius: 0.09, fill: { color: LIGHT }, line: { color: "E1E8F2", width: 1 } });
s.addText("VeReMi is near chance", { x: 9.26, y: 4.3, w: 3.1, h: 0.3,
  fontFace: B, fontSize: 11, color: AMBER, bold: true, charSpacing: 1.2, margin: 0 });
s.addText("Its attacks are defined by how a sender's claims change over time, and the cleaned export dropped the sender ID. Neither formulation can express the task. Needs re-acquisition.",
  { x: 9.26, y: 4.62, w: 3.1, h: 1.75, fontFace: B, fontSize: 11.5,
    color: GREY, margin: 0, lineSpacing: 15 });
s.addNotes("If asked why VeReMi is low: we measured it before training. Best single-feature class separation is 0.046 standard deviations - the features cannot express the task. Training then confirmed it at ROC-AUC 0.516.");

// ═════════════════════════════════════════════════════════════════════════
// 7 — what we built
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "What we built in Month 5", "Real cryptography replacing a simulation");
row(s, 0.7, 1.72, 5.85, "A", "Real CKKS encryption",
  "The Month-4 'encryption' was a numpy array plus 1e-9 noise. Now genuine TenSEAL ciphertexts, 2.47 MB per vehicle per round.", BLUE);
row(s, 0.7, 3.02, 5.85, "B", "FheFL robust aggregation",
  "Outliers scored by encrypted distance to the previous global model, then down-weighted — never excluded, never decrypted.", BLUE);
row(s, 0.7, 4.32, 5.85, "C", "Multi-key key sharing",
  "The decryption key is never assembled. Recovering one vehicle's update needs collusion with U−1 others.", BLUE);
row(s, 6.75, 1.72, 5.85, "D", "A fix the paper does not have",
  "Masks only cancel if every keyed vehicle reports in — one offline breaks decryption. We re-scope per round.", GREEN);
row(s, 6.75, 3.02, 5.85, "E", "Transport security restored",
  "ECDH-P256 + AES-256-GCM + Ed25519. FHE gives confidentiality only — not authentication, integrity or replay protection.", GREEN);
row(s, 6.75, 4.32, 5.85, "F", "105 automated assertions",
  "Three suites gating every result: labelling, split disjointness, and the cryptographic invariants.", GREEN);
s.addNotes("Point D is our own contribution beyond the paper. FheFL samples a random subset of users each round but generates pairwise secrets once at enrolment - so any dropout breaks decryption silently. For a vehicle fleet that is the normal case, not an edge case.");

// ═════════════════════════════════════════════════════════════════════════
// 8 — month 1-4 catch-up
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "Then we closed three older deliverables",
  "Months 1–4 items that had never been started");
tbl(s, [
  [hdr("Deliverable"), hdr("Due"), hdr("What we delivered"), hdr("Status")],
  ["Optimized packing & encoding module", "M3–4",
   "29.6% lossless bandwidth reduction — 3.51 MB down to 2.47 MB per vehicle", "Complete"],
  ["High-performance NTT implementation", "M3–4",
   "Negacyclic NTT, validated exactly against a reference oracle. 11.22× over an optimised baseline. Test vectors exported for the C port", "Reference done"],
  ["Baseline benchmarking on hardware", "M1–2",
   "Portable harness plus a full host baseline. The target-board run is the only missing piece", "Harness done"],
], { y: 1.68, colW: [3.5, 0.95, 5.85, 1.6], rowH: 0.95, fontSize: 11.5 });

s.addShape(p.ShapeType.roundRect, { x: 0.7, y: 5.08, w: 11.9, h: 1.16,
  rectRadius: 0.09, fill: { color: "EEF9F4" }, line: { color: GREEN, width: 1.25 } });
s.addText("Deliverables due by end of Month 4:  5 of 8  →  7 of 8",
  { x: 1.0, y: 5.32, w: 11.3, h: 0.62, fontFace: H, fontSize: 20,
    color: NAVY, bold: true, margin: 0 });
s.addNotes("These were genuinely not started before this month. The packing win came from reading the protocol rather than the cryptography - the server's two operations act on independent copies of each ciphertext, so the update only needs one multiplicative level, not two.");

// ═════════════════════════════════════════════════════════════════════════
// 9 — engineering wins
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "Two measured engineering results", "Both reproducible from the repository");

s.addShape(p.ShapeType.roundRect, { x: 0.7, y: 1.72, w: 5.85, h: 4.5,
  rectRadius: 0.1, fill: { color: LIGHT }, line: { color: "E1E8F2", width: 1 } });
s.addText("Bandwidth", { x: 1.0, y: 1.96, w: 5.2, h: 0.34, fontFace: B,
  fontSize: 12, color: BLUE, bold: true, charSpacing: 1.5, margin: 0 });
s.addText("29.6%", { x: 1.0, y: 2.32, w: 5.2, h: 0.85, fontFace: H,
  fontSize: 46, color: NAVY, bold: true, margin: 0 });
s.addText("smaller uploads, at zero accuracy cost", { x: 1.0, y: 3.16, w: 5.2,
  h: 0.34, fontFace: B, fontSize: 13, color: GREY, margin: 0 });
s.addText([
  { text: "3.51 MB → 2.47 MB per vehicle per round", options: { bullet: true, breakLine: true } },
  { text: "Found by analysing the protocol, not the crypto", options: { bullet: true, breakLine: true } },
  { text: "The server's two operations use independent copies, so only one multiplicative level is needed — not two", options: { bullet: true } },
], { x: 1.0, y: 3.62, w: 5.2, h: 2.3, fontFace: B, fontSize: 12,
  color: INK, margin: 0, lineSpacing: 16, paraSpaceAfter: 7 });

s.addShape(p.ShapeType.roundRect, { x: 6.75, y: 1.72, w: 5.85, h: 4.5,
  rectRadius: 0.1, fill: { color: LIGHT }, line: { color: "E1E8F2", width: 1 } });
s.addText("NTT kernel", { x: 7.05, y: 1.96, w: 5.2, h: 0.34, fontFace: B,
  fontSize: 12, color: BLUE, bold: true, charSpacing: 1.5, margin: 0 });
s.addText("11.22×", { x: 7.05, y: 2.32, w: 5.2, h: 0.85, fontFace: H,
  fontSize: 46, color: NAVY, bold: true, margin: 0 });
s.addText("faster than an optimised O(N²) baseline", { x: 7.05, y: 3.16,
  w: 5.2, h: 0.34, fontFace: B, fontSize: 13, color: GREY, margin: 0 });
s.addText([
  { text: "The hottest kernel in any FHE library", options: { bullet: true, breakLine: true } },
  { text: "Our first version was slower than naive — it made ~8,191 tiny calls per transform", options: { bullet: true, breakLine: true } },
  { text: "Batching each stage made it 53× faster. Lesson: memory pattern dominates, not arithmetic", options: { bullet: true } },
], { x: 7.05, y: 3.62, w: 5.2, h: 2.3, fontFace: B, fontSize: 12,
  color: INK, margin: 0, lineSpacing: 16, paraSpaceAfter: 7 });
s.addNotes("The NTT lesson transfers directly to the embedded port: performance is governed by memory access pattern and per-operation overhead, not by the butterfly arithmetic. That is why the production kernel needs contiguous SIMD lanes rather than a literal transcription of the pseudocode.");

// ═════════════════════════════════════════════════════════════════════════
// 10 — honest limitations
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "What we are not claiming", "Stated up front so nothing reads as an overclaim");
row(s, 0.7, 1.78, 11.9, "1", "This is not full multi-key CKKS yet",
  "The homomorphic arithmetic is real. The multi-key key management is an algebraic model, because TenSEAL exposes no multi-key API. Migrating to OpenFHE closes this — it is the Month-6 priority.", AMBER);
row(s, 0.7, 3.02, 11.9, "2", "Nothing has run on target hardware",
  "The NTT reference, packing module and benchmark harness are all built and validated, but every number was measured on a development laptop.", AMBER);
row(s, 0.7, 4.26, 11.9, "3", "Byzantine robustness is untested against patient attackers",
  "Our scoring rewards staying close to the consensus, so a low-magnitude persistent attacker is an open blind spot. The experiment is scheduled for Month 6.", AMBER);
row(s, 0.7, 5.50, 11.9, "4", "One dataset contributes nothing until re-acquired",
  "VeReMi's cleaned export dropped the sender ID, and its attacks are defined over time per sender. We measured this before training and training confirmed it.", AMBER);
s.addNotes("Being explicit here is deliberate. Every one of these has a dated plan attached. Raising them ourselves is better than having them found in review.");

// ═════════════════════════════════════════════════════════════════════════
// 11 — the blocker / the ask
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
s.background = { color: NAVY };
s.addText("The one thing blocking us", { x: 0.8, y: 0.72, w: 11.7, h: 0.7,
  fontFace: H, fontSize: 32, color: WHITE, bold: true, margin: 0 });
s.addText("Every remaining Month 1–4 item is blocked on the same thing, and nothing else",
  { x: 0.8, y: 1.42, w: 11.7, h: 0.4, fontFace: B, fontSize: 14,
    color: ICE, margin: 0 });

s.addShape(p.ShapeType.roundRect, { x: 0.8, y: 2.12, w: 11.7, h: 1.5,
  rectRadius: 0.1, fill: { color: NAVY_D }, line: { color: AMBER, width: 1.5 } });
s.addText("No target hardware has been ordered", { x: 1.15, y: 2.38, w: 11.0,
  h: 0.5, fontFace: H, fontSize: 24, color: AMBER, bold: true, margin: 0 });
s.addText("The embedded track is now software-complete and waiting on a board. Ordering one is about an hour of work.",
  { x: 1.15, y: 2.90, w: 11.0, h: 0.5, fontFace: B, fontSize: 14,
    color: ICE, margin: 0 });

s.addText("What we are asking for", { x: 0.8, y: 3.92, w: 11.7, h: 0.36,
  fontFace: B, fontSize: 12, color: ICE, bold: true, charSpacing: 1.5, margin: 0 });

s.addShape(p.ShapeType.roundRect, { x: 0.8, y: 4.32, w: 5.75, h: 1.95,
  rectRadius: 0.1, fill: { color: NAVY_D }, line: { color: "39457F", width: 1 } });
s.addText("NXP S32G evaluation board", { x: 1.1, y: 4.54, w: 5.15, h: 0.36,
  fontFace: B, fontSize: 15, color: WHITE, bold: true, margin: 0 });
s.addText("The realistic production target — an automotive network processor built for vehicle gateways.",
  { x: 1.1, y: 4.92, w: 5.15, h: 1.15, fontFace: B, fontSize: 12.5,
    color: ICE, margin: 0, lineSpacing: 17 });

s.addShape(p.ShapeType.roundRect, { x: 6.75, y: 4.32, w: 5.75, h: 1.95,
  rectRadius: 0.1, fill: { color: NAVY_D }, line: { color: GREEN, width: 1.25 } });
s.addText("Raspberry Pi 5  — available this week", { x: 7.05, y: 4.54, w: 5.15,
  h: 0.36, fontFace: B, fontSize: 15, color: WHITE, bold: true, margin: 0 });
s.addText("An interim ARM host. Removes procurement delay from the critical path so cross-compilation and NTT profiling can start immediately.",
  { x: 7.05, y: 4.92, w: 5.15, h: 1.15, fontFace: B, fontSize: 12.5,
    color: ICE, margin: 0, lineSpacing: 17 });
s.addNotes("This is the ask. The Pi is the important half - it is inexpensive and it unblocks the work now, while the automotive board is sourced. Without a board, months 7-12 (hardware-in-the-loop, power audit) cannot start either.");

// ═════════════════════════════════════════════════════════════════════════
// 12 — next steps
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
head(s, "Month 6 plan", "In priority order");
tbl(s, [
  [hdr("Priority"), hdr("Task"), hdr("Effort"), hdr("Why it is ranked here")],
  ["P0", "Order target hardware", "1 hour", "Unblocks the entire embedded track"],
  ["P0", "Bind round number into the channel; enforce noise flooding", "3 hours", "Closes replay and an approximate-decryption exposure"],
  ["P1", "Migrate to OpenFHE", "12 days", "The only way to make multi-key CKKS real — TenSEAL cannot express it"],
  ["P1", "Low-magnitude poisoning experiment", "3 days", "Tests our known blind spot in Byzantine robustness"],
  ["P1", "Scale to 50 vehicles / 50 rounds", "4 days", "Moves toward the roadmap target of 50–200"],
  ["P1", "Re-acquire VeReMi with sender IDs", "2 days", "Restores a dataset that currently contributes nothing"],
], { y: 1.62, colW: [1.15, 4.85, 1.3, 4.6], rowH: 0.52, fontSize: 11.5 });

s.addShape(p.ShapeType.roundRect, { x: 0.7, y: 5.28, w: 11.9, h: 1.0,
  rectRadius: 0.09, fill: { color: LIGHT }, line: { color: "E1E8F2", width: 1 } });
s.addText("The embedded track shrank from ~40 days to ~22 this month, and the on-hardware benchmark from 2 days to half a day.",
  { x: 1.0, y: 5.52, w: 11.3, h: 0.55, fontFace: B, fontSize: 13.5,
    color: INK, margin: 0 });
s.addNotes("OpenFHE is the biggest single item and the most important. Until it lands we should not describe the system as full multi-key CKKS in any writeup.");

// ═════════════════════════════════════════════════════════════════════════
// 13 — closing
// ═════════════════════════════════════════════════════════════════════════
s = p.addSlide();
s.background = { color: NAVY };
s.addText("Summary", { x: 0.9, y: 0.85, w: 11.5, h: 0.72, fontFace: H,
  fontSize: 34, color: WHITE, bold: true, margin: 0 });

const sum = [
  ["Audited the project and fixed seven defects", "All machine-verified by 105 automated assertions", GREEN],
  ["Replaced simulated encryption with real CKKS", "And showed encryption costs no accuracy", GREEN],
  ["Closed three Month 1–4 deliverables", "7 of 8 now complete, up from 5 of 8", GREEN],
  ["One blocker remains: order a board", "The embedded track is software-complete and waiting", AMBER],
];
let yy = 1.85;
sum.forEach(([t, d, c]) => {
  s.addShape(p.ShapeType.ellipse, { x: 0.9, y: yy + 0.04, w: 0.32, h: 0.32,
    fill: { color: c } });
  s.addText(t, { x: 1.45, y: yy - 0.02, w: 10.9, h: 0.38, fontFace: B,
    fontSize: 17, color: WHITE, bold: true, margin: 0 });
  s.addText(d, { x: 1.45, y: yy + 0.36, w: 10.9, h: 0.36, fontFace: B,
    fontSize: 13, color: ICE, margin: 0 });
  yy += 1.02;
});

s.addText("github.com/hithesh2205/LG-IoV", { x: 0.9, y: 6.28, w: 11.5, h: 0.4,
  fontFace: B, fontSize: 14, color: ICE, margin: 0 });
s.addText("Full documentation: 27-page master PDF + 16 supporting documents in the repository",
  { x: 0.9, y: 6.64, w: 11.5, h: 0.36, fontFace: B, fontSize: 11.5,
    color: "8FA3CC", margin: 0 });
s.addNotes("Close on the ask. Everything else is on track and documented; the board is the one decision we need from this meeting.");

p.writeFile({ fileName: OUT }).then(() => console.log("wrote " + OUT));

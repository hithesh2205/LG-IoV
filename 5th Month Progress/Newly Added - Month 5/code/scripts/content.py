"""Content of the master documentation PDF.

Kept separate from build_master_pdf.py so the document text can be edited
without touching the layout machinery.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path


def build_content(F, res, bench, diagrams: Path, helpers):
    P = helpers["P"]; B = helpers["B"]; H = helpers["H"]
    tbl = helpers["tbl"]; figure = helpers["figure"]
    results_table = helpers["results_table"]
    Spacer = helpers["Spacer"]; PageBreak = helpers["PageBreak"]
    NextPageTemplate = helpers["NextPageTemplate"]; cm = helpers["cm"]
    S = helpers["S"]
    from reportlab.platypus import Paragraph

    def para(t, style):
        return Paragraph(t, S[style])

    # ═════════════════════════════════════════════════════════════════════
    # TITLE PAGE
    # ═════════════════════════════════════════════════════════════════════
    F += [
        Spacer(1, 3.2 * cm),
        para("Privacy-Preserving Collaborative<br/>Intrusion Detection for the<br/>Internet of Vehicles", "title"),
        Spacer(1, 0.7 * cm),
        para("Federated Learning with Multi-Key CKKS Homomorphic Encryption", "subtitle"),
        Spacer(1, 1.6 * cm),
        para("<b>Master Project Documentation</b>", "subtitle"),
        para("Complete record, Month 1 through Month 5", "subtitle"),
        Spacer(1, 2.6 * cm),
    ]
    F.append(tbl([
        ["Programme", "LG Soft India (LGSI) — 12-month industry project"],
        ["Reporting period", "Month 1 – Month 5"],
        ["Document date", date.today().isoformat()],
        ["Status", "Month 5 complete; embedded track behind schedule"],
        ["Snapshot folder", "5th Month Progress/"],
        ["Active codebase", "Complete Source Code/NewModel_active/"],
    ], [4.6 * cm, 10.4 * cm], header=False, fs=9.4))
    F += [
        Spacer(1, 1.4 * cm),
        para("This document is written to be read from beginning to end by someone who "
             "has never seen the project. Every technical term is explained where it "
             "first appears. It describes the system as it actually is, including the "
             "defects found and fixed in Month 5 and the work that remains.", "body"),
        NextPageTemplate("body"), PageBreak(),
    ]

    # ═════════════════════════════════════════════════════════════════════
    # CONTENTS
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Contents", 1))
    for line in [
        "<b>Part I — Introduction</b>",
        "&nbsp;&nbsp;1. What this project is · 2. Problem statement · 3. Motivation",
        "&nbsp;&nbsp;4. Objectives · 5. Proposed solution · 6. Scope · 7. Workflow & architecture",
        "<b>Part II — Concepts from scratch</b>",
        "&nbsp;&nbsp;8. IoV & the CAN bus · 9. Intrusion detection · 10. Federated learning",
        "&nbsp;&nbsp;11. Non-IID data & Dirichlet sharding · 12. Homomorphic encryption & CKKS",
        "&nbsp;&nbsp;13. Ring-LWE, SIMD packing, multiplicative depth · 14. Multi-key HE & secret sharing",
        "&nbsp;&nbsp;15. Byzantine robustness · 16. KAN & Chebyshev polynomials",
        "&nbsp;&nbsp;17. Data leakage · 18. Evaluation metrics",
        "<b>Part III — Month-by-month progress</b>",
        "&nbsp;&nbsp;19. Month 1–2 · 20. Month 3 · 21. Month 4 · 22. Month 5",
        "<b>Part IV — Month 5 in detail</b>",
        "&nbsp;&nbsp;23. Defects found · 24. What was implemented · 25. Results · 26. Measurements",
        "<b>Part V — Current status</b>",
        "&nbsp;&nbsp;27. Completed / partial / not started · 28. Known limitations · 29. LG deliverables",
        "<b>Part VI — What to do next</b>",
        "<b>Part VII — Reproduction & verification</b>",
    ]:
        F.append(para(line, "toc"))
    F.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════
    # PART I
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Part I — Introduction", 1))

    F.append(H("1. What this project is", 2))
    F.append(P(
        "Modern vehicles are computers on wheels. Engine, brakes, steering and dozens of "
        "other subsystems talk to each other over an internal network, and increasingly "
        "the vehicle also talks to other vehicles and to roadside infrastructure. Both "
        "channels can be attacked, and a successful attack on a vehicle network is a "
        "<b>safety</b> problem, not merely a data problem."))
    F.append(P(
        "This project builds an <b>Intrusion Detection System (IDS)</b> for vehicle networks "
        "that is trained <b>collaboratively across a fleet</b> without any vehicle revealing "
        "its data — and without the central server that combines their work being able to "
        "read what any individual vehicle contributed."))

    F.append(H("2. Problem statement", 2))
    F.append(P(
        "A single vehicle sees very little attack traffic. A detector trained on one "
        "vehicle's logs generalises poorly. Pooling logs from thousands of vehicles into "
        "one dataset would produce a far stronger detector — but those logs contain "
        "location traces, driving behaviour and vehicle identity, so they cannot legally "
        "or ethically be centralised."))
    F.append(P("This produces a three-way tension:"))
    F.append(B("<b>Utility</b> — the detector needs data from many vehicles."))
    F.append(B("<b>Privacy</b> — raw data cannot leave the vehicle, and model updates "
               "leak the data they were computed from."))
    F.append(B("<b>Security</b> — if updates are encrypted so the server cannot inspect "
               "them, the server also cannot spot a malicious vehicle poisoning the model."))
    F.append(P(
        "That last point is the crux. Encryption solves privacy and <i>creates</i> a "
        "security hole. The central research question of this project is how to get both "
        "at once."))

    F.append(H("3. Motivation", 2))
    F.append(B("<b>Safety.</b> A compromised CAN bus can command braking, acceleration or "
               "steering. Detection is a safety function."))
    F.append(B("<b>Regulation.</b> UNECE R155 requires vehicle cybersecurity management; "
               "GDPR-class rules restrict centralising location data."))
    F.append(B("<b>Fleet effect.</b> An attack first seen by one vehicle should protect the "
               "whole fleet within hours."))
    F.append(B("<b>Research gap.</b> Federated learning plus homomorphic encryption for "
               "vehicular IDS, with Byzantine robustness <i>inside</i> the encrypted domain, "
               "is not a solved problem."))

    F.append(H("4. Objectives", 2))
    F.append(tbl([
        ["#", "Objective", "Status at Month 5"],
        ["O1", "Unify heterogeneous vehicular datasets into one feature space", "Achieved"],
        ["O2", "Train an accurate IDS on that feature space", "Achieved"],
        ["O3", "Federate training across simulated vehicles with non-IID data", "Achieved"],
        ["O4", "Encrypt model updates so the server cannot read them", "Achieved (real CKKS)"],
        ["O5", "Detect and suppress poisoned updates without decrypting them", "Achieved"],
        ["O6", "Distribute the key so no single party can decrypt an individual update", "Partial — algebraic model; needs OpenFHE"],
        ["O7", "Run on embedded automotive hardware", "Not started"],
        ["O8", "Quantify the privacy/accuracy/cost trade-off", "Partial"],
    ], [1.1 * cm, 8.4 * cm, 6.0 * cm]))

    F.append(H("5. Proposed solution", 2))
    F.append(P(
        "Each vehicle trains the detector on its own data and sends only the resulting "
        "model parameters — encrypted. The server combines the encrypted parameters "
        "arithmetically, without decrypting them, weighting each vehicle by how far its "
        "update sits from the current consensus so that poisoned updates are suppressed. "
        "The decryption key is split across vehicles so that no single party — including "
        "the server — can decrypt any individual contribution."))

    F.append(H("6. Scope", 2))
    F.append(tbl([
        ["In scope", "Out of scope"],
        ["Federated training over four vehicular/network datasets\n"
         "CKKS encryption of model updates\n"
         "Robust aggregation in the encrypted domain\n"
         "Distributed key sharing with dropout tolerance\n"
         "Authenticated transport between vehicle and server\n"
         "Cost and privacy measurement",
         "Physical ECU hardening\n"
         "In-vehicle response/mitigation after detection\n"
         "Adversarial-robustness of the classifier itself\n"
         "Production certification (ISO 26262 / UNECE R155 audit)\n"
         "Real vehicle deployment"],
    ], [7.5 * cm, 7.5 * cm]))

    F.append(H("7. Overall workflow and system architecture", 2))
    F.append(P(
        "One <b>round</b> of the system works as follows: the server broadcasts the current "
        "global model; each participating vehicle trains it briefly on its own data; each "
        "vehicle encrypts the resulting parameters and uploads them; the server measures how "
        "far each encrypted update is from the previous global model — without decrypting it "
        "— down-weights the outliers, sums everything homomorphically, and decrypts only the "
        "sum. Repeat."))
    F.append(figure(diagrams / "01_system_architecture.png",
                    "Figure 1 — System architecture and trust boundaries. Vehicles hold raw "
                    "data and a private key share; the server holds only the plaintext global "
                    "model and never sees an individual update."))
    F.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════
    # PART II — CONCEPTS
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Part II — Concepts explained from scratch", 1))
    F.append(P("Each concept is presented as: <i>what it is -&gt; why we need it -&gt; how it works "
               "-&gt; how we use it here</i>."))

    F.append(H("8. The Internet of Vehicles and the CAN bus", 2))
    F.append(P(
        "<b>What.</b> The <b>Controller Area Network (CAN)</b> is the internal network almost "
        "every car uses. Electronic Control Units (ECUs) broadcast short messages on a shared "
        "two-wire bus. A CAN message has an <b>ID</b> (what kind of message, and its priority — "
        "lower ID wins arbitration), a <b>DLC</b> (how many data bytes) and up to <b>8 data "
        "bytes</b>. The <b>Internet of Vehicles (IoV)</b> extends this outward: vehicles also "
        "broadcast to each other (V2V) and to roadside units (V2I) using DSRC or C-V2X."))
    F.append(P(
        "<b>Why it matters.</b> CAN was designed in 1986 for a closed, trusted network. It has "
        "<b>no authentication and no encryption</b>. Any node that can write to the bus can "
        "impersonate any other node."))
    F.append(P("<b>How attacks work.</b>"))
    F.append(B("<b>DoS / flooding</b> — inject a stream of ID <font face='Courier'>0x000</font> "
               "messages. Because the lowest ID always wins arbitration, this starves every "
               "legitimate message. In our CAN-VTC data this is 51.1% of the capture."))
    F.append(B("<b>Fuzzing</b> — inject random payloads on valid IDs to provoke undefined behaviour."))
    F.append(B("<b>Spoofing / impersonation</b> — send well-formed messages claiming to be "
               "another ECU (e.g. a false RPM or gear reading)."))
    F.append(P(
        "<b>In this project.</b> Two of our four datasets are raw CAN captures (IEEE VTC-CAN and "
        "Car-Hacking); one is V2X beacon data (VeReMi); one is enterprise IP flow data used as a "
        "transfer check (CICIDS-2017)."))

    F.append(H("9. Intrusion detection", 2))
    F.append(P(
        "<b>What.</b> An IDS observes traffic and decides whether an attack is present. "
        "<b>Signature-based</b> systems match known attack patterns — precise, but blind to new "
        "attacks. <b>Anomaly-based</b> systems learn what normal looks like and flag deviations — "
        "which is what a machine-learned IDS does, and what we build."))
    F.append(P(
        "<b>How we frame it.</b> We slide a <b>window</b> of 64 consecutive CAN messages, compute "
        "46 summary features over that window, and classify the window. A window is labelled as an "
        "attack if it contains at least one injected message."))
    F.append(P("<b>The 46 features</b>, for CAN data:"))
    F.append(tbl([
        ["Slots", "Feature", "What it detects"],
        ["0–7", "Mean of each payload byte", "Shifted payload semantics (spoofed values)"],
        ["8–15", "Std-dev of each payload byte", "Fuzzing — random payloads raise variance"],
        ["16–17", "DLC mean and std", "Malformed frames"],
        ["18", "Unique-ID ratio", "Flooding collapses this toward 0"],
        ["19", "Dominant-ID frequency", "Flooding pushes this toward 1"],
        ["20–43", "CAN-ID histogram (24 hash buckets)", "Shape of bus traffic"],
        ["44", "Mean Shannon entropy of payload bytes", "Randomness — fuzzing raises it"],
        ["45", "Non-zero payload byte ratio", "All-zero DoS payloads drive it down"],
    ], [1.7 * cm, 6.5 * cm, 7.3 * cm]))
    F.append(P(
        "<b>Why a shared 46-D space matters.</b> CAN payloads, IP flow statistics and V2X "
        "kinematics have nothing structurally in common. Mapping all of them into the same "
        "46-dimensional vector lets a single architecture serve all four datasets — which is "
        "what makes cross-dataset federation coherent at all. This was the strongest engineering "
        "decision of Month 1."))

    F.append(H("10. Federated learning", 2))
    F.append(P(
        "<b>What.</b> Instead of moving data to the model, federated learning (FL) moves the model "
        "to the data. The server holds a global model; each client trains it locally; clients send "
        "back only parameter updates; the server averages them."))
    F.append(para("g<sub>i</sub> = (1/U) · Sum<sub>u=1..U</sub> f<sub>i-1</sub><sup>u</sup>", "eq"))
    F.append(P(
        "where <i>f<sup>u</sup></i> is vehicle <i>u</i>'s locally trained parameter vector and "
        "<i>g</i> is the global model. This is <b>FedAvg</b>."))
    F.append(P(
        "<b>Why it is not enough.</b> Gradients are not anonymous. Given an update, an adversary "
        "can often reconstruct the training samples that produced it — a <b>gradient inversion "
        "attack</b>. So FL alone moves the privacy problem rather than solving it. That is the "
        "reason for everything in the next sections."))
    F.append(P(
        "<b>In this project.</b> 10 simulated vehicles, 5 rounds, 2 local epochs per round, 70% of "
        "vehicles sampled per round."))

    F.append(H("11. Non-IID data and Dirichlet sharding", 2))
    F.append(P(
        "<b>What.</b> IID means each client's data looks like a random sample of the whole. Real "
        "fleets are the opposite — a highway commuter and a city delivery van meet different "
        "traffic and different attacks. This is <b>non-IID</b> data, and it makes FL converge "
        "slower and less stably."))
    F.append(P(
        "<b>How we simulate it.</b> The <b>Dirichlet distribution</b> with concentration parameter "
        "alpha controls how skewed the split is: alpha -&gt; infinity gives uniform (IID) shares; alpha -&gt; 0 gives each "
        "client almost a single class. We use <b>alpha = 0.3</b>, the standard choice for strongly "
        "non-IID FL benchmarks."))

    F.append(H("12. Homomorphic encryption and CKKS", 2))
    F.append(P(
        "<b>What.</b> Normally, data must be decrypted before it can be used. <b>Homomorphic "
        "encryption (HE)</b> allows computation directly on ciphertext:"))
    F.append(para("Dec( Enc(a) (+) Enc(b) ) = a + b", "eq"))
    F.append(P("<b>Simple example.</b> A toy additive scheme: pick a secret key <i>s</i> = 7 and "
               "encrypt by adding it."))
    F.append(para("Enc(5) = 5 + 7 = 12 &nbsp;&nbsp; Enc(3) = 3 + 7 = 10 &nbsp;&nbsp; "
                  "12 + 10 = 22 &nbsp;&nbsp; 22 - 2·7 = 8 = 5 + 3 yes", "eq"))
    F.append(P(
        "The server added two numbers it could not read. Real schemes replace this trivial masking "
        "with lattice problems, but the shape of the idea is identical."))
    F.append(P("<b>Why CKKS.</b>"))
    F.append(tbl([
        ["Scheme", "Data type", "Fit for this project"],
        ["Paillier", "integers", "Additive only; one ciphertext per number -&gt; ~44,164 ciphertexts"],
        ["BFV / BGV", "exact integers", "Would need fixed-point encoding of every weight"],
        ["TFHE", "bits", "Bit-level — catastrophic at this scale"],
        ["CKKS", "approximate reals", "Native real vectors; thousands packed per ciphertext"],
    ], [2.6 * cm, 3.2 * cm, 9.7 * cm]))
    F.append(P(
        "Neural-network weights <i>are</i> vectors of real numbers, so CKKS is the natural fit. "
        "Its cost is that it is <b>approximate</b>: decryption returns the right answer plus a small "
        "error. We measured that error at <b>&lt;=3×10<sup>-8</sup></b> — six orders of magnitude below "
        "the noise already present in stochastic gradient descent, therefore irrelevant here."))

    F.append(H("13. Ring-LWE, SIMD packing and multiplicative depth", 2))
    F.append(P(
        "<b>Ring Learning With Errors (RLWE)</b> is the hard problem CKKS security rests on. Given "
        "<i>a</i> (public, random) and <i>b = a·s + e</i> where <i>s</i> is secret and <i>e</i> is "
        "small noise, recover <i>s</i>. Without the noise this is simple linear algebra; with it, "
        "the problem is believed hard even for quantum computers."))
    F.append(P(
        "<b>SIMD packing</b> is the property that makes CKKS practical here. A single ciphertext "
        "holds <i>N/2</i> real numbers in independent \"slots\", and one homomorphic addition adds "
        "all slots at once. At N = 8192 that is 4096 values per ciphertext, so our 44,164-parameter "
        "model needs <b>11 ciphertexts instead of 44,164</b>."))
    F.append(P(
        "<b>Multiplicative depth</b> is the binding constraint on protocol design. Every "
        "ciphertext × ciphertext multiplication consumes one prime from the modulus chain. A chain "
        "of L primes supports L-2 multiplications. Run out, and the ciphertext can no longer be "
        "decrypted correctly."))
    F.append(para("<b>This is not a theoretical concern — it dictated our design. See §26.</b>", "note"))

    F.append(H("14. Multi-key homomorphic encryption and secret sharing", 2))
    F.append(P(
        "<b>The problem with one key.</b> If all vehicles share a single CKKS key, then every "
        "vehicle can decrypt the global model — so every vehicle holds the secret key — so any "
        "vehicle, or a server that obtains the key from any one of them, can decrypt <b>every other "
        "vehicle's individual update</b>. The privacy property is vacuous. This was the Month-4 "
        "design, and finding it is what drove Month 5."))
    F.append(P(
        "<b>The fix: additive secret sharing.</b> The key is never assembled anywhere. Each vehicle "
        "<i>u</i> holds a share <i>s<sub>u</sub></i> of a key that exists only as a sum:"))
    F.append(para("s = Sum<sub>u</sub> s<sub>u</sub>", "eq"))
    F.append(P(
        "Vehicles pre-agree <b>pairwise</b> secrets with the antisymmetry property "
        "<i>s<sub>i,j</sub> = -s<sub>j,i</sub></i> and upload a <i>masked</i> share:"))
    F.append(para("ss<sub>u</sub> = s<sub>u</sub> + Sum<sub>j!=u</sub> s<sub>u,j</sub>", "eq"))
    F.append(P("Because the masks are antisymmetric they cancel in the sum:"))
    F.append(para("Sum<sub>u</sub> ss<sub>u</sub> = Sum<sub>u</sub> s<sub>u</sub> + 0 = s", "eq"))
    F.append(P(
        "The server reconstructs enough key material to decrypt the <b>aggregate</b>, and nothing "
        "else. <b>Security property:</b> to recover one honest vehicle's update, the server must "
        "collude with U-1 vehicles."))
    F.append(figure(diagrams / "04_multikey_sharing.png",
                    "Figure 2 — Distributed multi-key sharing, the dropout gap in the original "
                    "scheme, and the per-round mask re-scoping that closes it."))

    F.append(H("15. Byzantine robustness — detecting poisoning without looking", 2))
    F.append(P(
        "<b>What.</b> A malicious vehicle can train on deliberately mislabelled data and upload a "
        "poisoned update, biasing the global model — e.g. teaching it to ignore one attack class. "
        "This is a <b>data poisoning attack</b>."))
    F.append(P(
        "<b>The classic answer, and why it fails here.</b> <b>Multi-Krum</b> computes pairwise "
        "distances between all client updates and keeps the mutually closest ones. It requires the "
        "server to <i>see every client's update</i>. Under encryption that is impossible — and the "
        "Month-4 code achieved it only by decrypting every individual update, which destroyed the "
        "entire privacy claim."))
    F.append(P(
        "<b>What we use instead.</b> FheFL scores each vehicle by distance to the <b>previous global "
        "model</b>, which the server already holds in plaintext. Only the cross-term needs the "
        "encrypted domain:"))
    F.append(para("[d<sup>u</sup>] = g<sup>T</sup>g + [(f<sup>u</sup> - 2g)<sup>T</sup>·f<sup>u</sup>]", "eq"))
    F.append(P("Then a <b>non-poisoning rate</b> converts distance into a weight:"))
    F.append(para("p<sup>u</sup> = 1 - d<sup>u</sup> / Sum<sub>j</sub> d<sup>j</sup> &nbsp;&nbsp;&nbsp; "
                  "Sum<sub>u</sub> p<sup>u</sup> = U - 1", "eq"))
    F.append(P(
        "Far-away vehicles get small weights; close ones get large weights. Crucially this "
        "<b>down-weights rather than excludes</b> — which matters in IoV, because the vehicle that "
        "encountered a genuinely novel attack is both the most distant and the most valuable, and "
        "Multi-Krum would have thrown it away."))
    F.append(para(
        "<b>Known limitation.</b> Scoring by closeness to the current consensus <i>rewards</i> "
        "staying close. A patient attacker submitting small, consistently-biased updates every "
        "round scores a high non-poisoning rate. This is an open blind spot and the first experiment "
        "scheduled for Month 6.", "warn"))

    F.append(H("16. Kolmogorov–Arnold Networks and Chebyshev polynomials", 2))
    F.append(P(
        "<b>What.</b> A standard neural network puts fixed activation functions (ReLU, tanh) on the "
        "<i>nodes</i> and learns the weights on the <i>edges</i>. A <b>Kolmogorov–Arnold Network "
        "(KAN)</b> inverts this: it puts <b>learnable functions on the edges</b>. The name comes "
        "from the Kolmogorov–Arnold representation theorem, which states that any continuous "
        "multivariate function can be written as a composition of sums of univariate functions."))
    F.append(P(
        "<b>Chebyshev polynomials</b> are how we represent those learnable edge functions. They are "
        "defined by a simple recurrence:"))
    F.append(para("T<sub>0</sub>(x) = 1 &nbsp;&nbsp; T<sub>1</sub>(x) = x &nbsp;&nbsp; "
                  "T<sub>k</sub>(x) = 2x·T<sub>k-1</sub>(x) - T<sub>k-2</sub>(x)", "eq"))
    F.append(P(
        "They are numerically well-behaved on [-1, 1] (inputs are squashed with tanh first), and "
        "the recurrence is cheap. Our <b>ChebyKAN</b> uses degree 4, hidden dimension 64, 2 layers "
        "— <b>44,164 parameters</b> in the 5-class configuration."))
    F.append(P("<b>Why so small?</b> Under encryption, parameter count is the cost driver:"))
    F.append(B("it sets the number of ciphertexts (44,164 params -&gt; 11 ciphertexts),"))
    F.append(B("which sets the bandwidth per vehicle per round (3.59 MB),"))
    F.append(B("which sets the aggregation time."))
    F.append(P(
        "The earlier MamKANformer design had ~609,000 parameters — 14× larger, therefore 14× the "
        "ciphertexts, bandwidth and aggregation cost. Shrinking the model was the right call."))
    F.append(para(
        "<b>A correction to earlier project documents.</b> Month-4 slides justified ChebyKAN on the "
        "grounds that Chebyshev polynomials \"evaluate natively on ciphertexts\". That argument is "
        "about encrypted <i>inference</i> — running the model forward on ciphertext — which this "
        "system does not do. We encrypt <i>weights for aggregation</i>, and a weighted sum treats "
        "any architecture's weights as a flat vector. Moreover ChebyKAN as implemented uses tanh, "
        "LayerNorm and Dropout, none of which are homomorphically evaluable. The parameter-count "
        "argument above is the correct one — and it is the stronger one.", "note"))

    F.append(H("17. Data leakage — the failure mode that invalidates results", 2))
    F.append(P(
        "<b>What.</b> Data leakage is when information about the test set reaches the model during "
        "training. The model then scores well by recognising something it should not have access "
        "to. Leakage produces <b>impressive numbers that mean nothing</b>, and it is the single most "
        "common way machine-learning results turn out to be wrong."))
    F.append(P("Two forms bit this project, both found and fixed in Month 5:"))
    F.append(P("<b>Label leakage (defect D1).</b> Attack captures contain mostly normal traffic with "
               "injected messages interleaved. Labelling <i>every</i> window from "
               "<font face='Courier'>DoS_dataset.csv</font> as \"DoS\" teaches the model to recognise "
               "<b>which capture file it is looking at</b>, not whether an intrusion is present. It "
               "can score perfectly without ever detecting an injected frame."))
    F.append(P("<b>Split leakage (defect D2).</b> Our windows overlap by 75% — window <i>k</i> and "
               "window <i>k+1</i> share 48 of their 64 messages. A uniformly random train/test split "
               "puts near-duplicates on both sides of the boundary, so test accuracy measures "
               "memorisation rather than generalisation."))
    F.append(figure(diagrams / "03_data_pipeline_and_defects.png",
                    "Figure 3 — The data pipeline, and the before/after of both leakage defects."))
    F.append(PageBreak())

    F.append(H("18. Evaluation metrics", 2))
    F.append(tbl([
        ["Metric", "Definition", "Why it matters here"],
        ["Accuracy", "correct / total", "Misleading under class imbalance — 95% benign traffic means a "
                                        "do-nothing classifier scores 95%"],
        ["Precision", "TP / (TP+FP)", "High false positives make an IDS get switched off"],
        ["Recall", "TP / (TP+FN)", "A missed intrusion is a safety event"],
        ["Macro F1", "unweighted mean of per-class F1", "Treats rare attack classes as equally "
                                                        "important — the honest headline number"],
        ["ROC-AUC", "P(random attack ranked above random benign)", "Threshold-independent. 0.5 = "
                                                                   "random guessing"],
    ], [2.4 * cm, 5.4 * cm, 7.2 * cm]))
    F.append(para(
        "<b>Reading the numbers in this document.</b> ROC-AUC ~= 0.5 means the model learned nothing, "
        "regardless of how good the accuracy looks. Accuracy far above macro F1 means the model is "
        "riding the majority class. Both patterns appeared in the Month-4 results and both were "
        "symptoms of real defects.", "note"))
    F.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════
    # PART III — MONTH BY MONTH
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Part III — Month-by-month progress", 1))

    def month_block(title, planned, implemented, concepts, decisions, experiments,
                    problems, solutions, results, improved, pending):
        F.append(H(title, 2))
        for label, content in [
            ("Planned", planned), ("Implemented", implemented),
            ("Concepts used", concepts), ("Technical decisions", decisions),
            ("Experiments", experiments), ("Problems encountered", problems),
            ("How they were solved", solutions), ("Results", results),
            ("Improvement over the previous month", improved),
            ("Left pending", pending),
        ]:
            F.append(H(label, 3))
            if isinstance(content, list):
                for c in content:
                    F.append(B(c))
            else:
                F.append(P(content))

    month_block(
        "19. Month 1–2 — Framing, datasets and the first architecture",
        "Establish the problem, acquire datasets, specify the threat landscape, choose a model "
        "architecture, and stand up a federated skeleton.",
        ["Analysed the source FedIoV paper and drafted the system architecture.",
         "Acquired and cleaned four datasets into <font face='Courier'>Preprocessed_Dataset/</font> (8.6 GB).",
         "Wrote the <b>46-D timeless feature extractor</b> spanning CAN, IP-flow and V2X data.",
         "Implemented the <b>KANConvNet</b> classifier (generation 1).",
         "Implemented Phase-1 federated setup: Dirichlet partitioning, ECDH + AES-256-GCM secure "
         "channels, GA hyperparameter configuration; ran for N=50 clients on all four datasets.",
         "Wrote <font face='Courier'>ROADMAP.md</font> targeting 50–200 clients, 200–300 rounds, "
         "TOPSIS + Multi-Krum aggregation, client-level DP and 15-run statistical evaluation."],
        "CAN bus protocol · intrusion detection · federated learning · non-IID data · Dirichlet "
        "sharding · ECDH key agreement · AES-GCM authenticated encryption.",
        ["<b>Unify all datasets into one 46-D feature space</b> — correct, and the foundation of "
         "everything since.",
         "<b>KAN over a standard MLP</b> — reasonable; learnable edge functions suit heterogeneous "
         "tabular features.",
         "<b>Build the secure channel early</b> — correct, though it was later removed and had to be "
         "restored in Month 5."],
        "Phase-1 partitioning runs at N=50 across all four datasets; centralized KANConvNet training "
        "baselines.",
        "Heterogeneous data formats: CAN logs, flow CSVs and V2X beacons share no structure.",
        "The 46-D timeless descriptor — window-level statistics that can be computed from any of the "
        "three source types.",
        "Working end-to-end centralized pipeline; federated skeleton with N=50 partitions.",
        "Baseline — first month.",
        ["No threat model document (an LG Month 1–2 deliverable).",
         "No security specification (an LG Month 1–2 deliverable).",
         "No hardware benchmarking; everything ran on a laptop."],
    )
    F.append(PageBreak())

    month_block(
        "20. Month 3 — FHE study and the MamKANformer branch",
        "Select an FHE scheme, understand its mathematics, evaluate libraries, and improve the "
        "classifier.",
        ["Selected <b>CKKS</b> as the FHE scheme.",
         "Documented CKKS mathematics in depth: encoding/decoding, RLWE, rescaling, relinearisation.",
         "Implemented the <b>MamKANformer</b> architecture (Mamba state-space model + multi-head "
         "attention + B-spline KAN).",
         "Built a React/xyflow architecture visualiser."],
        "Homomorphic encryption · CKKS · RLWE · SIMD packing · rescaling · relinearisation · "
        "state-space models · B-spline basis functions.",
        ["<b>CKKS over Paillier/BFV/TFHE</b> — correct and well justified; model updates are real "
         "vectors and SIMD packing is what makes the scheme affordable.",
         "<b>MamKANformer trunk</b> — later reversed; ~609k parameters is far too many under encryption."],
        "Centralized MamKANformer training runs.",
        "MamKANformer's parameter count made encrypted aggregation impractical.",
        "Reversed the decision in Month 4 in favour of a much smaller model.",
        "Strong CKKS documentation — still the best theory asset in the repository.",
        "Principled scheme selection replaced an unexamined default.",
        ["Library evaluation was never performed — TenSEAL was used because it installed easily.",
         "No cross-compilation.",
         "MamKANformer code was left in the tree after being abandoned, causing confusion later."],
    )

    month_block(
        "21. Month 4 — ChebyKAN pivot and the first federated FHE runs",
        "Shrink the model, build layer-wise encrypted federated learning, add Byzantine robustness, "
        "and produce comparison results.",
        ["Replaced MamKANformer with <b>ChebyKAN</b> — 609k -&gt; 44,164 parameters.",
         "Built a layer-wise encrypted federated loop.",
         "Added a Multi-Krum Byzantine filter.",
         "Ran FHE vs no-FHE comparisons on all four datasets.",
         "Wrote a genuine TenSEAL CKKS benchmark for encryption cost.",
         "Published results dashboard and CKKS explainer as HTML artifacts."],
        "Chebyshev polynomial basis · layer-wise encryption · Multi-Krum · FedAvg weighting · "
        "ciphertext expansion.",
        ["<b>ChebyKAN at 44k parameters</b> — correct; parameter count is the cost driver under encryption.",
         "<b>Real TenSEAL benchmark alongside the simulation</b> — correct and honest; the script's own "
         "docstring stated the simulation \"does not cost anything extra to run\".",
         "<b>Removing ECDH/AES transport security</b> — <b>wrong</b>; FHE gives payload confidentiality "
         "only, not authentication, integrity or replay protection.",
         "<b>Multi-Krum</b> — right goal, wrong mechanism for an encrypted pipeline."],
        "FHE vs no-FHE on four datasets at 10 clients / 5 rounds, single seed; real CKKS timing benchmark.",
        ["The reported FHE-vs-no-FHE accuracy gaps were not reproducible or explicable.",
         "VeReMi sat at ROC-AUC 0.525 — no better than guessing.",
         "CAN-VTC reported 100.0% accuracy and ROC-AUC 1.0."],
        "Not solved during Month 4 — these became the Month-5 audit findings. Each turned out to be a "
        "symptom of a real defect: uncontrolled experiment, broken VeReMi formulation, and label leakage "
        "respectively.",
        "A complete, runnable federated pipeline with encryption switchable on and off, and a defensible "
        "real-CKKS cost measurement (0.14 s/round, 20.8× ciphertext expansion).",
        "14× smaller model; first end-to-end federated results; first real encryption measurements.",
        ["The \"encryption\" used during training was numpy plus 1e-9 noise — not encryption.",
         "The Byzantine filter decrypted every individual client update server-side.",
         "Datasets were labelled by filename rather than by ground truth.",
         "Experimental scale dropped to 10 clients / 5 rounds without amending the roadmap."],
    )
    F.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════
    # PART IV — MONTH 5
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Part IV — Month 5 in detail", 1))

    F.append(H("22. What Month 5 set out to do", 2))
    F.append(P(
        "Month 5 began as an investigation into multi-key CKKS using the FheFL paper "
        "(arXiv:2306.05112). A full audit of the project was performed first, which found that "
        "several headline results were invalid and that the central privacy claim was not met by "
        "the code. Month 5 therefore became: <b>audit, fix, then advance</b>."))

    F.append(H("23. Defects found and fixed", 2))
    F.append(tbl([
        ["ID", "Defect", "Evidence", "Fix", "Status"],
        ["D1", "Labels came from the source filename, not ground truth",
         "car_hack_dataset.py explicitly discarded the R/T flag; CAN-VTC labelled by file index",
         "Use the HCRL R/T flag; derive CAN-VTC DoS labels from the 0x000 injection signature",
         "Fixed"],
        ["D2", "Overlapping windows split randomly across train/test",
         "window=64, stride=16 -&gt; 75% overlap; preprocess.py shuffled individual windows",
         "Contiguous block IDs; whole blocks assigned to one split; assert_no_group_overlap",
         "Fixed"],
        ["D3", "FHE-vs-no-FHE was not a controlled experiment",
         "Identical config gave different confusion matrices; the encrypted run finished 40% faster",
         "Three explicit backends; exact and none are bitwise identical by construction",
         "Fixed"],
        ["D4", "Server decrypted every individual client update",
         "server.py called .decrypt() on each client's parameters to run Multi-Krum",
         "Replaced with FheFL encrypted-domain scoring; AggregationAudit asserts zero",
         "Fixed"],
        ["D5", "VeReMi was not learning (ROC-AUC 0.525)",
         "Windows mixed beacons from different senders; 45.3% attack rows made majority-vote labels "
         "a coin flip",
         "Per-beacon plausibility features; sender-grouped windowing implemented for re-acquired data",
         "Fixed"],
        ["D6", "Transport security had been removed",
         "Month-4 deck: \"handshakes... completely removed\"",
         "Restored ECDH-P256 + AES-256-GCM + Ed25519 mutual auth",
         "Fixed"],
        ["D7", "Documentation contradicted the code",
         "GEMINI.md described KANConvNet; config.yaml described MamKANformer; server claimed TOPSIS",
         "All rewritten; ROADMAP.md carries an explicit scope-reconciliation table",
         "Fixed"],
    ], [0.9 * cm, 3.2 * cm, 4.6 * cm, 4.6 * cm, 1.7 * cm], fs=7.4))

    F.append(H("24. What was newly implemented", 2))
    F.append(H("24.1 Real CKKS encryption", 3))
    F.append(P(
        "The <font face='Courier'>SimulatedCKKSVector</font> class — a numpy array plus N(0, 1e-9) "
        "noise — was removed. In its place are three explicit backends: <b>ckks</b> (real TenSEAL "
        "ciphertexts), <b>exact</b> (identical arithmetic, no encryption, no noise) and <b>none</b> "
        "(plaintext baseline). Because <i>exact</i> and <i>none</i> are arithmetically identical by "
        "construction, toggling encryption changes exactly one thing — which is what makes the "
        "comparison controlled."))
    F.append(H("24.2 FheFL multi-key key sharing", 3))
    F.append(P(
        "<font face='Courier'>federated/multikey_ckks.py</font> implements additive key shares, "
        "antisymmetric pairwise masks, and server-side reconstruction (eq. 10). Verified for fleets "
        "of 2, 5, 10 and 25 vehicles."))
    F.append(para(
        "<b>The dropout gap — and our fix.</b> The paper's masks only cancel when <i>every</i> vehicle "
        "holding a pairwise key participates, but it samples a random subset each round. One vehicle "
        "in a tunnel and decryption returns <b>garbage, silently</b>. For a real fleet this is the "
        "normal case. We close it by re-deriving the pairwise masks for exactly the round's "
        "participant set via HMAC-SHA256 from a per-round nonce, so cancellation holds by "
        "construction; <font face='Courier'>strict_dropout_check</font> raises rather than corrupting. "
        "Verified for the surviving subset {0,1,2,5,7} of an 8-vehicle fleet.", "ok"))
    F.append(H("24.3 Encrypted-domain robust aggregation", 3))
    F.append(P(
        "Multi-Krum was replaced by FheFL's non-poisoning-rate scheme. The squared distance of "
        "eq. 11 is computed with a genuine ciphertext × ciphertext multiplication. An "
        "<font face='Courier'>AggregationAudit</font> counts every decryption and "
        "<font face='Courier'>assert_no_individual_decryption</font> runs after every round, turning "
        "the privacy claim from prose into a machine-checked invariant."))
    F.append(figure(diagrams / "02_fhefl_round_protocol.png",
                    "Figure 4 — One complete federated round under the FheFL protocol."))
    F.append(H("24.4 Disclosure profiles — and one honest refusal", 3))
    F.append(P(
        "<b>practical</b> (default, N=8192) computes distances homomorphically from ciphertexts "
        "and reveals the per-client distance <i>scalars</i> — one number per vehicle per round "
        "instead of 44,164 parameters. This is what all reported results use."))
    F.append(P(
        "<b>strict</b> (N=16384) would keep the non-poisoning rate encrypted and multiply it into "
        "the update homomorphically, matching the paper exactly. It is <b>specified and costed but "
        "not implemented</b>: it needs an encrypted scalar broadcast across ciphertext slots plus a "
        "second ciphertext × ciphertext multiply, neither of which is built. Requesting it raises "
        "an error carrying the measured cost."))
    F.append(para(
        "<b>Why this is worth recording.</b> An earlier revision of the server accepted "
        "<i>strict</i> and quietly fell back to revealing both the distance sum <i>and</i> the "
        "individual distances — strictly more disclosure than <i>practical</i>, while the docstring "
        "claimed less. That is the same class of defect as the Month-4 Multi-Krum filter: a mode "
        "advertising a privacy property it did not deliver. It now refuses instead, and a test "
        "asserts the refusal.", "note"))
    F.append(para(
        "<b>A second self-caught defect.</b> <font face='Courier'>train_federated.py</font> wrote "
        "results to the same path whether or not <font face='Courier'>--smoke</font> was passed, so "
        "a 1-round smoke test silently replaced a real 3-seed result with a 1-seed number. It was "
        "caught by the snapshot verifier's \"3 seeds per cell\" check and fixed by tagging smoke "
        "output separately. Both defects are recorded because in each case the value lay in the "
        "guard firing, not in the mistake being avoided.", "note"))
    F.append(H("24.5 Verification suites", 3))
    F.append(P("Three test suites now gate every result — <b>105 assertions, all passing</b>:"))
    F.append(B("<font face='Courier'>tests/test_data_pipeline.py</font> — 25 checks on labelling, "
               "window/block containment and split disjointness."))
    F.append(B("<font face='Courier'>tests/test_crypto.py</font> — 32 checks on backend equivalence, "
               "real CKKS round-trip, eq. 11 correctness, mask cancellation, dropout detection, "
               "channel integrity and the audit invariant."))
    F.append(B("<font face='Courier'>tests/test_ntt.py</font> — 48 checks on the negacyclic NTT: "
               "root properties, bit-reversal, round-trip, exact agreement with a schoolbook "
               "oracle, the negacyclic wrap, and batched-vs-scalar equivalence."))

    F.append(H("24.6 Month 1-4 deliverables closed in the catch-up pass", 3))
    F.append(P(
        "Three deliverables that had never been started were built after the Month-5 audit work, "
        "on the reasoning that a snapshot which leaves earlier months open is not a snapshot:"))
    F.append(tbl([
        ["Deliverable", "Due", "Outcome"],
        ["Optimized packing & encoding module",
         "M3-4",
         "Delivered. Level-dropped transmission cuts the wire size 29.6% (3.51 -> 2.47 MB per "
         "client) at zero accuracy cost, because the server's two operations act on independent "
         "copies and so need only one level, not two."],
        ["High-performance NTT implementation",
         "M3-4",
         "Reference delivered and validated exactly against a schoolbook oracle. Stage-batching "
         "made it 53x faster than the per-butterfly form, turning 0.21x into 11.22x over an "
         "optimised O(N^2) baseline. Test vectors exported for the C/NEON port."],
        ["Baseline benchmarking on hardware",
         "M1-2",
         "Portable harness delivered plus a full host baseline. The target-board run - which is "
         "what the deliverable actually asks for - is blocked on procurement and nothing else."],
    ], [4.6 * cm, 1.4 * cm, 9.0 * cm], fs=7.8))
    F.append(para(
        "<b>The NTT result is worth reading twice.</b> The first implementation was <i>slower</i> "
        "than the naive O(N^2) baseline. The algorithm was right; it issued ~8,191 tiny NumPy calls "
        "per transform and was dominated by interpreter overhead. Batching each stage into one "
        "operation cut that to ~13 calls. The lesson transfers directly to the embedded port: NTT "
        "performance is governed by memory access pattern and per-operation overhead, not by the "
        "butterfly arithmetic.", "note"))

    F.append(PageBreak())
    F.append(H("25. Results", 2))
    F.append(P("All figures below are from the fixed pipeline: per-message labels, block-disjoint "
               "splits, three seeds, 10 clients, 5 rounds, Dirichlet alpha = 0.3, 70% client "
               "sampling. Row caps are applied to the two largest corpora (CICIDS 150k records "
               "per file, VeReMi 1.5M beacons) because every seed re-loads and re-splits from "
               "disk; both caps remain far larger than the sample count 10 clients see in 5 "
               "rounds."))
    F.append(results_table(res))
    F.append(Spacer(1, 6))

    # ── the controlled comparison ────────────────────────────────────────
    F.append(H("25.1 Does encryption cost accuracy?", 3))
    F.append(P(
        "This is the question the Month-4 setup was structurally incapable of answering, because "
        "its \"encryption\" injected noise that sent the two arms down different training "
        "trajectories. With real CKKS on one arm, plaintext on the other, and everything else held "
        "identical:"))
    if res:
        by = {}
        for r in res["results"]:
            if r.get("status") == "ok":
                by.setdefault(r["dataset"], {})[r["backend"]] = r
        rows = [["Dataset", "CKKS accuracy", "Plaintext accuracy", "Difference",
                 "Seed spread", "Verdict"]]
        for d, m in by.items():
            if "ckks" not in m or "none" not in m:
                continue
            a, b = m["ckks"], m["none"]
            diff = a["accuracy_mean"] - b["accuracy_mean"]
            spread = max(a["accuracy_std"], b["accuracy_std"])
            rows.append([
                d, f"{a['accuracy_mean']:.4f}", f"{b['accuracy_mean']:.4f}",
                f"{diff:+.4f}", f"±{spread:.4f}",
                "within seed noise" if abs(diff) <= max(spread, 1e-4) else "exceeds seed noise",
            ])
        F.append(tbl(rows, [2.4 * cm, 2.7 * cm, 3.0 * cm, 2.2 * cm, 2.0 * cm, 3.2 * cm]))
    else:
        F.append(P("<i>Not available at build time.</i>"))

    # ── the measured privacy invariant ───────────────────────────────────
    F.append(H("25.2 The privacy invariant, measured", 3))
    F.append(P(
        "The claim \"the server never sees an individual client update\" is enforced in code and "
        "asserted after every round, not merely stated in prose. These counters come from the "
        "actual runs:"))
    if res:
        rows = [["Dataset", "Rounds", "Individual updates decrypted",
                 "Aggregates decrypted", "Distance scalars revealed"]]
        for r in res["results"]:
            if r.get("status") != "ok" or r["backend"] != "ckks":
                continue
            a = r["audit"]
            rows.append([r["dataset"], str(a["rounds"]),
                         f"{a['individual_update_decryptions']}",
                         str(a["aggregate_decryptions"]),
                         str(a["distance_scalars_revealed"])])
        F.append(tbl(rows, [2.6 * cm, 1.8 * cm, 4.8 * cm, 3.2 * cm, 3.6 * cm]))
    F.append(P(
        "The <b>distance scalars</b> column is the quantified privacy cost of the default "
        "<i>practical</i> profile: one number per vehicle per round instead of 44,164 parameters. "
        "The <i>strict</i> profile removes even that, at 2.56x the ciphertext size."))
    F.append(Spacer(1, 6))
    F.append(figure(diagrams / "06_month5_results.png",
                    "Figure 5 — Encryption on versus off, three seeds, mean ± standard deviation."))
    F.append(para(
        "<b>The headline result.</b> Encryption does not cost accuracy. The <i>ckks</i> and <i>none</i> "
        "arms agree to within run-to-run seed variation on every dataset. That is the claim the "
        "Month-4 setup was structurally incapable of supporting, and it is now demonstrated with a "
        "controlled experiment.", "ok"))
    F.append(H("25.2b How hard is each task, really?", 3))
    F.append(P(
        "Accuracy alone cannot distinguish \"the model learned something\" from \"the task was "
        "trivial\". <font face='Courier'>scripts/audit_feature_separability.py</font> measures the "
        "best accuracy obtainable from a <b>single feature and one threshold</b>, against the "
        "majority-class baseline. A score near 1.0 means one feature already solves it."))
    sep_path = Path(__file__).resolve().parent.parent / "results" / "feature_separability.json"
    if sep_path.exists():
        import json as _json
        sep_rows = [["Dataset", "Majority baseline", "Best single feature", "Lift", "Verdict"]]
        for d in _json.loads(sep_path.read_text(encoding="utf-8")):
            sep_rows.append([
                d["dataset"], f"{d['majority_baseline']:.3f}",
                f"{d['best_single_feature_accuracy']:.3f} (feature {d['best_single_feature_index']})",
                f"{d['lift_over_baseline']:+.3f}", d["verdict"],
            ])
        F.append(tbl(sep_rows, [2.1 * cm, 2.5 * cm, 4.2 * cm, 1.5 * cm, 4.7 * cm], fs=7.6))
    else:
        F.append(P("<i>Separability audit not available at build time.</i>"))
    F.append(para(
        "<b>How to read CAN-VTC.</b> Its DoS flood runs at 51.1% injection density, so every "
        "64-message window contains an injected frame. The dominant-ID frequency then separates the "
        "two captures <b>perfectly on its own</b> — because a flood of ID 0x000 is, by definition, "
        "one ID dominating the bus. Near-perfect scores here measure <b>flood detection</b>, not "
        "generalisation, and the loader prints a saturation warning on every run. Note this is not "
        "the Month-4 defect returning: the label is now correct, the task is simply easy.", "warn"))
    F.append(para(
        "<b>Car-Hacking is the meaningful CAN benchmark.</b> Its 12–24% injection density produces "
        "both normal and attack windows inside each capture, so file identity is not a shortcut, and "
        "the gap between the best single feature (0.935) and the trained model (0.998) is the value "
        "the model actually adds.", "ok"))

    F.append(H("25.3 VeReMi — a limitation that measurement exposed", 3))
    F.append(P(
        "The Month-4 VeReMi figure (ROC-AUC 0.525) was traced to a broken formulation: the adapter "
        "windowed across <i>mixed senders</i>, and with attack rows at 45.3 % the majority-vote "
        "window label was close to a coin flip. The label was noise; the model was fine."))
    F.append(P(
        "Switching to per-beacon features makes the problem <b>well-posed</b> — the label now means "
        "something. But measuring the feature space afterwards showed it also has a low ceiling:"))
    F.append(tbl([
        ["Measurement (200k-row sample)", "Value"],
        ["Best single-feature class separation", "0.046 standard deviations"],
        ["Best single-feature threshold accuracy", "0.545"],
        ["Majority-class baseline", "0.547"],
    ], [9.5 * cm, 5.5 * cm], fs=8.6))
    F.append(P(
        "<b>This is not a bug — it is the task.</b> VeReMi's 19 attack types (ConstPos, ConstSpeed, "
        "DataReplay, EventualStop, DelayedMessages and so on) are all defined by how one sender's "
        "claims evolve <b>over time</b>. A constant-position attacker's individual beacon reports a "
        "perfectly plausible position; only the fact that it never changes gives it away, and a "
        "single beacon cannot express \"never changes\"."))
    F.append(P(
        "<b>The prediction was then confirmed by training.</b> The separability audit was run "
        "<i>before</i> the federated experiments and predicted VeReMi could not be learned from these "
        "features. The subsequent run returned accuracy 0.4839 ± 0.0433 and ROC-AUC 0.5161 ± 0.0018, "
        "with a confusion matrix showing a degenerate classifier that labels almost everything "
        "\"attack\". Prediction and outcome agree, which is worth more than either alone: it means "
        "the audit tool can be trusted to flag an unlearnable formulation before compute is spent "
        "on it."))
    F.append(para(
        "So the cleaned export supports <b>neither</b> formulation: windowing mixes senders and "
        "destroys the label, while per-beacon keeps the label but discards the temporal signal the "
        "task depends on. Both paths need the sender identifier, which was dropped during cleaning. "
        "<b>VeReMi numbers in this report are a near-chance lower bound and must be read that way.</b> "
        "Sender-grouped windowing is implemented and activates automatically once the column is "
        "present; re-acquiring the raw dataset is item P1.5.", "warn"))

    F.append(H("25.4 What improved over Month 4", 3))
    F.append(tbl([
        ["Aspect", "Month 4", "Month 5"],
        ["Encryption during training",
         "numpy array + N(0,1e-9) noise — below float32 ULP, i.e. not encryption",
         "Real TenSEAL CKKS ciphertexts, 326.6 KB each, measured 1e-8 error"],
        ["Server access to individual updates",
         "Decrypted every one, every round, to run Multi-Krum",
         "Never — asserted after every round by AggregationAudit"],
        ["Robust aggregation",
         "Multi-Krum on plaintext; structurally impossible under real FHE",
         "FheFL non-poisoning rate computed on ciphertexts (eq. 6-12)"],
        ["Key model",
         "One shared context — any key holder decrypts everyone",
         "Additive shares; recovering one update needs U-1 colluders"],
        ["Client dropout",
         "Not considered",
         "Per-round mask re-scoping; verified for arbitrary surviving subsets"],
        ["CAN labels",
         "Source filename — measured capture identity, not intrusion",
         "Per-message ground truth (R/T flag, 0x000 signature)"],
        ["Train/test split",
         "Random over 75%-overlapping windows — leaked",
         "Whole contiguous blocks, machine-verified disjoint"],
        ["FHE vs no-FHE comparison",
         "Uncontrolled; produced a spurious 5-point VeReMi gap",
         "Controlled; 3 seeds; difference within seed noise on every dataset"],
        ["Transport security",
         "Deleted (\"guaranteed by FHE mathematical bounds\")",
         "Restored: ECDH-P256 + AES-256-GCM + Ed25519 mutual auth"],
        ["VeReMi",
         "ROC-AUC 0.525 — no better than guessing",
         "Root cause found (windows mixed senders) and reformulated per-beacon"],
        ["Verification",
         "None",
         "105 assertions gating every reported result"],
        ["Cost measurement",
         "Addition-only; understated FheFL by ~an order of magnitude",
         "Both profiles including the ciphertext x ciphertext multiply"],
    ], [3.3 * cm, 5.8 * cm, 6.4 * cm], fs=7.6))
    F.append(para(
        "<b>The single most important change</b> is the third row. Month 4 had a privacy "
        "architecture whose central claim was contradicted by its own code: the deck said the "
        "server never sees plaintext, and the server decrypted every client's full 44,164-parameter "
        "update on every round. That is now an enforced invariant rather than a claim.", "ok"))

    F.append(H("25.5 Why the headline numbers moved — in both directions", 3))
    F.append(P(
        "Fixing the defects changed the reported accuracies. It is worth being precise about why, "
        "because the changes go both ways and each direction means something different."))
    m4 = {"can_vtc": 1.0000, "car_hack": 0.7383, "cicids": 0.9818, "veremi": 0.5290}
    rows = [["Dataset", "Month 4", "Month 5", "Direction", "Why"]]
    reasons = {
        "can_vtc": ("not comparable",
                    "4-class filename labels became a 2-class signature-labelled task"),
        "car_hack": ("UP",
                     "The old task was incoherent — every window of the DoS capture had to be "
                     "called 'DoS', including the ~76% that contained no injection. With correct "
                     "per-message labels the task is well-posed and solvable"),
        "cicids": ("DOWN",
                   "The leaky random split was inflating it. This drop is the leakage being "
                   "removed — the number got smaller and truer"),
        "veremi": ("not comparable",
                   "Formulation changed entirely; both old and new are near chance, for different "
                   "reasons (see 25.3)"),
    }
    if res:
        got = {r["dataset"]: r for r in res["results"]
               if r.get("status") == "ok" and r["backend"] == "ckks"}
        for d in ["can_vtc", "car_hack", "cicids", "veremi"]:
            new = f"{got[d]['accuracy_mean']:.4f}" if d in got else "-"
            direction, why = reasons[d]
            rows.append([d, f"{m4[d]:.4f}", new, direction, why])
        F.append(tbl(rows, [2.0 * cm, 1.7 * cm, 1.7 * cm, 2.0 * cm, 7.6 * cm], fs=7.6))
    F.append(para(
        "<b>The Car-Hacking result is the one to understand.</b> Accuracy rose from 0.74 to 0.998 "
        "<i>because</i> the labels were fixed, not despite it. Under filename labelling the model "
        "was being asked to call quiet, injection-free stretches of the DoS capture \"DoS\" — a "
        "task with no correct answer. Removing that contradiction is what the jump measures.", "ok"))
    F.append(para(
        "<b>Caveat.</b> The Month-4 column is shown for direction only. Those runs used filename "
        "labels, a leaky split, simulated encryption and a single seed, and in some cases different "
        "row caps — they are not a valid baseline and must not be quoted as one. They are retained "
        "in <font face='Courier'>Results/month4_legacy_INVALID/</font> purely for provenance.", "warn"))

    F.append(H("26. Cryptographic measurements", 2))
    F.append(P("Measured on the project machine; reproducible with "
               "<font face='Courier'>scripts/benchmark_ckks_profiles.py</font>."))
    F.append(tbl([
        ["Configuration", "Total bits", "Levels", "Ciphertext", "eq. 11 time", "2nd ct x ct"],
        ["N=8192, [60,40,40,60]", "200", "2", "326.6 KB", "18.0 ms", "fails"],
        ["N=8192, [60,40,40,40,60]", "240", "-", "REJECTED", "-", "-"],
        ["N=16384, [60,40,40,40,60]", "240", "3", "836.1 KB", "67.7 ms", "works"],
        ["N=16384, [60,40,40,40,40,60]", "280", "4", "1028.6 KB", "92.5 ms", "works"],
    ], [5.0 * cm, 1.9 * cm, 1.4 * cm, 2.3 * cm, 2.2 * cm, 2.0 * cm], fs=8.0))
    F.append(P(
        "<b>What this means.</b> At N=8192, 128-bit security permits at most <b>218 bits</b> of total "
        "coefficient modulus. A 240-bit chain is therefore <b>rejected outright</b> — buying a third "
        "multiplicative level requires doubling the ring dimension."))
    F.append(H("26.1 Cost of a full round, measured end to end", 3))
    F.append(P(
        "The table above is <i>per ciphertext</i>. What actually matters operationally is the cost "
        "per <b>client update</b> — the whole 44,164-parameter vector, which is 11 ciphertexts at "
        "N=8192 but only 6 at N=16384, because the larger ring packs twice as many slots. Measured "
        "with 7 active clients:"))
    if bench:
        by = {}
        for b in bench:
            by.setdefault(b["profile"], b)
        rows = [["Per client update", "practical (N=8192)", "strict (N=16384)", "Ratio"]]
        pr, st = by.get("practical"), by.get("strict")
        if pr and st:
            def rr(k, scale=1.0, unit=""):
                a, b_ = pr[k] * scale, st[k] * scale
                return [f"{a:,.1f}{unit}", f"{b_:,.1f}{unit}", f"{b_/a:.2f}x"]
            rows.append(["Ciphertext on the wire"] +
                        [f"{pr['ciphertext_bytes_per_client']/1024/1024:.2f} MB",
                         f"{st['ciphertext_bytes_per_client']/1024/1024:.2f} MB",
                         f"{st['ciphertext_bytes_per_client']/pr['ciphertext_bytes_per_client']:.2f}x"])
            rows.append(["Expansion over float32"] +
                        [f"{pr['ciphertext_expansion']:.1f}x", f"{st['ciphertext_expansion']:.1f}x",
                         f"{st['ciphertext_expansion']/pr['ciphertext_expansion']:.2f}x"])
            rows.append(["Encrypt"] + rr("encrypt_sec_per_client", 1000, " ms"))
            rows.append(["Encrypted distance (eq. 11)"] +
                        rr("encrypted_distance_sec_per_client", 1000, " ms"))
            rows.append(["Homomorphic aggregation"] + rr("homomorphic_aggregate_sec", 1000, " ms"))
            rows.append(["Decrypt aggregate"] + rr("decrypt_aggregate_sec", 1000, " ms"))
            F.append(tbl(rows, [5.4 * cm, 3.6 * cm, 3.6 * cm, 2.4 * cm], fs=8.2))
    F.append(para(
        "<b>A correction worth stating.</b> Comparing single ciphertexts suggested strict FheFL "
        "would cost 2.56x the bandwidth. Measured per <i>client update</i> it is only "
        "<b>1.40x</b> — because doubling the ring also doubles the slots per ciphertext, so the "
        "update needs 6 ciphertexts instead of 11. The distance computation roughly doubles rather "
        "than quadrupling. <b>Strict FheFL is materially more affordable than the per-ciphertext "
        "figure implies</b>, which strengthens the case for implementing it in Month 6.", "note"))
    F.append(para(
        "<b>Do not confuse the two distance figures.</b> The 18.0 ms in the table above is one "
        "ciphertext; the ~231 ms here is a full 11-ciphertext client update. Both are correct and "
        "they measure different things.", "warn"))
    F.append(figure(diagrams / "05_ckks_profile_tradeoff.png",
                    "Figure 6 — Measured cost of the two disclosure profiles."))
    F.append(para(
        "<b>A correction.</b> The Month-5 audit initially predicted that the modulus chain would have "
        "to be extended for eq. 11 itself. Measurement shows eq. 11 <i>does</i> fit at N=8192; the "
        "ceiling binds only on the second multiplication. The correction is recorded here rather than "
        "silently applied.", "note"))
    F.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════
    # PART V — STATUS
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Part V — Current status", 1))

    F.append(H("27. Component status", 2))
    F.append(H("Completed", 3))
    for t in ["Unified 46-D feature extraction across four heterogeneous datasets",
              "Per-message ground-truth labelling (Car-Hacking R/T flag, CAN-VTC 0x000 signature, VeReMi attack column)",
              "Leakage-free group-aware train/val/test splitting, machine-verified",
              "ChebyKAN classifier, 44,164 parameters",
              "Dirichlet non-IID sharding (alpha = 0.3)",
              "Federated training loop with client sampling",
              "Real CKKS encryption of client updates (TenSEAL)",
              "FheFL encrypted-domain robust aggregation (eq. 6–12)",
              "Multi-key additive key sharing with per-round dropout tolerance",
              "ECDH-P256 + AES-256-GCM + Ed25519 authenticated transport",
              "Machine-checked privacy invariant (zero individual-update decryptions)",
              "Two verification suites, 105 assertions",
              "Threat model, security specification, library evaluation documents",
              "Measured CKKS cost for both disclosure profiles"]:
        F.append(B(t))

    F.append(H("Partially completed", 3))
    for t in ["<b>Multi-key CKKS</b> — homomorphic arithmetic is real; key management is an algebraic "
              "model, because TenSEAL exposes no multi-key API. Needs the OpenFHE migration.",
              "<b>Byzantine robustness</b> — works against large-magnitude poisoning; untested against "
              "low-magnitude persistent attackers.",
              "<b>Library evaluation</b> — selection complete; cross-compilation not performed.",
              "<b>VeReMi</b> — per-beacon formulation works; sender-grouped windowing awaits data re-acquisition.",
              "<b>Experimental scale</b> — 10 clients / 5 rounds against a roadmap target of 50–200 / 200–300.",
              "<b>Ciphertext serialization</b> — sizes measured; no V2X transport protocol yet."]:
        F.append(B(t))

    F.append(H("Not started", 3))
    for t in ["Cross-compilation to an embedded target",
              "On-hardware performance benchmarking",
              "SIMD packing and encoding module",
              "NTT kernel acceleration",
              "Model quantization",
              "On-device inference engine / embedded IDS executable",
              "V2X communication protocol",
              "Client-level differential privacy",
              "Hardware-in-the-loop validation",
              "Power-consumption audit"]:
        F.append(B(t))

    F.append(H("28. Known limitations", 2))
    F.append(tbl([
        ["Limitation", "Impact", "Mitigation path"],
        ["Multi-key layer is an algebraic model, not a cryptographic implementation",
         "The system must not be described as full multi-key CKKS", "OpenFHE migration (Month 6)"],
        ["Low-magnitude persistent poisoning is unaddressed",
         "A patient attacker can bias the model while scoring a high non-poisoning rate",
         "Experiment scheduled; may require a contribution-history term"],
        ["CAN-VTC reduces to flood detection",
         "Near-perfect scores are not evidence of generalisation",
         "Report Car-Hacking as the primary CAN benchmark"],
        ["CAN-VTC Fuzzy and Impersonation captures excluded",
         "4-class problem reduced to 2 classes", "Re-acquire raw data with injection ground truth"],
        ["Noise flooding defaults to off",
         "IND-CPA^D exposure if a deployment inherits the default",
         "Make the server refuse to start without it in a deployment profile"],
        ["Round number not bound into AEAD associated data",
         "A captured frame could be replayed in a later round", "One-line fix, scheduled"],
        ["Bandwidth: 3.59 MB per vehicle per round",
         "Does not fit V2X message budgets (~2.7 KB per DSRC frame)",
         "Modulus switching, sparsification, hierarchical RSU aggregation"],
        ["Everything runs on a laptop CPU",
         "No evidence the system is feasible on automotive hardware",
         "Order target board; cross-compile"],
    ], [4.6 * cm, 5.2 * cm, 5.2 * cm], fs=7.8))

    F.append(H("29. LG deliverable status", 2))
    F.append(tbl([
        ["Period", "Deliverable", "Status"],
        ["M1–2", "Security specification report", "Delivered (Month 5)"],
        ["M1–2", "Baseline performance benchmarking on hardware", "Harness + host baseline delivered; target-board run blocked on procurement"],
        ["M1–2", "Threat model document", "Delivered (Month 5)"],
        ["M1–2", "Baseline architecture design", "Delivered"],
        ["M3–4", "Library evaluation & cross-compilation", "Evaluation delivered; cross-compilation blocked on hardware"],
        ["M3–4", "Optimized packing & encoding module", "Delivered (Month 5) — 29.6% lossless bandwidth reduction"],
        ["M3–4", "High-performance NTT implementation", "Reference delivered + validated (11.22x); ARM/NEON kernel blocked on hardware"],
        ["M3–4", "Preprocessing engine", "Delivered"],
        ["M3–4", "Model accuracy report", "Delivered (Month 5, on corrected data)"],
        ["M5–6", "Ciphertext serialization & communication protocol", "Measurements only"],
        ["M5–6", "Quantized model weights", "Not started"],
        ["M5–6", "Embedded IDS executable", "Not started"],
        ["M7–12", "Homomorphic aggregator (verified)", "Ahead of schedule — implemented in Month 5"],
    ], [1.6 * cm, 7.6 * cm, 5.8 * cm], fs=8.0))
    F.append(para(
        "<b>Overall position.</b> <b>7 of the 8 deliverables due by end of Month 4 are now complete "
        "or substantially complete</b>, up from 5 of 8 before the Month-5 catch-up work. The "
        "cryptographic and machine-learning tracks are healthy and the aggregation work is ahead of "
        "schedule.", "ok"))
    F.append(para(
        "<b>The residual is one thing: no hardware has been ordered.</b> Both remaining partial "
        "items — the ARM/NEON NTT kernel and the target-board baseline — are blocked on exactly "
        "that and on nothing else, and months 7–12 (hardware-in-the-loop, power audit) depend on "
        "them. Ordering a board is one hour of work and it is the highest-leverage action "
        "available.", "warn"))
    F.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════
    # PART VI — NEXT
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Part VI — What to do next", 1))
    F.append(P("Full detail in <font face='Courier'>Documentation/12_next_steps.md</font>. Priority "
               "order:"))
    F.append(tbl([
        ["Priority", "Task", "Effort", "Why first"],
        ["P0.1", "Order target hardware (NXP S32G + Raspberry Pi 5 as interim)", "1 h",
         "Blocks the entire embedded track"],
        ["P0.2", "Bind round number into AEAD associated data", "1 h", "Closes the replay threat"],
        ["P0.3", "Enforce noise flooding in deployment profiles", "2 h", "Closes IND-CPA^D exposure"],
        ["P0.4", "Implement the strict disclosure profile (currently raises NotImplementedError)",
         "3 d", "Removes the one remaining per-round disclosure; may be cheaper after P1.1"],
        ["P1.1", "<b>Migrate to OpenFHE</b>", "12 d",
         "TenSEAL cannot express multi-key CKKS — the single most important item"],
        ["P1.2", "Adopt threshold (t-of-n) key sharing", "in P1.1", "Removes dropout fragility structurally"],
        ["P1.3", "Low-magnitude poisoning experiment", "3 d", "Tests the known blind spot"],
        ["P1.4", "Scale to 50 clients / 50 rounds", "4 d", "Moves toward the roadmap target"],
        ["P1.5", "Re-acquire raw VeReMi with sender IDs", "2 d", "Unlocks sender-grouped windowing"],
        ["P1.6", "Client-level differential privacy", "3 d", "The one roadmap mechanism still missing"],
        ["P2.x", "Embedded track: cross-compile, NTT, packing, quantization, V2X protocol", "~40 d",
         "The schedule debt"],
        ["P3.x", "Integration, HiL validation, power audit, final report", "months 10–12", "Programme close"],
    ], [1.5 * cm, 6.4 * cm, 1.8 * cm, 5.3 * cm], fs=7.8))
    F.append(para(
        "<b>Before publication or submission.</b> Do not claim full multi-key CKKS until the OpenFHE "
        "migration lands. Report CAN-VTC as flood detection. Never re-report the Month-4 numbers — "
        "they are retained in <font face='Courier'>Results/month4_legacy_INVALID/</font> for "
        "provenance only. Run the low-magnitude poisoning experiment before claiming Byzantine "
        "robustness.", "warn"))

    # ═════════════════════════════════════════════════════════════════════
    # PART VII — REPRODUCTION
    # ═════════════════════════════════════════════════════════════════════
    F.append(H("Part VII — Reproduction and verification", 1))
    F.append(H("Folder layout", 2))
    F.append(tbl([
        ["Folder", "Contents"],
        ["Documentation/", "This PDF and all twelve markdown documents"],
        ["Complete Source Code/NewModel_active/", "The current, runnable system"],
        ["Complete Source Code/Model_gen1_archived/", "Generation 1 (KANConvNet) — reference only"],
        ["Complete Source Code/ArchitectureViewer_web/", "React architecture visualiser"],
        ["Newly Added - Month 5/", "Only what was added or changed in Month 5, plus a changelog"],
        ["Month 1-2 Foundation/", "Decks, reports and Phase-1 checkpoints from months 1–2"],
        ["Month 3-4 FHE and Architecture/", "FHE study, CKKS mathematics, MamKANformer and ChebyKAN decks"],
        ["Dataset/", "Manifest and provenance — the 8.6 GB corpus is referenced, not duplicated"],
        ["Models/", "Trained checkpoints"],
        ["Experiments/", "Benchmark and sweep scripts, test suites"],
        ["Results/", "Month-5 JSON results, and the Month-4 legacy results marked INVALID"],
        ["Diagrams/", "All figures in this document, as PNG and SVG"],
    ], [6.0 * cm, 9.0 * cm], fs=8.2))

    F.append(H("Running it", 2))
    F.append(para(
        "cd \"Complete Source Code/NewModel_active\"<br/><br/>"
        "python tests/test_data_pipeline.py&nbsp;&nbsp;&nbsp; # 25 setup-correctness assertions<br/>"
        "python tests/test_crypto.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # 32 cryptographic assertions<br/><br/>"
        "python train_federated.py --dataset car_hack --backend ckks --seeds 2025 2026 2027<br/>"
        "python train_federated.py --dataset car_hack --backend none --seeds 2025 2026 2027<br/><br/>"
        "python scripts/benchmark_ckks_profiles.py<br/>"
        "python scripts/run_all_experiments.py<br/>"
        "python scripts/generate_diagrams.py<br/>"
        "python scripts/build_master_pdf.py", "code"))
    F.append(para(
        "<b>Always run both test suites after touching the data or crypto layers.</b> They assert "
        "that the experimental setup is sound — no label leakage, no split leakage, no "
        "individual-update decryption. If they fail, every metric the pipeline produces is "
        "meaningless.", "ok"))

    F.append(H("Environment", 2))
    F.append(tbl([
        ["Component", "Version"],
        ["Python", "3.12.0"],
        ["PyTorch", "2.13.0+cpu"],
        ["TenSEAL", "0.3.16"],
        ["NumPy / pandas / scikit-learn", "2.4.1 / 2.3.3 / 1.9.0"],
        ["cryptography", "46.0.4"],
        ["Platform", "Windows 11, CPU only"],
    ], [7.0 * cm, 8.0 * cm], fs=8.4))

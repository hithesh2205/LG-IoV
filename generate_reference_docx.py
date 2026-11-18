import os
import docx
from docx.shared import Inches, Pt, RGBColor

doc = docx.Document()

# Set standard 0.8 inch margins
for section in doc.sections:
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

# Title & Subtitle
title_p = doc.add_paragraph()
title_run = title_p.add_run("Homomorphic Functions (f) in CKKS-Encrypted Federated Learning with ChebyKAN")
title_run.font.size = Pt(20)
title_run.font.bold = True
title_run.font.color.rgb = RGBColor(26, 54, 93)

sub_p = doc.add_paragraph()
sub_run = sub_p.add_run("Technical Reference & System Gap Analysis for Connected Vehicle Intrusion Detection (IoV)")
sub_run.font.size = Pt(12)
sub_run.font.italic = True
sub_run.font.color.rgb = RGBColor(74, 85, 104)

doc.add_paragraph("—" * 55)

def add_h1(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = RGBColor(43, 108, 176)
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)

def add_h2(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = RGBColor(45, 55, 72)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)

def add_body(text, bold_prefix=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.bold = True
        r_pre.font.size = Pt(10.5)
    r = p.add_run(text)
    r.font.size = Pt(10.5)

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.bold = True
        r_pre.font.size = Pt(10.5)
    r = p.add_run(text)
    r.font.size = Pt(10.5)

# 1. Executive Summary
add_h1("1. Executive Summary & Context of the Meeting")
add_h2("1.1 The Meeting Dialogue & The Core Misunderstanding")
add_body("In the project review meeting between Amrita students (Thrishwant, Hithesh), Dr. Praveen K, and LGSI mentor Fahiem Altaf, a major point of confusion arose regarding the role of the homomorphic function:")
add_bullet('"If the server knows how the homomorphic function works, then there is no need of keeping the homomorphic function. It can be simple."', "Thrishwant: ")
add_bullet('"I didn\'t understand you exactly."', "Fahiem Altaf: ")
add_bullet('"Yes, sir, we will see that function and broadcasting certain group key thing, yeah."', "Dr. Praveen K: ")

add_h2("1.2 Demystifying the Confusion: Kerckhoffs's Principle & FHE")
add_bullet("In modern cryptography, security must NEVER depend on keeping the algorithm hidden. The server is untrusted with the private data, but it is fully aware of the mathematical task it must perform (e.g., Federated Averaging or distance metrics).", "1. The Function f is Public: ")
add_bullet("If the server performed computation 'simply' using plaintext math, clients would have to send unencrypted weights, completely destroying privacy. The server could invert weights to reconstruct vehicle driving paths and telemetry.", "2. Why Plaintext is Forbidden: ")
add_bullet("FHE enables the server to evaluate public function f directly over ciphertexts without possessing the private decryption key: Eval(pk, f, [w_1], ..., [w_N]) -> [f(w_1, ..., w_N)].", "3. The Role of FHE: ")

# 2. Architecture Diagram
add_h1("2. Deconstructing the LG Mentor's Architecture Diagram")
add_body("The mentor's diagram establishes a strict cryptographic boundary:")
add_bullet("Possesses the Secret Decryption Key (sk). Vehicles train locally on private CAN/telemetry logs, produce local updates w_i, and encrypt them locally to produce ciphertexts [w_i].", "Client Domain: ")
add_bullet("Possesses NO decryption key. Receives [w_i] over V2X/TLS. Executes the homomorphic function f([w_1], ..., [w_N]) entirely in the encrypted domain to yield result ciphertext [w_global].", "Untrusted Server Domain (RSU/Cloud): ")
add_bullet("Sends [w_global] back to the client domain, where vehicles decrypt it locally using sk.", "Decryption Loop: ")

# 3. BookCKKS Page 424
add_h1("3. Cryptographic Grounding: Page 424 of BookCKKS.pdf")
add_body("Fahiem Altaf directed the team to Book Page 424 of the reference material (Cheon et al., 'Homomorphic Encryption for Arithmetic of Approximate Numbers', ASIACRYPT 2017). Section 4 (Homomorphic Evaluation of Functions) on Page 424 lays out the exact rules:")
add_bullet("Constant addition f(x) = x + a and constant multiplication f(x) = ax consume ZERO modulus levels (Lemma 4).", "Constant Operations: ")
add_bullet("Power polynomial f(x) = x^d for d=2^r evaluates via repeated squaring c_j = Rescale(Mult(c_{j-1}, c_{j-1})), consuming exactly r modulus levels (Algorithm 1).", "Power Polynomials: ")
add_bullet("Any arbitrary polynomial f(x) = sum(a_i x^i) or analytic function (Taylor/Chebyshev) is evaluated as a tree of additions, multiplications, and rescalings (Lemmas 6 & 7).", "General Functions: ")

# 4. Taxonomy
add_h1("4. Taxonomy of f Functions for CKKS + FL + ChebyKAN")
add_h2("Category 1: Model Aggregation Functions (f_agg)")
add_bullet("Computes weighted average sum(alpha_k [w_k]). Depth: 0. Latency: ~5 ms for 44k params. Fully implemented in server.py.", "1. Homomorphic FedAvg: ")
add_bullet("Updates global model via (1-gamma)*g + gamma*[w_agg] to counteract client drift in non-IID vehicular traffic. Depth: 0.", "2. Homomorphic FedProx: ")
add_bullet("Maintains encrypted momentum [v^(t)] = beta*v^(t-1) + (1-beta)*[Delta w_agg] on RSU. Depth: 0.", "3. Homomorphic Server Momentum: ")

add_h2("Category 2: Byzantine-Resilient Defenses (f_def)")
add_bullet("Computes [d_k] = g^T g + [(w_k - 2g)^T w_k]. Consumes 1 modulus level. Evaluates parameter deviation under encryption. Latency: ~18 ms.", "1. FheFL Squared Euclidean Distance: ")
add_bullet("Evaluates <[w_k], v_anchor> / ||v_anchor||^2 against clean RSU validation gradient. Depth: 0. Fast and depth-free.", "2. Directional Cosine Similarity: ")
add_bullet("Applies smooth Gaussian decay 1 - c1*[d] + c2*[d]^2 instead of non-polynomial if/else. Consumes 2 levels (requires N=16384).", "3. Continuous Polynomial Weighting: ")

add_h2("Category 3: ChebyKAN-Specific Functions (f_KAN)")
add_bullet("ChebyKAN models learnable edges as phi(x) = w_b*x + sum(c_j * T_j(x)). Malicious vehicles manipulate high-degree coefficients. The RSU applies homomorphic damping lambda_j * [c_j] where lambda_j = 1/(1 + eta*j^2). Depth: 0.", "1. High-Degree Coefficient Damping: ")
add_bullet("Aggregates linear base weights w_b globally while aggregating non-linear spline coefficients with distance weighting.", "2. Trunk vs. Spline Modular Split: ")

add_h2("Category 4: Encrypted Inference (f_infer) — The ChebyKAN Synergy")
add_body("Standard neural networks use ReLU, which requires high-degree polynomial approximations (3-4 modulus levels). ChebyKAN is ALREADY a polynomial by definition. The forward pass uses Chebyshev polynomials T_j(x) evaluated via Clenshaw recurrence T_{j+1}(x) = 2x*T_j(x) - T_{j-1}(x). This means ChebyKAN forward evaluation on encrypted CAN traffic requires ZERO activation approximations!")

# 5. Gap Analysis
add_h1("5. Project Gap Analysis ('Where We Lag')")
add_bullet("Currently Single-Key CKKS with a simulated Trusted Dealer. If 1 vehicle ECU is hacked, all privacy collapses. Needs multi-key xMK-CKKS key masking.", "1. Key Management Gap: ")
add_bullet("In server.py line 269, acc.decrypt() is called inside the server object in Python simulation. Diagram requires server to hold NO secret key.", "2. Server Execution Gap: ")
add_bullet("disclosure='strict' throws NotImplementedError. Pipeline uses 'practical' mode which decrypts 1 distance scalar per client per round.", "3. FheFL Disclosure Gap: ")
add_bullet("An encrypted 44k ChebyKAN update expands to 2.47 MB (915 DSRC frames). Serialization and fragmentation spec remain open.", "4. Communication Overhead: ")
add_bullet("VeReMi accuracy is near chance (~50%) because sender_id was dropped during cleaning, destroying temporal position-tracking.", "5. VeReMi Dataset Defect: ")
add_bullet("INT8 quantization not started.", "6. Model Quantization: ")

# 6. Action Checklist
add_h1("6. Action Checklist for October 5th Meeting")
add_bullet("'The server is aware of the function f, but oblivious to the data. Our f functions are FedAvg (depth 0) and FheFL squared distance (depth 1), strictly complying with Section 4 (Page 424) of Cheon et al. 2017.'", "Clarify Function f: ")
add_bullet("'ChebyKAN basis functions are polynomials by definition, making ChebyKAN natively compatible with CKKS arithmetic circuits without ReLU approximation penalties.'", "Present ChebyKAN Synergy: ")
add_bullet("'We have modeled xMK-CKKS key masking where pairwise secrets cancel out over the participating set, ensuring individual updates remain private.'", "Address Group Key Broadcast: ")
add_bullet("'Our baseline confirms CKKS encryption introduces zero accuracy degradation (<0.07 pp) across all benchmarks.'", "Present Parity Baseline: ")

# Save to both folders
p1 = os.path.abspath("Presentation/Homomorphic_Functions_CKKS_ChebyKAN.docx")
p2 = os.path.abspath("Team/LG_IoV/Documents/Homomorphic_Functions_CKKS_ChebyKAN.docx")

doc.save(p1)
doc.save(p2)
print("Saved DOCX files successfully:")
print(" -", p1)
print(" -", p2)

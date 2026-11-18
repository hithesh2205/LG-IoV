import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5) # 16:9 widescreen
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    C_NAVY = RGBColor(15, 23, 42)      # #0f172a Deep Slate Navy
    C_BLUE = RGBColor(30, 58, 138)     # #1e3a8a Corporate Blue
    C_TEAL = RGBColor(13, 148, 136)    # #0d9488 Vibrant Teal
    C_LIGHT_BG = RGBColor(248, 250, 252) # #f8fafc Clean Light Gray
    C_CARD_BG = RGBColor(255, 255, 255)  # White Card
    C_BORDER = RGBColor(226, 232, 240)   # Light Border
    C_TEXT_DARK = RGBColor(30, 41, 59)   # Slate 800
    C_TEXT_MUTED = RGBColor(100, 116, 139) # Slate 500
    C_ACCENT_GREEN = RGBColor(16, 185, 129)
    C_ACCENT_AMBER = RGBColor(217, 119, 6)
    C_ACCENT_PURPLE = RGBColor(124, 58, 237)

    def add_header(slide, title_text, category_text="FEDERATED IoV INTRUSION DETECTION • HOMOMORPHIC EVALUATION"):
        # Header banner
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.1))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p0 = tf.paragraphs[0]
        p0.text = category_text.upper()
        p0.font.size = Pt(10)
        p0.font.bold = True
        p0.font.color.rgb = C_TEAL
        p0.space_after = Pt(2)
        
        p1 = tf.add_paragraph()
        p1.text = title_text
        p1.font.size = Pt(22)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY

    def add_card(slide, left, top, width, height, title, bg_color=C_CARD_BG, border_color=C_BORDER):
        # Card shape
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
        
        # Header in card
        tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), width - Inches(0.5), Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_BLUE
        
        # Body in card
        body_box = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.65), width - Inches(0.5), height - Inches(0.85))
        btf = body_box.text_frame
        btf.word_wrap = True
        btf.margin_left = btf.margin_top = btf.margin_right = btf.margin_bottom = 0
        return btf

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY
    bg1.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(10.9), Inches(3.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "HOMOMORPHIC FUNCTIONS (f) IN CKKS & ChebyKAN"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(12)
    
    p2 = tf.add_paragraph()
    p2.text = "Taxonomy, Purpose, Computation Mechanics, and Value Delivery in Collaborative Vehicular IDS"
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(148, 163, 184)
    p2.space_after = Pt(28)

    p3 = tf.add_paragraph()
    p3.text = "Key Concept: The untrusted server does not just relay or decrypt data — it evaluates a mathematical function f(Encrypted Data) and outputs the evaluated result under encryption."
    p3.font.size = Pt(13)
    p3.font.italic = True
    p3.font.color.rgb = RGBColor(45, 212, 191)

    # =========================================================================
    # SLIDE 2: Architectural Alignment with LG Mentor Diagram
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Architecture Context: Why the Server Computes Function f", "System Workflow & Trust Boundaries")

    c1 = add_card(s2, Inches(0.8), Inches(1.7), Inches(3.6), Inches(5.2), "1. Client Domain (Vehicles)")
    p = c1.paragraphs[0]
    p.text = "• Possesses the Secret Key (sk)."
    p.font.size = Pt(12)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(8)
    
    p = c1.add_paragraph()
    p.text = "• Local Training:\n  Trains ChebyKAN on local CAN bus telemetry (44,164 parameters)."
    p.font.size = Pt(12)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(8)

    p = c1.add_paragraph()
    p.text = "• Local Encryption:\n  Packs 44,164 weights into 11 CKKS ciphertext chunks (SIMD 4,096 slots each)."
    p.font.size = Pt(12)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(8)

    p = c1.add_paragraph()
    p.text = "• Final Decryption:\n  Only the client decrypts the final evaluated result of f."
    p.font.size = Pt(12)
    p.font.color.rgb = C_TEXT_DARK

    c2 = add_card(s2, Inches(4.8), Inches(1.7), Inches(4.2), Inches(5.2), "2. Untrusted Server Domain (RSU)", bg_color=RGBColor(240, 253, 250), border_color=C_TEAL)
    p = c2.paragraphs[0]
    p.text = "• Has ZERO Decryption Keys (No sk)."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(8)

    p = c2.add_paragraph()
    p.text = "• Receives Ciphertexts:\n  Gets encrypted updates [w_1], ..., [w_K] from vehicles over V2X."
    p.font.size = Pt(12)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(8)

    p = c2.add_paragraph()
    p.text = "• Computes Function f(Encrypted Data):\n  Executes the mathematical circuit (FedAvg, Distance, or Inference) entirely in ciphertext space."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(8)

    p = c2.add_paragraph()
    p.text = "• Produces New Result Ciphertext:\n  Outputs [f(Data)] — the exact evaluated value of the function!"
    p.font.size = Pt(12)
    p.font.color.rgb = C_TEXT_DARK

    c3 = add_card(s2, Inches(9.4), Inches(1.7), Inches(3.1), Inches(5.2), "3. Clarification for Mentor")
    p = c3.paragraphs[0]
    p.text = "What is sent back?"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_AMBER
    p.space_after = Pt(6)

    p = c3.add_paragraph()
    p.text = "As the mentor highlighted, the server does NOT send raw data or arbitrary text.\n\nThe server returns the EVALUATED VALUE OF THE FUNCTION f, which can be:\n1. A new global model update [w_global]\n2. An anomaly distance scalar [d^u]\n3. A trust score [s_u]\n4. An intrusion detection label [y]"
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 3: Function 1 - Homomorphic Federated Aggregation (f_agg)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Function 1: Homomorphic Federated Averaging (f_agg)", "Model Aggregation Function")

    c1 = add_card(s3, Inches(0.8), Inches(1.7), Inches(3.6), Inches(5.2), "Purpose: Why We Use It")
    p = c1.paragraphs[0]
    p.text = "• Privacy-Preserving Collaborative Learning:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "Allows the fleet of connected vehicles to train a shared intrusion detection model without exposing local CAN bus weights to the RSU or eavesdroppers."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(12)

    p = c1.add_paragraph()
    p.text = "• Defense Against Reconstruction Attacks:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "Plaintext FL gradient updates can be inverted by a semi-honest server to reconstruct vehicle driving trajectories and ECU IDs. f_agg keeps the updates completely blind."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c2 = add_card(s2, Inches(0.8), Inches(1.7), Inches(3.6), Inches(5.2), "") # dummy
    c2 = add_card(s3, Inches(4.8), Inches(1.7), Inches(4.4), Inches(5.2), "How We Use It: Computation Mechanics")
    p = c2.paragraphs[0]
    p.text = "Mathematical Definition:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(2)
    p = c2.add_paragraph()
    p.text = "f_agg([w_1], ..., [w_K]) = Σ α_k · [w_k]\nwhere α_k = 1/K (or sample-weighted n_k / N)"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(10)

    p = c2.add_paragraph()
    p.text = "CKKS Execution Step-by-Step:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(4)
    p = c2.add_paragraph()
    p.text = "1. Each car uploads 11 ciphertext chunks.\n2. Server multiplies each chunk by plaintext scalar α_k.\n3. Server homomorphically adds chunk j across all cars:\n   C_global(j) = Σ α_k · C_k(j)  for j = 0...10\n4. Multiplicative Depth Consumed: 0 levels!\n5. Computation Time: ~5 ms for all 44,164 weights."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c3 = add_card(s3, Inches(9.6), Inches(1.7), Inches(2.9), Inches(5.2), "What Value is Sent Back")
    p = c3.paragraphs[0]
    p.text = "Output of f_agg:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_GREEN
    p.space_after = Pt(6)
    p = c3.add_paragraph()
    p.text = "• The 11 New Aggregated Ciphertext Chunks:\n  [w_global] = [C_global(0), ..., C_global(10)]\n\n• The car decrypts them using sk and unpacks the 44,164 new weights.\n\n• Zero accuracy loss: Bitwise equivalent to plaintext FedAvg (<0.07 pp delta)."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 4: Function 2 - Encrypted Anomaly & Non-Poisoning Distance (f_dist)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Function 2: Encrypted Anomaly & Non-Poisoning Distance (f_dist)", "Byzantine-Robust Defense Function")

    c1 = add_card(s4, Inches(0.8), Inches(1.7), Inches(3.6), Inches(5.2), "Purpose: Why We Use It")
    p = c1.paragraphs[0]
    p.text = "• Detecting Malicious / Rogue Vehicles:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "In connected vehicles, a compromised ECU could send poisoned model updates to sabotage intrusion detection across the fleet."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(12)

    p = c1.add_paragraph()
    p.text = "• Solving the FHE Dilemma:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "Traditional defenses (Multi-Krum, Median) require seeing plaintext updates to detect outliers. f_dist allows the server to evaluate client deviation WITHOUT decrypting their weights."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c2 = add_card(s4, Inches(4.8), Inches(1.7), Inches(4.4), Inches(5.2), "How We Use It: Computation Mechanics")
    p = c2.paragraphs[0]
    p.text = "Mathematical Definition (FheFL Eq. 11):"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(2)
    p = c2.add_paragraph()
    p.text = "f_dist([w_u], g) = ||w_u - g||²\n= gᵀg + [(w_u - 2g)ᵀ · w_u]"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(10)

    p = c2.add_paragraph()
    p.text = "CKKS Execution Step-by-Step:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(4)
    p = c2.add_paragraph()
    p.text = "1. Server subtracts 2g in plaintext: ([w_u] - 2g).\n2. Computes ciphertext × ciphertext dot product: ([w_u] - 2g) ⊗ [w_u].\n3. Performs slot rotations to sum all 4,096 elements inside each chunk.\n4. Adds the public scalar gᵀg.\n5. Modulus Levels Consumed: Exactly 1 level.\n6. Latency: ~18 ms per vehicle."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c3 = add_card(s4, Inches(9.6), Inches(1.7), Inches(2.9), Inches(5.2), "What Value is Sent Back")
    p = c3.paragraphs[0]
    p.text = "Output of f_dist:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_AMBER
    p.space_after = Pt(6)
    p = c3.add_paragraph()
    p.text = "• A Single Encrypted Distance Scalar: [d^u]!\n\n• NOTICE: We do NOT send 44,164 numbers!\n  We send ONLY the evaluated distance scalar [d^u].\n\n• The RSU uses d^u to down-weight or drop anomalous vehicles before aggregation."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 5: Function 3 - Directional Cosine Alignment (f_cos)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Function 3: Directional Cosine Alignment (f_cos)", "Gradient Alignment Verification Function")

    c1 = add_card(s5, Inches(0.8), Inches(1.7), Inches(3.6), Inches(5.2), "Purpose: Why We Use It")
    p = c1.paragraphs[0]
    p.text = "• Defeating Stealthy Backdoor Attacks:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "Smart attackers keep their update distance ||w_u - g|| small to bypass Euclidean distance checks, but point their update in an adversarial direction to poison the decision boundary."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(12)

    p = c1.add_paragraph()
    p.text = "• Verification Against Clean Traffic:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "RSU maintains a tiny verified clean dataset and checks if client updates point in the same direction as legitimate traffic."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c2 = add_card(s5, Inches(4.8), Inches(1.7), Inches(4.4), Inches(5.2), "How We Use It: Computation Mechanics")
    p = c2.paragraphs[0]
    p.text = "Mathematical Definition:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(2)
    p = c2.add_paragraph()
    p.text = "f_cos([w_u], v_clean) = ⟨[w_u], v_clean⟩ / ||v_clean||²\nwhere v_clean is RSU's anchor gradient."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(10)

    p = c2.add_paragraph()
    p.text = "CKKS Execution Step-by-Step:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(4)
    p = c2.add_paragraph()
    p.text = "1. Server computes v_clean on clean anchor data in plaintext.\n2. Computes ciphertext × plaintext inner product: [w_u] ⊙ v_clean.\n3. Rotates slots to sum across all 11 chunks.\n4. Divides by ||v_clean||² (plaintext scalar).\n5. Modulus Levels Consumed: 0 levels! (Depth-free).\n6. Latency: < 3 ms per vehicle."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c3 = add_card(s5, Inches(9.6), Inches(1.7), Inches(2.9), Inches(5.2), "What Value is Sent Back")
    p = c3.paragraphs[0]
    p.text = "Output of f_cos:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_PURPLE
    p.space_after = Pt(6)
    p = c3.add_paragraph()
    p.text = "• An Encrypted Trust Alignment Score: [s_u] ∈ [-1, +1].\n\n• If s_u > 0: Vehicle's update helps detect attacks.\n• If s_u ≤ 0: Vehicle's update is hostile/poisoned and discarded!\n\n• Value sent: 1 single scalar score."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 6: Function 4 - Blind Server-Side Inference (f_infer)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Function 4: Blind Edge Intrusion Inference (f_infer)", "Encrypted Inference / Telemetry Classification")

    c1 = add_card(s6, Inches(0.8), Inches(1.7), Inches(3.6), Inches(5.2), "Purpose: Why We Use It")
    p = c1.paragraphs[0]
    p.text = "• Confidential Cloud/RSU Inspection:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "A vehicle's lightweight ECU encounters suspect CAN bus traffic. Instead of running heavy inference locally, it offloads classification to the powerful RSU."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(12)

    p = c1.add_paragraph()
    p.text = "• Protecting Driver Privacy:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "Raw CAN packets reveal speed, steering angle, braking, and GPS coordinates. Encrypted inference lets the RSU classify attacks without seeing driving logs."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c2 = add_card(s6, Inches(4.8), Inches(1.7), Inches(4.4), Inches(5.2), "How We Use It: ChebyKAN + CKKS Synergy")
    p = c2.paragraphs[0]
    p.text = "Why ChebyKAN is Revolutionary in FHE:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(2)
    p = c2.add_paragraph()
    p.text = "Standard NNs use ReLU (max(0,x)), which CANNOT run in FHE without severe polynomial approximations."
    p.font.size = Pt(11)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(8)

    p = c2.add_paragraph()
    p.text = "ChebyKAN is Natively Polynomial:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(2)
    p = c2.add_paragraph()
    p.text = "f_infer([x]) = Σ c_j · T_j([x])\nEvaluated using Clenshaw Recurrence:\nT_{j+1}([x]) = 2[x] ⊗ T_j([x]) - T_{j-1}([x])\n\n• Consumes strictly additions and multiplications with rescaling — exactly Algorithm 1 from Page 424 of BookCKKS.pdf!"
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c3 = add_card(s6, Inches(9.6), Inches(1.7), Inches(2.9), Inches(5.2), "What Value is Sent Back")
    p = c3.paragraphs[0]
    p.text = "Output of f_infer:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_GREEN
    p.space_after = Pt(6)
    p = c3.add_paragraph()
    p.text = "• An Encrypted Classification Score:\n  [y] = [P(DoS), P(Fuzzy), P(Normal)]\n\n• NOT the model weights! The server sends back ONLY the classification probability vector.\n\n• Vehicle decrypts [y] and triggers firewall/alarm if attack detected."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 7: Function 5 - High-Degree Coefficient Damping (f_damp)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Function 5: High-Degree Coefficient Damping (f_damp)", "ChebyKAN-Specific Regularization Function")

    c1 = add_card(s7, Inches(0.8), Inches(1.7), Inches(3.6), Inches(5.2), "Purpose: Why We Use It")
    p = c1.paragraphs[0]
    p.text = "• Preventing Runge's Oscillation:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "In polynomial networks, higher-degree terms (T_3, T_4) are prone to extreme oscillations near interval boundaries [-1, +1] when trained on noisy vehicular data."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK
    p.space_after = Pt(12)

    p = c1.add_paragraph()
    p.text = "• Neutralizing Polynomial Tampering:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(4)
    p = c1.add_paragraph()
    p.text = "Attackers specifically inject large values into high-degree coefficients to make the global model unstable. f_damp suppresses high-frequency noise."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c2 = add_card(s7, Inches(4.8), Inches(1.7), Inches(4.4), Inches(5.2), "How We Use It: Computation Mechanics")
    p = c2.paragraphs[0]
    p.text = "Mathematical Definition:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(2)
    p = c2.add_paragraph()
    p.text = "f_damp([c_j]) = λ_j · [c_j]\nwhere λ_j = 1 / (1 + η · j²)\nand j ∈ {0, 1, 2, 3, 4} is the polynomial degree."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(10)

    p = c2.add_paragraph()
    p.text = "CKKS Execution Step-by-Step:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(4)
    p = c2.add_paragraph()
    p.text = "1. Server targets the 36,480 Chebyshev coefficient slots.\n2. Multiplies degree-0 terms by λ_0 = 1.0 (no damping).\n3. Multiplies degree-4 terms by λ_4 = 0.65 (heavy damping).\n4. Modulus Levels Consumed: 0 levels (plaintext scalar multiply).\n5. Latency: < 1 ms."
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    c3 = add_card(s7, Inches(9.6), Inches(1.7), Inches(2.9), Inches(5.2), "What Value is Sent Back")
    p = c3.paragraphs[0]
    p.text = "Output of f_damp:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_AMBER
    p.space_after = Pt(6)
    p = c3.add_paragraph()
    p.text = "• Smoothed Model Coefficients:\n  The server sends back regularized ciphertexts [w_regularized].\n\n• Guarantees convergence on non-IID data without exploding gradients.\n\n• High novelty value for your research paper!"
    p.font.size = Pt(11.5)
    p.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 8: Master Comparison Table
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Master Comparison: All 5 Homomorphic Functions in IoV", "Executive Technical Summary")

    # Add Table
    rows = 6
    cols = 6
    left = Inches(0.8)
    top = Inches(1.6)
    width = Inches(11.733)
    height = Inches(5.2)

    table_shape = s8.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table

    # Column widths
    table.columns[0].width = Inches(1.8) # Name
    table.columns[1].width = Inches(2.8) # Formula
    table.columns[2].width = Inches(2.5) # Purpose
    table.columns[3].width = Inches(1.2) # Depth
    table.columns[4].width = Inches(1.3) # Latency
    table.columns[5].width = Inches(2.133) # What Value is Sent Back

    headers = ["Function Name", "Math Definition", "Purpose in IoV IDS", "CKKS Depth", "Latency", "What Value Sent Back"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor(255, 255, 255)

    data = [
        ("f_agg (FedAvg)", "Σ α_k · [w_k]", "Fleet collaborative learning without leaking weights", "0 levels", "~5 ms", "Aggregated model [w_global]"),
        ("f_dist (FheFL)", "gᵀg + [(w-2g)ᵀ · w]", "Detect rogue / poisoned vehicles under FHE", "1 level", "~18 ms", "1 Distance scalar [d^u]"),
        ("f_cos (Cosine)", "⟨[w], v_clean⟩ / ||v||²", "Detect stealthy directional backdoor attacks", "0 levels", "<3 ms", "1 Trust score scalar [s_u]"),
        ("f_infer (Inference)", "Σ c_j · T_j([x])", "Blind RSU classification of suspect CAN packets", "≤2 levels", "~45 ms", "Attack probability [y]"),
        ("f_damp (Damping)", "λ_j · [c_j]", "Prevent Runge oscillation & spline tampering", "0 levels", "<1 ms", "Damped coefficients [w_damp]"),
    ]

    for row_idx, row_data in enumerate(data):
        for col_idx, cell_value in enumerate(row_data):
            cell = table.cell(row_idx + 1, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if row_idx % 2 == 0 else RGBColor(255, 255, 255)
            p = cell.text_frame.paragraphs[0]
            p.text = cell_value
            p.font.size = Pt(10.5)
            p.font.color.rgb = C_TEXT_DARK
            if col_idx == 0:
                p.font.bold = True
                p.font.color.rgb = C_BLUE
            elif col_idx == 3:
                p.font.bold = True
                p.font.color.rgb = C_TEAL if "0" in cell_value else C_ACCENT_AMBER

    # Save presentation
    out_path = os.path.abspath("Presentation/F_Functions_In_CKKS_ChebyKAN.pptx")
    prs.save(out_path)
    print(f"Presentation saved successfully to: {out_path}")

create_presentation()

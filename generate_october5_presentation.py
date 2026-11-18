import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_presentation():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5) # 16:9 widescreen
    blank_layout = prs.slide_layouts[6]

    # Professional Color Palette
    C_NAVY = RGBColor(15, 23, 42)         # #0f172a Deep Slate Navy
    C_BLUE = RGBColor(30, 58, 138)        # #1e3a8a Corporate Royal Blue
    C_TEAL = RGBColor(13, 148, 136)       # #0d9488 Modern Teal
    C_LIGHT_BG = RGBColor(248, 250, 252)  # #f8fafc Clean Background
    C_CARD_BG = RGBColor(255, 255, 255)   # #ffffff Pure White
    C_BORDER = RGBColor(226, 232, 240)    # #e2e8f0 Slate Border
    C_TEXT_DARK = RGBColor(30, 41, 59)    # #1e293b Primary Text
    C_TEXT_MUTED = RGBColor(100, 116, 139)# #64748b Secondary Text
    C_GREEN = RGBColor(16, 185, 129)      # #10b981 Success
    C_AMBER = RGBColor(217, 119, 6)       # #d97706 Warning/Highlight
    C_ACCENT_AMBER = RGBColor(217, 119, 6)
    C_PURPLE = RGBColor(124, 58, 237)     # #7c3aed Highlight
    C_ACCENT_PURPLE = RGBColor(124, 58, 237)

    def add_slide_header(slide, title_text, category_text="AMRITA & LGSI COLLABORATIVE RESEARCH • OCTOBER 5, 2026"):
        # Category Tracker
        box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.35))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p0 = tf.paragraphs[0]
        p0.text = category_text.upper()
        p0.font.size = Pt(9.5)
        p0.font.bold = True
        p0.font.color.rgb = C_TEAL

        # Slide Title
        box2 = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.733), Inches(0.7))
        tf2 = box2.text_frame
        tf2.word_wrap = True
        tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
        p1 = tf2.paragraphs[0]
        p1.text = title_text
        p1.font.size = Pt(22)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY

    def add_content_card(slide, left, top, width, height, title, bg_color=C_CARD_BG, border_color=C_BORDER):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)

        # Title bar
        tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), width - Inches(0.5), Inches(0.45))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_BLUE

        # Content area
        body_box = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.65), width - Inches(0.5), height - Inches(0.85))
        btf = body_box.text_frame
        btf.word_wrap = True
        btf.margin_left = btf.margin_top = btf.margin_right = btf.margin_bottom = 0
        return btf

    # =========================================================================
    # SLIDE 1: Title Slide (High Impact Navy)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    bg = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_NAVY
    bg.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(1.2), Inches(1.5), Inches(10.9), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "PRIVACY-PRESERVING COLLABORATIVE IDS FOR CONNECTED VEHICLES"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(10)

    p2 = tf.add_paragraph()
    p2.text = "Homomorphic Function Evaluation (f), ChebyKAN Architecture & Multi-Key Key Management"
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(148, 163, 184)
    p2.space_after = Pt(26)

    p3 = tf.add_paragraph()
    p3.text = "Technical Review & Progress Update — October 5, 2026"
    p3.font.size = Pt(13)
    p3.font.bold = True
    p3.font.color.rgb = C_TEAL
    p3.space_after = Pt(16)

    p4 = tf.add_paragraph()
    p4.text = "Team: Thrishwant G, Hithesh Y | Amrita Mentor: Dr. Praveen K | LGSI Mentor: Fahiem Altaf"
    p4.font.size = Pt(12)
    p4.font.color.rgb = RGBColor(203, 213, 225)

    # =========================================================================
    # SLIDE 2: Executive Agenda
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "Executive Agenda & Review Deliverables")

    cards = [
        ("1. Function f Demystified", "Resolving the core review item:\n• What is the homomorphic function f?\n• Why the server knows f but not the data\n• How f is used to update the global model W_{t+1}"),
        ("2. 44k ChebyKAN Weights in CKKS", "Engineering mechanics of parameter handling:\n• Why ChebyKAN has 44,164 weights\n• Slicing into 11 chunks via SIMD slots\n• Why ChebyKAN natively matches Page 424 of BookCKKS"),
        ("3. Complete Taxonomy of f Functions", "What all f functions are used in IoV:\n• f_agg: Model update (Depth 0)\n• f_dist: Anomaly distance scalar (Depth 1)\n• f_cos: Directional alignment (Depth 0)\n• f_infer: Blind CAN inference (Depth ≤ 2)"),
        ("4. Key Management & Baseline Results", "Security & experimental validation:\n• xMK-CKKS key masking & group key broadcast\n• Encryption-neutral accuracy baseline (<0.07 pp)\n• System gap analysis & paper roadmap"),
    ]

    for i, (title, content) in enumerate(cards):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 5.95)
        top = Inches(1.6 + row * 2.7)
        c = add_content_card(s2, left, top, Inches(5.75), Inches(2.45), title)
        for line in content.split("\n"):
            p = c.add_paragraph() if c.paragraphs[0].text else c.paragraphs[0]
            p.text = line
            p.font.size = Pt(11.5)
            p.font.color.rgb = C_TEXT_DARK
            p.space_after = Pt(3)

    # =========================================================================
    # SLIDE 3: System Architecture & Trust Boundary
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "Architecture Blueprint: The Role of the Server & Function f")

    c1 = add_content_card(s3, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.3), "Client Domain (Vehicles)")
    lines1 = [
        "• Possesses Secret Decryption Key (sk)",
        "• Local On-Board Training:",
        "  Each vehicle trains its 44,164-weight ChebyKAN model on local CAN bus frames.",
        "• Local CKKS Encryption:",
        "  Packs 44k weights into 11 ciphertext chunks using public key pk.",
        "• Transmits to Server:",
        "  Uploads 11 encrypted chunks over secure V2X/TLS channel.",
        "• Local Decryption:",
        "  Receives evaluated result of f and decrypts locally using sk."
    ]
    for line in lines1:
        p = c1.add_paragraph() if c1.paragraphs[0].text else c1.paragraphs[0]
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(4)

    c2 = add_content_card(s3, Inches(4.7), Inches(1.6), Inches(4.3), Inches(5.3), "Untrusted Server Domain (RSU)", bg_color=RGBColor(240, 253, 250), border_color=C_TEAL)
    lines2 = [
        "• Possesses ZERO Decryption Keys (No sk)",
        "• Oblivious to Plaintext Data:",
        "  The RSU cannot inspect individual updates.",
        "• Computes Function f(Encrypted Data):",
        "  Executes the designated homomorphic circuit (FedAvg, Distance, or Inference) entirely in ciphertext space.",
        "• Generates New Result Ciphertext:",
        "  Evaluates f over the 11 chunks without decrypting.",
        "• Returns Evaluated Value of f:",
        "  Broadcasts the evaluated result of f back to the fleet."
    ]
    for line in lines2:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(4)

    c3 = add_content_card(s3, Inches(9.3), Inches(1.6), Inches(3.2), Inches(5.3), "The Mentor's Key Insight")
    lines3 = [
        "What Gets Sent Back?",
        "As mentor Fahiem Altaf emphasized:",
        "The server does NOT echo raw ciphertexts or unaggregated client data.",
        "The server transmits the EVALUATED VALUE OF THAT FUNCTION f!",
        "Examples of Evaluated Values:",
        "1. [W_{t+1}] -> The updated global model",
        "2. [d^u] -> A single distance scalar",
        "3. [s_u] -> A single alignment trust score",
        "4. [y] -> An attack probability vector"
    ]
    for i, line in enumerate(lines3):
        p = c3.add_paragraph() if c3.paragraphs[0].text else c3.paragraphs[0]
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = C_ACCENT_AMBER if i == 0 else C_TEXT_DARK
        p.font.bold = True if i in [0, 3, 4] else False
        p.space_after = Pt(3)

    # =========================================================================
    # SLIDE 4: How Function f Updates the Global Model
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "How Function f Updates the Global Model (Wt+1)")

    c1 = add_content_card(s4, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "Core FL Model Update Mechanics")
    p = c1.paragraphs[0]
    p.text = "In Federated Learning, the primary function f evaluated by the server is precisely the Global Model Update function:"
    p.font.size = Pt(11.5)
    p.space_after = Pt(8)

    p = c1.add_paragraph()
    p.text = "[W_{t+1}] = f(W_t, [W_1], [W_2], ..., [W_K])"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(10)

    points4 = [
        ("Input to f: ", "Previous global model W_t (plaintext on RSU) and encrypted client updates [W_1], ..., [W_K]."),
        ("Role of the Server: ", "The server applies the update rule f directly over the 11 ciphertext chunks using homomorphic addition and scalar multiplication."),
        ("Output of f: ", "A new set of 11 ciphertexts representing [W_{t+1}]. The server sends this evaluated value back to vehicles so they can refresh their local detection brains."),
    ]
    for title, body in points4:
        p = c1.add_paragraph()
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r2 = p.add_run()
        r2.text = body
        r2.font.size = Pt(11)
        p.space_after = Pt(6)

    c2 = add_content_card(s4, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "Three Mathematical Formulations of f")
    forms = [
        ("1. Homomorphic FedAvg (Standard Baseline):", "[W_{t+1}] = (1/K) ∑ [W_i]\n• Simple weighted average over all reporting vehicles.\n• Depth: 0 levels (instantaneous, ~5 ms for all 44k weights)."),
        ("2. Server-Step Global Delta Update:", "[W_{t+1}] = W_t + η · (1/K ∑ [ΔW_i])\n• Vehicles send encrypted gradient deltas [ΔW_i].\n• The RSU scales and adds the delta to W_t in ciphertext domain."),
        ("3. Byzantine-Robust Filtered Update:", "[W_{t+1}] = ∑ p_i([d_i]) · [W_i]\n• Server evaluates anomaly distance [d_i] under encryption.\n• Assigns non-poisoning weights p_i so rogue cars cannot poison W_{t+1}."),
    ]
    for title, body in forms:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        p.text = title
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = C_TEAL
        p.space_after = Pt(2)
        for line in body.split("\n"):
            p2 = c2.add_paragraph()
            p2.text = line
            p2.font.size = Pt(10.5)
            p2.font.color.rgb = C_TEXT_DARK
        p2.space_after = Pt(8)

    # =========================================================================
    # SLIDE 5: The 44,164 Weights in ChebyKAN
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_header(s5, "The 44,164 Parameters in ChebyKAN: Architecture Breakdown")

    c1 = add_content_card(s5, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "Where Does 44,164 Come From?")
    p = c1.paragraphs[0]
    p.text = "In standard MLPs, every connection has 1 weight. In ChebyKAN, every connection between two neurons has a flexible curve parameterized by Chebyshev polynomials!"
    p.font.size = Pt(11.5)
    p.space_after = Pt(8)

    p = c1.add_paragraph()
    p.text = "Our model has 7,296 total connections across 2 layers + output layer (46 inputs -> 64 -> 64 -> 4 classes):"
    p.font.size = Pt(11)
    p.space_after = Pt(8)

    breakdown = [
        ("Chebyshev Weights (5 per edge): ", "7,296 edges × 5 coefficients (c_0...c_4) = 36,480 weights (over 82% of model!)."),
        ("Base Linear Weights (1 per edge): ", "7,296 edges × 1 linear weight (w_b) = 7,296 weights."),
        ("Biases & Normalization: ", "Layer biases (64+64+4) + LayerNorm parameters = 388 weights."),
        ("TOTAL PARAMETERS: ", "36,480 + 7,296 + 388 = 44,164 weights!"),
    ]
    for title, body in breakdown:
        p = c1.add_paragraph()
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        if "TOTAL" in title: r1.font.color.rgb = C_BLUE
        r2 = p.add_run()
        r2.text = body
        r2.font.size = Pt(11)
        p.space_after = Pt(6)

    c2 = add_content_card(s5, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "Why This Parameter Count is Crucial for FHE")
    benefits = [
        ("14× Smaller than Transformer Trunk: ", "Our previous MamKANformer trunk had 618,000 parameters. In FHE, parameter count is the #1 cost driver. Reducing to 44,164 makes encryption practical."),
        ("One 1D Vector for Encryption: ", "Before encryption, flatten_model() extracts all 44,164 numbers into a single float64 array: w = [w_0, w_1, ..., w_44163]."),
        ("Dataset Class Adaptability: ", "• 4 classes (CAN-VTC multi-class): exactly 44,164 weights\n• 5 classes (Car-Hacking multi-class): 44,549 weights\n• 2 classes (Binary detection): 43,394 weights\nIn all cases, the model stays compactly within ~44k parameters!"),
    ]
    for title, body in benefits:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(12)
        r1.font.color.rgb = C_NAVY
        p.space_after = Pt(2)
        for line in body.split("\n"):
            p2 = c2.add_paragraph()
            p2.text = line
            p2.font.size = Pt(10.5)
            p2.font.color.rgb = C_TEXT_DARK
        p2.space_after = Pt(8)

    # =========================================================================
    # SLIDE 6: CKKS SIMD Slot Packing
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "CKKS SIMD Slot Packing: 44,164 Weights into 11 Ciphertexts")

    c1 = add_content_card(s6, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "SIMD Slot Packing Principle")
    p = c1.paragraphs[0]
    p.text = "In CKKS, one ciphertext is NOT one encrypted number. One ciphertext holds a vector of real numbers using SIMD (Single Instruction Multiple Data) batching."
    p.font.size = Pt(11.5)
    p.space_after = Pt(8)

    p = c1.add_paragraph()
    p.text = "Slots per Ciphertext = N / 2 = 8,192 / 2 = 4,096 numbers!"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(10)

    p = c1.add_paragraph()
    p.text = "To pack 44,164 numbers, we slice the array into 11 chunks:\n" \
           "• Chunk 0: Weights 0 to 4,095 (4,096 weights)\n" \
           "• Chunk 1: Weights 4,096 to 8,191 (4,096 weights)\n" \
           "• ...\n" \
           "• Chunk 10: Weights 40,960 to 44,163 (3,204 weights + 892 padding)\n\n" \
           "Total Chunks: ⌈44,164 / 4,096⌉ = 11 Ciphertext Chunks!"
    p.font.size = Pt(11)
    p.font.color.rgb = C_TEXT_DARK

    c2 = add_content_card(s6, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "Encoding, Encryption & Wire Size")
    steps = [
        ("Step 1 — Scaling Factor (Δ = 2⁴⁰): ", "Decimal numbers (e.g., 0.1042) are scaled by 2⁴⁰ to convert them into high-precision integers without precision loss."),
        ("Step 2 — Canonical Embedding: ", "The 4,096 numbers are transformed via inverse FFT into coefficients of a degree-8191 plaintext polynomial m(X)."),
        ("Step 3 — Public Key Encryption: ", "Encrypted with (a, b) and fresh noise: c_0 = b·u + e_0 + m, c_1 = a·u + e_1. The weights are buried under cryptographic noise."),
        ("Step 4 — Wire Payload: ", "Each ciphertext chunk is ~225 KB. All 11 chunks = 2.47 MB per client update. 11 additions on the server compute all 44,164 weights simultaneously!"),
    ]
    for title, body in steps:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r1.font.color.rgb = C_BLUE
        r2 = p.add_run()
        r2.text = body
        r2.font.size = Pt(10.5)
        p.space_after = Pt(8)

    # =========================================================================
    # SLIDE 7: Cryptographic Grounding (BookCKKS Page 424)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_header(s7, "Cryptographic Grounding: Section 4 (Page 424) of BookCKKS.pdf")

    c1 = add_content_card(s7, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "What Page 424 Formally Specifies")
    p = c1.paragraphs[0]
    p.text = "In Cheon, Kim, Kim, and Song (ASIACRYPT 2017), Section 4 defines how any arbitrary function f is evaluated in CKKS:"
    p.font.size = Pt(11.5)
    p.space_after = Pt(8)

    theorems = [
        ("Lemma 4 — Constant Operations: ", "f(x) = x + a and f(x) = a·x for constant a. Evaluated directly on ciphertext (c_0, c_1) at Depth 0."),
        ("Algorithm 1 — Power Polynomials: ", "f(x) = x^d for d = 2^r. Computed by recursive squaring and rescaling: c_j = Rescale(Mult(c_{j-1}, c_{j-1})). Consumes r modulus levels."),
        ("Lemma 7 — Arbitrary Polynomials: ", "Any polynomial f(x) = ∑ a_i x^i is decomposed into an arithmetic circuit of additions, multiplications, and rescalings."),
        ("Section 4.2 — Analytic Functions: ", "Functions like sigmoid, exponential, and inverse are approximated using Taylor series or Chebyshev polynomials!"),
    ]
    for title, body in theorems:
        p = c1.add_paragraph()
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r1.font.color.rgb = C_TEAL
        r2 = p.add_run()
        r2.text = body
        r2.font.size = Pt(11)
        p.space_after = Pt(8)

    c2 = add_content_card(s7, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "Why This Grounding Settles the Review Doubt")
    settles = [
        ("The Server IS Supposed to Know f: ", "Under Kerckhoffs's Principle, the evaluation circuit f is public. The server executes f on encrypted inputs without possessing sk."),
        ("Polynomial Decomposition: ", "Every function f evaluated on the server must map to additions and multiplications. This is why our FedAvg (Depth 0) and Distance (Depth 1) are strictly feasible within our 2-level budget."),
        ("Rescaling Controls Noise: ", "Page 424 proves that rescaling after multiplication truncates least significant bits, keeping approximation error bounded at ~1e-8 at our parameters."),
    ]
    for title, body in settles:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        r1 = p.add_run()
        r1.text = title
        r1.font.bold = True
        r1.font.size = Pt(12)
        r1.font.color.rgb = C_NAVY
        p.space_after = Pt(2)
        p2 = c2.add_paragraph()
        p2.text = body
        p2.font.size = Pt(11)
        p2.font.color.rgb = C_TEXT_DARK
        p2.space_after = Pt(10)

    # =========================================================================
    # SLIDE 8: Why ChebyKAN is a Native Match for CKKS
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_header(s8, "Why ChebyKAN is a Native Match for CKKS Homomorphic Evaluation")

    c1 = add_content_card(s8, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "Standard Neural Networks (The ReLU Bottleneck)")
    lines_nn = [
        "• Non-Polynomial Activations Fail in FHE:",
        "  Standard MLPs and CNNs use ReLU(x) = max(0, x), GELU, or Sigmoid.",
        "• The Approximation Problem:",
        "  FHE cannot compute max(0, x) directly. Cryptographers must fit degree 7–15 polynomials to approximate ReLU.",
        "• Catastrophic Consequences:",
        "  1. High multiplicative depth (consumes 3–4 modulus levels).",
        "  2. Large parameter sizes (N=16384 or 32768 needed).",
        "  3. Approximation errors degrade intrusion detection accuracy."
    ]
    for line in lines_nn:
        p = c1.add_paragraph() if c1.paragraphs[0].text else c1.paragraphs[0]
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(6)

    c2 = add_content_card(s8, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "ChebyKAN (Natively Polynomial by Definition)", bg_color=RGBColor(240, 253, 250), border_color=C_TEAL)
    lines_kan = [
        "• Basis Functions are Already Polynomials:",
        "  ChebyKAN uses Chebyshev basis polynomials: T_0=1, T_1=x, T_2=2x²-1, T_3=4x³-3x, T_4=8x⁴-8x²+1.",
        "• Zero Activation Approximation Loss:",
        "  Evaluating ChebyKAN requires NO Taylor series approximation. The network IS a polynomial!",
        "• Evaluates via Clenshaw Recurrence:",
        "  T_{j+1}([x]) = 2[x] ⊗ T_j([x]) - T_{j-1}([x]) strictly uses additions and multiplications with rescaling — exactly Algorithm 1 of Page 424!",
        "• Blind Inference Ready:",
        "  Allows the RSU to evaluate encrypted CAN packets directly."
    ]
    for line in lines_kan:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 9: Taxonomy Part 1 - Aggregation & Anomaly
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_header(s9, "Taxonomy of f Functions in IoV (Part 1: Aggregation & Anomaly)")

    c1 = add_content_card(s9, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "Function 1: Model Update Function (f_agg)")
    p = c1.paragraphs[0]
    p.text = "Mathematical Definition: [W_{t+1}] = (1/K) ∑ [W_k]"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(8)

    pts9_1 = [
        ("Purpose: ", "Fleet-wide collaborative intrusion detection without exposing individual vehicle parameters to the RSU or eavesdroppers."),
        ("How We Use It: ", "Server takes 11 chunks from each car, scales by 1/K, and homomorphically adds chunk j across all cars. Consumes 0 modulus levels (~5 ms latency)."),
        ("What Value is Sent Back: ", "The new global model ciphertext [W_{t+1}]! Cars decrypt it locally using sk and update their ChebyKAN models."),
    ]
    for t, b in pts9_1:
        p = c1.add_paragraph()
        r1 = p.add_run()
        r1.text = t
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r2 = p.add_run()
        r2.text = b
        r2.font.size = Pt(11)
        p.space_after = Pt(6)

    c2 = add_content_card(s9, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "Function 2: Anomaly Distance Function (f_dist)")
    p = c2.paragraphs[0]
    p.text = "Mathematical Definition: [d_u] = gᵀg + [(w_u - 2g)ᵀ · w_u]"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(8)

    pts9_2 = [
        ("Purpose: ", "Detect rogue or compromised ECUs injecting poisoned updates without needing plaintext access (solves the Multi-Krum/FHE conflict)."),
        ("How We Use It: ", "RSU subtracts public reference 2g, evaluates ciphertext × ciphertext dot product, and sums slots via rotation. Consumes 1 level (~18 ms latency)."),
        ("What Value is Sent Back: ", "A single encrypted distance scalar [d_u]! NOT 44k numbers — only the evaluated scalar distance, used to down-weight rogue cars."),
    ]
    for t, b in pts9_2:
        p = c2.add_paragraph()
        r1 = p.add_run()
        r1.text = t
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r2 = p.add_run()
        r2.text = b
        r2.font.size = Pt(11)
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 10: Taxonomy Part 2 - Alignment, Inference & Damping
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_header(s10, "Taxonomy of f Functions in IoV (Part 2: Alignment, Inference & Damping)")

    c1 = add_content_card(s10, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.3), "f_cos: Cosine Alignment")
    p = c1.paragraphs[0]
    p.text = "[s_u] = ⟨[w_u], v_clean⟩ / ||v_clean||²"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = C_BLUE
    p.space_after = Pt(6)
    pts10_1 = [
        "• Purpose: Defeat stealthy backdoor attacks that evade Euclidean checks.",
        "• Mechanics: Ciphertext-plaintext inner product with clean RSU validation gradient.",
        "• Depth: 0 levels (<3 ms).",
        "• Value Sent Back: Single trust score scalar [s_u] ∈ [-1, +1]."
    ]
    for line in pts10_1:
        p = c1.add_paragraph()
        p.text = line
        p.font.size = Pt(10.5)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(4)

    c2 = add_content_card(s10, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.3), "f_infer: Blind Edge Inference")
    p = c2.paragraphs[0]
    p.text = "[y] = ∑ c_j · T_j([x])"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(6)
    pts10_2 = [
        "• Purpose: Low-power ECU offloads CAN inspection to RSU without revealing driving logs.",
        "• Mechanics: Native ChebyKAN forward evaluation via Clenshaw recurrence.",
        "• Depth: ≤ 2 levels (~45 ms).",
        "• Value Sent Back: Encrypted attack probability vector [P(Attack)]."
    ]
    for line in pts10_2:
        p = c2.add_paragraph()
        p.text = line
        p.font.size = Pt(10.5)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(4)

    c3 = add_content_card(s10, Inches(8.8), Inches(1.6), Inches(3.7), Inches(5.3), "f_damp: Coefficient Damping")
    p = c3.paragraphs[0]
    p.text = "f_damp([c_j]) = λ_j · [c_j]"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = C_AMBER
    p.space_after = Pt(6)
    pts10_3 = [
        "• Purpose: Prevent Runge's oscillation in high-degree terms (T_3, T_4) on non-IID data.",
        "• Mechanics: Frequency filter scaling: λ_j = 1 / (1 + η·j²).",
        "• Depth: 0 levels (<1 ms).",
        "• Value Sent Back: Regularized global ciphertexts [W_regularized]."
    ]
    for line in pts10_3:
        p = c3.add_paragraph()
        p.text = line
        p.font.size = Pt(10.5)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(4)

    # =========================================================================
    # SLIDE 11: Master Summary Table
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_header(s11, "Master Comparison: All 5 Homomorphic Functions Evaluated by Server")

    # Table layout
    rows = 6
    cols = 6
    table_shape = s11.shapes.add_table(rows, cols, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.2))
    table = table_shape.table

    table.columns[0].width = Inches(1.6)
    table.columns[1].width = Inches(2.7)
    table.columns[2].width = Inches(2.6)
    table.columns[3].width = Inches(1.1)
    table.columns[4].width = Inches(1.2)
    table.columns[5].width = Inches(2.533)

    headers = ["Function", "Math Definition", "Purpose in IoV IDS", "Depth", "Latency", "What Value is Sent Back"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor(255, 255, 255)

    data11 = [
        ("f_agg (FedAvg)", "∑ α_k · [w_k]", "Collaborative learning without leaking weights", "0 levels", "~5 ms", "New global model [W_{t+1}]"),
        ("f_dist (FheFL)", "gᵀg + [(w-2g)ᵀ · w]", "Detect rogue / poisoned vehicles under FHE", "1 level", "~18 ms", "Single distance scalar [d_u]"),
        ("f_cos (Cosine)", "⟨[w], v_clean⟩ / ||v||²", "Detect stealthy directional backdoor attacks", "0 levels", "<3 ms", "Single trust score scalar [s_u]"),
        ("f_infer (Inference)", "∑ c_j · T_j([x])", "Blind RSU classification of suspect CAN packets", "≤2 levels", "~45 ms", "Attack probability [P(Attack)]"),
        ("f_damp (Damping)", "λ_j · [c_j]", "Prevent Runge oscillation & spline tampering", "0 levels", "<1 ms", "Damped model [W_regularized]"),
    ]
    for row_idx, rdata in enumerate(data11):
        for col_idx, cval in enumerate(rdata):
            cell = table.cell(row_idx + 1, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if row_idx % 2 == 0 else RGBColor(255, 255, 255)
            p = cell.text_frame.paragraphs[0]
            p.text = cval
            p.font.size = Pt(10)
            p.font.color.rgb = C_TEXT_DARK
            if col_idx == 0:
                p.font.bold = True
                p.font.color.rgb = C_BLUE
            elif col_idx == 3:
                p.font.bold = True
                p.font.color.rgb = C_TEAL if "0" in cval else C_AMBER

    # =========================================================================
    # SLIDE 12: Group Key Broadcasting & xMK-CKKS
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_slide_header(s12, "Group Key Broadcasting & Multi-Key CKKS (Answering Review Item)")

    c1 = add_content_card(s12, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "The Single-Key Vulnerability")
    lines12_1 = [
        "• The Flaw in Month-4 Pipeline:",
        "  Single-key CKKS shares one secret key across all clients via a Trusted Dealer.",
        "• Single Point of Failure in IoV:",
        "  If ANY single vehicle ECU is compromised, reverse-engineered, or stolen, the attacker learns sk and can decrypt EVERY vehicle's broadcast update.",
        "• Review Item Raised by Dr. Praveen K:",
        "  'How do we handle broadcasting certain group key things safely?'",
        "• Required Answer: Multi-Key Key Masking (xMK-CKKS)."
    ]
    for line in lines12_1:
        p = c1.add_paragraph() if c1.paragraphs[0].text else c1.paragraphs[0]
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(5)

    c2 = add_content_card(s12, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "How xMK-CKKS / FheFL Solves Key Broadcasting")
    lines12_2 = [
        "• Individual Secret Keys: Each vehicle u holds its own private key share s_u.",
        "• Pairwise Zero-Sum Masks: Vehicles agree on pairwise secrets s_{i,j} = -s_{j,i} derived deterministically via HKDF/ECDH.",
        "• Masked Shares: User hands the server a masked share:",
        "  ss_u = s_u + ∑_{j≠u} s_{u,j}",
        "• Perfect Mask Cancellation: When summed over the reporting set:",
        "  ∑ ss_u = ∑ s_u = s",
        "• Collusion Resistance: The server can reconstruct key material to decrypt the AGGREGATE ONLY, but learns zero individual updates unless colluding with K-1 vehicles!"
    ]
    for line in lines12_2:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(5)

    # =========================================================================
    # SLIDE 13: Empirical Results: FHE vs Plaintext Parity Baseline
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_slide_header(s13, "Experimental Validation: Plaintext vs. Real CKKS Encryption Baseline")

    c1 = add_content_card(s13, Inches(0.8), Inches(1.6), Inches(5.75), Inches(5.3), "Headline Finding: Zero Accuracy Cost")
    p = c1.paragraphs[0]
    p.text = "Core Takeaway: Homomorphic encryption introduces zero accuracy degradation across all four vehicular datasets (< 0.07 percentage points difference from plaintext)!"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = C_TEAL
    p.space_after = Pt(8)

    pts13 = [
        ("Controlled Comparison: ", "Real TenSEAL CKKS on one arm, exact plaintext on the other; identical seeds (2025, 2026, 2027), splits, and initializations."),
        ("Bitwise Test Assertion: ", "test_backend_equivalence verifies that aggregation produces bitwise identical results on the aggregation path."),
        ("Isolation of Variables: ", "Because encryption causes zero accuracy loss, when we apply INT8 quantization next, any change is solely attributable to quantization!"),
    ]
    for t, b in pts13:
        p = c1.add_paragraph()
        r1 = p.add_run()
        r1.text = t
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r2 = p.add_run()
        r2.text = b
        r2.font.size = Pt(11)
        p.space_after = Pt(6)

    c2 = add_content_card(s13, Inches(6.8), Inches(1.6), Inches(5.75), Inches(5.3), "Dataset Benchmark Results (Honest Reporting)")
    results13 = [
        ("Car-Hacking (The CAN Benchmark We Stand Behind): ", "Test Accuracy: 99.8% · F1-score: 0.998. 5 real attack classes (DoS, Fuzzy, RPM, Gear). Zero gap between FHE and plaintext."),
        ("CAN-VTC (Flood Detection): ", "Test Accuracy: 100.0%. Verified clean split. DoS attack floods one novel CAN ID separable at 13σ. Measures flood detection, not generalisation."),
        ("CICIDS-2017 (Network / Telematics): ", "Test Accuracy: 95.5% · ROC-AUC: 0.982. Group-aware train/test split prevents session leakage."),
        ("VeReMi (V2X Misbehaviour - Lower Bound): ", "Near chance (~50%). Verified cause: cleaned export dropped sender_id, preventing temporal tracking of position falsification. Re-acquisition scheduled."),
    ]
    for t, b in results13:
        p = c2.add_paragraph() if c2.paragraphs[0].text else c2.paragraphs[0]
        r1 = p.add_run()
        r1.text = t
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r1.font.color.rgb = C_NAVY
        r2 = p.add_run()
        r2.text = b
        r2.font.size = Pt(10.5)
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 14: System Gap Analysis
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_slide_header(s14, "System Gap Analysis: Where We Stand & What We Are Solving")

    gaps = [
        ("1. Key Management Architecture", "Current: Single-Key CKKS in simulation; xMK-CKKS modeled algebraically.\nTarget: OpenFHE C++ core migration to instantiate threshold decryption natively."),
        ("2. Server Execution Decoupling", "Current: server.py decrypt() called inside Python simulation object.\nTarget: Enforce strict architectural separation where server returns [W_{t+1}] without sk."),
        ("3. V2X Wire Bandwidth Optimization", "Current: 2.47 MB per client update (915 DSRC frames).\nTarget: Delivered 29.6% reduction via level-dropped packing; hierarchical RSU aggregation next."),
        ("4. Dataset Re-acquisition & Scale", "Current: 10 simulated clients, 5 rounds; VeReMi missing sender_id.\nTarget: Scale to 50 clients with vehicle dropout; re-acquire raw VeReMi preserving sender IDs."),
    ]
    for i, (title, content) in enumerate(gaps):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 5.95)
        top = Inches(1.6 + row * 2.7)
        c = add_content_card(s14, left, top, Inches(5.75), Inches(2.45), title)
        for line in content.split("\n"):
            p = c.add_paragraph() if c.paragraphs[0].text else c.paragraphs[0]
            p.text = line
            p.font.size = Pt(11)
            p.font.color.rgb = C_TEXT_DARK
            p.space_after = Pt(3)

    # =========================================================================
    # SLIDE 15: Research Paper Roadmap (Fahiem's Structure)
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    add_slide_header(s15, "Research Paper Structure: Addressing Mentor's Blueprint")

    sections = [
        ("1. Problem Statement", "Collaborative vehicular intrusion detection without trusting the RSU server and without leaking driver privacy or ECU telemetry."),
        ("2. Literature Gap", "Existing works either use plaintext FL (vulnerable to inversion) or single-key FHE (broken if 1 vehicle is hacked). Byzantine defenses like Multi-Krum fail under FHE."),
        ("3. Methodology", "ChebyKAN (44k params, native polynomials) + CKKS SIMD packing (11 chunks) + FheFL algebraic distance scoring (f_dist) + xMK-CKKS key masking."),
        ("4. Results & Comparison", "Zero accuracy loss across 4 benchmarks (<0.07 pp gap). 14× parameter reduction over transformer trunks. Quantitative comparison with prior FedIoV baselines."),
    ]
    for i, (title, content) in enumerate(sections):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 5.95)
        top = Inches(1.6 + row * 2.7)
        c = add_content_card(s15, left, top, Inches(5.75), Inches(2.45), title)
        p = c.paragraphs[0]
        p.text = content
        p.font.size = Pt(11.5)
        p.font.color.rgb = C_TEXT_DARK

    # =========================================================================
    # SLIDE 16: Conclusion & Discussion
    # =========================================================================
    s16 = prs.slides.add_slide(blank_layout)
    bg16 = s16.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg16.fill.solid()
    bg16.fill.fore_color.rgb = C_NAVY
    bg16.line.fill.background()

    tb = s16.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10.3), Inches(4.2))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "SUMMARY & DISCUSSION"
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(14)

    recap = [
        "1. The homomorphic function f is the server's public computational task — updating the global model W_{t+1} and evaluating anomaly distances under encryption.",
        "2. The server outputs the evaluated value of f ([W_{t+1}] or [d^u]), never raw client data.",
        "3. ChebyKAN's 44,164 parameters fit into 11 CKKS ciphertexts and evaluate natively without ReLU approximation penalties.",
        "4. Encryption costs zero accuracy (<0.07 pp) — establishing the rigorous control for upcoming quantization.",
        "5. Next Milestones: OpenFHE C++ core migration, sender-aware VeReMi re-acquisition, scale to 50 clients."
    ]
    for line in recap:
        p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(13)
        p.font.color.rgb = RGBColor(203, 213, 225)
        p.space_after = Pt(8)

    out_path = os.path.abspath("Presentation/October_5_Progress_Presentation_LGSI.pptx")
    prs.save(out_path)
    print(f"Presentation saved successfully: {out_path}")

build_presentation()

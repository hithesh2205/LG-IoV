import os, pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

def apply_deck_updates():
    src_path = "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
    out_paths = [
        "Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx",
        "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
    ]
    
    prs = pptx.Presentation(src_path)
    print(f"Loaded {src_path} with {len(prs.slides)} slides.")
    
    DARK_NAVY = RGBColor(15, 30, 65)
    BLUE_ACCENT = RGBColor(30, 58, 138)
    TEXT_DARK = RGBColor(35, 40, 50)
    MUTED_GRAY = RGBColor(90, 100, 115)
    
    def render_runs(paragraph, text, base_font_size=Pt(14.0), default_bold=False):
        import re
        pattern = r'(\^\{[^}]+\}|\^[0-9a-zA-Z\(\)\+\-]+|\_\{[^}]+\}|\_[0-9a-zA-Z\(\)\+\-]+)'
        tokens = re.split(pattern, text)
        for t in tokens:
            if not t:
                continue
            run = paragraph.add_run()
            run.font.name = "Segoe UI"
            run.font.size = base_font_size
            run.font.bold = default_bold
            run.font.color.rgb = TEXT_DARK
            if t.startswith('^'):
                content = t[2:-1] if t.startswith('^{') else t[1:]
                run.text = content
                run._r.get_or_add_rPr().set('baseline', '30000') # Superscript
            elif t.startswith('_'):
                content = t[2:-1] if t.startswith('_{') else t[1:]
                run.text = content
                run._r.get_or_add_rPr().set('baseline', '-25000') # Subscript
            else:
                run.text = t

    def add_section_header(tf, header_text, space_before=6, font_size=Pt(15.5)):
        p = tf.add_paragraph() if len(tf.paragraphs[0].text) > 0 else tf.paragraphs[0]
        p.space_before = Pt(space_before)
        p.space_after = Pt(2)
        run = p.add_run()
        run.text = header_text
        run.font.name = "Segoe UI"
        run.font.size = font_size
        run.font.bold = True
        run.font.color.rgb = DARK_NAVY

    def add_bullet_point(tf, bullet_text, indent=0, space_before=2, space_after=2, font_size=Pt(13.5)):
        p = tf.add_paragraph()
        p.space_before = Pt(space_before)
        p.space_after = Pt(space_after)
        prefix = "• " if indent == 0 else "  - "
        run_p = p.add_run()
        run_p.text = prefix
        run_p.font.name = "Segoe UI"
        run_p.font.size = font_size
        run_p.font.bold = (indent == 0)
        run_p.font.color.rgb = DARK_NAVY if indent == 0 else TEXT_DARK
        render_runs(p, bullet_text, base_font_size=font_size, default_bold=False)

    # =========================================================================
    # 1. UPDATE SLIDE 2: CONTENT (AGENDA)
    # =========================================================================
    s2 = prs.slides[1]
    s2.shapes.title.text = "Content:"
    for shp in s2.shapes:
        if shp != s2.shapes.title and shp.has_text_frame:
            tf2 = shp.text_frame
            tf2.clear()
            agenda_items = [
                "1. High-Level Cryptographic Architecture (Client vs. Server Trust Domains)",
                "2. Architectural Comparison: Plaintext FedAvg vs. Homomorphic Function F",
                "3. Formal Mathematical Formulation of Function F (Weighted Aggregation)",
                "4. Mathematical Proof of Correctness (Decryption Linearity)",
                "5. ChebyKAN Weight Representation, Datasets & 44,164 Parameters",
                "6. CKKS SIMD Slot Vectorization: Packing 44,164 Weights into 11 Chunks",
                "7. Downstream Model Reconstruction & Multi-Round Scale Refresh",
                "8. Few more Homomorphic Functions which can be Evaluated by Server",
                "9. Automotive Edge Feasibility & Hardware Benchmarks"
            ]
            for idx, item in enumerate(agenda_items):
                p = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
                p.space_before = Pt(4)
                p.space_after = Pt(2)
                run = p.add_run()
                run.text = item
                run.font.name = "Segoe UI"
                run.font.size = Pt(16.0)
                run.font.color.rgb = TEXT_DARK
            break

    # =========================================================================
    # 2. UPDATE SLIDE 7: CHEBYKAN REPRESENTATION, DATASETS & 44,164 PARAMETERS
    # (NO PHOTO, NO W=29, CLEAR 2-COLUMN TECHNICAL PRESENTATION)
    # =========================================================================
    s7 = prs.slides[6]
    s7.shapes.title.text = "ChebyKAN Weight Representation, Datasets & 44,164 Parameters"
    
    # Remove all non-title shapes on slide 7 (removing photo and old text boxes)
    shapes_to_remove7 = [shp for shp in s7.shapes if shp != s7.shapes.title]
    for shp in shapes_to_remove7:
        s7.shapes._spTree.remove(shp._element)
        
    # Column 1: ChebyKAN Weight Representation & Datasets (Left: 0.92 in, Width: 5.60 in)
    tb7_col1 = s7.shapes.add_textbox(Inches(0.92), Inches(1.80), Inches(5.60), Inches(4.30))
    tf7_c1 = tb7_col1.text_frame
    tf7_c1.word_wrap = True
    
    add_section_header(tf7_c1, "How Weights are Represented in ChebyKAN", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf7_c1, "Connection Curves: Standard MLPs use scalar multipliers (w · x). ChebyKAN replaces each connection with a learnable Chebyshev polynomial curve: φ(x) = w_b · x + ∑_{k=0}^{4} c_k · T_k(x_{norm})", font_size=Pt(13.0))
    add_bullet_point(tf7_c1, "6 Parameters per Edge: 1 base linear weight (w_b) captures baseline linear trends + 5 Chebyshev coefficients (c_0, c_1, c_2, c_3, c_4) shape non-linear attack boundaries.", font_size=Pt(13.0))
    add_bullet_point(tf7_c1, "CKKS Native Compatibility: Eliminates non-polynomial activation functions (e.g., ReLU) that cannot be evaluated under homomorphic encryption.", font_size=Pt(13.0))

    add_section_header(tf7_c1, "4 Heterogeneous Datasets & 46-D Feature Vector", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf7_c1, "4 Standalone Benchmarks: Car-Hacking (5 classes), CAN-VTC (4 classes), CICIDS-2017 (2 classes), VeReMi (2 classes) evaluated independently as separate automotive attack vectors.", font_size=Pt(13.0))
    add_bullet_point(tf7_c1, "Unified 46-D Feature Extraction: Sliding window transforms raw CAN frames into 46 statistical features (timing intervals, byte transitions, and Shannon entropy).", font_size=Pt(13.0))
    add_bullet_point(tf7_c1, "Fleet Non-IID Mode (Dirichlet α = 0.3): Shards data across N = 10 ECUs, accurately simulating real-world fleets where vehicles experience localized, unbalanced attack bursts.", font_size=Pt(13.0))

    # Column 2: Exact 44,164 Parameter Count & Target Classes (Left: 6.75 in, Width: 5.65 in)
    tb7_col2 = s7.shapes.add_textbox(Inches(6.75), Inches(1.80), Inches(5.65), Inches(4.30))
    tf7_c2 = tb7_col2.text_frame
    tf7_c2.word_wrap = True
    
    add_section_header(tf7_c2, "Exact Parameter Count Breakdown (44,164 Total)", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf7_c2, "Topology: 46 Inputs -> 64 Hidden -> 64 Hidden -> 4 Classes (7,296 total edges)", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Layer 1 (46 -> 64, 2,944 edges): 14,720 Cheby weights (2,944 × 5) + 2,944 base weights + 64 biases + 128 LayerNorm (γ, β) = 17,856 parameters", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Layer 2 (64 -> 64, 4,096 edges): 20,480 Cheby weights (4,096 × 5) + 4,096 base weights + 64 biases + 128 LayerNorm (γ, β) = 24,768 parameters", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Layer 3 (64 -> 4, 256 edges): 1,280 Cheby weights (256 × 5) + 256 base weights + 4 biases = 1,540 parameters", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Grand Total: 17,856 + 24,768 + 1,540 = EXACTLY 44,164 Parameters (36,480 Cheby weights + 7,296 base weights + 388 biases & LayerNorm).", font_size=Pt(13.0))

    add_section_header(tf7_c2, "4 Canonical Attack Classes (CAN-VTC)", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf7_c2, "Class 0: Attack_free (Normal benign in-vehicle CAN bus traffic)", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Class 1: DoS_attack (Bus flooding with dominant high-priority 0x000 frames)", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Class 2: Fuzzy_attack (Random arbitration IDs and scrambled payload injection)", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Class 3: Impersonation / Spoofing (Rogue node spoofing legitimate sensor messages)", font_size=Pt(13.0))

    # =========================================================================
    # 3. UPDATE SLIDE 11: AUTOMOTIVE EDGE FEASIBILITY & HARDWARE BENCHMARKS
    # (NO PHOTO, NO POST-QUANTUM MENTION, 2-COLUMN STRUCTURED FORMAT)
    # =========================================================================
    s11 = prs.slides[10]
    s11.shapes.title.text = "Automotive Edge Feasibility & Hardware Benchmarks"
    
    # Remove all non-title shapes on slide 11 (removing photo and old text boxes)
    shapes_to_remove11 = [shp for shp in s11.shapes if shp != s11.shapes.title]
    for shp in shapes_to_remove11:
        s11.shapes._spTree.remove(shp._element)
        
    # Column 1: Edge Operation & Hardware Budgets (Left: 0.92 in, Width: 5.60 in)
    tb11_col1 = s11.shapes.add_textbox(Inches(0.92), Inches(1.80), Inches(5.60), Inches(4.30))
    tf11_c1 = tb11_col1.text_frame
    tf11_c1.word_wrap = True
    
    add_section_header(tf11_c1, "Real-Time Detection vs. Federated Updating", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf11_c1, "Path A: Real-Time IDS Detection (Critical Path — Every 10 ms): Reads raw CAN frames, extracts 46 features, and executes ChebyKAN PLAINTEXT inference directly on ECU. Latency: < 1.5 ms per sample (85% safety margin under 10.0 ms CAN deadline).", font_size=Pt(13.0))
    add_bullet_point(tf11_c1, "Path B: Periodic FL Update (Background Path — Every 15–60 mins): Trains on buffered logs, computes Δw_k, encrypts via CKKS in ~150 ms, and transmits 3.52 MB ciphertext payload. Runs strictly as non-critical task during vehicle idling or EV charging.", font_size=Pt(13.0))

    add_section_header(tf11_c1, "Quantitative Performance & Hardware Feasibility", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf11_c1, "Model Footprint: 44,164 parameters (174 KB plaintext) — compact vs. multi-million parameter deep networks.", font_size=Pt(13.0))
    add_bullet_point(tf11_c1, "ECU RAM Overhead: < 20 MB TenSEAL memory footprint (fits easily in standard 1–4 GB automotive gateway ECUs).", font_size=Pt(13.0))
    add_bullet_point(tf11_c1, "5G NR / C-V2X Uplink: 3.52 MB payload (11 CKKS vectors) transmits in 0.19–0.56 s over 50–150 Mbps links.", font_size=Pt(13.0))
    add_bullet_point(tf11_c1, "RSU Server Aggregation: Aggregates 5 vehicles across 44,164 weights in ~5.2 ms on multi-core CPU (6.8s single-threaded).", font_size=Pt(13.0))

    # Column 2: Cryptographic Viability & Parity Verification (Left: 6.75 in, Width: 5.65 in)
    tb11_col2 = s11.shapes.add_textbox(Inches(6.75), Inches(1.80), Inches(5.65), Inches(4.30))
    tf11_c2 = tb11_col2.text_frame
    tf11_c2.word_wrap = True
    
    add_section_header(tf11_c2, "Cryptographic Viability of Function F", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf11_c2, "Plaintext Scalar Division: Division α_k = n_k / N is evaluated in ordinary 64-bit plaintext floating-point arithmetic (< 1 µs), bypassing expensive homomorphic ciphertext division.", font_size=Pt(13.0))
    add_bullet_point(tf11_c2, "Zero Ciphertext–Ciphertext Multiplications: RSU computes only scalar-ciphertext mult (α_k ⊙ c_k) and ciphertext addition ∑(α_k ⊙ c_k).", font_size=Pt(13.0))
    add_bullet_point(tf11_c2, "Zero Multiplicative Depth Exhaustion: Noise budget remains intact across all federated rounds without requiring bootstrapping.", font_size=Pt(13.0))

    add_section_header(tf11_c2, "Experimental Accuracy & Parity Bounds", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf11_c2, "Bitwise Numerical Bound: ε_{agg} = || Dec_{sk}(c_F) − Δw_{plaintext} ||_{∞} = 8.174 × 10^{-7}.", font_size=Pt(13.0))
    add_bullet_point(tf11_c2, "Accuracy Preservation: Plaintext 99.83% (IID) / 99.78% (Non-IID) vs. CKKS Encrypted 99.83% (IID) / 99.78% (Non-IID) — confirmed exact 0.0000% homomorphic accuracy gap!", font_size=Pt(13.0))
    add_bullet_point(tf11_c2, "Engineering Boundary: Vehicles transmit record count n_k in plaintext; reveals zero information on weights, telemetry, or attack specifics.", font_size=Pt(13.0))

    # =========================================================================
    # 4. POLISH BOUNDS ON ALL OTHER SLIDES (ENSURE Y <= 6.18 INCHES)
    # =========================================================================
    # Slide 3: Scale Picture 6 so it ends before footer (Y <= 6.18 in)
    s3 = prs.slides[2]
    for shp in s3.shapes:
        if shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
            orig_aspect = shp.width / shp.height
            shp.height = Inches(4.24)
            shp.width = int(Inches(4.24) * orig_aspect)
            
    # Slide 4: Set text box height to 3.9 in
    s4 = prs.slides[3]
    for shp in s4.shapes:
        if shp != s4.shapes.title and shp.has_text_frame:
            shp.height = Inches(3.90)

    # Slide 5: Set text box height to 4.0 in
    s5 = prs.slides[4]
    for shp in s5.shapes:
        if shp != s5.shapes.title and shp.has_text_frame:
            shp.height = Inches(4.00)

    # Slide 9: Polish bounds on Downstream Model Reconstruction
    s9 = prs.slides[8]
    for shp in s9.shapes:
        if shp != s9.shapes.title and shp.has_text_frame:
            shp.top = Inches(1.80)
            shp.height = Inches(4.25)
            for p in shp.text_frame.paragraphs:
                p.space_before = Pt(3)
                p.space_after = Pt(2)
                for r in p.runs:
                    if r.font.size and r.font.size > Pt(15):
                        r.font.size = Pt(15.0)
                    elif r.font.size:
                        r.font.size = Pt(13.5)

    # Slide 10: Polish Table 2 bounds on Homomorphic Functions
    s10 = prs.slides[9]
    for shp in s10.shapes:
        if shp.has_table:
            shp.top = Inches(1.85)
            for row in shp.table.rows:
                row.height = Inches(0.80)

    # Save to all target locations
    for op in out_paths:
        try:
            prs.save(op)
            print(f"SUCCESS: Saved updated presentation to {op}")
        except Exception as e:
            print(f"Notice: Could not save to {op} ({e})")

if __name__ == "__main__":
    apply_deck_updates()

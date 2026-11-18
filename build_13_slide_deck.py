import os, pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

def build_13_slide_presentation():
    src_path = "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
    out_paths = [
        "Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx",
        "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture_13Slides.pptx",
        "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
    ]
    
    prs = pptx.Presentation(src_path)
    print(f"Loaded {src_path} with initial {len(prs.slides)} slides.")
    
    DARK_NAVY = RGBColor(15, 30, 65)
    BLUE_ACCENT = RGBColor(30, 58, 138)
    TEXT_DARK = RGBColor(35, 40, 50)
    
    def render_runs(paragraph, text, base_font_size=Pt(13.5), default_bold=False):
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

    def add_section_header(tf, header_text, space_before=5, font_size=Pt(15.0)):
        p = tf.add_paragraph() if len(tf.paragraphs[0].text) > 0 else tf.paragraphs[0]
        p.space_before = Pt(space_before)
        p.space_after = Pt(2)
        run = p.add_run()
        run.text = header_text
        run.font.name = "Segoe UI"
        run.font.size = font_size
        run.font.bold = True
        run.font.color.rgb = DARK_NAVY

    def add_bullet_point(tf, bullet_text, indent=0, space_before=2, space_after=2, font_size=Pt(13.0)):
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

    # -------------------------------------------------------------------------
    # STEP 1: Add 2 extra slides using Layout 5 ("Title Only")
    # -------------------------------------------------------------------------
    # Initial slides: 11
    # We need:
    # 1 extra slide after slide 7 (for Datasets & Fleet Simulation) -> becomes slide 8
    # 1 extra slide after slide 11 (for Cryptographic Viability & Parity) -> becomes slide 13
    
    new_s8 = prs.slides.add_slide(prs.slide_layouts[5])  # appended at index 11
    new_s13 = prs.slides.add_slide(prs.slide_layouts[5]) # appended at index 12
    
    # Reorder slides using XML sldIdLst:
    # Move new_s8 to position index 7 (Slide 8)
    sldIdLst = prs.slides._sldIdLst
    sldIdLst.insert(7, sldIdLst[-2]) # insert the first new slide at index 7
    # Now new_s13 is naturally at the end (Slide 13)
    
    print(f"Presentation now has {len(prs.slides)} slides.")

    # -------------------------------------------------------------------------
    # STEP 2: Update Slide 2: Agenda (Content)
    # -------------------------------------------------------------------------
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
                "5. ChebyKAN Weight Representation & Edge Formulation",
                "6. Vehicular Datasets, Feature Extraction & Fleet Simulation",
                "7. CKKS SIMD Slot Vectorization: Packing 44,164 Weights into 11 Chunks",
                "8. Downstream Model Reconstruction & Multi-Round Scale Refresh",
                "9. Few more Homomorphic Functions which can be Evaluated by Server",
                "10. Real-Time Automotive Edge Feasibility & Hardware Budgets",
                "11. Cryptographic Viability of Function F & Precision Parity"
            ]
            for idx, item in enumerate(agenda_items):
                p = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
                p.space_before = Pt(3)
                p.space_after = Pt(2)
                run = p.add_run()
                run.text = item
                run.font.name = "Segoe UI"
                run.font.size = Pt(15.0)
                run.font.color.rgb = TEXT_DARK
            break

    # -------------------------------------------------------------------------
    # STEP 3: Setup Slide 7: ChebyKAN Weight Representation & Edge Formulation
    # -------------------------------------------------------------------------
    s7 = prs.slides[6]
    s7.shapes.title.text = "ChebyKAN Weight Representation & Edge Formulation"
    
    # Remove existing shapes on slide 7 except title
    for shp in [s for s in s7.shapes if s != s7.shapes.title]:
        s7.shapes._spTree.remove(shp._element)
        
    tb7_c1 = s7.shapes.add_textbox(Inches(0.92), Inches(1.80), Inches(5.60), Inches(4.30))
    tf7_c1 = tb7_c1.text_frame
    tf7_c1.word_wrap = True
    
    add_section_header(tf7_c1, "How Weights are Represented in ChebyKAN", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf7_c1, "Connection Curves: Standard MLPs use scalar multipliers (w · x). ChebyKAN replaces each connection with a learnable Chebyshev polynomial curve: φ(x) = w_b · x + ∑_{k=0}^{4} c_k · T_k(x_{norm})", font_size=Pt(13.0))
    add_bullet_point(tf7_c1, "6 Learnable Parameters per Edge: 1 base linear weight (w_b) captures baseline linear trends + 5 Chebyshev coefficients (c_0, c_1, c_2, c_3, c_4) shape non-linear attack boundaries.", font_size=Pt(13.0))
    add_bullet_point(tf7_c1, "Orthonormal Chebyshev Basis: Uses T_0=1, T_1=x, T_2=2x^2-1, T_3=4x^3-3x, T_4=8x^4-8x^2+1 defined over normalized range [-1, 1].", font_size=Pt(13.0))

    add_section_header(tf7_c1, "Native Cryptographic Compatibility (Why ChebyKAN?)", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf7_c1, "Eliminates Non-Polynomial ReLUs: Traditional DNNs rely on ReLU/Sigmoid activations, which cannot be computed under CKKS without expensive high-degree polynomial approximations.", font_size=Pt(13.0))
    add_bullet_point(tf7_c1, "Natively Algebraic: ChebyKAN non-linearities are purely algebraic polynomial operations, perfectly matching CKKS homomorphic additions and scalar multiplications.", font_size=Pt(13.0))

    tb7_c2 = s7.shapes.add_textbox(Inches(6.75), Inches(1.80), Inches(5.65), Inches(4.30))
    tf7_c2 = tb7_c2.text_frame
    tf7_c2.word_wrap = True
    
    add_section_header(tf7_c2, "Network Topology & Exact Parameter Count", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf7_c2, "ChebyKAN Topology: 46 Inputs -> 64 Hidden -> 64 Hidden -> 4 Classes (7,296 total edges)", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Layer 1 (46 -> 64, 2,944 edges): 14,720 Cheby weights (2,944 × 5) + 2,944 base weights + 64 biases + 128 LayerNorm (γ, β) = 17,856 parameters", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Layer 2 (64 -> 64, 4,096 edges): 20,480 Cheby weights (4,096 × 5) + 4,096 base weights + 64 biases + 128 LayerNorm (γ, β) = 24,768 parameters", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Layer 3 (64 -> 4, 256 edges): 1,280 Cheby weights (256 × 5) + 256 base weights + 4 biases = 1,540 parameters", font_size=Pt(13.0))
    
    add_section_header(tf7_c2, "4 Target Classes & 44,164 Parameters", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf7_c2, "4 Attack Classes: Normal (Benign), DoS (Flooding), Replay, Spoofing (Gear/RPM)", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Exact Parameters: 17,856 (L1) + 24,768 (L2) + 1,540 (L3) = EXACTLY 44,164 Parameters", font_size=Pt(13.0))
    add_bullet_point(tf7_c2, "Breakdown: 36,480 Chebyshev polynomial weights + 7,296 base linear weights + 388 biases & LayerNorm parameters.", font_size=Pt(13.0))

    # -------------------------------------------------------------------------
    # STEP 4: Setup Slide 8: Vehicular Datasets, Feature Extraction & Fleet Simulation
    # -------------------------------------------------------------------------
    s8 = prs.slides[7]
    s8.shapes.title.text = "Vehicular Datasets, Feature Extraction & Fleet Simulation"
    
    # Remove existing shapes except title
    for shp in [s for s in s8.shapes if s != s8.shapes.title]:
        s8.shapes._spTree.remove(shp._element)
        
    tb8_c1 = s8.shapes.add_textbox(Inches(0.92), Inches(1.80), Inches(5.60), Inches(4.30))
    tf8_c1 = tb8_c1.text_frame
    tf8_c1.word_wrap = True
    
    add_section_header(tf8_c1, "4 Heterogeneous Vehicular Datasets", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf8_c1, "4 Standalone Benchmarks: Evaluated independently as separate real-world attack vectors:", font_size=Pt(13.0))
    add_bullet_point(tf8_c1, "Car-Hacking: Real in-vehicle CAN bus traffic (5 attack classes: Normal, DoS, Fuzzy, RPM, Gear).", indent=1, font_size=Pt(12.5))
    add_bullet_point(tf8_c1, "CAN-VTC: CAN bus DoS, fuzzy, and impersonation attacks (4 classes).", indent=1, font_size=Pt(12.5))
    add_bullet_point(tf8_c1, "CICIDS-2017: Connected telematics & external network intrusion (2 classes).", indent=1, font_size=Pt(12.5))
    add_bullet_point(tf8_c1, "VeReMi: V2X wireless communication beacon attacks (2 classes).", indent=1, font_size=Pt(12.5))

    add_section_header(tf8_c1, "Unified 46-D Statistical Feature Extraction", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf8_c1, "46-D Numerical Vector: Converts raw asynchronous CAN frames into 46 statistical features.", font_size=Pt(13.0))
    add_bullet_point(tf8_c1, "Extracted Metrics: Inter-arrival timing intervals, arbitration ID frequencies, byte column transition counters, and Shannon payload entropy.", font_size=Pt(13.0))
    add_bullet_point(tf8_c1, "Edge Privacy: Zero raw CAN payloads or vehicle messages are transmitted outside the vehicle.", font_size=Pt(13.0))

    tb8_c2 = s8.shapes.add_textbox(Inches(6.75), Inches(1.80), Inches(5.65), Inches(4.30))
    tf8_c2 = tb8_c2.text_frame
    tf8_c2.word_wrap = True
    
    add_section_header(tf8_c2, "Fleet Simulation Mode (Non-IID Sharding)", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf8_c2, "Dirichlet Allocation (α = 0.3): Shards data across N = 10 simulated ECU nodes.", font_size=Pt(13.0))
    add_bullet_point(tf8_c2, "Realistic Fleet Dynamics: Accurately mirrors real-world driving fleets where vehicles experience localized, unbalanced attack bursts (e.g., one ECU sees 80% DoS while another sees normal driving).", font_size=Pt(13.0))
    add_bullet_point(tf8_c2, "Evaluates Client Drift: Robustly tests federated convergence under harsh statistical skew.", font_size=Pt(13.0))

    add_section_header(tf8_c2, "4 Target Classes & 44,164 Parameters", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf8_c2, "4 Attack Classes: Normal (Benign), DoS (Flooding), Replay, Spoofing (Gear/RPM)", font_size=Pt(13.0))
    add_bullet_point(tf8_c2, "ChebyKAN Topology: 46 Inputs -> 64 Hidden -> 64 Hidden -> 4 Classes", font_size=Pt(13.0))
    add_bullet_point(tf8_c2, "Exact Parameters: 17,856 (L1) + 24,768 (L2) + 1,540 (L3) = EXACTLY 44,164 Parameters", font_size=Pt(13.0))

    # -------------------------------------------------------------------------
    # STEP 5: Setup Slide 12: Real-Time Automotive Edge Feasibility & Hardware Budgets
    # -------------------------------------------------------------------------
    s12 = prs.slides[11]
    s12.shapes.title.text = "Real-Time Automotive Edge Feasibility & Hardware Budgets"
    
    # Remove existing shapes except title
    for shp in [s for s in s12.shapes if s != s12.shapes.title]:
        s12.shapes._spTree.remove(shp._element)
        
    tb12_c1 = s12.shapes.add_textbox(Inches(0.92), Inches(1.80), Inches(5.60), Inches(4.30))
    tf12_c1 = tb12_c1.text_frame
    tf12_c1.word_wrap = True
    
    add_section_header(tf12_c1, "Two Decoupled Processing Pipelines", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf12_c1, "Path A: Real-Time IDS Detection (Critical Path — Every 10 ms):", font_size=Pt(13.0))
    add_bullet_point(tf12_c1, "Directly inspects in-vehicle CAN bus traffic and extracts 46 statistical features.", indent=1, font_size=Pt(12.5))
    add_bullet_point(tf12_c1, "Executes ChebyKAN Plaintext Inference locally on ECU in < 1.5 ms per sample.", indent=1, font_size=Pt(12.5))
    add_bullet_point(tf12_c1, "Zero cryptographic overhead during driving; blocks attacks within 10.0 ms CAN deadline (85% safety margin).", indent=1, font_size=Pt(12.5))
    
    add_bullet_point(tf12_c1, "Path B: Periodic FL Update (Background Path — Every 15–60 mins):", font_size=Pt(13.0))
    add_bullet_point(tf12_c1, "Trains local model on buffered logs & computes weight delta: Δw_k = w_k(t+1) − w(t).", indent=1, font_size=Pt(12.5))
    add_bullet_point(tf12_c1, "Encrypts update via CKKS in ≈ 150 ms during vehicle idling, parking, or EV charging.", indent=1, font_size=Pt(12.5))
    add_bullet_point(tf12_c1, "Uploads 3.52 MB ciphertext payload over 5G NR / C-V2X in 0.19–0.56 s.", indent=1, font_size=Pt(12.5))

    tb12_c2 = s12.shapes.add_textbox(Inches(6.75), Inches(1.80), Inches(5.65), Inches(4.30))
    tf12_c2 = tb12_c2.text_frame
    tf12_c2.word_wrap = True
    
    add_section_header(tf12_c2, "Quantitative Hardware Footprint on Automotive ECUs", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf12_c2, "Model Size (d): 44,164 parameters (174 KB plaintext) — ultra-compact compared to multi-million parameter deep networks.", font_size=Pt(13.0))
    add_bullet_point(tf12_c2, "ECU RAM Overhead: < 20 MB TenSEAL memory footprint (fits comfortably on standard 1–4 GB automotive gateway ECUs).", font_size=Pt(13.0))
    add_bullet_point(tf12_c2, "5G NR / C-V2X Uplink: 3.52 MB payload (11 CKKS vectors × 320 KB) transmits in 0.19–0.56 s over standard 50–150 Mbps cellular channels.", font_size=Pt(13.0))
    add_bullet_point(tf12_c2, "RSU Server Aggregation: Aggregates 5 vehicles across 44,164 weights in ≈ 5.2 ms on multi-core CPU (6.8s single-threaded).", font_size=Pt(13.0))
    add_bullet_point(tf12_c2, "Feasibility Verdict: In an FL round occurring every 15–60 minutes, an upload transmission of 1–2 seconds is well within vehicular communication budgets.", font_size=Pt(13.0))

    # -------------------------------------------------------------------------
    # STEP 6: Setup Slide 13: Cryptographic Viability of Function F & Precision Parity
    # -------------------------------------------------------------------------
    s13 = prs.slides[12]
    s13.shapes.title.text = "Cryptographic Viability of Function F & Precision Parity"
    
    # Remove existing shapes except title
    for shp in [s for s in s13.shapes if s != s13.shapes.title]:
        s13.shapes._spTree.remove(shp._element)
        
    tb13_c1 = s13.shapes.add_textbox(Inches(0.92), Inches(1.80), Inches(5.60), Inches(4.30))
    tf13_c1 = tb13_c1.text_frame
    tf13_c1.word_wrap = True
    
    add_section_header(tf13_c1, "Cryptographic Viability of Function F", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf13_c1, "Plaintext Scalar Division: Aggregation fractions α_k = n_k / N are computed in ordinary 64-bit plaintext float arithmetic (< 1 µs), bypassing expensive homomorphic ciphertext division entirely.", font_size=Pt(13.0))
    add_bullet_point(tf13_c1, "Zero Ciphertext–Ciphertext Multiplications: RSU evaluates only scalar-ciphertext multiplication (α_k ⊙ c_k) and ciphertext addition ∑(α_k ⊙ c_k).", font_size=Pt(13.0))
    add_bullet_point(tf13_c1, "Zero Multiplicative Depth Exhaustion: Scalar multiplication does not consume polynomial modulus levels; noise budget remains intact across all federated rounds without bootstrapping.", font_size=Pt(13.0))

    tb13_c2 = s13.shapes.add_textbox(Inches(6.75), Inches(1.80), Inches(5.65), Inches(4.30))
    tf13_c2 = tb13_c2.text_frame
    tf13_c2.word_wrap = True
    
    add_section_header(tf13_c2, "Experimental Parity & Numerical Bounds", space_before=0, font_size=Pt(15.0))
    add_bullet_point(tf13_c2, "Bitwise Numerical Precision: ε_{agg} = || Dec_{sk}(c_F) − Δw_{plaintext} ||_{∞} = 8.174 × 10^{-7}.", font_size=Pt(13.0))
    add_bullet_point(tf13_c2, "Accuracy Preservation: Plaintext 99.83% (IID) / 99.78% (Non-IID) vs. CKKS Encrypted 99.83% (IID) / 99.78% (Non-IID) — confirmed exact 0.0000% homomorphic accuracy gap!", font_size=Pt(13.0))
    
    add_section_header(tf13_c2, "Engineering Boundaries & Practical Assumptions", space_before=6, font_size=Pt(15.0))
    add_bullet_point(tf13_c2, "Plaintext Sample Count (n_k): Vehicles transmit n_k in plaintext alongside c_k; RSU learns only sample count, revealing zero information about model weights or CAN traffic.", font_size=Pt(13.0))
    add_bullet_point(tf13_c2, "Key Distribution Model: Authorized vehicles hold shared secret key sk; RSU holds only public evaluation key pk (sk = ∅). Production deployments can extend to Threshold CKKS (t-CKKS).", font_size=Pt(13.0))

    # -------------------------------------------------------------------------
    # STEP 7: Polish Bounds on Other Slides (Slides 3, 4, 5, 9, 10, 11)
    # -------------------------------------------------------------------------
    # Slide 3 (Picture 6)
    s3 = prs.slides[2]
    for shp in s3.shapes:
        if shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
            orig_aspect = shp.width / shp.height
            shp.height = Inches(4.24)
            shp.width = int(Inches(4.24) * orig_aspect)
            
    # Slide 4
    s4 = prs.slides[3]
    for shp in s4.shapes:
        if shp != s4.shapes.title and shp.has_text_frame:
            shp.height = Inches(3.90)

    # Slide 5
    s5 = prs.slides[4]
    for shp in s5.shapes:
        if shp != s5.shapes.title and shp.has_text_frame:
            shp.height = Inches(4.00)

    # Slide 10: Downstream Model Reconstruction
    s10 = prs.slides[9]
    for shp in s10.shapes:
        if shp != s10.shapes.title and shp.has_text_frame:
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

    # Slide 11: Homomorphic Functions Table
    s11 = prs.slides[10]
    for shp in s11.shapes:
        if shp.has_table:
            shp.top = Inches(1.85)
            for row in shp.table.rows:
                row.height = Inches(0.80)

    # Save to all target locations
    for op in out_paths:
        try:
            prs.save(op)
            print(f"SUCCESS: Saved updated 13-slide presentation to {op}")
        except Exception as e:
            print(f"Notice: Could not save to {op} ({e})")

if __name__ == "__main__":
    build_13_slide_presentation()

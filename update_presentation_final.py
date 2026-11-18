import os, pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

def update_presentation():
    src_path = "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
    out_paths = [
        "Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx",
        "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx",
        "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture 9 50.pptx"
    ]
    
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source file not found at {src_path}")
        
    prs = pptx.Presentation(src_path)
    print(f"Loaded {src_path} with {len(prs.slides)} slides.")
    
    DARK_NAVY = RGBColor(15, 30, 65)
    BLUE_ACCENT = RGBColor(30, 58, 138)
    TEXT_DARK = RGBColor(35, 40, 50)
    
    def render_runs(paragraph, text, base_font_size=Pt(15.5), default_bold=False):
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

    def add_section_header(tf, header_text, space_before=8, font_size=Pt(17.5)):
        p = tf.add_paragraph() if len(tf.paragraphs[0].text) > 0 else tf.paragraphs[0]
        p.space_before = Pt(space_before)
        p.space_after = Pt(2)
        run = p.add_run()
        run.text = header_text
        run.font.name = "Segoe UI"
        run.font.size = font_size
        run.font.bold = True
        run.font.color.rgb = DARK_NAVY

    def add_bullet_point(tf, bullet_text, indent=0, space_before=3, space_after=2, font_size=Pt(15.0)):
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
                "5. Dataset Unification, Fleet Simulation & 44,164 Parameters",
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
                run.font.size = Pt(16.5)
                run.font.color.rgb = TEXT_DARK
            break

    # =========================================================================
    # 2. UPDATE SLIDE 7: DATASET UNIFICATION, FLEET MODE & 44,164 PARAMETERS
    # =========================================================================
    s7 = prs.slides[6]
    s7.shapes.title.text = "Dataset Unification, Fleet Simulation & 44,164 Parameters"
    
    # Remove existing non-title shapes on slide 7
    shapes_to_remove = [shp for shp in s7.shapes if shp != s7.shapes.title]
    for shp in shapes_to_remove:
        s7.shapes._spTree.remove(shp._element)
        
    # Embed Dataset Unification Diagram on Left
    diag_ds_path = "diagram_dataset_unification_fleet.png"
    if os.path.exists(diag_ds_path):
        s7.shapes.add_picture(diag_ds_path, Inches(0.92), Inches(1.80), width=Inches(5.30), height=Inches(4.30))
        
    # Add concise text box on Right
    tb7 = s7.shapes.add_textbox(Inches(6.40), Inches(1.80), Inches(6.15), Inches(4.30))
    tf7 = tb7.text_frame
    tf7.word_wrap = True
    
    add_section_header(tf7, "4 Heterogeneous Datasets Unified to 46-D", space_before=0)
    add_bullet_point(tf7, "Datasets Unified: Car-Hacking (5 classes), CAN-VTC (4 classes), CICIDS-2017 (15 classes), VeReMi (5 classes)")
    add_bullet_point(tf7, "Unified 46-D Feature Vector: Sliding window W=29 extracts timing, byte column transitions, and Shannon entropy")

    add_section_header(tf7, "Fleet Simulation Mode (Non-IID Sharding)", space_before=6)
    add_bullet_point(tf7, "Dirichlet Allocation (α = 0.3): Shards data unevenly across simulated vehicle nodes (N = 10 ECUs)")
    add_bullet_point(tf7, "Mirrors real-world fleet mobility: vehicles experience localized bursts of cyberattacks and benign driving")

    add_section_header(tf7, "4 Target Classes & 44,164 Parameters", space_before=6)
    add_bullet_point(tf7, "4 Attack Classes: Normal (Benign), DoS (Flooding), Replay, Spoofing (Gear/RPM)")
    add_bullet_point(tf7, "ChebyKAN Topology: 46 Inputs -> 64 Hidden -> 64 Hidden -> 4 Classes")
    add_bullet_point(tf7, "Exact Parameters: 17,856 (L1) + 24,768 (L2) + 1,540 (L3) = EXACTLY 44,164 Parameters")

    # =========================================================================
    # 3. UPDATE SLIDE 11: AUTOMOTIVE EDGE FEASIBILITY (MORE DIAGRAMS, LESS TEXT!)
    # =========================================================================
    s11 = prs.slides[10]
    s11.shapes.title.text = "Automotive Edge Feasibility & Hardware Benchmarks"
    
    # Remove existing non-title shapes on slide 11
    shapes_to_remove11 = [shp for shp in s11.shapes if shp != s11.shapes.title]
    for shp in shapes_to_remove11:
        s11.shapes._spTree.remove(shp._element)
        
    # Embed Feasibility Diagram on Left
    diag_feas_path = "diagram_edge_feasibility.png"
    if os.path.exists(diag_feas_path):
        s11.shapes.add_picture(diag_feas_path, Inches(0.92), Inches(1.80), width=Inches(5.40), height=Inches(4.30))
        
    # Add concise text box on Right
    tb11 = s11.shapes.add_textbox(Inches(6.55), Inches(1.80), Inches(6.00), Inches(4.30))
    tf11 = tb11.text_frame
    tf11.word_wrap = True
    
    add_section_header(tf11, "Real-World Automotive Edge Budgets", space_before=0)
    add_bullet_point(tf11, "Real-Time Inference: < 1.5 ms per window (CAN safety deadline is 10.0 ms — 85% safety margin)")
    add_bullet_point(tf11, "Periodic FL Encryption: ~150 ms on ECU (runs strictly when parked or charging, never during driving)")
    add_bullet_point(tf11, "5G NR Uplink Time: 3.52 MB (11 chunks) uploads in < 0.4s over standard 50–150 Mbps links")
    add_bullet_point(tf11, "ECU RAM Footprint: < 20 MB TenSEAL memory overhead (automotive gateways possess 1–4 GB RAM)")

    add_section_header(tf11, "Zero Cryptographic Accuracy Loss", space_before=8)
    add_bullet_point(tf11, "Plaintext Baseline Accuracy: 99.83 %  |  Macro F1: 0.9972")
    add_bullet_point(tf11, "CKKS Encrypted Accuracy: 99.83 %  |  Macro F1: 0.9972")
    add_bullet_point(tf11, "Bitwise Numerical Bound: ε_{agg} = || Dec_{sk}(c_{F}) − Δw_{unencrypted} ||_{∞} = 8.174 × 10^{-7}")
    add_bullet_point(tf11, "Exact Equivalence: Confirmed 0.0000% homomorphic accuracy gap under 128-bit post-quantum security!")

    # =========================================================================
    # 4. POLISH BOUNDS ON SLIDES 3, 4, 5 (ENSURE Y <= 6.18 INCHES)
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

    # Save to all target locations
    for op in out_paths:
        try:
            prs.save(op)
            print(f"SUCCESS: Saved updated presentation to {op}")
        except Exception as e:
            print(f"Notice: Could not save to {op} ({e})")

if __name__ == "__main__":
    update_presentation()

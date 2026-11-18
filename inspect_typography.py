import sys, pptx

sys.stdout.reconfigure(encoding='utf-8')
prs = pptx.Presentation(r'2nd_meeting_ChebyKAN.pptx')

for idx in [2, 3, 11, 13]:
    slide = prs.slides[idx]
    print(f"\n=================== SLIDE {idx+1} ===================")
    print(f"Slide layout name: {slide.slide_layout.name}")
    for shape in slide.shapes:
        print(f"\n--- Shape: '{shape.name}' ---")
        print(f"  Pos: Left={shape.left/914400:.2f}, Top={shape.top/914400:.2f}, W={shape.width/914400:.2f}, H={shape.height/914400:.2f}")
        if shape.has_text_frame:
            tf = shape.text_frame
            print(f"  Margins: L={tf.margin_left/914400:.2f}, R={tf.margin_right/914400:.2f}, T={tf.margin_top/914400:.2f}, B={tf.margin_bottom/914400:.2f}")
            print(f"  WordWrap: {tf.word_wrap}")
            for p_i, p in enumerate(tf.paragraphs):
                p_text = ''.join([r.text for r in p.runs]) if p.runs else p.text
                if not p_text.strip():
                    continue
                runs_detail = []
                for r in p.runs:
                    fn = r.font.name
                    fs = r.font.size.pt if r.font.size else None
                    b = r.font.bold
                    c = r.font.color.rgb if (r.font.color and hasattr(r.font.color, 'rgb')) else None
                    runs_detail.append(f"({r.text[:30]!r}, font={fn}, sz={fs}, b={b}, c={c})")
                print(f"    P{p_i} [level={p.level}, align={p.alignment}, sp_before={p.space_before.pt if p.space_before else None}, sp_after={p.space_after.pt if p.space_after else None}]:")
                print(f"       Runs: {runs_detail}")

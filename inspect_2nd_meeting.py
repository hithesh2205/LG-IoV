import sys, pptx

sys.stdout.reconfigure(encoding='utf-8')
prs = pptx.Presentation(r'2nd_meeting_ChebyKAN.pptx')
print(f'Total Slides: {len(prs.slides)}')

for i in range(len(prs.slides)):
    slide = prs.slides[i]
    print(f'\n=== SLIDE {i+1} ===')
    for shape in slide.shapes:
        left = shape.left / 914400.0 if shape.left else 0
        top = shape.top / 914400.0 if shape.top else 0
        w = shape.width / 914400.0 if shape.width else 0
        h = shape.height / 914400.0 if shape.height else 0
        txt_lines = []
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                t = p.text.strip()
                if t:
                    txt_lines.append(f"[{p.font.size.pt if (p.font and p.font.size) else 'def'}pt] {t[:70]}")
        print(f"  Shape '{shape.name}' ({shape.shape_type}) [L:{left:.2f}, T:{top:.2f}, W:{w:.2f}, H:{h:.2f}] Lines: {len(txt_lines)}")
        for l in txt_lines[:4]:
            print(f"    {l}")

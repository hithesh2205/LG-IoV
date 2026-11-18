import sys, pptx

sys.stdout.reconfigure(encoding='utf-8')
p_root = "Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
p_950 = "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture 9 50.pptx"

prs_root = pptx.Presentation(p_root)
prs_950 = pptx.Presentation(p_950)

print(f"Root slides: {len(prs_root.slides)}, 9:50 slides: {len(prs_950.slides)}")

for idx in range(min(len(prs_root.slides), len(prs_950.slides))):
    s_r = prs_root.slides[idx]
    s_9 = prs_950.slides[idx]
    
    t_r = s_r.shapes.title.text if s_r.shapes.title else ""
    t_9 = s_9.shapes.title.text if s_9.shapes.title else ""
    
    text_r = " ".join([p.text for shp in s_r.shapes if shp.has_text_frame for p in shp.text_frame.paragraphs])
    text_9 = " ".join([p.text for shp in s_9.shapes if shp.has_text_frame for p in shp.text_frame.paragraphs])
    
    if t_r != t_9 or text_r != text_9:
        print(f"\n--- Difference on Slide {idx+1} ---")
        print(f"Title Root: {t_r}")
        print(f"Title 9:50: {t_9}")
        if text_r != text_9:
            print("Text differs!")
            # print snippets
            print(f"Root text len: {len(text_r)}, 9:50 text len: {len(text_9)}")
            if idx == 1: # Agenda
                print("Root agenda:\n", text_r[:200])
                print("9:50 agenda:\n", text_9[:200])
            elif idx == 6: # Slide 7
                print("Root S7:\n", text_r[:200])
                print("9:50 S7:\n", text_9[:200])
            elif idx == 10: # Slide 11
                print("Root S11:\n", text_r[:200])
                print("9:50 S11:\n", text_9[:200])
    else:
        print(f"Slide {idx+1}: Identical text")

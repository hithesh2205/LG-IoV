import sys, pptx

sys.stdout.reconfigure(encoding='utf-8')
p_final = "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
p_root = "Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"

prs_final = pptx.Presentation(p_final)
prs_root = pptx.Presentation(p_root)

print(f"Final slides: {len(prs_final.slides)}, Root slides: {len(prs_root.slides)}")

for idx in range(min(len(prs_final.slides), len(prs_root.slides))):
    s_f = prs_final.slides[idx]
    s_r = prs_root.slides[idx]
    
    t_f = s_f.shapes.title.text if s_f.shapes.title else ""
    t_r = s_r.shapes.title.text if s_r.shapes.title else ""
    
    text_f = "\n".join([f"[{shp.name}]: {shp.text}" for shp in s_f.shapes if shp.has_text_frame])
    text_r = "\n".join([f"[{shp.name}]: {shp.text}" for shp in s_r.shapes if shp.has_text_frame])
    
    pics_f = [shp.name for shp in s_f.shapes if shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE]
    pics_r = [shp.name for shp in s_r.shapes if shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE]
    
    if t_f != t_r or text_f != text_r or pics_f != pics_r:
        print(f"\n=================== Difference on Slide {idx+1} ===================")
        print(f"Title Final (22:06): {t_f}")
        print(f"Title Root  (21:58): {t_r}")
        print(f"Pics Final: {pics_f}, Pics Root: {pics_r}")
        if text_f != text_r:
            print(f"--- TEXT IN FINAL (22:06) ---:\n{text_f}")
            print(f"--- TEXT IN ROOT  (21:58) ---:\n{text_r}")
    else:
        print(f"Slide {idx+1}: Identical")

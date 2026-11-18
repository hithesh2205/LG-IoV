import sys, pptx

sys.stdout.reconfigure(encoding='utf-8')
p1 = "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture 9 50.pptx"
prs = pptx.Presentation(p1)

for i, s in enumerate(prs.slides):
    title = s.shapes.title.text if s.shapes.title else "No Title"
    print(f"\n=================== SLIDE {i+1}: {title} ===================")
    for shp in s.shapes:
        if shp.has_text_frame:
            print(f"--- Shape: {shp.name} ---")
            for p in shp.text_frame.paragraphs:
                print(f"  {p.text}")
        elif shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
            print(f"--- Picture: {shp.name} ({shp.width/914400:.2f} x {shp.height/914400:.2f} in) ---")

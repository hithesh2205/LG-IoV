import sys, pptx
sys.stdout.reconfigure(encoding='utf-8')

prs = pptx.Presentation("Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx")
print(f"Total slides: {len(prs.slides)}")

for idx, s in enumerate(prs.slides):
    title = s.shapes.title.text if s.shapes.title and s.shapes.title.text else "No Title"
    print(f"\n==================================================")
    print(f"SLIDE {idx+1}: {title}")
    for shp in s.shapes:
        if shp != s.shapes.title and shp.has_text_frame:
            print(f"  Shape '{shp.name}' [Top={shp.top/914400:.2f}, Left={shp.left/914400:.2f}, W={shp.width/914400:.2f}, H={shp.height/914400:.2f}]")
            for p in shp.text_frame.paragraphs:
                txt = p.text.strip()
                if txt:
                    print(f"    {txt}")
        elif shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
            print(f"  PICTURE '{shp.name}' [Top={shp.top/914400:.2f}, Left={shp.left/914400:.2f}, W={shp.width/914400:.2f}, H={shp.height/914400:.2f}]")

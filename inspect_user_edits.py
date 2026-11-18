import sys, pptx
sys.stdout.reconfigure(encoding='utf-8')

for target in [
    "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
]:
    print(f"\n==========================================")
    print(f"Inspecting: {target}")
    prs = pptx.Presentation(target)
    print(f"Total Slides: {len(prs.slides)}")
    for idx, s in enumerate(prs.slides):
        title = s.shapes.title.text if s.shapes.title and s.shapes.title.text else "No Title"
        print(f"\n--- SLIDE {idx+1}: {title} ---")
        for shp in s.shapes:
            if shp.has_text_frame and shp != s.shapes.title:
                lines = [l.strip() for l in shp.text_frame.text.split('\n') if l.strip()]
                print(f"   Shape '{shp.name}' ({len(lines)} lines):")
                for l in lines[:6]:
                    print(f"     {l[:80]}")
            elif shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
                print(f"   [PICTURE: {shp.name}, size: {shp.image.size}]")

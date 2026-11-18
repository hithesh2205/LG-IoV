import os, time, pptx

print("Scanning for PPTX files...")
target_files = [
    "Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx",
    "Presentation/01_Final_Presentations/Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx"
]

for p in target_files:
    if os.path.exists(p):
        mtime = os.path.getmtime(p)
        print(f"\nFile: {p} (Modified: {time.ctime(mtime)}, Size: {os.path.getsize(p)} bytes)")
        try:
            prs = pptx.Presentation(p)
            print(f"Total Slides: {len(prs.slides)}")
            for idx, s in enumerate(prs.slides):
                title = "No Title"
                if s.shapes.title and s.shapes.title.text:
                    title = s.shapes.title.text
                elif len(s.shapes) > 0 and s.shapes[0].has_text_frame:
                    lines = [l.strip() for l in s.shapes[0].text_frame.text.split('\n') if l.strip()]
                    if lines:
                        title = lines[0]
                print(f"  Slide {idx+1}: {title[:70]}")
        except Exception as e:
            print(f"Error reading {p}: {e}")

# Check any other pptx modified in last hour
print("\nOther PPTX files modified in last 2 hours:")
now = time.time()
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.pptx') and not f.startswith('~$'):
            fp = os.path.join(root, f)
            mt = os.path.getmtime(fp)
            if now - mt < 7200:
                print(f"  {time.ctime(mt)} | {fp}")

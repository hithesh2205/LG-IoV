import sys, pptx

sys.stdout.reconfigure(encoding='utf-8')
prs = pptx.Presentation('Presentation_IoV_ChebyKAN_CKKS_Architecture.pptx')
print(f'Total Slides: {len(prs.slides)}')
max_bottom = 0

for idx, s in enumerate(prs.slides):
    slide_max = 0
    title = s.shapes.title.text if s.shapes.title and s.shapes.title.text else 'No Title'
    pics = []
    for shape in s.shapes:
        b = (shape.top + shape.height) / 914400.0 if shape.top and shape.height else 0
        if b > slide_max:
            slide_max = b
        if b > max_bottom:
            max_bottom = b
        if shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
            pics.append(f"{shape.name} ({shape.image.size})")
    print(f"Slide {idx+1:02d}: {title[:55]} [Bottom: {slide_max:.2f} in] Pics: {pics}")

print(f"Overall Max Bottom: {max_bottom:.2f} in (Safe boundary: < 6.25 in)")

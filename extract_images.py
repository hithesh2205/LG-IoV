import os, pptx

prs = pptx.Presentation('2nd_meeting_ChebyKAN.pptx')
os.makedirs('extracted_images', exist_ok=True)
count = 0
for s_idx, s in enumerate(prs.slides):
    for shp in s.shapes:
        if shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
            img = shp.image
            ext = img.content_type.split('/')[-1]
            fname = f"extracted_images/slide_{s_idx+1}_{shp.name}.{ext}"
            with open(fname, 'wb') as f:
                f.write(img.blob)
            print(f"Saved {fname} ({img.size})")
            count += 1
print(f"Total extracted: {count}")

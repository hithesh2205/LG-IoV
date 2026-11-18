import os, pptx
from PIL import Image

diag_dir = 'Presentation/02_Diagrams_and_Flowcharts'
for f in os.listdir(diag_dir):
    p = os.path.join(diag_dir, f)
    if f.endswith('.png') or f.endswith('.jpg'):
        im = Image.open(p)
        print(f, im.size)

prs = pptx.Presentation('2nd_meeting_ChebyKAN.pptx')
print('\nImages in 2nd_meeting_ChebyKAN.pptx:')
for s_idx, s in enumerate(prs.slides):
    for shp in s.shapes:
        if shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
            img = shp.image
            print(f'Slide {s_idx+1}: {shp.name}, size: {img.size}, left: {shp.left/914400:.2f}, top: {shp.top/914400:.2f}, w: {shp.width/914400:.2f}, h: {shp.height/914400:.2f}')

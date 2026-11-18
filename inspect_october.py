import pptx
from pptx.util import Inches

prs = pptx.Presentation('Presentation/01_Final_Presentations/October_5_Progress_Meeting.pptx')
print(f'October_5 slides: {len(prs.slides)}')
for idx, s in enumerate(prs.slides):
    pics = [shp.name for shp in s.shapes if shp.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE]
    print(f'Slide {idx+1}: Title: {s.shapes.title.text if s.shapes.title else "No title"} - Pictures: {pics}')

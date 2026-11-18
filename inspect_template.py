import sys, pptx

sys.stdout.reconfigure(encoding='utf-8')
prs = pptx.Presentation(r'Presentation TEMPLATE.pptx')
print(f'Total Layouts in Template: {len(prs.slide_layouts)}')
for i, l in enumerate(prs.slide_layouts):
    print(f'Layout {i}: {l.name}')
    for s in l.shapes:
        print(f'   Shape: {s.name} ({s.shape_type}) [L:{s.left/914400:.2f}, T:{s.top/914400:.2f}, W:{s.width/914400:.2f}, H:{s.height/914400:.2f}]')

import sys
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

def create_pdf(input_file, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(input_file, 'r', encoding='utf-16') as f:
        text = f.read()

    c = canvas.Canvas(output_file, pagesize=letter)
    width, height = letter
    c.setFont("Courier", 10)

    y = height - 50
    for line in text.split('\n'):
        lines = simpleSplit(line, "Courier", 10, width - 100)
        if not lines:
            y -= 12
        for subline in lines:
            if y < 50:
                c.showPage()
                c.setFont("Courier", 10)
                y = height - 50
            c.drawString(50, y, subline)
            y -= 12

    c.save()

if __name__ == '__main__':
    create_pdf('smoke_test_results.txt', r'D:\LG_IoV\Reports\smoke_test_results.pdf')

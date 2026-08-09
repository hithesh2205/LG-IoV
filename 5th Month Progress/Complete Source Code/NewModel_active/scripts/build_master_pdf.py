"""Build the master project documentation PDF.

    python scripts/build_master_pdf.py "<output_dir>"

Reads live results from ``results/month5_summary.json`` and
``results/ckks_profile_benchmark.json`` so the document always describes the
real state of the project rather than an assumed one. Diagrams are pulled from
the Diagrams folder next to the output directory.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

INK = colors.HexColor("#1a1a2e")
BLUE = colors.HexColor("#2d6cdf")
GREEN = colors.HexColor("#1e9e6a")
RED = colors.HexColor("#d64545")
AMBER = colors.HexColor("#d98324")
GREY = colors.HexColor("#5a6472")
LIGHT = colors.HexColor("#eef2f8")
RULE = colors.HexColor("#c8d2e0")

# ─────────────────────────────────────────────────────────────────────────
# styles
# ─────────────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()

S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontSize=26, leading=32,
                            textColor=INK, spaceAfter=10),
    "subtitle": ParagraphStyle("st", parent=ss["Normal"], fontSize=13.5,
                               leading=19, alignment=TA_CENTER, textColor=GREY),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=19, leading=24,
                         textColor=INK, spaceBefore=16, spaceAfter=9),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=14, leading=18,
                         textColor=BLUE, spaceBefore=13, spaceAfter=6),
    "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontSize=11.5, leading=15,
                         textColor=INK, spaceBefore=10, spaceAfter=4),
    "body": ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.6, leading=14.2,
                           alignment=TA_JUSTIFY, textColor=INK, spaceAfter=6),
    "bullet": ParagraphStyle("bu", parent=ss["BodyText"], fontSize=9.6, leading=14,
                             leftIndent=13, bulletIndent=4, spaceAfter=3,
                             textColor=INK),
    "code": ParagraphStyle("c", parent=ss["Code"], fontSize=8.3, leading=11.5,
                           textColor=INK, backColor=LIGHT, borderPadding=6,
                           leftIndent=6, spaceBefore=4, spaceAfter=8),
    "eq": ParagraphStyle("eq", parent=ss["Normal"], fontSize=10.5, leading=16,
                         alignment=TA_CENTER, textColor=INK, spaceBefore=6,
                         spaceAfter=8, fontName="Times-Italic"),
    "cap": ParagraphStyle("cap", parent=ss["Normal"], fontSize=8.3, leading=11,
                          alignment=TA_CENTER, textColor=GREY, spaceAfter=10),
    "note": ParagraphStyle("n", parent=ss["BodyText"], fontSize=9.2, leading=13.2,
                           textColor=INK, backColor=colors.HexColor("#fff8ec"),
                           borderPadding=7, borderWidth=0.7, borderColor=AMBER,
                           spaceBefore=5, spaceAfter=9),
    "warn": ParagraphStyle("w", parent=ss["BodyText"], fontSize=9.2, leading=13.2,
                           textColor=INK, backColor=colors.HexColor("#fdeeee"),
                           borderPadding=7, borderWidth=0.7, borderColor=RED,
                           spaceBefore=5, spaceAfter=9),
    "ok": ParagraphStyle("o", parent=ss["BodyText"], fontSize=9.2, leading=13.2,
                         textColor=INK, backColor=colors.HexColor("#eefaf4"),
                         borderPadding=7, borderWidth=0.7, borderColor=GREEN,
                         spaceBefore=5, spaceAfter=9),
    "toc": ParagraphStyle("toc", parent=ss["Normal"], fontSize=10, leading=17,
                          textColor=INK),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def B(t):
    return Paragraph(t, S["bullet"], bulletText="•")


def H(t, lvl=1):
    return Paragraph(t, S[f"h{lvl}"])


def tbl(data, widths=None, header=True, fs=8.4, align=None):
    # Plain strings in a reportlab cell do NOT wrap - they clip at the column
    # edge, silently truncating text mid-word. Wrapping every cell in a
    # Paragraph is what makes the column widths behave.
    cell = ParagraphStyle("cell", parent=ss["BodyText"], fontSize=fs,
                          leading=fs + 2.6, textColor=INK, spaceAfter=0,
                          spaceBefore=0)
    cell_h = ParagraphStyle("cellh", parent=cell, fontName="Helvetica-Bold")

    wrapped = []
    for r, row in enumerate(data):
        out = []
        for c in row:
            if isinstance(c, str):
                txt = c.replace("\n", "<br/>")
                out.append(Paragraph(txt, cell_h if (header and r == 0) else cell))
            else:
                out.append(c)
        wrapped.append(out)
    data = wrapped

    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), fs),
        ("LEADING", (0, 0), (-1, -1), fs + 3.2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT)]
    if align:
        for col, a in align.items():
            style.append(("ALIGN", (col, 0), (col, -1), a))
    t.setStyle(TableStyle(style))
    return t


def figure(path: Path, caption: str, width=16.0 * cm):
    if not path.exists():
        return P(f"<i>[diagram missing: {path.name}]</i>")
    from PIL import Image as PILImage  # bundled with matplotlib deps
    try:
        w, h = PILImage.open(path).size
        ratio = h / w
    except Exception:
        ratio = 0.6
    img = Image(str(path), width=width, height=width * ratio)
    return KeepTogether([img, Spacer(1, 3), P(caption, "cap")])


# ─────────────────────────────────────────────────────────────────────────
# data loading
# ─────────────────────────────────────────────────────────────────────────
def load_results():
    p = RESULTS / "month5_summary.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_bench():
    p = RESULTS / "ckks_profile_benchmark.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def results_table(res):
    if not res:
        return P("<i>Sweep results not available at build time.</i>")
    rows = [["Dataset", "Backend", "Accuracy", "Macro F1", "ROC-AUC", "Seeds"]]
    for r in res["results"]:
        if r.get("status") != "ok":
            rows.append([r["dataset"], r["backend"], "FAILED", "-", "-", "-"])
            continue
        rows.append([
            r["dataset"], r["backend"],
            f"{r['accuracy_mean']:.4f} ± {r['accuracy_std']:.4f}",
            f"{r['macro_f1_mean']:.4f} ± {r['macro_f1_std']:.4f}",
            f"{r['roc_auc_mean']:.4f} ± {r['roc_auc_std']:.4f}",
            str(r["n_runs"]),
        ])
    return tbl(rows, [2.6 * cm, 2.0 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm, 1.4 * cm])


# ─────────────────────────────────────────────────────────────────────────
# page furniture
# ─────────────────────────────────────────────────────────────────────────
TITLE = "Privacy-Preserving Collaborative IDS for the Internet of Vehicles"


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, A4[1] - 1.25 * cm, TITLE)
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.25 * cm,
                           "LGSI · Month 5 Master Documentation")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, A4[1] - 1.45 * cm, A4[0] - 2 * cm, A4[1] - 1.45 * cm)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.drawCentredString(A4[0] / 2, 1.05 * cm, f"page {doc.page}")
    canvas.restoreState()


def on_title(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BLUE)
    canvas.rect(0, A4[1] - 1.1 * cm, A4[0], 1.1 * cm, stroke=0, fill=1)
    canvas.setFillColor(INK)
    canvas.rect(0, 0, A4[0], 0.8 * cm, stroke=0, fill=1)
    canvas.restoreState()


def build(out_path: Path, diagrams: Path):
    res = load_results()
    bench = load_bench()

    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Privacy-Preserving Collaborative IDS for IoV — Master Documentation",
        author="LGSI IoV Project",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
    doc.addPageTemplates([
        PageTemplate(id="title", frames=[frame], onPage=on_title),
        PageTemplate(id="body", frames=[frame], onPage=on_page),
    ])

    F = []                      # flowables
    from content import build_content   # noqa: E402  (same folder)
    build_content(F, res, bench, diagrams,
                  helpers=dict(P=P, B=B, H=H, tbl=tbl, figure=figure,
                               results_table=results_table, S=S,
                               Spacer=Spacer, PageBreak=PageBreak,
                               NextPageTemplate=NextPageTemplate, cm=cm))
    doc.build(F)
    print(f"wrote {out_path}  ({out_path.stat().st_size/1024:.0f} KB)")


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    out_dir.mkdir(parents=True, exist_ok=True)
    diagrams = out_dir.parent / "Diagrams"
    build(out_dir / "00_MASTER_DOCUMENTATION.pdf", diagrams)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())

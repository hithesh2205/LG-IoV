"""Inline the current dashboard_data.json into the dashboard.html template and
write the publishable file. Run generate_dashboard_data.py first.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
TEMPLATE_PATH = ROOT / "dashboard_template.html"
OUT_PATH = ROOT / "dashboard.html"
MATH_URL = "https://claude.ai/code/artifact/8a6809b6-50f5-4d1e-9b70-948982812fc9"


def main() -> None:
    data = json.loads((RESULTS_DIR / "dashboard_data.json").read_text(encoding="utf-8"))
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    out = template.replace("__DASHBOARD_DATA__", json.dumps(data)).replace("__MATH_URL__", MATH_URL)
    OUT_PATH.write_text(out, encoding="utf-8")
    print(f"[build_dashboard] Wrote {OUT_PATH} ({data['n_datasets_done']}/{data['n_datasets_total']} datasets)")


if __name__ == "__main__":
    main()

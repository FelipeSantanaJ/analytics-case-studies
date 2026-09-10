"""
build_docs_pdf.py — collate the project docs into two styled PDFs.

    python docs/build_docs_pdf.py

  docs/Voxa+_Documentation.pdf   — the full set (01..09 + walkthrough + DAX + analysis index)
  docs/Voxa+_Summary.pdf         — condensed, < 2 MB (context + DQ + the diagnosis)

markdown -> one HTML (navy headers, zebra tables, callout quotes, mono code, A4) ->
Chrome headless --print-to-pdf.
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ANALYSIS = ROOT / "data_analysis"
CHROME = next((p for p in [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
] if Path(p).exists()), "chrome")

FULL = [
    ("README.md", ROOT / "README.md"),
    ("01 · Business context & KPI framework", DOCS / "01_business_context_kpis.md"),
    ("02 · Data architecture", DOCS / "02_data_architecture.md"),
    ("03 · Data dictionary", DOCS / "03_data_dictionary.md"),
    ("04 · ETL pipeline", DOCS / "04_etl_pipeline.md"),
    ("05 · Data model", DOCS / "05_data_model.md"),
    ("06 · DAX measures", DOCS / "06_dax_measures.md"),
    ("07 · Visual identity", DOCS / "07_visual_identity.md"),
    ("08 · Data quality", DOCS / "08_data_quality.md"),
    ("09 · Report structure", DOCS / "09_report_structure.md"),
    ("Analysis · Root-cause diagnosis (deep dive)", ANALYSIS / "deliverables" / "deep_dive_00_index.md"),
    ("Build walkthrough", DOCS / "walkthrough.md"),
]
SUMMARY = [
    ("README.md", ROOT / "README.md"),
    ("01 · Business context & KPI framework", DOCS / "01_business_context_kpis.md"),
    ("08 · Data quality", DOCS / "08_data_quality.md"),
    ("Root-cause diagnosis (deep dive)", ANALYSIS / "deliverables" / "deep_dive_00_index.md"),
]

CSS = """
@page { size: A4; margin: 18mm 15mm; }
* { box-sizing: border-box; }
body { font: 10.5pt/1.5 "Segoe UI", -apple-system, Roboto, Helvetica, Arial, sans-serif;
  color: #2c2a35; margin: 0; }
h1, h2, h3, h4 { color: #241348; line-height: 1.25; }
h1 { font-size: 20pt; border-bottom: 3px solid #E6A23C; padding-bottom: 5px;
  margin: 0 0 12px; page-break-before: always; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 14pt; margin: 22px 0 8px; border-bottom: 1px solid #E1DEEB; padding-bottom: 3px; }
h3 { font-size: 12pt; margin: 16px 0 6px; }
h4 { font-size: 10.5pt; margin: 12px 0 4px; color: #4B2E83; }
p, li { orphans: 2; widows: 2; }
a { color: #4B2E83; text-decoration: none; }
code { font-family: "Cascadia Code", Consolas, monospace; font-size: 9pt;
  background: #F2F1F7; padding: 1px 4px; border-radius: 3px; }
pre { background: #241348; color: #E9E4F5; padding: 10px 12px; border-radius: 6px;
  font-size: 8.5pt; line-height: 1.45; overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt;
  page-break-inside: avoid; }
th, td { border: 1px solid #E1DEEB; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #241348; color: #F4F2FA; }
tbody tr:nth-child(even) { background: #F7F6FB; }
blockquote { margin: 10px 0; padding: 8px 14px; background: #FBF3E6;
  border-left: 4px solid #E6A23C; color: #6b4e18; }
blockquote p { margin: 4px 0; }
hr { border: 0; border-top: 1px solid #E1DEEB; margin: 18px 0; }
.cover { page-break-after: always; padding-top: 60mm; text-align: center; }
.cover .wm { font-size: 30pt; font-weight: 700; color: #241348; }
.cover .wm b { color: #E6A23C; }
.cover .sub { color: #77738A; margin-top: 8px; font-size: 12pt; }
.cover .meta { color: #A7A2B6; margin-top: 40mm; font-size: 9pt; }
.section-sep { page-break-before: always; }
"""

MD_EXT = ["extra", "sane_lists", "tables", "toc", "admonition"]


def strip_mermaid(md: str) -> str:
    # render mermaid fences as a plain captioned code block (keeps the PDF valid)
    return re.sub(r"```mermaid\n", "```\n", md)


def build(entries, out_name, title, subtitle):
    parts = [f"""<div class="cover"><div class="wm">Voxa<b>+</b></div>
      <div class="sub">{subtitle}</div>
      <div class="meta">Subscriber Churn Diagnosis · data &amp; BI portfolio project ·
      synthetic, seed-generated data<br>Generated {__import__('datetime').date.today()}</div></div>"""]
    for label, path in entries:
        if not path.exists():
            print(f"  (skip missing {path.name})")
            continue
        md = strip_mermaid(path.read_text(encoding="utf-8"))
        html = markdown.markdown(md, extensions=MD_EXT)
        parts.append(f'<div class="section-sep"></div>\n{html}')
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
           f"<style>{CSS}</style></head><body>{''.join(parts)}</body></html>")
    html_path = DOCS / (out_name + ".html")
    html_path.write_text(doc, encoding="utf-8")
    pdf_path = DOCS / (out_name + ".pdf")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                   capture_output=True, text=True)
    size = pdf_path.stat().st_size / 1e6 if pdf_path.exists() else 0
    html_path.unlink(missing_ok=True)
    print(f"  {pdf_path.name}  {size:.2f} MB")


def main():
    print("build_docs_pdf.py")
    build(FULL, "Voxa+_Documentation", "Voxa+ Documentation",
          "Full project documentation")
    build(SUMMARY, "Voxa+_Summary", "Voxa+ Summary",
          "Context, data quality, and the root-cause diagnosis")


if __name__ == "__main__":
    main()

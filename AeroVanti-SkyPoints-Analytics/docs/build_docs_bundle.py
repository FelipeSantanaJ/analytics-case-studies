"""
build_docs_bundle.py — combine docs/*.md into one styled PDF, plus a condensed
summary PDF (< 2 MB).  markdown -> HTML -> headless-Chrome print-to-PDF.

    python docs/build_docs_bundle.py

Output:
  docs/AeroVanti-SkyPoints-Documentation.pdf   (full: 00..09 + walkthrough)
  docs/AeroVanti-SkyPoints-Summary.pdf         (00 scope + 01 context + 05 model + 06 DAX)
"""
from __future__ import annotations
import pathlib
import subprocess

import markdown

HERE = pathlib.Path(__file__).resolve().parent
FULL = ["00_scope", "01_business_context_kpis", "02_data_architecture", "03_data_dictionary",
        "04_etl_pipeline", "05_data_model", "06_dax_measures", "07_visual_identity",
        "08_data_quality", "09_report_structure", "walkthrough"]
SUMMARY = ["00_scope", "01_business_context_kpis", "05_data_model", "09_report_structure"]

CSS = """
:root{--navy:#0A2A43;--blue:#0B5FA5;--ink:#12212E;--amber:#E08A1E;--muted:#6C7A87;
      --line:#D3DBE3;--fill:#F4F8FB;}
*{box-sizing:border-box}
html{font-family:"Segoe UI",Arial,sans-serif;color:var(--ink);font-size:12.5px;line-height:1.5}
body{margin:0}
.wrap{max-width:900px;margin:0 auto;padding:26mm 16mm}
h1{font-size:23px;color:var(--navy);border-bottom:3px solid var(--amber);padding-bottom:6px;
   margin:34px 0 10px;break-before:page}
h1:first-of-type{break-before:avoid}
h2{font-size:17px;color:var(--navy);margin:22px 0 6px;border-bottom:1px solid var(--line);padding-bottom:4px}
h3{font-size:14px;margin:16px 0 4px}
p{margin:7px 0}
code{background:var(--fill);padding:1px 4px;border-radius:3px;font-size:11.5px}
pre{background:var(--fill);border:1px solid var(--line);border-radius:6px;padding:10px;overflow-x:auto;font-size:11px}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:11px}
th,td{border:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:top}
th{background:var(--fill);font-weight:600}
blockquote{border-left:4px solid var(--amber);background:var(--fill);margin:10px 0;padding:8px 14px;color:#33404B}
.cover{text-align:center;padding:60mm 0 40mm}
.cover .k{color:var(--amber);letter-spacing:.18em;font-weight:700;font-size:12px}
.cover h1{border:0;font-size:34px;break-before:avoid;margin:12px 0}
.cover p{color:var(--muted)}
@media print{.wrap{max-width:none}}
"""


def render(files, out, title, sub):
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "attr_list", "sane_lists"])
    body = [f'<div class="cover"><div class="k">AEROVANTI SKYPOINTS</div>'
            f'<h1>{title}</h1><p>{sub}</p>'
            f'<p>Fictional company · synthetic seeded data · generated 2026-09-02</p></div>']
    for f in files:
        p = HERE / f"{f}.md"
        if not p.exists():
            print(f"  (skip missing {f}.md)")
            continue
        body.append(md.convert(p.read_text(encoding="utf-8")))
        md.reset()
    html = (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>'
            f'<style>{CSS}</style></head><body><div class="wrap">{"".join(body)}</div></body></html>')
    htmlp = HERE / (out.replace(".pdf", ".html"))
    htmlp.write_text(html, encoding="utf-8")
    chrome = next((c for c in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"] if pathlib.Path(c).exists()), None)
    if chrome:
        subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={HERE / out}", htmlp.resolve().as_uri()],
                       capture_output=True, timeout=120)
        mb = (HERE / out).stat().st_size / 1e6
        print(f"  {out}  ({mb:.1f} MB)")
        htmlp.unlink()
    else:
        print(f"  {htmlp.name} (no Chrome/Edge — HTML only)")


if __name__ == "__main__":
    render(FULL, "AeroVanti-SkyPoints-Documentation.pdf",
           "Project Documentation", "ETL · data model · DAX · report · analysis walkthrough")
    render(SUMMARY, "AeroVanti-SkyPoints-Summary.pdf",
           "Project Summary", "Scope · business context · data model · report structure")

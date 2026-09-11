"""
Build the two deliverables as self-contained HTML (+ PDF via headless Chrome/Edge),
in the Voxa+ visual identity (assets/brand.py — violet).

  deliverables/board_summary.html / .pdf   — decision-first board read, ~2 pages
  deliverables/deep_dive.html      / .pdf   — deep_dive_00_index.md + findings F01–F10,
                                              consolidated into one exhaustive document

Re-runnable. If outputs/figures/*.png exist they are base64-embedded; the Voxa+
diagnosis is table-driven, so normally there are none and the script just skips them.

    python data_analysis/deliverables/build_deliverables.py
"""
from __future__ import annotations

import base64
import pathlib
import re
import subprocess

import markdown

HERE = pathlib.Path(__file__).resolve().parent
FIG = HERE.parent / "outputs" / "figures"

# --- Voxa+ identity (assets/brand.py) ------------------------------------------
CSS = """
:root{
  --violet:#4B2E83; --violet-deep:#241348; --violet-tint:#EDE9F5;
  --amber:#E6A23C; --steel:#5B7FB0;
  --ink:#1E1A33; --body:#3A3646; --muted:#77738A;
  --good:#2E7D5B; --bad:#C0453B;
  --page:#F2F1F7; --card:#FFFFFF; --line:#E1DEEB; --lightfill:#F7F6FB;
}
*{box-sizing:border-box}
html{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;color:var(--body);font-size:15px;line-height:1.55}
body{margin:0;background:var(--page);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{max-width:960px;margin:0 auto;padding:0 0 56px;background:var(--card)}
.band{background:var(--violet-deep);color:#F4F2FA;padding:20px 56px;border-bottom:3px solid var(--amber)}
.band .wm{font-weight:700;font-size:19px;letter-spacing:.02em}
.band .wm b{color:var(--amber);font-weight:700}
.band .lab{float:right;color:#C6BEDD;font-size:13px;margin-top:5px}
.body{padding:34px 56px}
h1{font-size:27px;font-weight:600;margin:0 0 2px;letter-spacing:-.01em;color:var(--ink)}
.sub{color:var(--muted);font-size:14px;margin:0 0 8px}
.lead{font-size:16px;color:var(--ink);margin:18px 0 8px}
h2{font-size:20px;font-weight:600;margin:34px 0 6px;color:var(--violet);border-bottom:2px solid var(--line);padding-bottom:6px}
h3{font-size:15px;font-weight:600;margin:20px 0 4px;color:var(--ink)}
p{margin:8px 0}
strong{font-weight:600;color:var(--ink)}
em{color:var(--muted)}
ul,ol{margin:8px 0 8px 22px;padding:0}
li{margin:5px 0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left}
th{background:var(--lightfill);font-weight:600;color:var(--ink)}
tr:nth-child(even) td{background:#FBFAFD}
code{background:var(--violet-tint);border-radius:4px;padding:1px 5px;font-size:12.5px}
.good{color:var(--good)} .bad{color:var(--bad)} .amber{color:var(--amber)} .muted{color:var(--muted)}
.rec{border-left:4px solid var(--amber);background:var(--lightfill);padding:12px 16px;margin:14px 0;border-radius:0 8px 8px 0}
.verdict{border-left:4px solid var(--violet);background:#fff;border:1px solid var(--line);
  border-radius:8px;padding:14px 18px;margin:14px 0}
.factor{display:flex;gap:12px;margin:10px 0;padding:12px 14px;background:#fff;border:1px solid var(--line);border-radius:8px}
.factor .tag{flex:none;width:26px;height:26px;border-radius:50%;background:var(--violet);color:#fff;
  font-weight:700;display:flex;align-items:center;justify-content:center;font-size:14px}
.factor .tag.amber{background:var(--amber)} .factor .tag.steel{background:var(--steel)}
img{max-width:100%;border:1px solid var(--line);border-radius:8px;margin:10px 0}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
.foot{color:var(--muted);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:10px}
.crumbs{font-size:13px;margin:0 0 14px}
.crumbs a{color:var(--violet);text-decoration:none} .crumbs a:hover{text-decoration:underline}
.toc{background:var(--lightfill);border:1px solid var(--line);border-radius:8px;padding:14px 20px;margin:16px 0 28px}
.toc strong{color:var(--ink);font-size:13px;text-transform:uppercase;letter-spacing:.04em}
.toc ol{columns:2;column-gap:28px;margin:8px 0 0 18px}
.toc a{color:var(--violet);text-decoration:none;font-size:13.5px} .toc a:hover{text-decoration:underline}
@media print{
  .toc,.crumbs{display:none}
  body{background:#fff}
  .page{max-width:none}
  .body,.band{padding-left:14mm;padding-right:14mm}
  h2{break-before:page;break-after:avoid}
  h2:first-of-type{break-before:avoid}
  table,.factor,.verdict,.rec{break-inside:avoid}
}
"""


def b64(name: str) -> str:
    p = FIG / name
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def _slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s+", "-", text.strip())


def _add_anchors(html: str) -> tuple[str, str]:
    """Give every <h2> an id and return (html_with_ids, a linked contents nav)."""
    items: list[tuple[str, str]] = []

    def repl(m: "re.Match[str]") -> str:
        inner = m.group(1)
        slug = _slugify(inner)
        items.append((slug, re.sub(r"<[^>]+>", "", inner)))
        return f'<h2 id="{slug}">{inner}</h2>'

    html = re.sub(r"<h2>(.*?)</h2>", repl, html)
    toc = ('<nav class="toc"><strong>Contents</strong><ol>'
           + "".join(f'<li><a href="#{slug}">{label}</a></li>' for slug, label in items)
           + "</ol></nav>")
    return html, toc


def shell(band_label: str, title: str, sub: str, inner: str, crumbs: str = "") -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body><div class="page">
<div class="band"><span class="wm">Voxa<b>+</b></span><span class="lab">{band_label}</span></div>
<div class="body"><h1>{title}</h1><p class="sub">{sub}</p>
{crumbs}
{inner}
<p class="foot">Synthetic, seed-generated data (a portfolio project). Every figure is
computed on two tracks — DuckDB SQL and pandas — with a parity assertion on each result
(<code>python data_analysis/run_analysis.py</code>, 15/15 pass). The mechanism that
produced the spike is not stated in any document; it lives only in <code>etl/config.py</code>
and was recovered from the data. Per-finding method and evidence:
<code>data_analysis/findings/F01</code>–<code>F10</code>.</p>
</div></div></body></html>"""


# --------------------------------------------------------------------------- #
# BOARD SUMMARY — decision-first, mirrors deliverables/board_summary (hand-authored
# source of record), regenerated here so the two deliverables share one identity.
# --------------------------------------------------------------------------- #
BOARD = """
<p class="lead">Gross monthly churn stepped from a stable <strong>4.1%</strong> to
<strong>6.8%</strong> at window-month 34 and has stayed there (6.9% &rarr; 6.6% &rarr; 7.0%).
<strong>90% of it is voluntary.</strong> It is not one event.</p>

<div class="verdict"><strong>Root cause: three factors that overlapped in time.
None explains the spike alone.</strong></div>

<div class="factor"><div class="tag">1</div><div>
  <strong>Connected-TV app regression</strong> — the app "v3" rollout reached smart-TV /
  streaming-stick last (window-month 32). Video-start failures <strong>tripled</strong>
  (1.1% &rarr; 3.0%). CTV-heavy subscribers churned the <strong>same</strong> as everyone
  else before; after, their churn <strong>doubled to 8.4%</strong> vs 5.6% for the rest.
  Acute trigger, biggest contributor, every market — weakest in the US.
</div></div>
<div class="factor"><div class="tag amber">2</div><div>
  <strong>Brazil price increase</strong> (Standard/Premium, window-month 32) —
  <strong>Brazil only</strong>. Zero measurable effect on engaged subscribers;
  <strong>+18 pp</strong> on subscribers who were already disengaged (many pushed there by
  Factor 1). Price &times; prior disengagement is what makes Brazil <em>step</em>
  (3.4% &rarr; 7.0%).
</div></div>
<div class="factor"><div class="tag steel">3</div><div>
  <strong>Mexico cohort-quality drag</strong> — <strong>Mexico only</strong>, and
  <strong>months old</strong>. Mexican subscribers acquired since ~mid-2025 retain
  <strong>~8 pp worse at month 3</strong> (vs ~3 pp elsewhere). This was already lifting
  Mexican churn before the spike and is still underneath it (Mexico 5.4% &rarr; 8.1%,
  drifting then stepping).
</div></div>

<p class="muted">Payments were tested and <strong>ruled out</strong>: payment-failure rate,
dunning recovery and involuntary churn are unchanged in every market.</p>

<h2>By market</h2>
<table>
  <tr><th>Market</th><th>Pre-shift</th><th>Now</th><th>Shape</th></tr>
  <tr><td>Brazil</td><td>3.4%</td><td class="bad">7.0%</td><td>flat, then a clean +3.0 pp step — acute</td></tr>
  <tr><td>Mexico</td><td>5.4%</td><td class="bad">8.1%</td><td>drifting up since ~mid-2025, then a further step</td></tr>
  <tr><td>United States</td><td>4.1%</td><td class="muted">4.4%</td><td>essentially unchanged — the control</td></tr>
</table>

<h2>What it is costing</h2>
<table>
  <tr><th>Measure</th><th>Pre-shift</th><th>Now</th></tr>
  <tr><td>Implied average subscriber lifetime</td><td>24.3 mo</td><td class="bad">14.7 mo</td></tr>
  <tr><td>Lifetime value per subscriber</td><td>—</td><td class="bad">−40%</td></tr>
  <tr><td>Excess subscribers lost (3 elevated months, vs the old rate)</td><td>—</td><td class="bad">≈ 5,400</td></tr>
</table>
<p class="muted">≈ $0.5–0.6 M of lifetime recurring revenue already forgone, compounding
monthly. A 40% lower LTV also cuts the allowable CAC by ~40% — the growth plan no longer
pencils at current acquisition cost.</p>

<h2>Recommendations — in priority order</h2>
<ol>
  <li><strong>Fix the connected-TV player (Sev-1).</strong> Roll back / hotfix v3 on
      smart-TV and streaming-stick; confirm video-start-failure returns to ~1%.
      Save-campaign the CTV-heavy subscribers whose viewing dropped after window-month 32.</li>
  <li><strong>Pause the Brazil price migration for low-engagement Standard/Premium
      subscribers.</strong> Give them a retention path (hold price, downgrade, or pause);
      re-test elasticity after the CTV fix.</li>
  <li><strong>Audit Mexico acquisition and onboarding since mid-2025.</strong> Cap spend on
      the weakest sources until month-3 retention recovers toward ~82%.</li>
  <li><strong>Instrument for next time:</strong> connected-TV quality on the exec dashboard,
      a leading "engagement health" trend, and price-change elasticity by engagement band.</li>
</ol>
"""


def build_deep_dive() -> str:
    md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list"])
    parts = [md.convert((HERE / "deep_dive_00_index.md").read_text(encoding="utf-8"))]

    findings_dir = HERE.parent / "findings"
    finding_files = sorted(findings_dir.glob("F[0-9][0-9]_*.md"))
    if finding_files:
        md.reset()
        parts.append(md.convert(
            "## Appendix — the ten findings in full\n\n"
            "Each numbered problem, with its hypothesis, both-tracks method, evidence table, "
            "conclusion, limitations and recommendation — exactly as recorded during the "
            "analysis."))
        for f in finding_files:
            text = f.read_text(encoding="utf-8")
            # demote the finding's H1 title to an H3 so it nests under the appendix H2
            text = re.sub(r"^# ", "### ", text, count=1, flags=re.MULTILINE)
            md.reset()
            parts.append("<hr/>\n" + md.convert(text))

    body, toc = _add_anchors("\n".join(parts))
    crumbs = ('<p class="crumbs"><a href="../../README.md">&larr; Back to project README</a>'
              ' &middot; <a href="board_summary.html">Board summary</a></p>')
    return shell(
        "Subscriber churn diagnosis — deep dive",
        "Voxa+ — Subscriber Churn: Root-Cause Diagnosis",
        "The exhaustive record behind the board summary · dual-track (DuckDB SQL + pandas)",
        toc + body,
        crumbs=crumbs)


def main() -> None:
    board_crumbs = ('<p class="crumbs"><a href="../../README.md">&larr; Back to project README</a>'
                     ' &middot; <a href="deep_dive.html">Full deep dive &rarr;</a></p>')
    board = shell(
        "Subscriber churn diagnosis — board summary",
        "Why churn nearly doubled — and what to do",
        "Board readout · analysis window Sep 2023 – Aug 2026 · figures dual-computed (SQL + Python), 15/15 parity checks pass",
        BOARD,
        crumbs=board_crumbs)
    (HERE / "board_summary.html").write_text(board, encoding="utf-8")

    (HERE / "deep_dive.html").write_text(build_deep_dive(), encoding="utf-8")

    chrome = next((p for p in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ] if pathlib.Path(p).exists()), None)
    if chrome:
        for name in ("board_summary", "deep_dive"):
            src = (HERE / f"{name}.html").resolve().as_uri()
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={HERE / (name + '.pdf')}", src],
                           capture_output=True, timeout=120)
            print(f"  {name}.html + .pdf")
    else:
        print("  (no Chrome/Edge found — HTML only)")
    print("deliverables built.")


if __name__ == "__main__":
    main()

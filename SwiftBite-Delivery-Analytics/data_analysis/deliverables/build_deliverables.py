"""
Build the two Phase-10 deliverables as self-contained HTML (+ PDF via headless
Chrome/Edge), in the SwiftBite visual identity (assets/brand.py — forest green).

  deliverables/board_summary.html / .pdf   — decision-first, ~2 pages
  deliverables/deep_dive.html      / .pdf   — index + findings 01–08, figures embedded

Re-runnable:
    python data_analysis/deliverables/build_deliverables.py
"""
from __future__ import annotations

import base64
import pathlib
import re
import subprocess
import sys

import markdown

HERE = pathlib.Path(__file__).resolve().parent
DA = HERE.parent
FIND = DA / "findings"
FIG = DA / "outputs" / "figures"
sys.path.insert(0, str(DA.parent / "assets"))
import brand as B  # noqa: E402

CSS = f"""
:root{{
  --green:{B.GREEN}; --green-deep:{B.GREEN_DEEP}; --tangerine:{B.TANGERINE};
  --stone:{B.STONE}; --ink:{B.INK_TITLE}; --body:{B.INK_BODY}; --muted:{B.INK_MUTED};
  --good:{B.GOOD}; --bad:{B.BAD}; --page:{B.PAGE_BG}; --card:#FFFFFF;
  --line:{B.HAIRLINE}; --fill:#F3F6F2;
}}
*{{box-sizing:border-box}}
html{{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;color:var(--body);font-size:15px;line-height:1.55}}
body{{margin:0;background:var(--page);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{max-width:960px;margin:0 auto;padding:0 0 56px;background:var(--card)}}
.band{{background:var(--green-deep);color:{B.ON_DARK};padding:20px 56px;border-bottom:3px solid var(--tangerine)}}
.band .wm{{font-weight:700;font-size:19px;letter-spacing:.02em}}
.band .wm b{{color:var(--tangerine);font-weight:700}}
.band .lab{{float:right;color:{B.ON_DARK_MUTED};font-size:13px;margin-top:5px}}
.body{{padding:34px 56px}}
h1{{font-size:27px;font-weight:600;margin:0 0 2px;color:var(--ink)}}
.sub{{color:var(--muted);font-size:14px;margin:0 0 8px}}
.lead{{font-size:16px;color:var(--ink);margin:18px 0 8px}}
h2{{font-size:20px;font-weight:600;margin:34px 0 6px;color:var(--green);border-bottom:2px solid var(--line);padding-bottom:6px}}
h3{{font-size:15px;font-weight:600;margin:20px 0 4px;color:var(--ink)}}
p{{margin:8px 0}} strong{{font-weight:600;color:var(--ink)}} em{{color:var(--muted)}}
ul,ol{{margin:8px 0 8px 22px;padding:0}} li{{margin:5px 0}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}}
th,td{{border:1px solid var(--line);padding:6px 9px;text-align:left}}
th{{background:var(--fill);font-weight:600;color:var(--ink)}}
tr:nth-child(even) td{{background:#FBFCFA}}
code{{background:var(--fill);border-radius:4px;padding:1px 5px;font-size:12.5px}}
.good{{color:var(--good)}} .bad{{color:var(--bad)}} .amber{{color:var(--tangerine)}} .muted{{color:var(--muted)}}
.rec{{border-left:4px solid var(--tangerine);background:var(--fill);padding:12px 16px;margin:14px 0;border-radius:0 8px 8px 0}}
.verdict{{border-left:4px solid var(--green);background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 18px;margin:14px 0}}
img{{max-width:100%;border:1px solid var(--line);border-radius:8px;margin:10px 0}}
hr{{border:0;border-top:1px solid var(--line);margin:26px 0}}
.foot{{color:var(--muted);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:10px}}
@media print{{body{{background:#fff}} .page{{max-width:none}} .body,.band{{padding-left:14mm;padding-right:14mm}}
  h2{{break-before:page;break-after:avoid}} h2:first-of-type{{break-before:avoid}}
  table,.rec,.verdict{{break-inside:avoid}}}}
"""


def b64(name: str) -> str:
    p = FIG / name
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def shell(label: str, title: str, sub: str, inner: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body><div class="page">
<div class="band"><span class="wm">Swift<b>Bite</b></span><span class="lab">{label}</span></div>
<div class="body"><h1>{title}</h1><p class="sub">{sub}</p>
{inner}
<p class="foot">Synthetic, seed-generated data (a portfolio project). Unit of randomisation
= the zone-day (~840, 420/arm, 12 zones); every headline number is computed on two tracks
(pandas + DuckDB) with a parity assertion — <code>python data_analysis/parity/run_all.py</code>
— and reported with cluster-robust, randomization-inference and wild-cluster-bootstrap
inference. The true effect lives only in <code>etl/config.py::INCENTIVE_EFFECT</code> and
was recovered from the data. Per-analysis detail: <code>data_analysis/findings/01</code>–<code>08</code>.</p>
</div></div></body></html>"""


BOARD = f"""
<p class="lead">The zone-hour incentive <strong>works on marketplace liquidity</strong> —
but the flat per-delivery bonus <strong>does not pay for itself</strong>. Improve the
design before rolling anything out.</p>

<div class="verdict"><strong>Recommendation: do not roll out the flat bonus as tested.
Restructure it to reward incremental supply, cap it to the supply-short and balanced zones,
and re-run.</strong></div>

<h2>Did it work? &nbsp;Yes — on liquidity.</h2>
<table>
<tr><th>Metric (zone-day)</th><th>Control</th><th>Treatment</th><th>Effect</th><th>95% CI</th><th>Robust?</th></tr>
<tr><td><strong>Fulfillment rate</strong> (primary)</td><td>95.7%</td><td>97.6%</td>
    <td class="good"><strong>+1.87 pp</strong></td><td>[+1.27, +2.46]</td>
    <td>cluster p 7e-10 · <strong>RI p 3e-4</strong> · wild-boot agrees</td></tr>
<tr><td>ETA p90 (min) — co-primary</td><td>46.2</td><td>40.1</td>
    <td class="good">−6.06</td><td>[−8.56, −3.57]</td><td>all p &lt; 0.002</td></tr>
<tr><td>No-courier cancel rate — co-primary</td><td>1.16%</td><td>0.80%</td>
    <td class="good">−0.36 pp</td><td>[−0.64, −0.08]</td><td>p ≈ 0.01–0.03</td></tr>
<tr><td>Courier earnings / active hour</td><td>R$ 33.0</td><td>R$ 41.2</td>
    <td class="good">+R$ 8.12</td><td>[+5.6, +10.6]</td><td>p 1e-10</td></tr>
</table>

<h2>Where it works — supply-short and balanced zones, not the well-supplied ones</h2>
<table>
<tr><th>Baseline supply-stress tier</th><th>Zones</th><th>Fulfillment effect</th><th>95% CI</th></tr>
<tr><td><strong>short</strong></td><td>6</td><td class="good">+2.29 pp</td><td>[+1.54, +3.04]</td></tr>
<tr><td><strong>balanced</strong></td><td>2</td><td class="good">+2.43 pp</td><td>[+0.69, +4.18]</td></tr>
<tr><td>long (well-supplied)</td><td>4</td><td class="muted">+0.94 pp</td><td>[+0.36, +1.53]</td></tr>
</table>
<p>Arm × tier interaction (cluster-robust Wald) p = 0.004; the short-tier and long-tier CIs
do not overlap. In the long zones the bonus is <strong>pure cost</strong>.</p>
<img src="__FOREST__" alt="Incentive effect by baseline supply-stress tier"/>

<h2>Why not to ship it — the economics (guardrail G1)</h2>
<table>
<tr><th></th><th></th></tr>
<tr><td>Incentive spend (treated zone-days)</td><td><strong>R$ 35,820</strong> on 7,446 delivered orders</td></tr>
<tr><td>Incremental delivered orders</td><td><strong>≈ 127</strong> — only <strong>1.7%</strong> of the subsidised orders</td></tr>
<tr><td><strong>Cost per incremental delivered order</strong></td><td class="bad"><strong>≈ R$ 281</strong> (95% CI [R$ 195, R$ 431])</td></tr>
<tr><td>Contribution margin of a delivered order</td><td>≈ R$ 10 → the bonus <strong>fails G1 by ~28×</strong></td></tr>
<tr><td>Value destroyed per subsidised order</td><td class="bad">≈ R$ 4.6</td></tr>
</table>
<p>The bonus is a <strong>flat payment on every delivery</strong> in the treated zone-block,
while ~98% of those orders would have been delivered anyway. The lever pulls real supply
(+1.7 courier-hours per treated zone-day); its <strong>pricing</strong> is wrong.</p>

<h2>Side effects — small</h2>
<p><strong>Neighbour-zone cannibalisation:</strong> control zones next to a treated zone
fulfil ~0.26 pp lower (p = 0.76 — not significant); the per-treated-neighbour drag is
−0.19 pp (p = 0.42). Implied ~17% of the local gain is supply pulled from neighbours →
metro-level net ≈ 83% of the summed local lift. Present, small, not statistically resolved
at 12 zones. <strong>Decay:</strong> no detectable trend over the 10 weeks (the weekly
series is too thin to confirm or rule out a launch bump).</p>

<div class="rec"><strong>Next steps.</strong> (1) Redesign the incentive to pay for
<em>incrementality</em> — a threshold / surge-triggered payment that fires only when a zone
is genuinely short, not a flat per-delivery bonus. (2) Scope any re-run to the supply-short
+ balanced zones only. (3) Keep the neighbour-zone spillover guardrail and a hard budget
cap live. (4) Give a re-run more zone-days per week so the decay question can be answered.</div>
"""


def build_deep_dive() -> str:
    md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list"])
    idx = (
        "## The question and the answer\n\n"
        "**Question.** SwiftBite ran a randomized zone-hour incentive (a peak-block per-delivery "
        "bonus, unit = zone-day) to fix supply-short liquidity. Does it work, is it safe, and "
        "should it roll out?\n\n"
        "**Answer.** It **improves liquidity** — fulfillment +1.87 pp, ETA p90 −6 min, "
        "no-courier cancels −0.36 pp, robust across cluster-robust, randomization-inference and "
        "wild-cluster-bootstrap inference, concentrated in the supply-short and balanced zones "
        "(interaction p = 0.004), with only a small (~17%, not significant) neighbour-zone drag. "
        "It **does not pay for itself**: ~R$ 281 per incremental delivered order vs a ~R$ 10 "
        "contribution margin, because the flat bonus subsidises every delivery while only ~2% "
        "are incremental. **Recommendation: don't ship the flat bonus; restructure it to reward "
        "incremental supply and cap it to the short + balanced zones.**\n")
    parts = [md.convert(idx)]
    md.reset()
    parts.append(md.convert("## Appendix — the eight analyses in full"))
    for f in sorted(FIND.glob("0[1-8]_*.md")):
        text = re.sub(r"^# ", "### ", f.read_text(encoding="utf-8"), count=1, flags=re.MULTILINE)
        md.reset()
        parts.append("<hr/>\n" + md.convert(text))
    for tag, fig in (("06_forest", "06_forest.png"), ("05_novelty", "05_novelty.png"),
                     ("02_love_plot", "02_love_plot.png")):
        u = b64(fig)
        if u:
            parts.append(f'<p><img src="{u}" alt="{tag}"/></p>')
    return shell("Zone-hour incentive — deep dive",
                 "SwiftBite Delivery — Zone-Hour Incentive: Experiment Read-Out",
                 "The exhaustive record behind the board summary · dual-track (pandas + DuckDB)",
                 "\n".join(parts))


def main() -> None:
    board = shell("Zone-hour incentive — board summary",
                  "Should we roll out the zone-hour incentive?",
                  "Ops / Growth / Finance readout · 10-week randomised test (zone-day), window-months 16–18",
                  BOARD.replace("__FOREST__", b64("06_forest.png")))
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

"""
Build the two Phase-10 deliverables as self-contained HTML (+ PDF via headless Chrome),
in the AeroVanti SkyPoints visual identity.

  deliverables/board_summary.html / .pdf   — decision-first, ~2 pages
  deliverables/deep_dive.html    / .pdf    — Deep Dive A + B, rendered from the markdown

Re-runnable: embeds the PNGs from outputs/figures/ as base64.
    python data_analysis/deliverables/build_deliverables.py
"""
from __future__ import annotations
import base64
import pathlib
import shutil
import subprocess

import markdown

HERE = pathlib.Path(__file__).resolve().parent
FIG = HERE.parent / "outputs" / "figures"
TAB = HERE.parent / "outputs" / "tables"

CSS = """
:root{
  --navy:#0A2A43; --blue:#0B5FA5; --ink:#12212E; --amber:#E08A1E; --steel:#5C8CB8;
  --good:#2E7D5B; --bad:#C0453B; --muted:#6C7A87;
  --page:#EEF3F8; --card:#FFFFFF; --line:#D3DBE3; --lightfill:#F4F8FB;
}
*{box-sizing:border-box}
html{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;color:var(--ink);font-size:15px;line-height:1.55}
body{margin:0;background:var(--page)}
.page{max-width:960px;margin:0 auto;padding:0 0 56px;background:var(--card)}
.band{background:var(--navy);color:#F1F6FB;padding:18px 56px;border-bottom:3px solid var(--amber)}
.band .wm{font-weight:600;font-size:19px;letter-spacing:.02em}
.band .wm b{color:var(--amber);font-weight:600}
.band .lab{float:right;color:#B9C8D6;font-size:13px;margin-top:4px}
.body{padding:36px 56px}
h1{font-size:28px;font-weight:600;margin:0 0 2px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:14px;margin:0 0 8px}
h2{font-size:20px;font-weight:600;margin:34px 0 6px;color:var(--navy);border-bottom:2px solid var(--line);padding-bottom:6px}
h3{font-size:15px;font-weight:600;margin:20px 0 4px}
p{margin:8px 0}
strong{font-weight:600}
ul,ol{margin:8px 0 8px 22px;padding:0}
li{margin:4px 0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left}
th{background:var(--lightfill);font-weight:600}
tr:nth-child(even) td{background:#FAFCFE}
.kpi{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
.kpi .c{flex:1 1 150px;border:1px solid var(--line);border-radius:14px;padding:12px 14px;background:#fff}
.kpi .v{font-size:24px;font-weight:600}
.kpi .l{font-size:12px;color:var(--muted);margin-top:2px}
.good{color:var(--good)} .bad{color:var(--bad)} .amber{color:var(--amber)}
.rec{border-left:4px solid var(--amber);background:var(--lightfill);padding:12px 16px;margin:14px 0;border-radius:0 8px 8px 0}
img{max-width:100%;border:1px solid var(--line);border-radius:8px;margin:10px 0}
.foot{color:var(--muted);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:10px}
@media print{.page{max-width:none}.body,.band{padding-left:14mm;padding-right:14mm}h2{break-after:avoid}}
"""


def b64(name):
    p = FIG / name
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def shell(band_label, title, sub, inner):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head><body><div class="page">
<div class="band"><span class="wm">Aero<b>Vanti</b></span><span class="lab">{band_label}</span></div>
<div class="body"><h1>{title}</h1><p class="sub">{sub}</p>
{inner}
<p class="foot">Synthetic, seed-generated data (SEED 20260902). Every figure is computed on
two tracks (pandas + DuckDB) with a parity assertion — <code>python
data_analysis/parity/run_all.py</code>. The true experiment effect is not in any document;
it lives only in <code>etl/config.py</code> and was detected from the data.</p>
</div></div></body></html>"""


# --------------------------------------------------------------------------- #
BOARD = """
<div class="kpi">
  <div class="c"><div class="v good">+2.7 pp</div><div class="l">redemption-rate lift (pooled, p ≈ 2×10⁻⁶)</div></div>
  <div class="c"><div class="v">+3.2 pp</div><div class="l">re-weighted to the member base</div></div>
  <div class="c"><div class="v">≈ +1.5 pp</div><div class="l">durable, after the launch bump decays</div></div>
  <div class="c"><div class="v amber">Blue + Silver</div><div class="l">where the effect is real (interaction p = 0.0007)</div></div>
</div>

<div class="rec"><strong>Recommendation.</strong> Roll out Flash Redemption to
<strong>Blue and Silver</strong>. Hold Gold and Platinum at the current 10,000-point
threshold — no measured benefit there. Keep a revenue-per-member guardrail and a
redemption-depth guardrail live for the first two quarters of rollout.</div>

<h2>Did it work?</h2>
<p>Yes. Lowering the minimum redemption threshold (10,000 → 3,500 SkyPoints) and adding a
low-cost reward catalog raised the 12-week redemption rate from <strong>12.8% to 15.5%</strong>
— a <strong>+2.69 pp</strong> lift, highly significant (z = 4.7, p ≈ 2×10⁻⁶). Randomisation
is clean (no sample-ratio mismatch; every pre-period covariate balanced). Re-weighted to the
real member base (68% Blue), the lift is <strong>≈ +3 pp</strong>.</p>

<h2>But not for everyone — and not all of it lasts</h2>
<table>
<tr><th>Tier</th><th>Control</th><th>Treatment</th><th>Lift (pp)</th><th>95% CI</th><th>Verdict</th></tr>
<tr><td>Blue</td><td>6.1%</td><td>9.9%</td><td><strong>+3.8</strong></td><td>[+2.5, +5.0]</td><td class="good">clear</td></tr>
<tr><td>Silver</td><td>10.8%</td><td>13.0%</td><td><strong>+2.2</strong></td><td>[+0.1, +4.2]</td><td class="good">yes, marginal</td></tr>
<tr><td>Gold</td><td>19.4%</td><td>21.9%</td><td>+2.5</td><td>[−0.6, +5.6]</td><td class="muted">not significant</td></tr>
<tr><td>Platinum</td><td>35.6%</td><td>35.1%</td><td>−0.5</td><td>[−5.2, +4.2]</td><td class="muted">no effect</td></tr>
</table>
<p>The arm × tier interaction is significant (LR χ² = 17.0, p = 0.0007): the effect really
does shrink from Blue to Platinum. Blue — members sitting just below the old threshold with
nowhere to spend — gain the most (<strong>+62% relative</strong>). Top-tier members already
redeem freely and gain nothing.</p>
<img src="__FOREST__" alt="Effect by tier — forest plot"/>
<p>About <strong>half the headline lift is a launch novelty bump</strong> that decays over
the window (weekly-increment trend −0.044 pp/week, p = 0.017). Plan the business case on the
<strong>durable ≈ +1.5–2 pp</strong>.</p>
<img src="__NOVELTY__" alt="Novelty effect — weekly increment"/>

<h2>Is it safe? (guardrails)</h2>
<table>
<tr><th>Guardrail</th><th>Effect</th><th>Read</th></tr>
<tr><td>Flight revenue per member</td><td>−0.09% (n.s.)</td><td>no harm, but the test is <em>too small to prove</em> non-inferiority — keep monitoring</td></tr>
<tr><td>90-day disengagement</td><td class="good">−2.0 pp (p = 0.001)</td><td>favourable — the causal echo of "redeemers stay"</td></tr>
<tr><td>Net point-liability cost / member</td><td>−R$0.81 (n.s.)</td><td>slightly favourable — more redemption draws down points that would expire</td></tr>
<tr><td>Value per redeeming member</td><td class="bad">−R$19 (−6.8%, p = 0.001)</td><td><strong>watch</strong> — Flash drives more but <em>shallower</em> redemptions</td></tr>
</table>

<h2>Why this matters — the hoarding problem</h2>
<p>Only <strong>32% of active members have ever redeemed</strong> (25% of Blue); just 9%
redeemed last quarter. Two-thirds hold enough points — they simply never start. The
co-brand card issues <strong>55% of all points</strong>, to members with no flight attached
and the weakest reason to engage. The unredeemed-points liability is <strong>R$25.7M</strong>
gross (R$15.4M breakage-adjusted), and the recognised figure swings <strong>±R$2.6M per
10 pp</strong> of the breakage assumption. Members who redeem lapse at 10.6% vs 21.1% for
never-redeemers (−6.0 pp after adjustment) — redemption is a retention lever, not just a
marker.</p>
<img src="__HOARDING__" alt="Redemption reach by tier; liability trajectory"/>

<div class="rec"><strong>Next steps.</strong> (1) Roll out to Blue + Silver.
(2) Add a co-brand-card redemption nudge — the highest-leverage adjacent move.
(3) Run a breakage cohort study when a full lot lifetime of data exists — the liability
estimate risk is material. (4) Extend the post-rollout window to turn the 90-day
disengagement signal into a 12-month retention number.</div>
"""


def main():
    board = shell("SkyPoints A/B test read-out — board summary",
                  "Flash Redemption: roll out to Blue &amp; Silver",
                  "AeroVanti loyalty leadership · 2026-09 · 12-week randomised test, months 19–21",
                  BOARD.replace("__FOREST__", b64("06_forest.png"))
                        .replace("__NOVELTY__", b64("05_novelty.png"))
                        .replace("__HOARDING__", b64("07_hoarding.png")))
    (HERE / "board_summary.html").write_text(board, encoding="utf-8")

    # deep dive: render the two markdown files
    md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list", "toc"])
    parts = []
    for f in ("deep_dive_00_index.md", "deep_dive_A_ab_test_readout.md", "deep_dive_B_program_health.md"):
        parts.append(md.convert((HERE / f).read_text(encoding="utf-8")))
        md.reset()
    for tag, fig in (("06_forest", "06_forest.png"), ("05_novelty", "05_novelty.png"),
                     ("07_hoarding", "07_hoarding.png"), ("02_love", "02_love_plot.png")):
        parts.append(f'<p><img src="{b64(fig)}" alt="{tag}"/></p>')
    dd = shell("SkyPoints A/B test read-out — deep dive",
               "AeroVanti SkyPoints — Deep Dive",
               "The exhaustive record behind the board summary · dual-track (pandas + DuckDB)",
               "\n<hr/>\n".join(parts))
    (HERE / "deep_dive.html").write_text(dd, encoding="utf-8")

    # PDF via headless Chrome / Edge
    chrome = next((p for p in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ] if pathlib.Path(p).exists()), None)
    if chrome:
        for name in ("board_summary", "deep_dive"):
            src = (HERE / f"{name}.html").resolve().as_uri()
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={HERE / (name + '.pdf')}", src],
                           capture_output=True, timeout=90)
            print(f"  {name}.html + .pdf")
    else:
        print("  (no Chrome/Edge found — HTML only)")
    print("deliverables built.")


if __name__ == "__main__":
    main()

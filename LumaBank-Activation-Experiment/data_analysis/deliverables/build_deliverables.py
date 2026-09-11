"""
Build the two Phase-10 deliverables as self-contained HTML (+ PDF via headless
Chrome/Edge), in the LumaBank visual identity (assets/brand.py -- petrol + coral).

  deliverables/board_summary.html / .pdf   -- decision-first, ~2 pages
  deliverables/deep_dive.html      / .pdf   -- index + incident timeline + findings 01-05

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
  --petrol:{B.PETROL}; --petrol-deep:{B.PETROL_DEEP}; --coral:{B.CORAL};
  --stone:{B.STONE}; --ink:{B.INK_TITLE}; --body:{B.INK_BODY}; --muted:{B.INK_MUTED};
  --good:{B.GOOD}; --bad:{B.BAD}; --page:{B.PAGE_BG}; --card:#FFFFFF;
  --line:{B.HAIRLINE}; --fill:#F1EEE6;
}}
*{{box-sizing:border-box}}
html{{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;color:var(--body);font-size:15px;line-height:1.55}}
body{{margin:0;background:var(--page);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{max-width:960px;margin:0 auto;padding:0 0 56px;background:var(--card)}}
.band{{background:var(--petrol-deep);color:{B.ON_DARK};padding:20px 56px;border-bottom:3px solid var(--coral)}}
.band .wm{{font-weight:700;font-size:19px;letter-spacing:.02em}}
.band .wm b{{color:var(--coral);font-weight:700}}
.band .lab{{float:right;color:{B.ON_DARK_MUTED};font-size:13px;margin-top:5px}}
.body{{padding:34px 56px}}
h1{{font-size:27px;font-weight:600;margin:0 0 2px;color:var(--ink)}}
.sub{{color:var(--muted);font-size:14px;margin:0 0 8px}}
.lead{{font-size:16px;color:var(--ink);margin:18px 0 8px}}
h2{{font-size:20px;font-weight:600;margin:34px 0 6px;color:var(--petrol);border-bottom:2px solid var(--line);padding-bottom:6px}}
h3{{font-size:15px;font-weight:600;margin:20px 0 4px;color:var(--ink)}}
p{{margin:8px 0}} strong{{font-weight:600;color:var(--ink)}} em{{color:var(--muted)}}
ul,ol{{margin:8px 0 8px 22px;padding:0}} li{{margin:5px 0}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}}
th,td{{border:1px solid var(--line);padding:6px 9px;text-align:left}}
th{{background:var(--fill);font-weight:600;color:var(--ink)}}
tr:nth-child(even) td{{background:#FBFAF6}}
code{{background:var(--fill);border-radius:4px;padding:1px 5px;font-size:12.5px}}
.good{{color:var(--good)}} .bad{{color:var(--bad)}} .coral{{color:var(--coral)}} .muted{{color:var(--muted)}}
.rec{{border-left:4px solid var(--coral);background:var(--fill);padding:12px 16px;margin:14px 0;border-radius:0 8px 8px 0}}
.verdict{{border-left:4px solid var(--petrol);background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 18px;margin:14px 0}}
.timeline{{border-left:3px solid var(--stone);margin:14px 0 14px 6px;padding-left:20px}}
.timeline .ev{{margin:0 0 14px;position:relative}}
.timeline .ev:before{{content:"";position:absolute;left:-25px;top:5px;width:9px;height:9px;border-radius:50%;background:var(--petrol)}}
.timeline .ev.bad:before{{background:var(--bad)}}
.timeline .ev.good:before{{background:var(--good)}}
.timeline .d{{font-weight:600;color:var(--ink)}}
img{{max-width:100%;border:1px solid var(--line);border-radius:8px;margin:10px 0}}
hr{{border:0;border-top:1px solid var(--line);margin:26px 0}}
.foot{{color:var(--muted);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:10px}}
@media print{{body{{background:#fff}} .page{{max-width:none}} .body,.band{{padding-left:14mm;padding-right:14mm}}
  h2{{break-before:page;break-after:avoid}} h2:first-of-type{{break-before:avoid}}
  table,.rec,.verdict,.timeline .ev{{break-inside:avoid}}}}
"""


def b64(name: str) -> str:
    p = FIG / name
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def shell(label: str, title: str, sub: str, inner: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body><div class="page">
<div class="band"><span class="wm">Luma<b>Bank</b></span><span class="lab">{label}</span></div>
<div class="body"><h1>{title}</h1><p class="sub">{sub}</p>
{inner}
<p class="foot">Synthetic, seed-generated data (a portfolio project). Unit of randomisation
= the user, 50/50 via a feature-flag hash. Every headline number is computed on two tracks
(pandas + DuckDB) with a parity assertion — <code>python data_analysis/parity/run_all.py</code>.
The true treatment effect and the exact production-bug magnitudes live only in
<code>etl/config.py::EFFECT</code> / <code>BUG</code> and were recovered from the data, not
read off. Per-block detail: <code>data_analysis/findings/01</code>–<code>05</code>.</p>
</div></div></body></html>"""


BOARD = f"""
<p class="lead">The redesigned onboarding <strong>increases Day-7 Activation by +4.58 pp</strong>
— but the first attempt to measure it <strong>broke in production on day 11</strong>, and the
clean re-run's guardrail read is <strong>not an unconditional pass</strong>.</p>

<div class="verdict"><strong>Recommendation: ship a monitored rollout with a fraud
circuit-breaker — not an unconditional launch.</strong> The activation lift is real and
statistically resolved. The flagged-fraud guardrail's non-inferiority is not established at
this sample size and needs to keep being watched post-launch.</div>

<h2>What happened</h2>
<p>Growth/Product redesigned onboarding (account created before KYC, not after) and launched
it as a 50/50, user-level A/B test, planned for 6 weeks. On <strong>day 11</strong>
(2026-07-16), a routine mobile release reset the on-device variant-assignment cache for a
share of already-assigned users and pushed new signups into a broken, region-biased
assignment fallback. The standing SRM monitor caught it 2 days later. Truncating the data or
excluding only the flagged users were both too underpowered and too residually biased to
trust (block 04) — the team restarted clean in a shorter, 4-week window with the statistics
re-planned from scratch.</p>
<img src="__SRM__" alt="Daily allocation and SRM p-value — the break"/>

<h2>Did the redesign work? — Yes, clearly</h2>
<table>
<tr><th>Day-7 Activation</th><th>Control</th><th>Treatment</th><th>Lift</th><th>95% CI</th><th>p</th></tr>
<tr><td><strong>Clean re-run</strong> (n=9,254)</td><td>45.24%</td><td>49.83%</td>
    <td class="good"><strong>+4.58 pp</strong></td><td>[+2.55, +6.62]</td><td>1.0e-5</td></tr>
</table>
<p>The recomputed MDE for the re-run's smaller sample was 2.92 pp (vs. 2.41 pp the original
6-week design could have resolved) — the deadline cost real precision, but the observed
effect clears the bar with room to spare.</p>

<h2>Is it safe? — One guardrail passes clean, one does not</h2>
<table>
<tr><th>Guardrail</th><th>Control</th><th>Treatment</th><th>Δ</th><th>95% upper bound</th><th>Margin</th><th>Verdict</th></tr>
<tr><td>KYC rejection rate</td><td>10.48%</td><td>10.17%</td><td class="good">−0.31 pp</td>
    <td>+0.92 pp</td><td>+1.5 pp</td><td class="good"><strong>Pass</strong></td></tr>
<tr><td><strong>Flagged-fraud rate</strong></td><td>0.95%</td><td>1.31%</td><td>+0.36 pp</td>
    <td class="bad">+0.89 pp</td><td>+0.5 pp</td><td class="bad"><strong>Not established</strong></td></tr>
</table>
<p>The fraud point estimate is small, but the confidence interval reaches past the agreed
safety margin — this is "cannot rule out a small increase," not "fraud got worse." In
fintech, that distinction is not a rounding error.</p>

<h2>Where it works best</h2>
<img src="__FOREST__" alt="Effect by acquisition channel"/>
<p>Largest for cold, top-of-funnel traffic (paid_social +6.2 pp, the only individually
significant channel at this sample size; influencer +7.3 pp, not significant), smallest for
warm referral traffic (+1.5 pp) — consistent with the hypothesis that the old flow's
document-upload wall cost the most intent from users who had the least of it to spare. The
formal interaction test is not significant (p = 0.52) — directionally right, not yet proven.</p>

<div class="rec"><strong>Next steps.</strong> (1) Ship to paid_social first — the channel
with both the largest and the most confidently estimated lift. (2) Keep the flagged-fraud
rate on a live guardrail dashboard through the rollout, not just at this one read. (3) Feed
the SRM monitoring runbook's lesson back into the assignment service's cache-reset handling
review, not just this one experiment. (4) Re-run the heterogeneity cut once more post-launch
data accrues — the channel story is directionally clear but not yet statistically proven.</div>
"""


def build_deep_dive() -> str:
    md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list"])
    idx = (
        "## The question and the answer\n\n"
        "**Question.** LumaBank ran a randomized, user-level A/B test of a redesigned "
        "onboarding flow (account first, KYC deferred). Does it lift Day-7 Activation, is "
        "it safe on fintech guardrails, and — since the first attempt broke mid-flight on a "
        "real production bug — what actually happened, and was the fix defensible?\n\n"
        "**Answer.** The redesign **works**: +4.58 pp Day-7 Activation (95% CI [+2.55, "
        "+6.62], p ≈ 1e-5) on a clean re-run. The original 6-week run **broke on day 11** "
        "when a mobile deploy reset the variant-assignment cache and pushed new signups "
        "into a region-biased fallback; the standing SRM monitor caught it within 2 days. "
        "Truncating or excluding only the flagged users were both too underpowered and too "
        "residually biased to trust, so the team restarted clean in a shorter 4-week window "
        "with power recomputed from scratch. On the clean re-run, the KYC-rejection "
        "guardrail passes; **the flagged-fraud guardrail's non-inferiority is not "
        "established** at this sample size. **Recommendation: a monitored rollout with a "
        "fraud circuit-breaker, not an unconditional launch.**\n")
    parts = [md.convert(idx)]
    md.reset()

    timeline_html = """
<h2>Incident timeline — day by day</h2>
<div class="timeline">
<div class="ev"><span class="d">2026-07-06 (Mon)</span> — Original experiment launches. 50/50,
  user-level, feature-flag hash assignment. Planned window: 6 weeks, ~13,500 users.</div>
<div class="ev"><span class="d">2026-07-06 → 07-15</span> — Clean allocation. Daily SRM checks
  all pass (trailing-7d p ranges 0.18–0.88); nothing visible yet.</div>
<div class="ev bad"><span class="d">2026-07-16 (Thu) — Day 11</span> — A routine mobile
  release ships (iOS + Android). It resets the on-device variant-assignment cache for a
  share of already-assigned users, and a latent fallback path — never exercised before —
  starts catching new signups with a broken, region/timezone-correlated assignment rule.</div>
<div class="ev"><span class="d">2026-07-17</span> — Trailing-7d SRM p dips to 0.011 — inside
  the "ok" band, but visibly moving toward it.</div>
<div class="ev bad"><span class="d">2026-07-18 — ALERT</span> — Trailing-7d SRM p crosses
  0.001 (p = 0.00008). The standing monitor fires; new enrollment auto-pauses; triage begins:
  release-calendar cross-reference, assignment_source breakdown, region breakdown.</div>
<div class="ev"><span class="d">2026-07-19 → 07-21</span> — ALERT persists on both tests.
  Investigation confirms two distinct effects: 191 contaminated pre-deploy users (arm
  switches + cache-reset-in-window), and a fallback that skews as far as 76.5% treatment in
  the Southeast vs. 35.3% in the North. Fallback share visibly decays (198 → 141 → 123 → 118
  → 72 → 29 signups/day) as a partial mitigation rolls.</div>
<div class="ev good"><span class="d">2026-07-22</span> — Hotfix ships, correcting cache-reset
  handling and the fallback's assignment logic.</div>
<div class="ev"><span class="d">2026-07-24</span> — Formal decision: abandon the original run.
  Truncating (block 04: MDE 5.4–6.6 pp) and excluding only the flagged users (MDE 4.8 pp,
  unresolved residual bias) are both rejected as too weak or too uncertain. Restart clean, in
  a 4-week window rather than another 6 — the business could not wait a full 6 weeks again —
  with power/MDE recomputed from scratch, not reused from the original design.</div>
<div class="ev good"><span class="d">2026-08-24 → 09-20</span> — Clean re-run executes. Daily
  SRM monitoring stays in the "ok" state for all 28 days.</div>
<div class="ev good"><span class="d">Readout</span> — +4.58 pp Day-7 Activation, p ≈ 1e-5. KYC
  guardrail clean; flagged-fraud guardrail's non-inferiority not established. Recommendation:
  monitored rollout with a fraud circuit-breaker.</div>
</div>
"""
    parts.append(timeline_html)

    parts.append(md.convert("## Appendix — the five investigation blocks in full"))
    for f in sorted(FIND.glob("0[1-5]_*.md")):
        text = re.sub(r"^# ", "### ", f.read_text(encoding="utf-8"), count=1, flags=re.MULTILINE)
        md.reset()
        parts.append("<hr/>\n" + md.convert(text))
    for tag, fig in (("02_srm_break", "02_srm_break.png"), ("03_fallback_bias", "03_fallback_bias.png"),
                     ("05_heterogeneity_forest", "05_heterogeneity_forest.png")):
        u = b64(fig)
        if u:
            parts.append(f'<p><img src="{u}" alt="{tag}"/></p>')
    return shell("Onboarding experiment — deep dive",
                 "LumaBank Onboarding Activation Experiment — Incident & Read-Out",
                 "The exhaustive record behind the board summary · dual-track (pandas + DuckDB)",
                 "\n".join(parts))


def main() -> None:
    board = shell("Onboarding experiment — board summary",
                  "Did the onboarding redesign work, and should we ship it?",
                  "Growth / Product / Risk & Compliance readout · user-level A/B test, broken and re-run",
                  BOARD.replace("__SRM__", b64("02_srm_break.png")).replace("__FOREST__", b64("05_heterogeneity_forest.png")))
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
        print("  (no Chrome/Edge found -- HTML only)")
    print("deliverables built.")


if __name__ == "__main__":
    main()

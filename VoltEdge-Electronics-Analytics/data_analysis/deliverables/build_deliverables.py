"""Build the two deliverables as self-contained HTML (print-to-PDF), VoltEdge theme.

  deliverables/board_summary.html   - decision-first, ~2 pages
  deliverables/deep_dive.html       - one section per business problem, figures embedded

Re-runnable: reads the PNGs from outputs/figures/ and base64-embeds them.
"""
from __future__ import annotations

import base64
import pathlib
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
FIG = HERE.parent / "outputs" / "figures"

# --- VoltEdge theme (powerbi/theme/VoltEdge.json) --------------------------------
CSS = """
:root{
  --navy:#123E6E; --ink:#0E2340; --amber:#D99311; --blue:#2E70B0;
  --good:#1E7F4F; --bad:#B23A3A; --muted:#64707F;
  --page:#EAEFF6; --card:#FFFFFF; --line:#DCE4EF; --lightfill:#F4F7FB;
}
*{box-sizing:border-box}
html{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;color:var(--ink);font-size:15px;line-height:1.5}
body{margin:0;background:var(--page)}
.page{max-width:960px;margin:0 auto;padding:48px 56px;background:var(--card)}
h1{font-size:30px;font-weight:600;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:21px;font-weight:600;margin:38px 0 6px;color:var(--navy);border-bottom:2px solid var(--line);padding-bottom:6px}
h3{font-size:16px;font-weight:600;margin:22px 0 4px;color:var(--ink)}
h4{font-size:13px;font-weight:600;margin:16px 0 4px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
p{margin:8px 0}
.sub{color:var(--muted);font-size:14px;margin-top:0}
.lead{font-size:16px}
.readlabel{margin-top:8px;color:var(--amber);text-transform:uppercase;letter-spacing:.06em;font-size:13px}
h3.readlabel + .lead{border-left:4px solid var(--amber);padding-left:16px;margin-left:0}
strong{font-weight:600}
em{color:var(--muted)}
ul,ol{margin:8px 0 8px 22px;padding:0}
li{margin:4px 0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left}
th{background:var(--lightfill);font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
figure{margin:16px 0;padding:0}
figure img{width:100%;border:1px solid var(--line);border-radius:10px}
figcaption{font-size:12.5px;color:var(--muted);margin-top:6px}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0}
.kpi{background:var(--lightfill);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .v{font-size:24px;font-weight:600;color:var(--navy);font-variant-numeric:tabular-nums}
.kpi .l{font-size:12.5px;color:var(--muted);margin-top:2px}
.callout{background:var(--lightfill);border-left:4px solid var(--amber);border-radius:6px;padding:12px 16px;margin:14px 0}
.rec{background:#F3F8F4;border-left:4px solid var(--good);border-radius:6px;padding:12px 16px;margin:14px 0}
.tag{display:inline-block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;
     background:var(--navy);color:#fff;border-radius:4px;padding:2px 8px;vertical-align:middle}
.good{color:var(--good);font-weight:600}
.bad{color:var(--bad);font-weight:600}
.meta{font-size:12.5px;color:var(--muted)}
hr{border:0;border-top:1px solid var(--line);margin:28px 0}
a{color:var(--blue)}
@media print{
  body{background:#fff}
  .page{max-width:none;padding:0 12mm;margin:0}
  h2{break-before:page}
  h2:first-of-type{break-before:avoid}
  figure,table{break-inside:avoid}
  .no-print{display:none}
}
"""


def img(name: str) -> str:
    p = FIG / name
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"


def figure(name: str, caption: str) -> str:
    return f'<figure><img src="{img(name)}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'


def html_doc(title: str, body: str) -> str:
    return textwrap.dedent(f"""\
    <!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{title}</title><style>{CSS}</style></head>
    <body><div class="page">{body}</div></body></html>
    """)


# ====================================================================== #
# BOARD SUMMARY
# ====================================================================== #
board_body = f"""
<h1>VoltEdge Electronics — Board Summary</h1>
<p class="sub">Analytics review · 24-month extract 2024-07 → 2026-06 · all figures USD · prepared 2026-09</p>

<h3 class="readlabel">The read</h3>
<p class="lead">VoltEdge has bought $22M of current-year revenue and reached contribution
break-even for the first time — but the break-even sits entirely on a temporarily-cheap CAC,
the underlying margin isn't rising (growth is pure volume into thin-margin categories), and
~$4.4M of cash is trapped in an oversized inventory. The fastest, most certain value is a
working-capital program; the biggest risk is CAC reverting to plan. Repeat behaviour is the
credible long-term profit path and deserves dedicated investment now.</p>

<h2>Recommendations</h2>
<p class="sub">In priority order. Rationale and evidence for each is in the numbered sections that follow.</p>
<ol>
<li><strong>Working-capital / inventory program — CFO priority #1.</strong> SKU-level reorder
points and a dead-stock clear-out; target Days Inventory Outstanding 90 (from 158) within two
quarters. Frees ~$3M now, ~$4.4M at benchmark — larger than every P&amp;L lever combined. Put
Cash Conversion Cycle and Inventory Value on the Executive Summary. <em>(§4)</em></li>
<li><strong>Protect and stress-test CAC.</strong> Present break-even as "positive <em>at current
CAC</em>". Track <strong>marginal</strong> (not blended) CAC monthly; stress the plan at CAC =
$33 and $45. MER of 12.8× signals under-investment — test scaling paid spend to a ~$45
marginal-CAC ceiling; there is likely profitable volume above budget. <em>(§2)</em></li>
<li><strong>Lift gross margin through category mix, and cut returns cost.</strong> A deliberate
mix-up plan into audio / accessories / wearables (the margin-carrying categories losing share) is
worth ~1–2pp of gross margin; set a category-mix guardrail. On returns: two KPIs on the Ops/CRM
page — restock rate (54% → 70%) and controllable return rate — worth ≈ $0.4–0.7M/yr. <em>(§3, §6)</em></li>
<li><strong>Promo and shipping-fee discipline.</strong> Cap Black Friday depth at 12–14% and
shorten events; re-scope other events toward margin-carrying categories. Raise free-shipping
thresholds market by market, starting with Brazil (5% recovery). Combined ≈ +$0.5–0.9M/yr
contribution. <em>(§5)</em></li>
<li><strong>Fund a +1-to-+3-month retention program.</strong> Lifecycle CRM + accessory
cross-sell; target +1-month re-order 16% → 20%. Model repeat revenue as improving, but do not let
it carry the plan yet — new-customer CAC is still the swing factor. <em>(§6)</em></li>
<li><strong>Reporting.</strong> Lead every growth slide with <strong>+40% like-for-like</strong>
(show +137% as "incl. expansion"). Add to the Executive Summary: CCC, Inventory Value trend,
shipping-cost recovery %, gross-profit-per-promo-day, and both returning-revenue definitions with
the reconciliation. <em>(§1)</em></li>
</ol>

<h2>Headline metrics</h2>
<p class="sub">Current year unless noted · full method in the Deep Dive.</p>
<div class="kpis">
  <div class="kpi"><div class="v">$31.3M</div><div class="l">Net Revenue, 24 months<br>($22.0M current year)</div></div>
  <div class="kpi"><div class="v">+137% / +40%</div><div class="l">Net Revenue YoY<br>total vs US like-for-like</div></div>
  <div class="kpi"><div class="v">+$325k</div><div class="l">Current-year contribution margin<br>(1.5% of Net Revenue)</div></div>
  <div class="kpi"><div class="v">17.8%</div><div class="l">Gross margin<br>thin by design; +1.3pp YoY</div></div>
  <div class="kpi"><div class="v">≈134 days</div><div class="l">Cash conversion cycle<br>almost entirely inventory</div></div>
  <div class="kpi"><div class="v">$26.91</div><div class="l">Blended CAC — 18% under plan<br>(the swing factor)</div></div>
</div>
<p class="meta">The six findings behind the recommendations — headline, number, "so what" — follow, one per page.</p>

<h2>1 · Growth is real, but the headline is expansion — plan the business on +40%</h2>
<p>Net Revenue grew <strong>+137%</strong>, but <strong>77% of that gain is new markets opening</strong>
(UK &amp; DE from Jan-25, BR from Jul-25). The proven US business grew <strong>+40% like-for-like</strong>
— healthy — but came in <span class="bad">2% under its own plan</span>, the only market to miss.
The +137% will not recur; next year's comparison already includes Europe.</p>
{figure("2026-09_02_yoy_growth_waterfall.png", "Where the year-over-year Net Revenue gain came from.")}
<div class="rec"><strong>Recommendation.</strong> Lead every growth slide with <strong>+40% like-for-like</strong>;
show +137% as "incl. expansion". Set FY27 US plan off the +40% trajectory with a deceleration
assumption. Press management on the US plan miss — it is hidden by the blended beat (+1.8% vs plan).</div>

<h2>2 · We are at break-even — and only because customers came cheap</h2>
<p>Contribution margin went from <span class="bad">−$365k</span> last year to <span class="good">+$325k</span>
this year. Almost all of that swing is <strong>marketing efficiency</strong>: spend fell from
11.9% to 7.8% of Net Revenue and blended CAC landed <strong>18% under plan</strong>. Gross margin
barely moved (+1.3pp).</p>
<table>
<tr><th>Current-year contribution margin</th><th class="n">Value</th></tr>
<tr><td>At actual CAC ($26.91)</td><td class="n good">+$325k</td></tr>
<tr><td>If CAC reverted to last year ($30.26)</td><td class="n">+$111k</td></tr>
<tr><td>If CAC hit plan ($32.80)</td><td class="n bad">−$51k (loss)</td></tr>
</table>
{figure("2026-09_07_marketing_efficiency.png", "The positive contribution margin is a function of a single input — CAC.")}
<div class="rec"><strong>Recommendation.</strong> Present break-even as "positive <em>at current CAC</em>".
Track <strong>marginal</strong> CAC monthly; stress-test the plan at CAC = $33 and $45. Separately,
MER of 12.8× signals under-investment — test scaling paid spend to a marginal-CAC ceiling.</div>

<h2>3 · The margin is not improving structurally — US growth is all volume</h2>
<p>US like-for-like growth decomposes to <strong>~110% volume, +8% price, −17% category mix</strong>.
There is no pricing power, and the mix is drifting <em>toward</em> Smartphones — the thinnest-margin,
highest-return category. Volume growth at a fixed thin margin does not fix profitability.</p>
{figure("2026-09_04_pvm_us_waterfall.png", "US like-for-like revenue growth: price / volume / mix.")}
<div class="rec"><strong>Recommendation.</strong> A deliberate mix-up plan into audio, accessories and
wearables (the margin-carrying categories that are <em>losing</em> share) is the cheapest route to
+1–2pp of gross margin.</div>

<h2>4 · The real constraint is cash: ~$4.4M frozen in inventory</h2>
<p>The P&amp;L is at break-even; the balance sheet is not. The cash conversion cycle is
<strong>~134 days and it is entirely inventory</strong> — Days Inventory Outstanding is
<strong>158 days vs a 45–75 benchmark</strong>, and average inventory has grown from $5.8M to $8.3M.
Payables (41 days) and receivables (ex-Brazil) are already well managed.</p>
{figure("2026-09_06_cash_conversion_cycle.png", "Cash conversion cycle composition, and DSO by market.")}
<div class="rec"><strong>Recommendation.</strong> An inventory-reduction program (SKU-level reorder
points, clear dead stock) targeting DIO 90 within two quarters frees ~$3M now, ~$4.4M at benchmark —
larger than every P&amp;L lever combined. Put CCC and Inventory Value on the Executive Summary.</div>

<h2>5 · Two self-inflicted margin leaks worth ~$0.9M/yr</h2>
<p><strong>Promo depth.</strong> Blended discounting is a healthy 4.6%, but on the 58 promo days a
day earns <strong>$372 of gross profit vs $5,680</strong> on a normal day — the 15.7% average
discount consumes the entire product margin. Cost ≈ <strong>−$308k/yr</strong>
[95% CI: −$379k, −$242k] vs treating those as normal days (p = 1.2×10⁻¹², Welch's t-test;
holds after controlling for calendar-month seasonality). Black Friday at 17–19% off is the
worst.</p>
<p><strong>Shipping-fee recovery.</strong> VoltEdge recovers only <strong>28%</strong> of shipping
cost in fees (Brazil: 5%) — a ~<strong>$0.6M/yr</strong> structural subsidy. Service levels are
otherwise on-benchmark; carriers are not the issue.</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
{figure("2026-09_05_discount_leakage.png", "Promo events vs baseline gross profit.")}
{figure("2026-09_10_fulfilment.png", "Service levels vs benchmark; shipping-fee recovery by market.")}
</div>
<div class="rec"><strong>Recommendation.</strong> Cap Black Friday depth at 12–14% and shorten the
window; re-scope other events toward margin-carrying categories. Raise free-shipping thresholds
market by market, starting with Brazil. Combined ≈ +$0.5–0.9M/yr contribution.</div>

<h2>6 · The path to profit — repeat revenue — is credible but young</h2>
<p>Lifetime repeat rate is <strong>37.6%</strong> (above the 25–35% benchmark) and the newer markets
already out-repeat the US. But re-order demand decays fast (16% at +1 month → 2% at +12), lifetime
is 1.67 orders/customer, and the base is &lt;2 years old, so <strong>84% of current-year revenue is
still from first-year customers</strong>.</p>
{figure("2026-09_08_retention_cohorts.png", "Cohort re-order curve and new-vs-returning revenue.")}
<div class="rec"><strong>Recommendation.</strong> Fund a +1-to-+3-month reactivation program (lifecycle
CRM, accessory cross-sell). Model repeat revenue as improving, but do not let it carry the plan yet —
new-customer CAC is still the swing factor. Also fix returns: 8.0% rate is fine, but $1.65M of margin
leaks and 63% is for controllable (defect / "not as described" / wrong-item) reasons.</div>

<hr>
<p class="meta">Every figure in this summary is reproduced on two independent stacks (DuckDB SQL and
Python/pandas) from the curated data; parity checks under <code>data_analysis/parity/</code>. Full
method, evidence and limitations in the companion Deep Dive.</p>
"""

# ====================================================================== #
# DEEP DIVE
# ====================================================================== #
def section(num, slug_title, tag, body):
    return f'<h2>{num} · {slug_title} <span class="tag">{tag}</span></h2>\n{body}\n'


deep_body = f"""
<h1>VoltEdge Electronics — Deep Dive</h1>
<p class="sub">Analytics review · 24-month extract 2024-07 → 2026-06 · all figures USD · prepared 2026-09</p>
<p>One section per business problem. Each states the decision it informs, the method on
<strong>both tracks</strong> (DuckDB SQL + Python/pandas, parity checked), the evidence, the
limitations, and a recommendation. Source files: <code>data_analysis/parity/NN_*.py</code>,
<code>data_analysis/findings/2026-09_NN_*.md</code>, figures in <code>data_analysis/outputs/</code>.</p>

<h3>Contents</h3>
<ol>
<li>Anchor — reproducing Net Revenue</li>
<li>Growth is mostly market expansion, not the core business</li>
<li>Contribution margin: at break-even, UK the drag</li>
<li>US like-for-like growth is all volume</li>
<li>Promo depth erases gross profit</li>
<li>Working capital: ~$4.4M frozen in inventory</li>
<li>Contribution margin depends on cheap CAC</li>
<li>Retention: healthy, not yet the engine</li>
<li>Returns: an $1.65M margin leak, mostly fixable</li>
<li>Fulfilment &amp; shipping-fee recovery</li>
</ol>

{section("1", "Anchor — reproducing Net Revenue", "calibration", f'''
<p><strong>Decision.</strong> None directly — calibration before exploring, and the SQL+Python
dual-track habit on a known number.</p>
<h4>Method</h4>
<p>Per <code>docs/06</code>: <code>Net Revenue (USD) = SUM(net_amount_usd) − SUM(refund_amount_usd)</code>
over <code>fact_order_lines</code> (grain: order line), <code>order_status &lt;&gt; 'cancelled'</code>.
276,962 lines → 275,020 after removing cancelled → 167,214 distinct orders.</p>
<h4>Result — both tracks agree to sub-cent</h4>
<table>
<tr><th>Metric</th><th class="n">Value</th></tr>
<tr><td>Gross Sales (USD)</td><td class="n">$34,803,649</td></tr>
<tr><td>Returns (USD)</td><td class="n">−$3,456,572</td></tr>
<tr><td><strong>Net Revenue (USD), full window</strong></td><td class="n"><strong>$31,347,077</strong></td></tr>
<tr><td>Current Year / Prior Year</td><td class="n">$22.05M / $9.30M</td></tr>
<tr><td>By market (US / UK / BR / DE)</td><td class="n">$17.62M / $4.86M / $4.59M / $4.28M</td></tr>
</table>
<h4>Reconciliation &amp; caveats</h4>
<ul>
<li>The DAX formula is reproduced exactly on both tracks; Net Revenue is <strong>$31.35M</strong>
($31,347,077), the figure of record.</li>
<li><strong>Header vs line grain:</strong> <code>fact_orders</code> has 167,396 non-cancelled
orders; count orders there, not on <code>fact_order_lines</code> (167,214). DAX-consistent AOV
(Net Revenue ÷ Orders) = $187, not the $208 in <code>docs/01 §12</code> (which is pre-returns).</li>
<li><code>order_status</code> in <code>fact_order_lines</code> only takes <code>delivered</code>
/ <code>cancelled</code>; returns are carried as columns on the delivered line.</li>
</ul>
''')}

{section("2", "Growth is mostly market expansion, not the core business", "CEO / CFO", f'''
<p><strong>Decision.</strong> Whether to plan next year on the +137% top-line or the +40%
like-for-like rate.</p>
<h4>Method (both tracks — <code>parity/02_growth_decomposition.py</code>)</h4>
<p>Net Revenue split CY/PY by <code>order_date_key</code>. <strong>Comparable Base</strong> =
<code>dim_market.is_comparable_base</code> = US only (live the whole CY+PY span), matching DAX
<code>Net Revenue (Comparable Base)</code>. <strong>Expansion</strong> = Total − Comparable.
Plan from <code>fact_target</code> (<code>metric='Net Revenue'</code>). SQL: DuckDB
<code>FILTER (WHERE …)</code>; Python: pandas pivot. Parity &lt;1e-6 on every market×period cell.</p>
{figure("2026-09_02_yoy_growth_waterfall.png", "PY total → +US like-for-like → +expansion → CY total.")}
<table>
<tr><th>Cut</th><th class="n">PY</th><th class="n">CY</th><th class="n">YoY</th></tr>
<tr><td>Total (all markets)</td><td class="n">$9.30M</td><td class="n">$22.05M</td><td class="n">+137.1%</td></tr>
<tr><td>Comparable Base (US like-for-like)</td><td class="n">$7.33M</td><td class="n">$10.29M</td><td class="n">+40.4%</td></tr>
<tr><td>Expansion (UK + DE + BR)</td><td class="n">$1.97M</td><td class="n">$11.76M</td><td class="n">—</td></tr>
</table>
<p>Expansion is 53% of CY Net Revenue and <strong>77% of the $12.7M YoY gain</strong>. Actual CY
vs plan: US <span class="bad">−2.4%</span>, UK +12.9%, DE +7.3%, BR −0.4%, total +1.8%.</p>
<h4>Limitations</h4>
<ul>
<li>Comparable Base = US only (static DAX definition). A Core-3 (US+UK+DE from 2025-01) cut would
give a like-for-like read from 2025 onward.</li>
<li>PY UK/DE is a partial (6-month) base, so their YoY% is not meaningful — only absolute dollars
are used in the decomposition.</li>
<li>US +40% not yet decomposed into price/volume/mix — see §4.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> Report growth two ways on every board slide;
anchor FY27 targets on the +40% trajectory with deceleration. CFO: press on the US −2% plan miss —
it is the most important growth signal and is masked by the blended beat.</div>
''')}

{section("3", "Contribution margin: at break-even, UK the drag", "CFO / CEO", f'''
<p><strong>Decision.</strong> Whether VoltEdge can "afford" its growth, and which market destroys
contribution.</p>
<h4>Method (both tracks — <code>parity/03_margin_to_breakeven.py</code>, 30 checks)</h4>
<p>The DAX chain in <code>docs/06</code>:
<code>Gross Profit = Net Revenue − COGS + Returns COGS Recovered</code>;
<code>Contribution Margin = Gross Profit − Marketing − Shipping Cost − (Payment Fees + Interest-Free
Financing)</code>. Periods by <code>order_date_key</code> (returns by <code>return_date_key</code>,
marketing by <code>date_key</code>). SQL: DuckDB CTE per component; Python: pandas.</p>
{figure("2026-09_03_contribution_margin.png", "CY gross profit → contribution margin, and CM% trajectory / by market.")}
<table>
<tr><th></th><th class="n">Full 24m</th><th class="n">Current Year</th><th class="n">Prior Year</th></tr>
<tr><td>Gross Profit</td><td class="n">$5.67M (18.1%)</td><td class="n">$3.93M (17.8%)</td><td class="n">$1.53M (16.5%)</td></tr>
<tr><td>− Marketing / Shipping / Payments</td><td class="n">$2.91M / $1.74M / $0.94M</td><td class="n">$1.72M / $1.20M / $0.69M</td><td class="n">$1.10M / $0.54M / $0.26M</td></tr>
<tr><td><strong>Contribution Margin</strong></td><td class="n"><strong>+$76k (0.2%)</strong></td><td class="n good"><strong>+$325k (1.5%)</strong></td><td class="n bad"><strong>−$365k (−3.9%)</strong></td></tr>
</table>
<p>By market (CY): Brazil <span class="good">+4.9%</span> (best — high gross margin + cheap Pix),
US +1.6%, Germany −0.0%, <strong>UK <span class="bad">−1.7%</span></strong> (lowest gross margin
15.4% + marketing load; <em>not</em> shipping — see §10).</p>
<h4>Limitations</h4>
<ul>
<li><code>Gross Profit</code> adds back <code>Returns COGS Recovered</code> per the live DAX
(<code>pbi_measures.py</code>); <code>docs/06</code> prose line 21 says it is not — the prose is
stale (+$1.83M / +5.9pp of gross margin over the window).</li>
<li>Contribution margin excludes fixed cost, payroll, tech — an operating-contribution proxy, not
net profit. Real profit is materially negative.</li>
<li>CM by market takes marketing at <code>market_key</code> face value; no HQ reallocation.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> Board line: "positive at the contribution line for
the first time (+1.5% vs −3.9%)" — but state it is $325k, i.e. fragile. Act on the UK: lift gross
margin via category mix. Protect the marketing-efficiency gain — it, not gross margin, moved CM
positive (§7).</div>
''')}

{section("4", "US like-for-like growth is all volume", "CEO / CFO / VP E-com", f'''
<p><strong>Decision.</strong> Whether the US engine can carry the business to profit — a
volume-only, flat-margin expansion does not.</p>
<h4>Method (both tracks — <code>parity/04_price_volume_mix_us.py</code>, 7 checks)</h4>
<p>Price/Volume/Mix per <code>docs/06 §07</code>, US non-cancelled <code>fact_order_lines</code>, by
<code>dim_product.category</code>. Price = Σ (ASP<sub>CY</sub>−ASP<sub>PY</sub>)×Units<sub>PY</sub>;
Volume = GrossRev<sub>PY</sub> × unit growth; Mix = ΔGrossRev − Price − Volume. Parity exact.</p>
{figure("2026-09_04_pvm_us_waterfall.png", "US Gross Revenue PY → CY: volume +$3.79M, price +$0.26M, mix −$0.60M.")}
<p>US Gross Revenue $8.55M → $12.01M (+40.3%); units +44.3%. <strong>Volume +$3.79M (110% of the
gain)</strong>, price +$0.26M (+8%), <strong>mix −$0.60M (−17%)</strong>. Revenue share is shifting
<strong>toward Smartphones (+2.7pp)</strong> — thinnest gross margin (8–14%) — and away from
Laptops (−2.0pp).</p>
<h4>Limitations</h4>
<ul>
<li>ASP numerator (Gross Revenue) includes warranty lines while the denominator (Units) is
product-only — the DAX definition; consistent across CY/PY so the effect split holds.</li>
<li>PVM is on Gross Revenue, not margin dollars; a margin-weighted mix effect would be more
negative given the Smartphone shift.</li>
<li>Single comparable market (US).</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> A deliberate mix-up plan into audio / accessories /
wearables is worth ~1–2pp of margin on a $12M base. Set a category-mix guardrail in the exec pack;
do not assume operating leverage from volume alone.</div>
''')}

{section("5", "Promo depth erases gross profit", "CFO / CMO", f'''
<p><strong>Decision.</strong> Keep the promo calendar as-is, or cut discount depth / shorten events.</p>
<h4>Method (both tracks — <code>parity/05_discount_leakage.py</code>)</h4>
<p><code>Discount Rate % = SUM(discount_amount_usd) ÷ SUM(gross_amount_usd)</code>. Promo days from
<code>dim_date.is_promo_period</code>. Promo-day P&amp;L uses line-level
<code>gp = (net − refund) − cogs_usd</code> aggregated to a per-day average. Discount-rate parity
exact to 1e-9; per-day gross profit parity (sum/mean/variance per group) before any significance
test runs on it. Significance: Welch's t-test. Uncertainty: percentile bootstrap (10,000
resamples, seed 42). Seasonality check: OLS with calendar-month fixed effects, robust SE.</p>
{figure("2026-09_05_discount_leakage.png", "Discount rate by promo event; average daily gross profit promo vs non-promo.")}
<ul>
<li>Blended discount rate <strong>4.6%</strong> — low end of the 4–10% benchmark; mild drift PY
4.3% → CY 4.7%. Non-promo days 2.7%; <strong>promo days 15.7%</strong>.</li>
<li>Promo day: ~2× the volume of a normal day but <strong>$372 of gross profit vs $5,680</strong>
(Welch t = −8.80, p = 1.2×10⁻¹²). Annual impact ≈ <span class="bad">−$308k</span>
[95% CI: −$379k, −$242k] across 58 promo days — roughly the size of the entire CY
contribution margin.</li>
<li>Black Friday is the deepest (17–19% off); discount rate is flat across categories, so this is a
calendar/depth decision, not a merchandising one.</li>
</ul>
<h4>Limitations</h4>
<ul>
<li>Pull-forward not modelled (would make promos look <em>worse</em>).</li>
<li>New-customer acquisition &amp; inventory-clearance value not credited (could justify part of
the cost — needs §8 and an aged-inventory view).</li>
<li>Baseline-day GP is a blended average, and promo days concentrate in specific calendar
months. Tested directly (month-fixed-effects regression): the seasonality-adjusted gap is
−$5,710/day, essentially unchanged from the naive −$5,308 — <strong>not</strong> a
seasonality artifact.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> Cap Black Friday at 12–14% and test shorter
windows; re-scope other events toward margin-carrying categories. If BF is kept, fund it from the
marketing budget with a CAC target, not invisibly from gross margin. Add "gross profit per promo
day vs baseline" to the CFO pack.</div>
''')}

{section("6", "Working capital: ~$4.4M frozen in inventory", "CFO / COO", f'''
<p><strong>Decision.</strong> Which lever — inventory, receivables, or payables — releases cash.
The answer is inventory.</p>
<h4>Method (both tracks — <code>parity/06_cash_conversion_cycle.py</code>)</h4>
<p>Per <code>docs/06 §11</code>: <code>DSO</code> = amount-weighted settlement lag over
<code>fact_payment_schedule</code>; <code>DIO = Avg Inventory Value × 365 ÷ COGS<sub>12M</sub></code>
(last-12 snapshot months); <code>DPO = AP Open × 365 ÷ COGS<sub>12M</sub></code> using the mean
month-end AP over the last 12 (the DAX point-in-time value is a noisy trough at 2026-06-30).
<code>CCC = DIO + DSO − DPO</code>. Parity exact on every component.</p>
{figure("2026-09_06_cash_conversion_cycle.png", "CCC composition vs benchmark bands; DSO by market.")}
<table>
<tr><th>Metric</th><th class="n">VoltEdge</th><th class="n">Benchmark</th></tr>
<tr><td><strong>DIO</strong></td><td class="n bad"><strong>158 days</strong></td><td class="n">45–75</td></tr>
<tr><td>DSO</td><td class="n">17.8 days</td><td class="n">US/EU low, BR higher</td></tr>
<tr><td>DPO</td><td class="n">41 days</td><td class="n">30–60</td></tr>
<tr><td><strong>CCC</strong></td><td class="n"><strong>≈134 days</strong></td><td class="n">lower is better</td></tr>
</table>
<p>Average inventory rose from $5.85M (24m) to <strong>$8.31M (last 12m)</strong>. At DIO 75 it
would be ~$3.95M → <strong>≈$4.4M of cash freed</strong>. Payables run at terms (paid ~1 day past
due) — no easy cash there. Brazil DSO 36.7 days (12× installments) + $114k/yr merchant-funded
"sem juros" financing; on current numbers a good trade for +$4.6M revenue and the best CM.</p>
<h4>Limitations</h4>
<ul>
<li>DIO basis matters: last-12m gives 158, full-24m gives 111 — both well above benchmark; pick one.</li>
<li>Month-end AP is a modelled proxy for a true daily AP balance.</li>
<li>No cost-of-capital rate applied — the $4.4M is gross cash, not an interest saving.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> CFO priority #1: an inventory-reduction program —
SKU-level reorder points, kill dead stock (§9) — targeting DIO 90 within two quarters. Frees ~$3M
immediately. Do not extend DPO further. Put CCC and Inventory Value trend on the Executive Summary.</div>
''')}

{section("7", "Contribution margin depends on cheap CAC", "CFO / CMO", f'''
<p><strong>Decision.</strong> How much confidence to place in the "we reached break-even" message.</p>
<h4>Method (both tracks — <code>parity/07_marketing_efficiency.py</code>)</h4>
<p><code>docs/06 §08</code>: <code>New Customers</code> = customers whose first-ever non-cancelled
order (<code>MIN(order_date_key)</code>) is in the period; <code>Blended CAC = Spend ÷ New
Customers</code>; <code>MER = Net Revenue ÷ Spend</code>. Sliced full/CY/PY, by channel group, vs
<code>fact_target</code>. SQL: DuckDB view on first order; Python: pandas. Parity exact.</p>
{figure("2026-09_07_marketing_efficiency.png", "Marketing intensity & CAC PY vs CY; CY contribution-margin sensitivity to CAC.")}
<table>
<tr><th></th><th class="n">PY</th><th class="n">CY</th></tr>
<tr><td>Blended CAC</td><td class="n">$30.26</td><td class="n">$26.91 (target $32.80 → −18%)</td></tr>
<tr><td>MER (Net Rev ÷ spend)</td><td class="n">8.4×</td><td class="n">12.8× (benchmark 6–10×)</td></tr>
<tr><td>Marketing as % of Net Revenue</td><td class="n">11.9%</td><td class="n">7.8%</td></tr>
</table>
<p>The −4.1pp drop in marketing intensity ≈ the entire +5.4pp CM swing. Channel mix did <em>not</em>
shift — 96.7% of spend is paid both years; what changed is efficiency (41% of CY new customers now
arrive via non-paid channels; paid-only CAC is $44.26). <strong>CY contribution margin: +$325k at
actual CAC; +$111k at PY CAC; −$51k at plan CAC.</strong></p>
<h4>Limitations</h4>
<ul>
<li>Left-censoring: dataset starts 2024-07, so PY/full new-customer revenue reads as 100%; only the
CY split (84% new / 16% returning by the DAX definition) is meaningful — reconciled with the 44%
order-month figure in §8.</li>
<li>ROAS/attribution is last-touch at channel level, not an MMM.</li>
<li>CM-sensitivity flexes only CAC, holding new-customer count fixed — a cushion estimate, not a forecast.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> Reframe the board message to "positive at current
CAC". Track marginal CAC monthly; stress-test at $33 and $45. Given MER 12.8×, test scaling paid
spend to a marginal-CAC ceiling (~$45) — there is likely profitable volume above budget.</div>
''')}

{section("8", "Retention: healthy, not yet the engine", "VP Customer / CEO", f'''
<p><strong>Decision.</strong> Whether "repeat revenue gets us to profit" is credible, and where
retention spend should go.</p>
<h4>Method (both tracks — <code>parity/08_retention_cohorts.py</code>)</h4>
<p><code>Repeat Purchase Rate % = (customers with &gt;1 non-cancelled order) ÷ (customers with ≥1)</code>.
Cohort retention: acquisition month = month of first order; share of the cohort ordering again at
month-offset <em>n</em>, averaged over cohorts with ≥6 months maturity. New-vs-returning revenue at
(customer, calendar-month) grain. Repeat rates parity-exact to 1e-9.</p>
{figure("2026-09_08_retention_cohorts.png", "Cohort re-order curve and new-vs-returning revenue by month.")}
<ul>
<li>Lifetime repeat rate <strong>37.6%</strong> (above the 25–35% benchmark); 1.67 orders/customer.
Newer markets out-repeat the US: DE 40.5%, BR 40.2%, UK 40.0%, <strong>US 36.0%</strong>.</li>
<li>Re-order decays fast: 16% at +1 month, 9.5% at +3, 2.1% at +12. Only 26.5% of buyers are "Active".</li>
<li><strong>Two "returning revenue" numbers, both correct:</strong> DAX <code>New Revenue %</code>
(customer "new" for the whole first year) → 16% returning; order-month grain → 44% returning. The
gap is the within-year repeat orders of customers acquired this year.</li>
</ul>
<h4>Limitations</h4>
<ul>
<li>Left-censoring flatters newer-market repeat rates and depresses the tail of the average curve.</li>
<li>Retention curve is order-count based; a revenue curve decays slightly slower.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> Own a +1-to-+3-month reactivation program (lifecycle
CRM, accessory cross-sell into margin-carrying categories); target +1-month re-order 16% → 20%. Report
both returning-revenue definitions with the reconciliation. Investigate why US repeat lags the newer
markets by 4pp.</div>
''')}

{section("9", "Returns: an $1.65M margin leak, mostly fixable", "VP Customer / COO", f'''
<p><strong>Decision.</strong> Whether returns need a dedicated program, and where.</p>
<h4>Method (both tracks — <code>parity/09_returns.py</code>)</h4>
<p><code>Return Rate % = SUM(returned_qty) ÷ Units Sold</code> (product lines). Net margin drag =
refund − <code>cogs_recovered_usd</code>. Sliced by category, market, reason. Rate &amp; value parity exact.</p>
{figure("2026-09_09_returns.png", "Return rate by category vs benchmark; refund value by reason (controllable vs choice).")}
<ul>
<li>Return rate <strong>8.0%</strong> — mid-benchmark, flat YoY and across all four markets.</li>
<li><strong>Net margin drag $1.65M</strong> over 24m (refund $3.48M − COGS recovered $1.83M) =
5.3% of Net Revenue, 29% of gross profit.</li>
<li>Restock rate only <strong>54%</strong> — 46% of returned units are written down. Biggest lever
on the drag.</li>
<li>Smartphones 11.8% and Wearables 11.2% (highest) — the categories US growth concentrates into.
<strong>63% of refunds are ops/quality-driven</strong> (defective $963k, "not as described" $545k,
wrong item, damaged, late).</li>
</ul>
<h4>Limitations</h4>
<ul>
<li><code>fact_returns</code> refund total ($3.48M) is ~1% above the <code>fact_order_lines</code>
refund column used for Net Revenue — a few returns map to cancelled/re-adjusted orders.</li>
<li>"Controllable vs choice" is an analyst bucketing of the 7 reason codes.</li>
<li>Unit-based rate; a value-based rate would be higher for Smartphones/Laptops.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> Two KPIs on the Ops/CRM page: restock rate (54% →
70%, ≈ +$180k per +10pp) and controllable return rate. Prioritise QA + PDP content on Smartphones
and Wearables. Combined realistic recovery ≈ $0.4–0.7M/yr.</div>
''')}

{section("10", "Fulfilment & shipping-fee recovery", "COO / CFO", f'''
<p><strong>Decision.</strong> Where (if anywhere) to invest in logistics.</p>
<h4>Method (both tracks — <code>parity/10_fulfillment.py</code>)</h4>
<p><code>docs/06 §10</code> KPIs on non-cancelled <code>fact_orders</code>, sliced by market,
carrier, Q4 vs rest. SQL: DuckDB <code>COUNT(DISTINCT …) FILTER</code>; Python: pandas. Parity exact
on every KPI and market cell.</p>
{figure("2026-09_10_fulfilment.png", "Service levels vs benchmark; shipping cost vs fee recovery by market.")}
<table>
<tr><th>KPI</th><th class="n">VoltEdge</th><th class="n">Benchmark</th></tr>
<tr><td>On-time delivery %</td><td class="n">94.5%</td><td class="n">92–96%</td></tr>
<tr><td>Avg delivery days</td><td class="n">4.5</td><td class="n">3–6</td></tr>
<tr><td>Perfect order rate %</td><td class="n bad">82.9%</td><td class="n">88–93%</td></tr>
<tr><td>Shipping cost recovery %</td><td class="n bad">28%</td><td class="n">—</td></tr>
</table>
<p>Service levels are uniform and on-target; carrier spread is tiny. Shipping costs $1.74M/24m;
fees recover ~$0.49M → <strong>~$0.6M/yr structural loss</strong>. Recovery: UK 38%, US 31%, DE
29%, <strong>BR 5%</strong>. Q4 cost/order +12% — manageable. <strong>Corrects §3:</strong> the UK
CM drag is gross margin, not shipping (UK ship cost/order is the lowest of the four).</p>
<h4>Limitations</h4>
<ul>
<li>Synthetic carrier data shows little differentiation — don't over-read "no bad carrier".</li>
<li>Free-shipping-threshold logic is embedded in the fee, not modelled separately.</li>
</ul>
<div class="rec"><strong>Recommendation.</strong> CFO/CMO joint call on the free-shipping threshold
market by market, starting with Brazil. Lifting blended recovery 28% → 45% ≈ +$0.3–0.4M/yr
contribution. Do not spend on carrier changes. Track shipping cost recovery % on the Executive
Summary alongside CCC.</div>
''')}

<hr>
<h3>Cross-finding synthesis</h3>
<p>The findings compound. VoltEdge's reported +137% growth is mostly one-time expansion (§2); the
underlying US engine grows +40% but purely on volume into its thinnest-margin, highest-return
categories (§4, §9), so gross margin barely moves. Contribution margin turned positive (§3) almost
entirely because CAC came in 18% under plan (§7) — revert to plan and it is negative again. Two
controllable leaks (promo depth §5 ≈ $0.3M/yr, shipping subsidy §10 ≈ $0.6M/yr) are each comparable
to the whole contribution margin. And the largest prize sits on the balance sheet: ~$4.4M of cash
frozen in an oversized inventory (§6). The credible long-run profit path is repeat revenue (§8) —
healthy at 37.6% but too young to carry the plan. <strong>Priority order: (1) working-capital /
inventory program, (2) protect &amp; stress-test CAC, (3) category mix-up + returns cost, (4)
promo &amp; shipping-fee discipline, (5) fund +1–3 month retention.</strong></p>

<p class="meta">All numbers reproduced on two independent stacks (DuckDB SQL + Python/pandas) from
<code>data/curated/</code>; parity scripts in <code>data_analysis/parity/</code>, per-finding
write-ups in <code>data_analysis/findings/</code>.</p>
"""

(HERE / "board_summary.html").write_text(html_doc("VoltEdge — Board Summary", board_body), encoding="utf-8")
(HERE / "deep_dive.html").write_text(html_doc("VoltEdge — Deep Dive", deep_body), encoding="utf-8")
print("wrote", HERE / "board_summary.html")
print("wrote", HERE / "deep_dive.html")

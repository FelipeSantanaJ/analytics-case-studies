# Finding 04 — US like-for-like growth is almost all volume, with no pricing power

**Decision it informs:** whether the US growth engine can carry the business to profit — a
volume-only, flat-margin expansion doesn't, a pricing/mix-up story might.
**Audience:** CEO, CFO, VP E-commerce.
**Time window:** CY 2025-07→2026-06 vs PY, **US only** (`dim_market.is_comparable_base`).

## Question
US grew +40% like-for-like (Finding 02). Is that **more units**, **higher prices**, or a
**shift toward richer categories**?

## Method (both tracks — `parity/04_price_volume_mix_us.py`, 7/7 checks pass)
Price/Volume/Mix per `docs/06 §07`, on US non-cancelled `fact_order_lines`, by
`dim_product.category`:
- `Units Sold` = `SUM(quantity)` where `line_type = 'product'`; `Gross Revenue` = `SUM(gross_amount_usd)`
- `ASP` = Gross Revenue ÷ Units
- **Price** = Σ_cat (ASP_CY − ASP_PY) × Units_PY,cat
- **Volume** = GrossRev_PY,total × (Units_CY − Units_PY) ÷ Units_PY
- **Mix** = ΔGrossRev − Price − Volume
- SQL: DuckDB view + per-period category aggregate. Python: pandas groupby. Parity exact.

## Evidence

US Gross Revenue **$8.55M → $12.01M** (Δ **+$3.45M, +40.3%**); units **75,963 → 109,594 (+44.3%)**.

| Effect | $ | Share of the gain |
|---|---:|---:|
| **Volume** (more units at PY mix) | **+$3.79M** | **+110%** |
| Price (higher ASP within category) | +$0.26M | +8% |
| Category mix (shift between categories) | −$0.60M | −17% |

By category (Gross Revenue, ASP, price effect, share shift):

| Category | Gross PY | Gross CY | ASP PY→CY | Price effect | Rev-share Δ |
|---|---:|---:|---:|---:|---:|
| Laptops & Tablets | $3.54M | $4.72M | ↑ | +$227k | −2.0pp |
| Smartphones | $2.57M | $3.93M | ↑ | +$119k | **+2.7pp** |
| Audio | $0.69M | $1.02M | ≈flat | −$1k | +0.4pp |
| Gaming | $0.40M | $0.54M | ↓ | −$46k | −0.1pp |
| Wearables | $0.58M | $0.73M | ↑ | +$19k | −0.7pp |

## What the data says
1. **~110% of US growth is unit volume.** VoltEdge is selling a lot more boxes to a lot more
   customers, at essentially the same prices.
2. **No pricing power.** Within-category ASP moved the total only +$0.26M (+8% of the gain) —
   and that is concentrated in Laptops and Smartphones, likely spec/model drift rather than
   deliberate price increases.
3. **Category mix is a −$0.60M drag.** Share is shifting **toward Smartphones (+2.7pp)** — the
   thinnest-margin category (8–14% gross per `docs/01`) — and **away from Laptops (−2.0pp)**.
   This is the composition risk behind the flat gross margin in Finding 03: the US is growing
   fastest in its worst-margin category.
4. Ties out: +40% volume-led growth + flat mix-adjusted price + only +1.3pp gross margin
   (Finding 03) + −2% vs plan (Finding 02) ⇒ the US engine is a **volume machine at a fixed
   thin margin**, not a business moving upmarket.

## Limitations & assumptions
- ASP numerator (`Gross Revenue`) includes warranty lines while the denominator (`Units`)
  is product-only — this is the DAX definition; it inflates ASP by the warranty attach, but
  consistently across CY/PY so the *effect* decomposition is sound.
- PVM is on **Gross Revenue**, not margin dollars — it explains the revenue bridge, not the
  profit bridge. A margin-weighted mix effect would be more negative given the Smartphone shift.
- "Unknown" category ($0.10M→$0.06M, `product_key = -1`) left in; its −$55k price effect is
  a late-arriving-key artefact, immaterial.
- Single comparable market (US). UK/DE PVM from 2025-01 is possible but out of scope here.

## Recommendation
- **Merchandising/pricing:** there is untapped room to push ASP and attach in audio,
  accessories and wearables — the margin-carrying categories that are *losing* share. A
  deliberate mix-up plan is the cheapest path to margin, worth ~1–2pp on a $12M base.
- **Plan realism:** if FY27 US growth stays volume-led at this margin, contribution margin
  does **not** improve from revenue alone — the CFO should not assume operating leverage.
- Watch the Smartphone share creep; set a category-mix guardrail in the exec pack.

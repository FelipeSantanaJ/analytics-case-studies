# AeroVanti SkyPoints — Visual Identity

**Document status:** Phase 5 deliverable. The single source of truth is
`assets/brand.py`, imported by `assets/gen_logo.py` and
`powerbi/gen_report_visuals.py` so the logo, page backgrounds, theme and every
scripted visual override draw from the same values.

---

## Tone

Corporate, restrained, CFO-facing. Aviation-adjacent, not a marketing page — this
is an A/B test read-out and a program-health dashboard.

## Palette

| Role | Hex | Use |
|---|---|---|
| **AeroVanti blue** | `#0B5FA5` | brand, primary series, table accent |
| Navy | `#0A2A43` | header band, darkest ink |
| **Amber** (accent) | `#E08A1E` | treatment arm · current period · "look here" |
| **Steel** (comparison) | `#5C8CB8` | control arm · prior year · target |
| Page ground | `#EEF3F8` | light body |
| Card | `#FFFFFF` | |
| Gridline / hairline | `#E4E9EF` / `#D3DBE3` | quiet |
| Good / Bad / Neutral | `#2E7D5B` / `#C0453B` / `#8A8A99` | semantic; **breakage / lapse / liability are lower-is-better** |

Categorical ramp: blue, steel, amber, teal `#3E9C93`, plum `#8E5EA8`, grey `#6B7280`,
rose `#C77CA6`, indigo `#4C6EA6`. Tier ramp: Blue `#4C6EA6`, Silver `#9AA6B2`,
Gold `#C9922E`, Platinum `#5B6B7A`.

## Type

Segoe UI family. Semibold for titles / callouts, Regular for body / labels.
Callout (KPI value) 30 px, title 12–15 px, label 9 px.

## Signature element (every page)

Navy header band (58 px) with the **AeroVanti** wordmark (amber "Vanti"), an amber
3 px hairline under it, a right-aligned "SkyPoints — Loyalty Analytics" label, then
the page title + one-line question on the light body. Below: a slicer row
(Analysis period · Experiment arm · Tier stratum), a white rounded KPI frame with
6 value cards, then two content rows on the 3-30-300 gradient.

## Assets emitted (`assets/gen_logo.py` → `powerbi/assets/`)

- `logo_mark_on_light.png` / `_on_dark.png` — rounded-square tile, upward chevron
  ("sky") + an amber points dot.
- `wordmark_on_light.png` / `_on_dark.png` — "AeroVanti" lockup.
- `bg_01_executive.png` (1280×860) · `bg_02_tiers.png` · `bg_03_experiment.png` ·
  `bg_04_funnel.png` (1280×720) — full-page backgrounds carrying the band + title.
- `_page_heights.json`.

## Theme

`powerbi/theme/theme.json` — `dataColors`, semantic colours, 4 text classes, and
`visualStyles` for ~20 visual types + `page`: white card background, 8 px rounded
border, no drop shadow on cards / KPIs / frames, a soft shadow on charts via the
`*` wildcard, data labels on for bar / column / line / combo / waterfall, gridlines
only on the value axis. `pbir theme validate` passes.

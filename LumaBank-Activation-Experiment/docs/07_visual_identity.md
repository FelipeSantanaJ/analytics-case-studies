# LumaBank — Visual Identity

**Document status:** Phase 5 deliverable. The single source of truth is `assets/brand.py`,
imported by `assets/gen_logo.py` and `powerbi/gen_report_visuals.py` (Phase 8) so the logo,
page backgrounds, theme, and every scripted visual override draw from the same values.

---

## Tone

Trust-first fintech, not a marketing page — this is an incident read-out and an experiment
integrity monitor as much as it is a dashboard. Deliberately **not** blue (AeroVanti,
VoltEdge) and not violet or forest green (Voxa+, SwiftBite), and deliberately **not**
money-green either.

## Palette

| Role | Hex | Use |
|---|---|---|
| **Petrol** (brand) | `#0E4A52` | brand, primary series, table accent |
| Petrol deep | `#0A333A` | header band, darkest ink |
| **Coral** (accent) | `#E2624B` | **treatment arm** · current period · the break · "look here" |
| **Stone** (comparison) | `#93A29C` | **control arm** · prior period · target |
| Page ground | `#F3F1EC` | warm off-white — not the sibling projects' cool blue-grey |
| Card | `#FFFFFF` | |
| Gridline / hairline | `#E9E5DC` / `#D8D2C4` | quiet |
| Good / Bad / Neutral | `#3C8073` / `#C0453B` / `#8A8F8A` | semantic; **KYC rejection / fraud / tickets are lower-is-better** |

Categorical ramp: petrol, stone, coral, gold `#C99A3E`, plum `#7A5C7E`, slate `#5B6B72`,
dusty rose `#C77C6E`, deep blue `#3B5B73`. Channel ramp (`CHANNEL_COLORS`): paid_social
slate-blue, organic petrol, app_store_search plum, referral gold, influencer dusty rose,
unknown grey. SRM `alert_state` ramp (`ALERT_COLORS`): ok teal-green, warn gold,
alert bad-red — used on the Integrity Monitor page's daily strip.

## Type

Segoe UI family. Semibold for titles / callouts, Regular for body / labels. Callout (KPI
value) 30 px, title 12–15 px, label 9 px.

## Signature element (every page)

Petrol header band (58 px) with the **LumaBank** wordmark ("Luma" ink, "Bank" coral), a
coral 3 px hairline under it, a right-aligned "Activation Experiment — Fintech Analytics"
label, then the page title + one-line question on the warm light body. Below: a slicer row
(Cohort · Experiment arm · Acquisition channel), a white rounded KPI frame, then two
content rows on the 3-30-300 gradient.

## Assets emitted (`assets/gen_logo.py` → `powerbi/assets/`)

- `logo_mark_on_light.png` / `_on_dark.png` — rounded-square tile, a rising step-line
  ("activation") to a coral dot (the Day-7 activation moment) — not a vault, shield, or
  piggy-bank cliché.
- `wordmark_on_light.png` / `_on_dark.png` — "LumaBank" lockup.
- `bg_01_executive.png` (1280×860) · `bg_02_funnel.png` · `bg_03_integrity.png` ·
  `bg_04_readout.png` (1280×720) — full-page backgrounds carrying the band + title.
- `_page_heights.json`.

## Theme

`powerbi/theme/theme.json` — `dataColors`, semantic colours, 4 text classes. Lean, matching
the AeroVanti-style "PBI lite" scope (Phase 0): no `visualStyles` block — per-visual
formatting is set directly on each visual in Phase 8, not centralised in the theme.

*End of Phase 5 deliverable.*

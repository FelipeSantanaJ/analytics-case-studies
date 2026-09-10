# SwiftBite Delivery — Visual Identity

**Document status:** Phase 5 deliverable. The single source of truth is
`assets/brand.py`, imported by `assets/gen_logo.py`, the Phase 6/8 Power BI scripts
and the Phase 10 board deliverables so the logo, page backgrounds, `theme.json` and
every scripted override draw from the same values.

> **PT.** Identidade própria do SwiftBite — não reutiliza navy do AeroVanti/VoltEdge nem
> violeta do Voxa+. Uma cor de marca (verde-floresta), um accent (tangerina — zona
> tratada / período atual / "olhe aqui"), uma cor de comparação (cinza-pedra frio —
> braço de controle / período anterior / meta), neutros mornos e gridlines discretas.

---

## Tone

Corporate, restrained, operations- and finance-facing. Delivery-adjacent, not a
marketing page — this is a marketplace-liquidity diagnosis and a randomized
incentive-experiment read-out.

## Palette

| Role | Hex | Use |
|---|---|---|
| **SwiftBite green** | `#1E6B4F` | brand, primary series, table accent, hyperlink |
| Green-deep | `#113A2C` | header band, darkest ink on light |
| **Tangerine** (accent) | `#E8823C` | treated zone · current period · "look here" |
| **Stone** (comparison) | `#8090A0` | control arm · prior period · target · secondary series |
| Page ground | `#F2F4F1` | warm-neutral, faintly green off-white |
| Card | `#FFFFFF` | |
| Gridline / hairline | `#E6E9E4` / `#D6DAD3` | quiet |
| Good / Bad / Neutral | `#2E7D5B` / `#C0453B` / `#8A8A99` | semantic; **ETA, cancellation rate, idle-courier ratio and incentive cost are lower-is-better** |

Categorical ramp: green, stone, tangerine, teal `#3E9C93`, plum `#8E5EA8`, ochre
`#C9922E`, rose `#C77CA6`, grey `#6B7280`.

**Supply-stress tier ramp** (supply-short zones read "hot"): short `#E8823C` · balanced
`#8090A0` · long `#1E6B4F`. **Experiment arm:** treatment `#E8823C` · control `#8090A0`.

Diverging scale (vs-target, lift, spillover): `#C0453B` → `#EAD9C4` → `#2E7D5B`.

## Type

Segoe UI family. Semibold for titles / callouts, Regular for body / labels. Callout
(KPI value) 30 px, title 15 px, header 12 px, label 9 px. Inks: title `#17241E`,
body `#33403A`, muted `#6B7A72`; on dark `#F0F5F1` / `#B7C7BD`.

## Signature element (every page)

Green-deep header band (58 px) with the **SwiftBite** wordmark (tangerine "Bite"), a
tangerine 3 px hairline under it, a right-aligned "Marketplace Analytics" label, then
the page title + its one business question on the light body, and a hairline divider.
Below: a slicer row (Analysis period · Arm · Zone / stress tier), a white rounded KPI
frame with 6 value cards, then two content rows on the 3-30-300 gradient.

## Assets emitted (`python assets/gen_logo.py` → `powerbi/assets/`)

- `logo_mark_on_light.png` / `_on_dark.png` — rounded-square tile, two forward speed
  chevrons ("swift") + a trailing tangerine dot ("bite").
- `wordmark_on_light.png` / `_on_dark.png` — "SwiftBite" lockup, tangerine "Bite".
- `bg_01_executive.png` (1280×860) · `bg_02_health.png` · `bg_03_experiment.png` ·
  `bg_04_courier.png` (1280×720) — full-page backgrounds carrying the band + title.
- `_page_heights.json` — page → canvas height, read in Phase 8.

## Theme

`powerbi/theme/theme.json` — `dataColors` (the 8-colour ramp), semantic colours, the
diverging min/center/max, 4 text classes, and a `visualStyles` baseline: white card
background, 8 px rounded `#D6DAD3` border, no drop shadow, no visual header, and the
page ground `#F2F4F1`. The per-visual-type overrides (data labels, axis gridlines,
KPI/card specifics) are promoted into the theme during Phase 6/8 via the `pbir` CLI;
`pbir theme validate` must pass.

*End of Phase 5 deliverable.*

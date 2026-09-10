# Voxa+ — Power BI project

Everything here is **generated from code**. Do not hand-edit the `.SemanticModel` or
`.Report` folders.

```
python powerbi/gen_semantic_model.py      # (re)build the .pbip + TMDL from data/curated/
python assets/gen_logo.py                 # (re)build the brand PNGs + page backgrounds
pbir theme validate powerbi/theme/theme.json
bash powerbi/build_report.sh              # Phase 8 — build the 7 report pages
```

## Structure

| Path | What |
|---|---|
| `VoxaChurnDiagnosis.pbip` | the project file — open this in Power BI Desktop |
| `VoxaChurnDiagnosis.SemanticModel/` | TMDL model: `definition/{database,model,expressions,relationships}.tmdl` + `definition/tables/*.tmdl` |
| `VoxaChurnDiagnosis.Report/` | report shell (`definition.pbir` points at the model); Phase 8 fills `definition/` with pages |
| `theme/theme.json` | the report theme (Phase 5) |
| `assets/` | generated brand PNGs + `_page_heights.json` |
| `gen_semantic_model.py` | regenerates the model from the curated Parquet schemas |

## The model

- **24 imported tables** — one per `data/curated/*.parquet` (except `fact_viewing_daily`,
  which stays analyst-only for Phase 10; the model uses the compact
  `fact_engagement_device_month` rollup instead).
- **5 helper tables** built from M `#table(...)` literals: `Reporting Currency` (currency
  slicer), `P&L Line` (finance-page ordering, related to `fact_finance_month`),
  `Subscriber Bridge` and `Funnel Stage` (disconnected, used in DAX), and `_Measures`
  (measure holder — populated in Phase 7).
- Every table imports through the **`pDataFolder`** parameter (`expressions.tmdl`), default
  `…/voxaplus-churn-diagnosis/data/curated`.
- **34 relationships**: `dim_date[date_key]` to each fact's date key; `dim_subscriber` is
  the hub (market / channel / tier / device slice through it for subscriber-grain facts);
  direct `dim_market` links only for the aggregate facts with no subscriber path;
  `dim_content[release_date_key] → dim_date` is **inactive** (role-playing).

## First open (one time)

The generator produces a valid project, but Power BI Desktop needs a manual pass the first
time:

1. Open `VoxaChurnDiagnosis.pbip`.
2. **Transform data → `pDataFolder`** — confirm it points at this repo's `data/curated`
   folder, then **Close & Apply** / **Refresh**.
3. Model view → select `dim_date` → **Mark as date table** → date column = `date`.
   *(Phase-7 time-intelligence measures avoid `SAMEPERIODLASTYEAR` and use `month_sort`
   arithmetic, so this is belt-and-braces, but keep it marked.)*
4. Close Power BI Desktop before running `build_report.sh`.

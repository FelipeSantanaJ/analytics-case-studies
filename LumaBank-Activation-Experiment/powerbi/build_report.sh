#!/usr/bin/env bash
# build_report.sh — rebuild the LumaBank Activation Power BI report end to end.
#
#   cd powerbi && bash build_report.sh
#
# Regenerates brand assets, the semantic model, the DAX doc, and the report
# itself (4 pages) via the `pbir` CLI, then applies the LumaBank theme,
# page backgrounds, page-level filters, and sort orders. Safe to re-run —
# wipes and recreates powerbi/LumaBankActivation.Report each time.
#
# Close Power BI Desktop first (the build aborts if PBIDesktop.exe /
# msmdsrv.exe is running — pbir would otherwise validate against the stale
# live model).
#
# Windows/OneDrive note: `pbir rm` / `pbir pages rename` occasionally hit a
# transient WinError 5 (Access denied) deleting the temp `.{page,visual}
# -delete-*` folder pbir creates during a safe delete — a OneDrive
# Files-on-Demand lock on a just-touched folder, the same class of issue
# `etl/utils.py::_atomic_write` retries around for Parquet writes. `pbir_run`
# below retries those calls; if all retries are exhausted, delete the
# reported `.{page,visual}-delete-*` path by hand (Explorer or PowerShell
# `Remove-Item -Force` succeed where the retry sometimes still won't) and
# re-run this script.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
NAME="LumaBankActivation"
RPT="$NAME.Report"

if command -v tasklist >/dev/null 2>&1; then
  if tasklist 2>/dev/null | grep -Eiq "PBIDesktop\.exe|msmdsrv\.exe"; then
    echo "ERROR: Power BI Desktop / Analysis Services is running. Close it and re-run." >&2
    exit 1
  fi
fi

# Retry wrapper for pbir calls that delete a folder (OneDrive lock workaround).
pbir_run() {
  local tries=4 i out
  for ((i = 1; i <= tries; i++)); do
    if out=$(pbir -q "$@" 2>&1); then
      echo "$out"
      return 0
    fi
    if echo "$out" | grep -qiE "WinError 5|being used by another process"; then
      echo "  (retry $i/$tries after a lock: $*)" >&2
      sleep 2
      continue
    fi
    echo "$out" >&2
    return 1
  done
  echo "$out" >&2
  return 1
}

echo "== 1/6  brand assets"
python "$ROOT/assets/gen_logo.py"

echo "== 2/6  semantic model (TMDL) + DAX measures + DAX doc"
python "$ROOT/powerbi/gen_semantic_model.py"
python "$ROOT/etl/gen_dax_doc.py"

echo "== 3/6  fresh report, rebound to the local semantic model"
[ -d "$RPT" ] && pbir_run rm "$RPT" -f || true
pbir_run new report "$RPT" --thick --no-title
pbir_run report rebind "$RPT" --local "../$NAME.SemanticModel"

echo "== 4/6  theme"
pbir -q theme create-template --new-template theme/theme.json --name lumabank \
  --description "LumaBank petrol + coral fintech identity" 2>/dev/null || true
pbir_run theme apply-template "$RPT" lumabank -f

echo "== 5/6  pages + visuals"
pbir_run pages rename "$RPT/Page 1.Page" --to "Executive Overview" -f
pbir_run pages resize "$RPT/Executive Overview.Page" --width 1280 --height 860
pbir_run pages background "$RPT/Executive Overview.Page" --image assets/bg_01_executive.png
pbir_run add visual "$RPT/Executive Overview.Page" --from-json _visuals_01_executive.json

pbir_run add page "$RPT/Onboarding Funnel.Page" -n "Onboarding & Activation Funnel"
pbir_run rm "$RPT/Onboarding & Activation Funnel.Page/Title.Visual" -f
pbir_run pages background "$RPT/Onboarding & Activation Funnel.Page" --image assets/bg_02_funnel.png
pbir_run add visual "$RPT/Onboarding & Activation Funnel.Page" --from-json _visuals_02_funnel.json

pbir_run add page "$RPT/Experiment Integrity.Page" -n "Experiment Integrity Monitor"
pbir_run rm "$RPT/Experiment Integrity Monitor.Page/Title.Visual" -f
pbir_run pages background "$RPT/Experiment Integrity Monitor.Page" --image assets/bg_03_integrity.png
pbir_run add visual "$RPT/Experiment Integrity Monitor.Page" --from-json _visuals_03_integrity.json
pbir_run add filter fact_srm_daily experiment_phase -p "$RPT/Experiment Integrity Monitor.Page" --values original
pbir_run visuals sort "$RPT/Experiment Integrity Monitor.Page/alloc-vs-srm.Visual" -f "fact_srm_daily.assign_date" -d Ascending
pbir_run visuals sort "$RPT/Experiment Integrity Monitor.Page/fallback-trend.Visual" -f "fact_srm_daily.assign_date" -d Ascending
pbir_run visuals sort "$RPT/Experiment Integrity Monitor.Page/mismatch-trend.Visual" -f "fact_srm_daily.assign_date" -d Ascending

pbir_run add page "$RPT/Experiment Readout.Page" -n "Experiment Readout"
pbir_run rm "$RPT/Experiment Readout.Page/Title.Visual" -f
pbir_run pages background "$RPT/Experiment Readout.Page" --image assets/bg_04_readout.png
pbir_run add visual "$RPT/Experiment Readout.Page" --from-json _visuals_04_readout.json
pbir_run visuals bind "$RPT/Experiment Readout.Page/guardrails-card.Visual" -a "Values:_Measures.Exp Fraud Delta pp"
pbir_run visuals bind "$RPT/Experiment Readout.Page/guardrails-card.Visual" -a "Values:_Measures.Exp Tickets per 1k Delta"
pbir_run add filter fact_activation in_analysis_flag -p "$RPT/Experiment Readout.Page" --values TRUE

pbir_run pages move "$RPT/Onboarding & Activation Funnel.Page" --to 2
pbir_run pages move "$RPT/Experiment Integrity Monitor.Page" --to 3
pbir_run pages move "$RPT/Experiment Readout.Page" --to 4
pbir_run pages active-page "$RPT" "Executive Overview"

echo "== 6/6  validate"
pbir -q validate "$RPT" --all

echo
echo "Done. Open powerbi/$NAME.pbip in Power BI Desktop:"
echo "  1. Transform data -> set pDataFolder to $ROOT/data/curated -> Close & Apply"
echo "  2. Model view -> mark 'dim_date' as a date table (column: date)"

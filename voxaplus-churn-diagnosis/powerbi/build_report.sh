#!/usr/bin/env bash
# build_report.sh — rebuild the Voxa+ Power BI report end to end.
#
#   cd powerbi && bash build_report.sh
#
# Regenerates the brand assets, the semantic model, and the report layout, then
# drives `pbir` to build all 7 pages. Safe to re-run. Close Power BI Desktop first
# (the build aborts if PBIDesktop.exe / msmdsrv.exe is running — pbir would
# otherwise validate against the stale live model).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"

export PBIR_ADOMD_DIR="${PBIR_ADOMD_DIR:-/c/Program Files/Power BI Report Builder}"

# --- abort if Power BI Desktop is running -------------------------------------
# (pbir reads the model from the on-disk TMDL, but a running Desktop that holds
#  THIS .pbip open locks files and can shadow the model. Override with
#  VOXA_ALLOW_DESKTOP=1 only if Desktop has a different report open.)
if [ "${VOXA_ALLOW_DESKTOP:-0}" != "1" ] && command -v tasklist >/dev/null 2>&1; then
  if tasklist 2>/dev/null | grep -Eiq "PBIDesktop\.exe|msmdsrv\.exe"; then
    echo "ERROR: Power BI Desktop / Analysis Services is running. Close it and re-run" >&2
    echo "       (or re-run with VOXA_ALLOW_DESKTOP=1 if a different report is open)." >&2
    exit 1
  fi
fi

echo "== 1/4  brand assets"
python "$ROOT/assets/gen_logo.py"

echo "== 2/4  semantic model (TMDL) + DAX measures"
python "$ROOT/powerbi/gen_semantic_model.py"
python "$ROOT/etl/gen_dax_doc.py"
# drop Power BI's imported-data snapshot so the next open re-imports cleanly
rm -f "$ROOT/powerbi/VoxaChurnDiagnosis.SemanticModel/.pbi/cache.abf"

echo "== 3/4  report layout manifest"
python "$ROOT/powerbi/gen_report_visuals.py"

echo "== 4/4  drive pbir -> VoxaChurnDiagnosis.Report"
python "$ROOT/powerbi/_drive_pbir.py"

echo
echo "Done. Open powerbi/VoxaChurnDiagnosis.pbip in Power BI Desktop:"
echo "  1. Transform data -> set pDataFolder to $ROOT/data/curated -> Close & Apply"
echo "  2. Model view -> Mark 'dim_date' as a date table (column: date)"
echo "  3. Review each page; iterate with pbir + 'pbir desktop refresh/screenshot'."

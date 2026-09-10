#!/usr/bin/env bash
# build_report.sh — rebuild the SwiftBite Delivery Power BI report end to end.
#
#   cd powerbi && bash build_report.sh
#
# Regenerates brand assets, the semantic model, the DAX doc, and the report
# layout, then drives `pbir` to build all 4 pages. Safe to re-run.
# Close Power BI Desktop first (the build aborts if PBIDesktop.exe / msmdsrv.exe
# is running — pbir would otherwise validate against the stale live model).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
NAME="SwiftBiteDelivery"

export PBIR_ADOMD_DIR="${PBIR_ADOMD_DIR:-/c/Program Files/Power BI Report Builder}"

if [ "${SB_ALLOW_DESKTOP:-0}" != "1" ] && command -v tasklist >/dev/null 2>&1; then
  if tasklist 2>/dev/null | grep -Eiq "PBIDesktop\.exe|msmdsrv\.exe"; then
    echo "ERROR: Power BI Desktop / Analysis Services is running. Close it and re-run" >&2
    echo "       (or SB_ALLOW_DESKTOP=1 if a different report is open)." >&2
    exit 1
  fi
fi

echo "== 1/4  brand assets"
python "$ROOT/assets/gen_logo.py"

echo "== 2/4  semantic model (TMDL) + DAX measures + DAX doc"
python "$ROOT/powerbi/gen_semantic_model.py"
python "$ROOT/etl/gen_dax_doc.py"
rm -f "$ROOT/powerbi/$NAME.SemanticModel/.pbi/cache.abf" 2>/dev/null || true

echo "== 3/4  report layout manifest"
python "$ROOT/powerbi/gen_report_visuals.py"

echo "== 4/4  drive pbir -> $NAME.Report"
python "$ROOT/powerbi/_drive_pbir.py"

# minimal .pbip wrapper (pbir 'new report' does not always emit one)
cat > "$ROOT/powerbi/$NAME.pbip" <<JSON
{
  "\$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [ { "report": { "path": "$NAME.Report" } } ],
  "settings": { "enableAutoRecovery": true }
}
JSON

echo
echo "Done. Open powerbi/$NAME.pbip in Power BI Desktop:"
echo "  1. Transform data -> set pDataFolder to $ROOT/data/curated -> Close & Apply"
echo "  2. View > Themes > Browse -> powerbi/theme/theme.json"
echo "  3. Model view -> mark 'dim_date' as a date table (column: date)"

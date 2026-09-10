#!/usr/bin/env bash
# Rebuild the VoltEdge Power BI report end to end from the generators.
# Run from the powerbi/ folder:  bash build_report.sh
set -uo pipefail
Q() { grep -vE "conda.sh"; }

# pbir >= 0.9.31 validates every `add visual` field against the model schema and needs the
# .NET ADOMD client to do it. It is not on PATH on this box; point pbir at the copy that
# ships with Power BI Report Builder. Without this, `add visual --from-json` throws
# `NameError: name 'AdomdConnection' is not defined` and silently adds zero visuals.
export PBIR_ADOMD_DIR="${PBIR_ADOMD_DIR:-/c/Program Files/Power BI Report Builder}"

REPORT="VoltEdge Electronics.Report"
ETL="../etl"
SLUGS=(executive-summary sales-performance marketing-acquisition website-digital
       logistics-fulfillment crm-customer product-inventory)
TIME_VISUALS=(executive-summary/exec_trend executive-summary/exec_cmtrend
  sales-performance/sal_trend sales-performance/sal_cash
  marketing-acquisition/mkt_trend website-digital/web_trend
  logistics-fulfillment/log_trend logistics-fulfillment/log_wc
  logistics-fulfillment/log_cash crm-customer/crm_new
  crm-customer/crm_cohort product-inventory/prd_inv)

# pbir >= 0.9.31 validates every `add visual` field against a LIVE model. If Power BI
# Desktop is open on this report, pbir binds against its in-memory model, which is stale
# until Desktop is closed and reopened — renamed/added measures then read as "not found"
# and whole pages build with only their header. Refuse to run while Desktop is up.
if tasklist 2>/dev/null | grep -qiE "PBIDesktop\.exe|msmdsrv\.exe"; then
  echo "!! Power BI Desktop is running. Close it completely (so its Analysis Services"
  echo "   engine stops), then re-run this script. Reopen the .pbip afterwards."
  exit 1
fi

echo "== 1. regenerate semantic model + empty report scaffold =="
rm -rf "$REPORT"
# Power BI's imported-data snapshot (.pbi/cache.abf) is kept: for visual-only rebuilds the
# model is unchanged, so Desktop reopens with current data and no manual refresh. After a
# DATA regen (run_pipeline.py), delete it manually or hit "Atualizar" once on open.
python "$ETL/gen_logo.py" | Q
python "$ETL/gen_semantic_model.py" | Q
python "$ETL/gen_report_visuals.py" | Q

build_page() {                       # $1 = slug ; resets the page folder, then builds it
  local slug="$1" P="$REPORT/$1.Page"
  rm -rf "$REPORT/definition/pages/$slug"
  python - "$REPORT" "$slug" <<'PY'
import json, pathlib, sys
rep, slug = sys.argv[1], sys.argv[2]
heights = json.load(open(pathlib.Path("_visuals") / "_page_heights.json"))
p = pathlib.Path(rep) / "definition" / "pages" / slug; (p / "visuals").mkdir(parents=True)
(p / "page.json").write_text(json.dumps({
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": slug, "displayName": slug.replace("-", " ").title(),
  "displayOption": "FitToPage", "height": heights.get(slug, 1000), "width": 1280,
  "objects": {"background": [{"properties": {}}]}}, indent=2))
PY
  sleep 1
  # brand header as a full-canvas page background (image *visuals* do not reliably render a
  # bound RegisteredResource through pbir; a page background does). The PNG is 1280x900:
  # navy header band on top, theme page colour below.
  pbir -q pages background "$P" -i "assets/pagebg-$slug.png" -s Fill 2>&1 | Q | grep -iE "error|background" || true
  pbir -q add visual "$P" --from-json "_visuals/$slug.json" -f 2>&1 | Q
}

echo
echo "== 2. per page: brand header image + visuals =="
for slug in "${SLUGS[@]}"; do
  for attempt in 1 2 3 4; do
    OUT=$(build_page "$slug")
    echo "$OUT" | grep -E "Created [0-9]|problem|Image:"
    echo "$OUT" | grep -qE "Acesso negado|Access is denied|WinError 5|WinError 32|not found|already exist" || break
    echo "  ($slug) transient failure — retry $attempt"; sleep 4
  done
done

echo
echo "== 3. format the dynamic insight card (text, not a KPI) =="
AI="$REPORT/executive-summary.Page/exec_insight.Visual"
pbir -q set "$AI.labels.fontSize"           --value 11   2>&1 | Q | grep -iE error || true
pbir -q set "$AI.labels.preserveWhitespace" --value true 2>&1 | Q | grep -iE error || true
pbir -q set "$AI.labels.color" --json '{"solid":{"color":"#0E2340"}}' 2>&1 | Q | grep -iE error || true
pbir -q set "$AI.wordWrap.show"             --value true 2>&1 | Q | grep -iE error || true

echo
echo "== 3b. KPI 'vs Target' card: transparent, bold, > 0 green / else red =="
python - "$REPORT" <<'PY' | Q
import json, pathlib, subprocess, sys
R = sys.argv[1]
GREEN, RED = "#1E7F4F", "#B23A3A"                          # waterfall sentiment colours
LOWER_BETTER = {"Blended CAC vs Target %"}                 # below target = good = green

def run(*a):
    subprocess.run(["pbir", "-q", *a], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def cond_color(meas, positive_is_good):
    up, down = (GREEN, RED) if positive_is_good else (RED, GREEN)
    m = {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": meas}}
    case = lambda kind, hexc: {"Condition": {"Comparison": {"ComparisonKind": kind, "Left": m,
                               "Right": {"Literal": {"Value": "0D"}}}},
                               "Value": {"Literal": {"Value": f"'{hexc}'"}}}
    # QueryComparisonKind: 2 = GreaterThanOrEqual, 3 = LessThan
    return json.dumps({"solid": {"color": {"expr": {"Conditional": {
        "Cases": [case(2, up), case(3, down)]}}}}})

NULL_FILL = json.dumps({"solid": {"color": {"expr": {"Literal": {"Value": "null"}}}}})

def kpi_idx(name):
    return int(name.split("_")[1])

for d in sorted(pathlib.Path(R, "definition/pages").glob("*/visuals/kpi_*")):
    vp = f"{R}/{d.parent.parent.name}.Page/{d.name}.Visual"
    i = kpi_idx(d.name)
    # z band: frame lowest, then value, then delta -- so the white frame sits BEHIND
    if d.name.endswith("_bg"):
        run("set", f"{vp}.position.z", "--value", str(10 + i))
    elif d.name.endswith("_d"):
        run("set", f"{vp}.position.z", "--value", str(102 + i * 4))
    else:
        run("set", f"{vp}.position.z", "--value", str(100 + i * 4))
    if d.name.endswith("_bg"):
        # white rounded frame behind the cards -- no shadow (user: "estilo sem sombra")
        run("set", f"{vp}.fill.fillColor", "--value", "#FFFFFF")
        run("set", f"{vp}.shape.rectangleRoundedCurve", "--value", "20")
        run("set", f"{vp}.shape.roundEdge", "--value", "20")
        run("set", f"{vp}.outline.show", "--value", "false")
        run("set", f"{vp}.shadow.show", "--value", "false")
        continue
    # value / delta cards: no fill, no background/shadow/border, title with no fill
    run("visuals", "background", vp, "--transparency", "100")
    run("set", f"{vp}.background.show", "--value", "false")
    run("set", f"{vp}.dropShadow.show", "--value", "false")
    run("set", f"{vp}.border.show", "--value", "false")
    run("set", f"{vp}.title.alignment", "--value", "center")
    run("set", f"{vp}.title.background", "--json", NULL_FILL)
    if d.name.endswith("_d"):
        meas = json.load(open(d / "visual.json", encoding="utf-8")
                         )["visual"]["query"]["queryState"]["Values"]["projections"][0]["field"]["Measure"]["Property"]
        run("set", f"{vp}.labels.fontSize", "--value", "16")
        run("set", f"{vp}.labels.bold", "--value", "true")
        run("set", f"{vp}.title.fontSize", "--value", "10")
        run("set", f"{vp}.labels.color", "--json", cond_color(meas, meas not in LOWER_BETTER))
    else:
        run("set", f"{vp}.labels.fontSize", "--value", "30")
        run("set", f"{vp}.title.fontSize", "--value", "13")

for t in ("executive-summary/exec_budget", "marketing-acquisition/mkt_campaign",
          "crm-customer/crm_returns", "product-inventory/prd_slow"):
    run("set", f"{R}/{t.split('/')[0]}.Page/{t.split('/')[1]}.Visual.total.totals", "--value", "false")
PY

echo
echo "== 4. chronological sort on time-series visuals =="
for tv in "${TIME_VISUALS[@]}"; do
  V="$REPORT/${tv%%/*}.Page/${tv##*/}.Visual"
  fld="dim_date.month_year"
  case "$tv" in *crm_cohort) fld="dim_customer.acquisition_month";; esac
  pbir -q visuals sort "$V" -f "$fld" -d Ascending 2>&1 | Q | grep -iE "error" || true
done

echo
echo "== 4b. restrict cohort + cash charts to the 24 in-window months (drop the blank/buffer) =="
WIN_MONTHS=$(for m in 2024-07 2024-08 2024-09 2024-10 2024-11 2024-12 \
  2025-01 2025-02 2025-03 2025-04 2025-05 2025-06 2025-07 2025-08 2025-09 2025-10 2025-11 2025-12 \
  2026-01 2026-02 2026-03 2026-04 2026-05 2026-06; do printf ' --values %s' "$m"; done)
pbir -q add filter dim_customer acquisition_month -v "$REPORT/crm-customer.Page/crm_cohort.Visual" \
  $WIN_MONTHS 2>&1 | Q | grep -iE "error|added" || true
for v in sales-performance/sal_cash logistics-fulfillment/log_cash; do
  pbir -q add filter dim_date month_year -v "$REPORT/${v%%/*}.Page/${v##*/}.Visual" \
    $WIN_MONTHS 2>&1 | Q | grep -iE "error|added" || true
done

echo
echo "== 5. slicers: date = Between, currency = required single-select (USD), header off =="
for slug in "${SLUGS[@]}"; do
  P="$REPORT/$slug.Page"
  pbir -q set "$P/slcDate.Visual.data.mode" --value "Between" 2>&1 | Q | grep -iE "error" || true
  for s in slcDate slcCurrency slcMarket; do
    pbir -q set "$P/$s.Visual.header.show" --value false 2>&1 | Q | grep -iE "error" || true
  done
  for s in slcCurrency slcMarket; do
    pbir -q set "$P/$s.Visual.data.mode" --value "Dropdown" 2>&1 | Q | grep -iE "error" || true
  done
  # currency: required single-select. Force Selection auto-picks the first item; the
  # 'Currency' column is sorted by 'Sort' (USD first), so USD is the default while GBP /
  # EUR / BRL stay in the list. No selection filter -> the item list is never restricted.
  pbir -q set "$P/slcCurrency.Visual.selection.singleSelect"       --value true 2>&1 | Q | grep -iE "error" || true
  pbir -q set "$P/slcCurrency.Visual.selection.strictSingleSelect" --value true 2>&1 | Q | grep -iE "error" || true
  pbir -q set "$P/slcCurrency.Visual.selection.selectAllCheckboxEnabled" --value false 2>&1 | Q | grep -iE "error" || true
done

echo
echo "== 5b. data labels on charts (theme-level; Power BI thins them on dense axes) =="
for vt in columnChart clusteredColumnChart barChart clusteredBarChart lineChart \
          lineClusteredColumnComboChart lineStackedColumnComboChart waterfallChart; do
  pbir -q theme set-formatting "$REPORT" "$vt.*.labels.show" --value true 2>&1 | Q | grep -iE "error" || true
  pbir -q theme set-formatting "$REPORT" "$vt.*.labels.fontSize" --value 9 2>&1 | Q | grep -iE "error" || true
done
# the two dense 24-month combos read better without a label on every bar
for v in sales-performance/sal_cash marketing-acquisition/mkt_trend \
         website-digital/web_trend logistics-fulfillment/log_trend executive-summary/exec_trend; do
  pbir -q set "$REPORT/${v%%/*}.Page/${v##*/}.Visual.labels.show" --value false 2>&1 | Q | grep -iE "error" || true
done

echo
echo "== 5c. soft drop shadow on every visual (bottom-right, blur 20, 70% transparent) =="
pbir -q theme set-formatting "$REPORT" "*.*.dropShadow.show"         --value true        2>&1 | Q | grep -iE "error" || true
pbir -q theme set-formatting "$REPORT" "*.*.dropShadow.preset"       --value BottomRight 2>&1 | Q | grep -iE "error" || true
pbir -q theme set-formatting "$REPORT" "*.*.dropShadow.shadowBlur"   --value 20          2>&1 | Q | grep -iE "error" || true
pbir -q theme set-formatting "$REPORT" "*.*.dropShadow.transparency" --value 70          2>&1 | Q | grep -iE "error" || true

echo
echo "== 6. theme + validation =="
pbir -q theme validate "$REPORT" 2>&1 | Q | grep -E "passed|failed|error"
pbir -q validate "$REPORT" --all 2>&1 | Q | grep -E "Pages:|Fields:|Errors|Warnings by|Invalid|Valid"
echo "done."

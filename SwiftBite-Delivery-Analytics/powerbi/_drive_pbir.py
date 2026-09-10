"""
_drive_pbir.py — build the SwiftBite Delivery report from powerbi/_report_layout.json using pbir.

Called by build_report.sh (which does the env / abort-if-Desktop-running checks).
Idempotent: wipes and recreates powerbi/SwiftBiteDelivery.Report each run.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _pbir_raw(*args):
    return subprocess.run(["pbir", "-q", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout or ""

PBI = Path(__file__).resolve().parent
NAME = "SwiftBiteDelivery"
RPT = f"{NAME}.Report"
SM = PBI / f"{NAME}.SemanticModel"
LAYOUT = json.loads((PBI / "_report_layout.json").read_text())
ASSETS = PBI / "assets"
THEME = PBI / "theme" / "theme.json"

FAILURES = []


def run(*args, check=True, retries=4):
    """Run a pbir command with retry-on-lock; returns (rc, out)."""
    cmd = ["pbir", "-q", *[str(a) for a in args]]
    last = ""
    for i in range(retries):
        p = subprocess.run(cmd, cwd=str(PBI), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = (p.stdout or "") + (p.stderr or "")
        if p.returncode == 0:
            return 0, out
        last = out
        if any(k in out.lower() for k in ("being used by another process", "permission denied",
                                          "winerror 32", "winerror 5")):
            time.sleep(1.0 * (i + 1))
            continue
        break
    if check:
        FAILURES.append((" ".join(cmd[2:]), last.strip().splitlines()[-1] if last.strip() else "?"))
    return 1, last


def vpath(page, name):
    return f"{RPT}/{page}.Page/{name}.Visual"


# ---------------------------------------------------------------------------
def scaffold():
    for p in (PBI / RPT, PBI / f"{NAME}.pbip"):
        for _ in range(6):                       # OneDrive can hold a lock on the tree
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
            if not p.exists():
                break
            time.sleep(1.5)
    print(">> new report + rebind")
    run("new", "report", RPT, "--thick", "--no-title")
    run("report", "rebind", RPT, "--local", f"../{NAME}.SemanticModel")
    # Theme: our authored theme is powerbi/theme/theme.json. `pbir theme apply-template`
    # only takes registered template *names*, not an arbitrary file, and wrapping it as a
    # template proved brittle. Apply it in Power BI Desktop on first open
    # (View > Themes > Browse for themes > powerbi/theme/theme.json), or via
    # `pbir theme build` from a serialized folder. The report ships with the default theme.
    print("   theme: apply powerbi/theme/theme.json in Desktop on first open")


def make_pages():
    pages = LAYOUT["pages"]
    first = pages[0]
    # rename the default 'Page 1'
    run("pages", "rename", f"{RPT}/Page 1.Page", "--to", first["name"], "-f", check=False)
    run("pages", "rename", f"{RPT}/*.Page", "--to", first["name"], "-f", check=False)
    run("pages", "resize", f"{RPT}/{first['name']}.Page",
        "--width", LAYOUT["canvas_width"], "--height", first["height"], check=False)
    for pg in pages[1:]:
        run("add", "page", f"{RPT}/{first['name']}.Page", "-n", pg["name"],
            "--width", LAYOUT["canvas_width"], "--height", pg["height"])
    for pg in pages:
        bg = ASSETS / f"bg_{pg['key']}.png"
        if bg.exists():
            run("pages", "background", f"{RPT}/{pg['name']}.Page", "--image", str(bg), check=False)
        run("pages", "display", f"{RPT}/{pg['name']}.Page", "FitToPage", check=False)
    # drop the default title textboxes pbir adds — the page-background PNG carries the title
    run("rm", f"{RPT}/**/Title.Visual", "-f", check=False)


# ---------------------------------------------------------------------------
def page_bundle(pg) -> list[dict]:
    """One --from-json bundle: KPI frame, KPI value+delta cards, content visuals, slicers.
    --from-json only supports keys: visual_type, name, title, x, y, width, height, fields."""
    b = []
    fr = LAYOUT["kpi_frame"]
    b.append({"visual_type": "shape", "name": f"{_slug(pg['key'])}-kpiframe",
              "x": fr["x"], "y": fr["y"], "width": fr["w"], "height": fr["h"]})
    for it in pg["kpis"]:
        b.append({"visual_type": "card", "name": _slug(pg['key'], it['title'], 'v'),
                  "x": it["x"], "y": it["y"], "width": it["w"], "height": 70,
                  "title": it["title"], "fields": {"Values": [it["value"]]}})
        if it.get("delta"):
            b.append({"visual_type": "card", "name": _slug(pg['key'], it['title'], 'd'),
                      "x": it["x"], "y": it["delta_y"], "width": it["w"], "height": it["delta_h"],
                      "fields": {"Values": [it["delta"]]}})
    for v in pg["visuals"]:
        b.append({"visual_type": v["type"], "name": v["name"], "x": v["x"], "y": v["y"],
                  "width": v["w"], "height": v["h"], "title": v["title"], "fields": v["roles"]})
    for sl in LAYOUT["slicers"]:
        b.append({"visual_type": "slicer", "name": f"{_slug(pg['key'])}-{sl['name']}",
                  "x": sl["x"], "y": sl["y"], "width": sl["w"], "height": sl["h"],
                  "title": sl["title"], "fields": {"Values": [sl["field"]]}})
    return b


def _slug(*parts):
    s = "-".join(str(p) for p in parts).lower()
    return "".join(c if c.isalnum() or c == "-" else "" for c in s.replace(" ", "-"))[:60]


def add_visuals():
    for pg in LAYOUT["pages"]:
        bundle = page_bundle(pg)
        f = PBI / f"_visuals_{pg['key']}.json"
        f.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        rc, out = run("add", "visual", f"{RPT}/{pg['name']}.Page", "--from-json", str(f), "--force")
        added = out.count("Created") + out.count("created")
        print(f">> {pg['name']}: from-json rc={rc}  (~{added} created)")
        if rc != 0:
            print("   " + "\n   ".join(out.strip().splitlines()[-4:]))


def post_pass():
    for pg in LAYOUT["pages"]:
        for v in pg["visuals"]:
            if v.get("sort"):
                run("visuals", "sort", vpath(pg["name"], v["name"]),
                    "-f", v["sort"]["by"], "-d",
                    "Ascending" if v["sort"]["dir"] == "asc" else "Descending", check=False)
        for it in pg["kpis"]:
            if not it.get("delta"):
                continue
            dv = vpath(pg["name"], _slug(pg["key"], it["title"], "d"))
            bad_hi = it["good"] == "low"
            run("visuals", "cf", dv, "--rules", "--field", it["delta"],
                "--rule", f"gt 0 {'bad' if bad_hi else 'good'}",
                "--rule", f"lte 0 {'good' if bad_hi else 'bad'}",
                "--on", "labels.color", check=False)
    # KPI frame shapes -> white, rounded, no shadow
    for pg in LAYOUT["pages"]:
        fr = vpath(pg["name"], f"{_slug(pg['key'])}-kpiframe")
        run("set", f"{fr}.fill.show", "--value", "true", check=False)
        run("set", f"{fr}.fill.fillColor.color", "--value", "#FFFFFF", check=False)
        run("set", f"{fr}.roundEdge", "--value", "18", check=False)
        run("set", f"{fr}.dropShadow.show", "--value", "false", check=False)
    # narrative card -> wrap the text
    for pg in LAYOUT["pages"]:
        run("set", f"{vpath(pg['name'], 'exec_insight')}.wordWrap.show", "--value", "true", check=False)
    # friendly tab names (folder / internal name stays <key>)
    for pg in LAYOUT["pages"]:
        disp = pg.get("display", pg["name"])
        if disp != pg["name"]:
            run("set", f"{RPT}/{pg['name']}.Page.displayName", "--value", disp, check=False)


def finish():
    run("theme", "validate", RPT, check=False)
    rc, out = run("validate", RPT, "--all", check=False)
    print("\n=== validate --all ===")
    print("\n".join(out.strip().splitlines()[-30:]))
    if FAILURES:
        print(f"\n=== {len(FAILURES)} pbir command failures ===")
        for cmd, err in FAILURES[:40]:
            print(f"  ! {cmd}\n      {err}")


if __name__ == "__main__":
    for cand in (r"C:\Program Files\Power BI Report Builder",
                 r"C:\Program Files (x86)\Microsoft Power BI Report Builder",
                 r"C:\Program Files\Microsoft Power BI Desktop\bin"):
        if Path(cand).exists():
            os.environ["PBIR_ADOMD_DIR"] = cand
            break
    os.environ["PBIR_ALLOW_OVERLAP"] = "1"
    scaffold()
    make_pages()
    add_visuals()
    post_pass()
    finish()

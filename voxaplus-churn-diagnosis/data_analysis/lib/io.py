"""DuckDB + pandas access to the curated Parquet."""
from __future__ import annotations
from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CUR = ROOT / "data" / "curated"

# window anchors (see docs/01)
SHIFT_IDX = 33            # window-month 34 = first elevated month
PRE = (24, 32)            # pre-shift baseline months
PEAK = (33, 35)           # elevated months
CHANNEL_SHIFT_IDX = 24
BR_PRICE_HIKE_IDX = 30
APP_V3_CTV_IDX = 32       # smart-TV / stick on v3


def con() -> duckdb.DuckDBPyConnection:
    """A DuckDB connection with a view per curated table."""
    c = duckdb.connect()
    for pq in sorted(CUR.glob("*.parquet")):
        c.execute(f"CREATE OR REPLACE VIEW {pq.stem} AS "
                  f"SELECT * FROM read_parquet('{pq.as_posix()}')")
    vd = CUR / "fact_viewing_daily"
    if vd.is_dir():
        c.execute("CREATE OR REPLACE VIEW fact_viewing_daily AS "
                  f"SELECT * FROM read_parquet('{(vd / '*.parquet').as_posix()}')")
    # convenience: subscriber attributes joined onto the monthly fact
    c.execute("""
        CREATE OR REPLACE VIEW sm AS
        SELECT f.*, s.market AS sub_market, s.cohort_month, s.first_paid_month_idx,
               s.acquisition_channel, s.first_tier, s.current_tier AS sub_current_tier,
               s.billing_period AS sub_billing, s.primary_device_family,
               s.is_incentivised, s.is_comparable_base, s.is_l4l_cohort,
               ch.is_low_quality
        FROM fact_subscription_month f
        JOIN dim_subscriber s USING (subscriber_key)
        LEFT JOIN dim_channel ch ON ch.channel = s.acquisition_channel
    """)
    return c


def load(name: str) -> pd.DataFrame:
    if name == "fact_viewing_daily":
        return pd.read_parquet(CUR / "fact_viewing_daily")
    return pd.read_parquet(CUR / f"{name}.parquet")


def sm_py() -> pd.DataFrame:
    """pandas equivalent of the `sm` view."""
    f = load("fact_subscription_month")
    s = load("dim_subscriber")
    ch = load("dim_channel")[["channel", "is_low_quality"]]
    out = f.merge(s, on="subscriber_key", suffixes=("", "_s"))
    out = out.merge(ch, left_on="acquisition_channel", right_on="channel", how="left")
    out = out.rename(columns={"market_s": "sub_market"} if "market_s" in out else {})
    if "market_x" in out.columns:  # both fact and dim carry `market`
        out = out.rename(columns={"market_x": "market", "market_y": "sub_market"})
    elif "sub_market" not in out.columns:
        out["sub_market"] = out["market"]
    return out

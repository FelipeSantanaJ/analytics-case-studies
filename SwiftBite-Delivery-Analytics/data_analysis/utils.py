"""Shared loaders + stats helpers for the SwiftBite Delivery analysis (Phase 10).

The unit of randomisation is the **zone-day** (~840, 420/arm), clustered in 12
zones. Inference therefore uses three routes and reports all of them:
  - cluster-robust (by zone) OLS SEs (anti-conservative with 12 clusters — a floor);
  - randomization inference: permute `arm` within zone × weekday/weekend strata;
  - wild-cluster bootstrap (Rademacher weights on residuals, resampled by zone).
"""
from __future__ import annotations

import os
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CUR = pathlib.Path(os.environ.get("SB_DATA_DIR", str(ROOT / "data"))) / "curated"
OUT_TAB = ROOT / "data_analysis" / "outputs" / "tables"
OUT_FIG = ROOT / "data_analysis" / "outputs" / "figures"
OUT_TAB.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

TIERS = ["short", "balanced", "long"]
SEED = 20260910


def t(name: str) -> pd.DataFrame:
    return pd.read_parquet(CUR / f"{name}.parquet")


def con():
    import duckdb
    c = duckdb.connect()
    for pq in CUR.glob("*.parquet"):
        c.execute(f"CREATE OR REPLACE VIEW {pq.stem} AS "
                  f"SELECT * FROM read_parquet('{pq.as_posix()}')")
    # convenience views mirroring sql/_prelude.sql
    c.execute("CREATE OR REPLACE VIEW ezd AS SELECT * FROM fact_experiment_zone_day")
    c.execute("CREATE OR REPLACE VIEW fia AS SELECT * FROM fact_incentive_assignment")
    c.execute("CREATE OR REPLACE VIEW ebw AS SELECT * FROM fact_experiment_zone_block_week")
    c.execute("""
        CREATE OR REPLACE VIEW zd AS
        SELECT e.*, f.day_of_week, f.pre_fulfillment_rate, f.pre_eta_p90_min,
               f.pre_orders_placed_mean, f.pre_liquidity_ratio, f.pre_idle_courier_ratio,
               z.zone_id, z.zone_name, z.baseline_supply_stress_tier AS tier,
               CASE WHEN e.arm = 'treatment' THEN 1 ELSE 0 END AS treat,
               CASE WHEN f.day_of_week >= 5 THEN 1 ELSE 0 END   AS is_weekend
        FROM fact_experiment_zone_day e
        JOIN fact_incentive_assignment f USING (zone_key, date_key)
        JOIN dim_zone z USING (zone_key)
    """)
    return c


def zone_day(with_tier: bool = True) -> pd.DataFrame:
    """fact_experiment_zone_day joined to its assignment covariates + zone tier."""
    ezd = t("fact_experiment_zone_day")
    fia = t("fact_incentive_assignment")[[
        "zone_key", "date_key", "day_of_week", "pre_fulfillment_rate", "pre_eta_p90_min",
        "pre_orders_placed_mean", "pre_liquidity_ratio", "pre_idle_courier_ratio"]]
    d = ezd.merge(fia, on=["zone_key", "date_key"], how="left")
    if with_tier:
        dz = t("dim_zone")[["zone_key", "zone_id", "zone_name", "baseline_supply_stress_tier"]]
        d = d.merge(dz, on="zone_key", how="left")
    d["treat"] = (d["arm"] == "treatment").astype(int)
    d["is_weekend"] = (d["day_of_week"] >= 5).astype(int)
    return d


# --------------------------------------------------------------------------- #
# stats
# --------------------------------------------------------------------------- #
def welch_t(a, b, alt="two-sided"):
    from scipy import stats
    a, b = np.asarray(a, float), np.asarray(b, float)
    tstat, p = stats.ttest_ind(b, a, equal_var=False, alternative=alt)
    diff = b.mean() - a.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return dict(mean_control=a.mean(), mean_treatment=b.mean(), diff=diff,
                ci_lo=diff - 1.959964 * se, ci_hi=diff + 1.959964 * se,
                t=float(tstat), p_value=float(p), se=se, n1=len(a), n2=len(b))


def smd(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return (b.mean() - a.mean()) / sp if sp else 0.0


def cluster_ols(df: pd.DataFrame, y: str, rhs: str, cluster: str = "zone_key"):
    """OLS y ~ rhs with cluster-robust (by `cluster`) covariance. Returns the fit."""
    import statsmodels.formula.api as smf
    m = smf.ols(f"{y} ~ {rhs}", data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df[cluster]})
    return m


def diff_in_means_cluster(df: pd.DataFrame, y: str, cluster="zone_key", covars: str = ""):
    """Treatment effect on `y` from OLS with cluster-robust SE; optional covariate
    adjustment. Returns dict with coef, se, ci, p."""
    rhs = "treat" + (f" + {covars}" if covars else "")
    m = cluster_ols(df, y, rhs, cluster)
    b = m.params["treat"]
    se = m.bse["treat"]
    return dict(coef=float(b), se=float(se), ci_lo=float(b - 1.959964 * se),
                ci_hi=float(b + 1.959964 * se), p_value=float(m.pvalues["treat"]),
                n=int(m.nobs), model=m)


def randomization_inference(df: pd.DataFrame, y: str, strata=("zone_key", "is_weekend"),
                            n=2000, seed=SEED, stat="mean_diff"):
    """Permute `treat` within `strata`, recomputing the treated-minus-control mean of
    `y`. Returns (observed, p_two_sided, null_draws)."""
    rng = np.random.default_rng(seed)
    g = df.groupby(list(strata))["treat"]
    idx_by_stratum = [v.index.to_numpy() for _, v in g]
    treat0 = df["treat"].to_numpy()
    yv = df[y].to_numpy()

    def eff(tr):
        return yv[tr == 1].mean() - yv[tr == 0].mean()

    obs = eff(treat0)
    draws = np.empty(n)
    for i in range(n):
        tr = treat0.copy()
        for ix in idx_by_stratum:
            tr[ix] = rng.permutation(tr[ix])
        draws[i] = eff(tr)
    p = (np.sum(np.abs(draws) >= abs(obs) - 1e-12) + 1) / (n + 1)
    return dict(observed=float(obs), p_value=float(p), n_perm=n,
                null_mean=float(draws.mean()), null_sd=float(draws.std()))


def wild_cluster_bootstrap(df: pd.DataFrame, y: str, rhs: str = "treat",
                           cluster="zone_key", n=2000, seed=SEED):
    """Rademacher wild-cluster bootstrap CI + p for the `treat` coefficient
    (restricted/null-imposed on the treat term)."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    rng = np.random.default_rng(seed)
    full = smf.ols(f"{y} ~ {rhs}", data=df).fit()
    b_hat = full.params["treat"]
    se_hat = smf.ols(f"{y} ~ {rhs}", data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df[cluster]}).bse["treat"]
    ti = list(full.params.index).index("treat")
    # null model: drop `treat`
    rhs0 = " + ".join(x for x in rhs.split(" + ") if x != "treat") or "1"
    null = smf.ols(f"{y} ~ {rhs0}", data=df).fit()
    resid0 = null.resid.to_numpy()
    fit0 = null.fittedvalues.to_numpy()
    X = np.asarray(full.model.exog)
    clusters = df[cluster].to_numpy()
    uc = np.unique(clusters)
    tstats = np.empty(n)
    for i in range(n):
        w = rng.choice([-1.0, 1.0], size=len(uc))
        wmap = dict(zip(uc, w))
        yb = fit0 + resid0 * np.array([wmap[c] for c in clusters])
        try:
            fb = sm.OLS(yb, X).fit(cov_type="cluster", cov_kwds={"groups": clusters})
        except Exception:
            fb = sm.OLS(yb, X).fit()
        tstats[i] = fb.params[ti] / fb.bse[ti] if fb.bse[ti] else 0.0
    t_obs = b_hat / se_hat if se_hat else 0.0
    p = (np.sum(np.abs(tstats) >= abs(t_obs)) + 1) / (n + 1)
    q_lo, q_hi = np.quantile(tstats, [0.025, 0.975])
    return dict(coef=float(b_hat), se_cluster=float(se_hat), t_obs=float(t_obs),
                p_value=float(p), ci_lo=float(b_hat - q_hi * se_hat),
                ci_hi=float(b_hat - q_lo * se_hat), n_boot=n)


def ratio_bootstrap(num_by_zone: pd.Series, den_by_zone: pd.Series, n=4000, seed=SEED):
    """Cluster (zone) bootstrap CI for sum(num)/sum(den) — e.g. incentive spend per
    incremental order."""
    rng = np.random.default_rng(seed)
    zk = num_by_zone.index.to_numpy()
    nv, dv = num_by_zone.to_numpy(), den_by_zone.to_numpy()
    pt = nv.sum() / dv.sum() if dv.sum() else np.nan
    draws = np.empty(n)
    for i in range(n):
        s = rng.integers(0, len(zk), len(zk))
        draws[i] = nv[s].sum() / dv[s].sum() if dv[s].sum() else np.nan
    lo, hi = np.nanquantile(draws, [0.025, 0.975])
    return dict(point=float(pt), ci_lo=float(lo), ci_hi=float(hi))


def chisq_srm(counts: dict, expected_ratio=(0.5, 0.5)):
    from scipy import stats
    obs = np.array(list(counts.values()), float)
    exp = obs.sum() * np.array(expected_ratio)
    chi2 = ((obs - exp) ** 2 / exp).sum()
    return dict(chi2=float(chi2), p_value=float(stats.chi2.sf(chi2, df=len(obs) - 1)),
                observed=counts)


# --------------------------------------------------------------------------- #
def save_table(df: pd.DataFrame, name: str):
    p = OUT_TAB / f"{name}.csv"
    df.to_csv(p, index=False)
    return p


def parity(name: str, py_val, sql_val, tol=1e-6, rel=True):
    a, b = float(py_val), float(sql_val)
    ok = (abs(a - b) <= tol) if not rel else (abs(a - b) <= tol * max(1.0, abs(a), abs(b)))
    print(f"  parity[{'OK ' if ok else 'MISMATCH'}] {name:46s} py={a:.6g}  sql={b:.6g}")
    if not ok:
        raise AssertionError(f"parity mismatch {name}: py={a} sql={b}")
    return ok


def banner(s):
    print(f"\n{'=' * 76}\n{s}\n{'=' * 76}")

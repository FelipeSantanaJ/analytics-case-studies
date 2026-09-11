"""Shared loaders + stats helpers for the LumaBank Activation analysis (Phase 10)."""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CUR = ROOT / "data" / "curated"
OUT_TAB = ROOT / "data_analysis" / "outputs" / "tables"
OUT_FIG = ROOT / "data_analysis" / "outputs" / "figures"
OUT_TAB.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

CHANNELS = ["paid_social", "organic", "app_store_search", "referral", "influencer"]


def t(name: str) -> pd.DataFrame:
    return pd.read_parquet(CUR / f"{name}.parquet")


def con():
    import duckdb
    c = duckdb.connect()
    for pq in CUR.glob("*.parquet"):
        c.execute(f"CREATE OR REPLACE VIEW {pq.stem} AS SELECT * FROM read_parquet('{pq.as_posix()}')")
    return c


# --------------------------------------------------------------------------- #
# stats
# --------------------------------------------------------------------------- #
def two_prop(x1, n1, x2, n2, alt="two-sided"):
    """Two-proportion test (2 = treatment, 1 = control). Returns dict."""
    from scipy import stats
    p1, p2 = x1 / n1, x2 / n2
    diff = p2 - p1
    pbar = (x1 + x2) / (n1 + n2)
    se_pool = np.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))
    z = diff / se_pool
    se_unpool = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    if alt == "two-sided":
        p = 2 * stats.norm.sf(abs(z))
    elif alt == "larger":
        p = stats.norm.sf(z)
    else:
        p = stats.norm.cdf(z)
    lo, hi = diff - 1.959964 * se_unpool, diff + 1.959964 * se_unpool
    return dict(p1=p1, p2=p2, diff=diff, rel=diff / p1 if p1 else np.nan,
               ci_lo=lo, ci_hi=hi, z=z, p_value=p, se_unpool=se_unpool, n1=n1, n2=n2)


def ni_test(x_ctrl, n_ctrl, x_treat, n_treat, margin_abs, alpha=0.05):
    """One-sided non-inferiority test: H0: p_treat - p_ctrl >= margin (treatment worse
    by at least `margin`). Reject H0 (=non-inferiority established) if the one-sided
    upper confidence bound on (p_treat - p_ctrl) is BELOW margin."""
    from scipy import stats
    p1, p2 = x_ctrl / n_ctrl, x_treat / n_treat
    diff = p2 - p1
    se = np.sqrt(p1 * (1 - p1) / n_ctrl + p2 * (1 - p2) / n_treat)
    z_alpha = stats.norm.ppf(1 - alpha)
    upper_bound = diff + z_alpha * se
    ni_established = upper_bound < margin_abs
    return dict(p_control=p1, p_treatment=p2, diff=diff, se=se,
               upper_95=upper_bound, margin=margin_abs, ni_established=ni_established)


def chisq_srm(counts: dict, expected_ratio=(0.5, 0.5)):
    from scipy import stats
    obs = np.array(list(counts.values()), float)
    exp = obs.sum() * np.array(expected_ratio)
    chi2 = ((obs - exp) ** 2 / exp).sum()
    p = stats.chi2.sf(chi2, df=len(obs) - 1)
    return dict(chi2=chi2, p_value=p, observed=counts, expected=dict(zip(counts, exp)))


def n_for_power(p1, mde_abs, power=0.8, alpha=0.05):
    from scipy import stats
    p2 = p1 + mde_abs
    pbar = (p1 + p2) / 2
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return ((za * np.sqrt(2 * pbar * (1 - pbar)) + zb * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
            / mde_abs ** 2)


def mde_for_n(p1, n_per_arm, power=0.8, alpha=0.05):
    """Solve for the MDE (absolute) achievable at a given n/arm, by bisection."""
    lo, hi = 0.0001, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        need = n_for_power(p1, mid, power, alpha)
        if need > n_per_arm:
            lo = mid
        else:
            hi = mid
    return hi


def save_table(df: pd.DataFrame, name: str):
    p = OUT_TAB / f"{name}.csv"
    df.to_csv(p, index=False)
    return p


def parity(name: str, py_val, sql_val, tol=1e-6, rel=True):
    a, b = float(py_val), float(sql_val)
    ok = (abs(a - b) <= tol) if not rel else (abs(a - b) <= tol * max(1.0, abs(a), abs(b)))
    status = "OK " if ok else "MISMATCH"
    print(f"  parity[{status}] {name:44s} py={a:.6g}  sql={b:.6g}")
    if not ok:
        raise AssertionError(f"parity mismatch {name}: py={a} sql={b}")
    return ok


def banner(s):
    print(f"\n{'=' * 76}\n{s}\n{'=' * 76}")

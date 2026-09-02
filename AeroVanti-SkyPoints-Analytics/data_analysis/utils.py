"""Shared loaders + stats helpers for the AeroVanti SkyPoints analysis (Phase 10)."""
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

# population active-member tier mix (docs/01 §4) — for post-stratification
POP_TIER_MIX = {"Blue": 0.68, "Silver": 0.20, "Gold": 0.09, "Platinum": 0.03}
STRATA = ["Blue", "Silver", "Gold", "Platinum"]


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
    # Cohen's h
    h = 2 * np.arcsin(np.sqrt(p2)) - 2 * np.arcsin(np.sqrt(p1))
    return dict(p1=p1, p2=p2, diff=diff, rel=diff / p1 if p1 else np.nan,
               ci_lo=lo, ci_hi=hi, z=z, p_value=p, se_unpool=se_unpool,
               cohens_h=h, n1=n1, n2=n2)


def newcombe_ci(x1, n1, x2, n2, alpha=0.05):
    """Newcombe (score) CI for a difference of proportions (p2 - p1)."""
    from scipy import stats
    z = stats.norm.ppf(1 - alpha / 2)

    def wilson(x, n):
        p = x / n
        d = 1 + z**2 / n
        c = p + z**2 / (2 * n)
        adj = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
        return (c - adj) / d, (c + adj) / d

    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    p1, p2 = x1 / n1, x2 / n2
    lo = (p2 - p1) - np.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = (p2 - p1) + np.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return lo, hi


def welch_t(a, b, alt="two-sided"):
    from scipy import stats
    a, b = np.asarray(a, float), np.asarray(b, float)
    tstat, p = stats.ttest_ind(b, a, equal_var=False, alternative=alt)
    diff = b.mean() - a.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return dict(mean_control=a.mean(), mean_treatment=b.mean(), diff=diff,
                ci_lo=diff - 1.959964 * se, ci_hi=diff + 1.959964 * se,
                t=tstat, p_value=p, se=se, n1=len(a), n2=len(b))


def smd(a, b):
    """Standardized mean difference (treatment - control) / pooled sd."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return (b.mean() - a.mean()) / sp if sp else 0.0


def power_two_prop(p1, mde_abs, n_per_arm, alpha=0.05):
    """Approx power for a two-sided two-proportion test."""
    from scipy import stats
    p2 = p1 + mde_abs
    pbar = (p1 + p2) / 2
    za = stats.norm.ppf(1 - alpha / 2)
    num = abs(mde_abs) * np.sqrt(n_per_arm) - za * np.sqrt(2 * pbar * (1 - pbar))
    den = np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return float(stats.norm.cdf(num / den))


def n_for_power(p1, mde_abs, power=0.8, alpha=0.05):
    from scipy import stats
    p2 = p1 + mde_abs
    pbar = (p1 + p2) / 2
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return ((za * np.sqrt(2 * pbar * (1 - pbar)) + zb * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
            / mde_abs ** 2)


def chisq_srm(counts: dict, expected_ratio=(0.5, 0.5)):
    from scipy import stats
    obs = np.array(list(counts.values()), float)
    exp = obs.sum() * np.array(expected_ratio)
    chi2 = ((obs - exp) ** 2 / exp).sum()
    p = stats.chi2.sf(chi2, df=len(obs) - 1)
    return dict(chi2=chi2, p_value=p, observed=counts, expected=dict(zip(counts, exp)))


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

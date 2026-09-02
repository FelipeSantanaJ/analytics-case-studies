"""
AeroVanti SkyPoints — 01_generate_raw.py

Builds the whole synthetic world in memory (members, monthly activity, point
lots, flights, co-brand card, tiers, the Flash Redemption experiment) and then
writes it out as *source-shaped, messy* raw exports under data/raw/.

The true experiment effect comes from config.FLASH_EFFECT and is applied here.
Nothing downstream (staging, curated, analysis) sees config.FLASH_EFFECT.

Run:  python etl/01_generate_raw.py      (respects SKP_SCALE env for dev)
"""

from __future__ import annotations

import shutil
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

import config as C
from utils import (
    add_months,
    banner,
    date_key,
    fmt_money_brl,
    jitter_date_string,
    logistic,
    mojibake,
    month_key,
    rng,
    to_excel_serial,
    write_raw_csv,
)

N_M = C.N_MONTHS
MONTH0 = C.WINDOW_START  # date(2024, 9, 1)

CITIES_BY_REGION = {
    "Sudeste": ["São Paulo", "Campinas", "Rio de Janeiro", "Belo Horizonte", "Vitória"],
    "Sul": ["Curitiba", "Porto Alegre", "Florianópolis", "Londrina"],
    "Nordeste": ["Recife", "Salvador", "Fortaleza", "Natal", "São Luís"],
    "Centro-Oeste": ["Brasília", "Goiânia", "Campo Grande", "Cuiabá"],
    "Norte": ["Manaus", "Belém", "Porto Velho"],
}
AIRPORTS = ["VCP", "GRU", "CGH", "SDU", "GIG", "CNF", "REC", "SSA", "FOR", "BSB",
            "CWB", "POA", "FLN", "MAO", "BEL", "NAT", "GYN"]

PRE_FLASH_REWARDS = [r for r in C.REWARD_CATALOG if not r[4]]           # award_flight + points+cash
LOW_COST_REWARDS = [r for r in C.REWARD_CATALOG if r[4]]


def cal_month(m_idx: int) -> int:
    """Calendar month number (1-12) for a 0-indexed window month (m=0 -> Sep)."""
    return ((MONTH0.month - 1 + m_idx) % 12) + 1


def month_start_date(m_idx: int) -> date:
    return add_months(MONTH0, m_idx)


# ======================================================================== #
# 1. Members
# ======================================================================== #
def build_members() -> pd.DataFrame:
    g = rng("members")
    n = C.N_MEMBERS_ENROLLED_TOTAL

    w = np.array(C.ENROLLMENT_MONTH_WEIGHTS, dtype=float)
    w = w / w.sum()
    enroll_m = g.choice(np.arange(N_M), size=n, p=w)

    ch_names = list(C.ENROLLMENT_CHANNEL_MIX)
    ch_p = np.array([C.ENROLLMENT_CHANNEL_MIX[k] for k in ch_names])
    channel = g.choice(ch_names, size=n, p=ch_p / ch_p.sum())

    reg_names = list(C.REGION_MIX)
    reg_p = np.array([C.REGION_MIX[k] for k in reg_names])
    region = g.choice(reg_names, size=n, p=reg_p / reg_p.sum())
    city = np.empty(n, dtype=object)
    for r in reg_names:
        mask = region == r
        opts = CITIES_BY_REGION[r]
        city[mask] = g.choice(opts, size=mask.sum())

    eng = g.normal(0, 1, size=n)

    # ---- target status tier: drawn to hit TIER_MIX_TARGET, tilted by engagement.
    # Tier is a status property (not derived from the fragile simulated flight count)
    # so the experiment strata are always fillable and revenue-by-tier rises steeply.
    tmix = np.array([C.TIER_MIX_TARGET[t] for t in C.TIERS])
    score = 0.7 * eng + g.normal(0, 1, n)
    qrank = score.argsort().argsort() / n                     # uniform [0,1)
    cum = np.cumsum(tmix)[:-1]
    target_tier_rank = 1 + (qrank[:, None] >= cum[None, :]).sum(axis=1)   # 1..4
    ramp_delay = g.integers(0, 4, size=n)                     # months at Blue before status kicks in

    # annual flight propensity — heavy-tailed, correlated with engagement AND tier
    tier_boost = np.array([1.0, 2.0, 3.8, 7.0])[target_tier_rank - 1]
    flight_prop = g.gamma(shape=1.6, scale=1.2, size=n) * np.exp(0.30 * eng) * tier_boost
    flight_prop = np.clip(flight_prop, 0.0, 60.0)

    # co-brand card ever-holding
    p_card = np.select(
        [channel == "card", channel == "web", channel == "flight", channel == "partner"],
        [0.98, 0.18, 0.17, 0.10],
    )
    p_card = np.clip(p_card * np.exp(0.15 * eng), 0, 0.99)
    has_card = g.random(n) < p_card
    card_start_m = np.where(
        channel == "card", enroll_m,
        np.minimum(enroll_m + g.integers(0, 13, size=n), N_M - 1),
    )
    card_start_m = np.where(has_card, card_start_m, 99)

    # legacy migrated members (enrolled in the first 3 months) carry an opening balance
    migrated = enroll_m <= 2
    legacy_bal = np.zeros(n)
    mig_n = int(migrated.sum())
    # mixture: many members sit in the 3.5k-15k "can't do much" band
    comp = g.choice([0, 1, 2], size=mig_n, p=[0.30, 0.55, 0.15])
    draw = np.where(
        comp == 0, g.uniform(0, 3500, mig_n),
        np.where(comp == 1, g.lognormal(np.log(7000), 0.45, mig_n),
                 g.lognormal(np.log(28000), 0.5, mig_n)),
    )
    legacy_bal[migrated] = np.round(draw / 100) * 100
    legacy_expire_m = np.full(n, 999)
    legacy_expire_m[migrated] = g.integers(16, 23, size=mig_n)  # Feb-Aug 2026 wave

    member_id = np.array([f"SKP{100000 + i}" for i in range(n)])

    return pd.DataFrame(
        dict(
            m_idx=np.arange(n),
            member_id=member_id,
            enroll_m=enroll_m,
            enroll_date=[month_start_date(int(mm)) + timedelta(days=int(g.integers(0, 27)))
                         for mm in enroll_m],
            channel=channel,
            region=region,
            home_city=city,
            eng=eng,
            flight_prop=flight_prop,
            target_tier_rank=target_tier_rank,
            ramp_delay=ramp_delay,
            has_card=has_card,
            card_start_m=card_start_m,
            legacy_bal=legacy_bal,
            legacy_expire_m=legacy_expire_m,
        )
    )


# ======================================================================== #
# 2. Flight segments + tier trajectory + earn
# ======================================================================== #
def build_activity(members: pd.DataFrame):
    g = rng("activity")
    n = len(members)
    enroll_m = members["enroll_m"].to_numpy()
    eng = members["eng"].to_numpy()
    flight_prop = members["flight_prop"].to_numpy()

    exists = np.arange(N_M)[None, :] >= enroll_m[:, None]        # (n, N_M)
    tenure = np.clip(np.arange(N_M)[None, :] - enroll_m[:, None], 0, None)
    tenure_ramp = np.clip(0.35 + 0.65 * tenure / 9.0, 0.35, 1.0)

    season = np.array([C.TRAVEL_SEASONALITY[cal_month(m)] for m in range(N_M)])
    lam = (flight_prop[:, None] / 12.0) * season[None, :] * tenure_ramp * exists
    flights_m = g.poisson(lam).astype(np.int32)                  # (n, N_M)

    # ---- expand to segments -------------------------------------------------
    flat = flights_m.reshape(-1)
    seg_mi = np.repeat(np.repeat(np.arange(n), N_M), flat)
    seg_mo = np.repeat(np.tile(np.arange(N_M), n), flat)
    ns = seg_mi.size
    base_fare = g.lognormal(np.log(C.BASE_FARE_BRL_MEAN) - 0.5 * 0.55 ** 2, 0.55, ns)
    base_fare = np.round(np.clip(base_fare, 80, 6000), 2)
    is_flex = g.random(ns) < C.FLEX_FARE_SHARE
    tp_seg = base_fare * C.TIER_POINTS_PER_BRL_BASE_FARE + C.TIER_POINTS_PER_SEGMENT

    seg = pd.DataFrame(dict(m_idx=seg_mi, mo=seg_mo, base_fare=base_fare,
                            is_flex=is_flex, tp=tp_seg))

    # ---- effective tier per member-month --------------------------------
    # Blue until enrolment + ramp_delay, then the member's status tier, with a
    # little downgrade / upgrade drift so the tier-change ledger has movement.
    target = members["target_tier_rank"].to_numpy().astype(np.int8)
    ramp_delay = members["ramp_delay"].to_numpy()
    mrel = np.arange(N_M)[None, :] - enroll_m[:, None]
    at_status = mrel >= ramp_delay[:, None]
    eff = np.where(exists, np.where(at_status, target[:, None], 1), 0).astype(np.int8)

    # ~11% of Silver+ members lose a tier at a random month in the 2nd year
    drop_mask = (target >= 2) & (g.random(n) < 0.11)
    drop_month = g.integers(13, N_M, size=n)
    dm2 = drop_mask[:, None] & (np.arange(N_M)[None, :] >= drop_month[:, None]) & exists
    eff = np.where(dm2, np.maximum(eff - 1, 1), eff).astype(np.int8)
    # ~7% of Blue/Silver members gain a tier mid-window
    up_mask = (target <= 2) & (g.random(n) < 0.07)
    up_month = g.integers(6, N_M - 3, size=n)
    um2 = up_mask[:, None] & (np.arange(N_M)[None, :] >= up_month[:, None]) & exists & at_status
    eff = np.where(um2, np.minimum(eff + 1, 4), eff).astype(np.int8)

    # tier multiplier per member-month
    mult_by_rank = np.array([0, 1.0, 1.25, 1.5, 2.0])
    seg_rank = eff[seg["m_idx"].to_numpy(), seg["mo"].to_numpy()]
    seg["tier_rank"] = seg_rank
    seg["skypoints"] = np.round(
        seg["base_fare"].to_numpy() * C.SKYPOINTS_PER_BRL_BASE_FARE
        * mult_by_rank[seg_rank]
        * (1.0 + np.where(seg["is_flex"].to_numpy(), C.FLEX_FARE_EARN_BONUS, 0.0))
    ).astype(np.int64)

    flight_earn_m = (seg.groupby(["m_idx", "mo"])["skypoints"].sum()
                     .unstack(fill_value=0).reindex(index=np.arange(n), columns=np.arange(N_M),
                                                    fill_value=0).to_numpy())
    flight_rev_m = (seg.groupby(["m_idx", "mo"])["base_fare"].sum()
                    .unstack(fill_value=0.0).reindex(index=np.arange(n), columns=np.arange(N_M),
                                                     fill_value=0.0).to_numpy())

    # ---- co-brand card spend & earn -------------------------------------
    card_start = members["card_start_m"].to_numpy()
    card_active = (np.arange(N_M)[None, :] >= card_start[:, None]) & exists
    spend = g.lognormal(np.log(1500) - 0.5 * 0.7 ** 2, 0.7, size=(n, N_M))
    spend_season = np.array([1.0 + (0.12 if cal_month(m) in (11, 12) else 0.0) for m in range(N_M)])
    card_spend_m = np.round(spend * spend_season[None, :] * card_active, 2)
    card_earn_m = np.floor(card_spend_m / C.COBRAND_SPEND_PER_SKYPOINT_BRL).astype(np.int64)
    # welcome bonus in the card-start month
    for i in np.where(card_start < N_M)[0]:
        card_earn_m[i, card_start[i]] += C.COBRAND_WELCOME_BONUS_PTS

    # ---- partner / promo / service-recovery earn -----------------------
    partner_hit = (g.random((n, N_M)) < 0.06) & exists
    partner_m = np.round(g.lognormal(np.log(800), 0.5, (n, N_M))) * partner_hit
    promo_hit = (g.random((n, N_M)) < 0.04) & exists
    promo_m = g.choice([500, 1000, 2000], (n, N_M)) * promo_hit
    svc_hit = (g.random((n, N_M)) < 0.010) & exists
    svc_m = g.choice([1000, 2500, 5000], (n, N_M)) * svc_hit

    earn_by_source = {
        "flight": flight_earn_m.astype(np.int64),
        "cobrand_card": card_earn_m.astype(np.int64),
        "partner_hotel": np.round(partner_m * 0.55).astype(np.int64),
        "partner_car": np.round(partner_m * 0.25).astype(np.int64),
        "partner_retail": np.round(partner_m * 0.20).astype(np.int64),
        "promo": promo_m.astype(np.int64),
        "service_recovery": svc_m.astype(np.int64),
    }
    earned_m = np.sum(list(earn_by_source.values()), axis=0)

    return dict(
        exists=exists, tenure=tenure, tenure_ramp=tenure_ramp,
        flights_m=flights_m, seg=seg, eff_tier=eff,
        flight_rev_m=flight_rev_m, card_spend_m=card_spend_m,
        earn_by_source=earn_by_source, earned_m=earned_m,
    )


# ======================================================================== #
# 3. Redemption + point-lot engine (monthly, vectorized across members)
# ======================================================================== #
def run_point_engine(members, act):
    g = rng("point_engine")
    n = len(members)
    eng = members["eng"].to_numpy()
    exists = act["exists"]
    tenure_ramp = act["tenure_ramp"]
    eff = act["eff_tier"]
    earned_m = act["earned_m"]

    # lots[:, 0] = legacy lot; lots[:, j+1] = points earned in window month j
    lots = np.zeros((n, N_M + 1))
    lots[:, 0] = members["legacy_bal"].to_numpy()
    legacy_expire_m = members["legacy_expire_m"].to_numpy()

    season = np.array([C.TRAVEL_SEASONALITY[cal_month(min(m + C.REDEMPTION_SEASONALITY_LEAD_MONTHS,
                                                          N_M - 1))] for m in range(N_M)])

    redeemed_m = np.zeros((n, N_M))
    redeem_cnt_m = np.zeros((n, N_M), dtype=np.int32)
    redeem_val_m = np.zeros((n, N_M))
    expired_m = np.zeros((n, N_M))
    balance_eom = np.zeros((n, N_M))

    r_names = np.array([r[0] for r in PRE_FLASH_REWARDS])
    r_cats = np.array([r[1] for r in PRE_FLASH_REWARDS])
    r_price = np.array([r[2] for r in PRE_FLASH_REWARDS], dtype=float)
    r_vpp = np.array([r[3] for r in PRE_FLASH_REWARDS], dtype=float)
    r_low = np.array([r[4] for r in PRE_FLASH_REWARDS])
    rw_mi, rw_mo, rw_ridx, rw_cost = [], [], [], []

    A0 = -3.25  # calibrated intercept (see docs/walkthrough Phase 3 calibration)
    for m in range(N_M):
        lots[:, m + 1] += earned_m[:, m]                       # points post this month
        avail = lots.sum(axis=1)

        can = exists[:, m] & (avail >= C.MIN_REDEMPTION_THRESHOLD_DEFAULT)
        z = (A0
             + 0.62 * eng
             + 0.55 * (tenure_ramp[:, m] - 0.7)
             + 0.40 * (season[m] - 1.0)
             + 0.30 * (eff[:, m] - 1)
             + 0.18 * np.log1p(avail / 10000.0))
        p = logistic(z) * can
        idx = np.where(g.random(n) < p)[0]

        if idx.size:
            rw = g.choice(len(PRE_FLASH_REWARDS), size=idx.size, p=[0.35, 0.45, 0.20])
            unif = g.uniform(0.85, 1.4, idx.size)
            cost = np.minimum(np.round(r_price[rw] * unif / 100) * 100, avail[idx]).astype(np.int64)
            keep = cost >= 3000
            idx, rw, cost = idx[keep], rw[keep], cost[keep]
            # vectorized FIFO subtraction across this month's redeemers
            rem = cost.astype(float).copy()
            for j in range(0, m + 2):
                take = np.minimum(lots[idx, j], rem)
                lots[idx, j] -= take
                rem -= take
            val = np.round(cost * r_vpp[rw], 2)
            redeemed_m[idx, m] = cost
            redeem_cnt_m[idx, m] = 1
            redeem_val_m[idx, m] = val
            rw_mi.append(idx); rw_mo.append(np.full(idx.size, m)); rw_ridx.append(rw); rw_cost.append(cost)

        exp_mask = (legacy_expire_m == m)
        if exp_mask.any():
            expired_m[exp_mask, m] += lots[exp_mask, 0]
            lots[exp_mask, 0] = 0.0

        balance_eom[:, m] = lots.sum(axis=1)

    mi = np.concatenate(rw_mi) if rw_mi else np.array([], dtype=int)
    mo = np.concatenate(rw_mo) if rw_mo else np.array([], dtype=int)
    ridx = np.concatenate(rw_ridx) if rw_ridx else np.array([], dtype=int)
    cst = np.concatenate(rw_cost) if rw_cost else np.array([], dtype=int)
    reward_df = pd.DataFrame(dict(
        m_idx=mi, mo=mo, reward_name=r_names[ridx] if ridx.size else [],
        reward_category=r_cats[ridx] if ridx.size else [],
        points=cst, value_brl=np.round(cst * r_vpp[ridx], 2) if ridx.size else [],
        is_low_cost=r_low[ridx] if ridx.size else [],
    ))
    return dict(redeemed_m=redeemed_m, redeem_cnt_m=redeem_cnt_m, redeem_val_m=redeem_val_m,
               expired_m=expired_m, balance_eom=balance_eom, reward_df=reward_df,
               lots_final=lots)


# ======================================================================== #
# 4. Active / lapse flags
# ======================================================================== #
def build_lapse(members, act, eng_out):
    n = len(members)
    exists = act["exists"]
    enroll_m = members["enroll_m"].to_numpy()
    activity = (act["earned_m"] > 0) | (eng_out["redeemed_m"] > 0)

    msla = np.full((n, N_M), 99, dtype=np.int32)   # months since last activity
    lapsed = np.full((n, N_M), -1, dtype=np.int8)  # -1 = undeterminable
    became = np.zeros((n, N_M), dtype=bool)
    react = np.zeros((n, N_M), dtype=bool)
    counter = np.full(n, 99)
    prev_lapsed = np.zeros(n, dtype=bool)
    for m in range(N_M):
        act_now = activity[:, m] & exists[:, m]
        counter = np.where(act_now, 0, counter + 1)
        counter = np.where(exists[:, m], counter, 99)
        msla[:, m] = counter
        tenure = m - enroll_m
        determinable = exists[:, m] & (tenure >= C.LAPSE_INACTIVITY_MONTHS)
        is_lap = determinable & (counter >= C.LAPSE_INACTIVITY_MONTHS)
        lapsed[:, m] = np.where(determinable, is_lap.astype(np.int8), -1)
        became[:, m] = is_lap & ~prev_lapsed
        react[:, m] = act_now & prev_lapsed
        prev_lapsed = is_lap
    return dict(msla=msla, lapsed=lapsed, became=became, react=react, activity=activity)


# ======================================================================== #
# 5. The Flash Redemption experiment
# ======================================================================== #
def build_experiment(members, act, eng_out, lap):
    g = rng("experiment")
    n = len(members)
    FE = C.FLASH_EFFECT
    FREEZE_M = 18  # Mar 2026
    WIN_MONTHS = [18, 19, 20]

    eff = act["eff_tier"]
    exists = act["exists"]
    earned_m = act["earned_m"]
    redeemed_m = eng_out["redeemed_m"]
    redeem_cnt_m = eng_out["redeem_cnt_m"]
    redeem_val_m = eng_out["redeem_val_m"]
    balance_eom = eng_out["balance_eom"]
    flight_rev_m = act["flight_rev_m"]
    flights_m = act["flights_m"]

    tier_name = np.array(["", "Blue", "Silver", "Gold", "Platinum"])[eff[:, FREEZE_M]]
    trailing_earn = earned_m[:, 6:18].sum(axis=1)
    trailing_redeem = redeem_cnt_m[:, 6:18].sum(axis=1)
    trailing_flights = flights_m[:, 6:18].sum(axis=1)
    not_lapsed_freeze = lap["lapsed"][:, 17] != 1
    active_trailing = (trailing_earn > 0) | (trailing_redeem > 0) | (flights_m[:, 6:18].sum(axis=1) > 0)
    eligible = exists[:, FREEZE_M] & active_trailing & not_lapsed_freeze & (tier_name != "")

    pre_balance = balance_eom[:, 17]
    prior_redeemer = redeem_cnt_m[:, 0:18].sum(axis=1) > 0

    def _z(x):
        x = x.astype(float)
        return (x - x.mean()) / (x.std() + 1e-9)

    # Blocked (pair-matched) randomisation within each stratum: rank the chosen
    # members by a pre-period redemption-propensity score, form adjacent pairs,
    # and flip a coin per pair for which member gets treatment. This keeps the
    # arms balanced on prior behaviour by construction (the balance check in
    # Phase 10 will show it) while still injecting real assignment randomness.
    arm = np.full(n, "none", dtype=object)
    stratum = np.full(n, "", dtype=object)
    for tname, k in C.EXPERIMENT_STRATA_N.items():
        pool = np.where(eligible & (tier_name == tname))[0]
        take = min(k, pool.size)
        chosen = g.choice(pool, size=take, replace=False)
        score = (2.0 * prior_redeemer[chosen] + _z(pre_balance[chosen])
                 + _z(trailing_earn[chosen]) + 0.01 * g.random(take))
        order = chosen[np.argsort(score)]
        npair = len(order) // 2
        flip = g.random(npair) < 0.5
        a = np.where(flip, order[0:2 * npair:2], order[1:2 * npair:2])   # treatment
        b = np.where(flip, order[1:2 * npair:2], order[0:2 * npair:2])   # control
        arm[a] = "treatment"
        arm[b] = "control"
        if len(order) % 2:                       # odd one out -> random arm
            arm[order[-1]] = g.choice(["treatment", "control"])
        stratum[chosen] = tname
        if take < k:
            print(f"  [warn] stratum {tname}: wanted {k}, only {pool.size} eligible")

    subj = np.where(arm != "none")[0]

    base_red_win = (redeemed_m[:, WIN_MONTHS].sum(axis=1) > 0)
    base_val_win = redeem_val_m[:, WIN_MONTHS].sum(axis=1)
    base_pts_win = redeemed_m[:, WIN_MONTHS].sum(axis=1)

    # ---- treatment incremental redemptions --------------------------------
    control_rate_by_stratum = {}
    for tname in C.EXPERIMENT_STRATA_N:
        cmask = (arm == "control") & (stratum == tname)
        control_rate_by_stratum[tname] = base_red_win[cmask].mean() if cmask.any() else 0.11

    inc_red = np.zeros(n, dtype=bool)
    inc_week = np.full(n, -1)
    inc_pts = np.zeros(n)
    inc_val = np.zeros(n)
    inc_low_only = np.zeros(n, dtype=bool)

    novelty_w = np.array([
        1.0 + (FE["novelty_hazard_mult_week1"] - 1.0) * np.exp(-(w) / FE["novelty_decay_tau_weeks"])
        for w in range(C.EXPERIMENT_WEEKS)
    ])
    base_week_trend = np.linspace(0.9, 1.15, C.EXPERIMENT_WEEKS)  # slight rise toward July peak

    for tname in C.EXPERIMENT_STRATA_N:
        L = FE["ate_abs_pp_by_tier"][tname]
        tmask = (arm == "treatment") & (stratum == tname)
        if L <= 0 or not tmask.any():
            continue  # no effect built in at this tier (Platinum)
        # a treatment non-redeemer can convert only if they can now transact (>=3500).
        # Pick a DETERMINISTIC count so the per-stratum incremental redemption rate
        # equals L up to which-members noise; the analysis still faces real binomial
        # sampling variance when it estimates the effect.
        cand = tmask & ~base_red_win & (pre_balance >= C.MIN_REDEMPTION_THRESHOLD_FLASH)
        pool = np.where(cand)[0]
        n_conv = min(int(round(L * tmask.sum())), pool.size)
        newr = np.zeros(n, dtype=bool)
        if n_conv > 0:
            newr[g.choice(pool, size=n_conv, replace=False)] = True
        inc_red |= newr
        ni = np.where(newr)[0]
        # reward mix: 46% low-cost-only, rest include a cheap award / points+cash
        low_only = g.random(ni.size) < FE["low_cost_only_share_treatment_redeemers"]
        inc_low_only[ni] = low_only
        for k, i in enumerate(ni):
            if low_only[k]:
                name, cat, price, vpp, _, _ = LOW_COST_REWARDS[g.integers(0, len(LOW_COST_REWARDS))]
            else:
                name, cat, price, vpp, _, _ = PRE_FLASH_REWARDS[g.choice(3, p=[0.5, 0.3, 0.2])]
            cost = min(int(round(price * g.uniform(0.85, 1.3) / 100) * 100), int(max(0, pre_balance[i])))
            cost = max(cost, 1500)
            inc_pts[i] = cost
            inc_val[i] = round(cost * vpp, 2)
            wk = g.choice(C.EXPERIMENT_WEEKS, p=(novelty_w / novelty_w.sum()))
            inc_week[i] = wk

    # novelty pull-forward for some base redeemers (timing only, no extra volume)
    # ---- guardrail outcomes ---------------------------------------------
    rev_base = flight_rev_m[:, 18:22].sum(axis=1) + 0.5 * flight_rev_m[:, 22]
    rev = rev_base.copy()
    tmask_all = arm == "treatment"
    rev[tmask_all] = rev_base[tmask_all] * (
        1.0 + FE["revenue_per_member_rel"]
        + g.normal(0, 0.02, tmask_all.sum())
    )

    tot_pts_win = base_pts_win + inc_pts
    tot_val_win = base_val_win + inc_val
    tot_cnt_win = redeem_cnt_m[:, WIN_MONTHS].sum(axis=1) + inc_red.astype(int)

    liability_drawdown = tot_pts_win * C.POINT_UNIT_COST_BRL
    # cash cost: low-cost redemptions cost ~R$0.011/pt from partners, award ~R$0.0015/pt
    cash_factor = np.where(inc_low_only, 0.011, 0.0035)
    reward_cash_cost = inc_pts * cash_factor + base_pts_win * 0.0015
    net_liability_cost = reward_cash_cost - liability_drawdown * C.EXPECTED_BREAKAGE

    # 90-day post-window disengagement proxy (Jun-Aug 2026 = months 21-23)
    post_activity = (act["earned_m"][:, 21:24].sum(axis=1) > 0) | (eng_out["redeemed_m"][:, 21:24].sum(axis=1) > 0)
    base_diseng = ~post_activity
    diseng = base_diseng.copy()
    flip = tmask_all & base_diseng & (g.random(n) < (abs(FE["disengage_90d_post_abs_pp"]) /
                                                     max(0.05, base_diseng[tmask_all].mean())))
    diseng[flip] = False

    # ---- assignment table ----------------------------------------------
    asg = pd.DataFrame(dict(
        m_idx=subj,
        member_id=members["member_id"].to_numpy()[subj],
        arm=arm[subj],
        stratum=stratum[subj],
        pre_earn_12m_pts=trailing_earn[subj].astype(int),
        pre_flights_12m=trailing_flights[subj].astype(int),
        pre_redemptions_12m=trailing_redeem[subj].astype(int),
        pre_balance_pts=np.round(pre_balance[subj]).astype(int),
        prior_redeemer_flag=(eng_out["redeem_cnt_m"][:, 0:18].sum(axis=1)[subj] > 0),
        pre_tenure_months=(18 - members["enroll_m"].to_numpy()[subj]).astype(int),
    ))
    a_gen = rng("flesk_assign")
    asg["assigned_ts"] = [
        (date(2026, 3, 1) + timedelta(days=int(a_gen.integers(0, 2)))).isoformat()
        + f"T{a_gen.integers(8,20):02d}:{a_gen.integers(0,60):02d}:{a_gen.integers(0,60):02d}Z"
        for _ in range(len(asg))
    ]

    # ---- weekly table -------------------------------------------------
    wk_rows = []
    for i in subj:
        # base redemptions in window months -> weeks
        base_events = []
        for mm in WIN_MONTHS:
            for _ in range(int(redeem_cnt_m[i, mm])):
                wk = (mm - 18) * 4 + int(g.integers(0, 4))
                wk = min(wk, C.EXPERIMENT_WEEKS - 1)
                base_events.append((wk, redeem_val_m[i, mm] / max(1, redeem_cnt_m[i, mm]),
                                    redeemed_m[i, mm] / max(1, redeem_cnt_m[i, mm]), False))
        if inc_red[i]:
            base_events.append((int(inc_week[i]), inc_val[i], inc_pts[i], bool(inc_low_only[i])))
        by_week = {}
        for wk, val, pts, low in base_events:
            d = by_week.setdefault(wk, [0, 0.0, 0.0, True])
            d[0] += 1
            d[1] += val
            d[2] += pts
            d[3] = d[3] and low
        for wk in range(C.EXPERIMENT_WEEKS):
            d = by_week.get(wk)
            wk_rows.append(dict(
                member_id=members["member_id"].iloc[i],
                arm=arm[i], stratum=stratum[i], week=wk + 1,
                redeemed_w=bool(d) and d[0] > 0,
                redemptions_w=(d[0] if d else 0),
                points_redeemed_w=(round(d[2]) if d else 0),
                redemption_value_brl_w=(round(d[1], 2) if d else 0.0),
                low_cost_only_w=(bool(d[3]) if d else False),
            ))
    weekly = pd.DataFrame(wk_rows)

    # ---- outcome table ----------------------------------------------
    out = pd.DataFrame(dict(
        member_id=members["member_id"].to_numpy()[subj],
        arm=arm[subj], stratum=stratum[subj],
        redeemed_in_window=(base_red_win | inc_red)[subj],
        redemptions_in_window=tot_cnt_win[subj].astype(int),
        redemption_value_brl=np.round(tot_val_win[subj], 2),
        points_redeemed_in_window=np.round(tot_pts_win[subj]).astype(int),
        low_cost_only=np.where(inc_red[subj], inc_low_only[subj], False),
        revenue_brl_window_plus8w=np.round(rev[subj], 2),
        liability_drawdown_brl=np.round(liability_drawdown[subj], 2),
        reward_cash_cost_brl=np.round(reward_cash_cost[subj], 2),
        net_liability_cost_brl=np.round(net_liability_cost[subj], 2),
        disengaged_90d_post=diseng[subj],
        earn_in_window=(act["earned_m"][:, 18:21].sum(axis=1) > 0)[subj],
        flights_in_window=act["flights_m"][:, 18:21].sum(axis=1)[subj].astype(int),
        active_post_quarter=(~diseng)[subj],
    ))

    # exposure log (treatment only, mostly)
    e_gen = rng("flesk_expo")
    exp_rows = []
    for i in subj:
        if arm[i] != "treatment":
            continue
        k = 1 + int(e_gen.integers(0, 3))
        for _ in range(k):
            d = date(2026, 3, 2) + timedelta(days=int(e_gen.integers(0, 84)))
            exp_rows.append(dict(
                member_id=members["member_id"].iloc[i],
                exposure_at=d.isoformat() + f"T{e_gen.integers(0,24):02d}:{e_gen.integers(0,60):02d}:00Z",
                surface=e_gen.choice(["email", "app_banner", "app_banner"]),
            ))
    exposure = pd.DataFrame(exp_rows)

    return dict(assignment=asg, weekly=weekly, outcome=out, exposure=exposure,
                inc_red=inc_red, inc_pts=inc_pts, inc_val=inc_val, inc_week=inc_week,
                inc_low_only=inc_low_only, subj=subj, arm=arm, stratum=stratum)


# ======================================================================== #
# RAW EMISSION
# ======================================================================== #
def emit_raw(members, act, eng_out, lap, exp):
    g = rng("raw_emit")
    RAW = C.RAW_DIR
    if RAW.exists():
        shutil.rmtree(RAW)
    for sub in ["skycore", "bancoav", "reserva", "aurora", "flesk", "ledger"]:
        (RAW / sub).mkdir(parents=True, exist_ok=True)

    mid = members["member_id"].to_numpy()
    eff = act["eff_tier"]
    tier_name_m = np.array(["", "Blue", "Silver", "Gold", "Platinum"])[eff]

    TIER_ARR = np.array(["", "Blue", "Silver", "Gold", "Platinum"])
    enroll_dt = pd.to_datetime(members["enroll_date"]).to_numpy()
    home_city_arr = members["home_city"].to_numpy().astype(str)
    region_arr = members["region"].to_numpy()
    channel_arr = members["channel"].to_numpy()

    # ---------- SkyCore: members_snapshot (monthly, dup-heavy) ----------
    banner("raw: SkyCore member snapshots")
    for m in range(N_M):
        idx = np.where(act["exists"][:, m])[0]
        bal = np.round(eng_out["balance_eom"][idx, m]).astype(np.int64)
        ranks = eff[idx, m].astype(int)
        drift = g.random(idx.size) < C.TIER_SNAPSHOT_DRIFT_RATE
        newranks = np.clip(ranks + g.choice([-1, 1], idx.size), 1, 4)
        snap_tier = np.where(drift, TIER_ARR[newranks], TIER_ARR[ranks])
        since = pd.Series(enroll_dt[idx])
        iso_mask = g.random(idx.size) < 0.5
        member_since = np.where(iso_mask, since.dt.strftime("%Y-%m-%d"), since.dt.strftime("%d/%m/%Y"))
        up = g.random(idx.size) < 0.25
        city = np.where(up, np.char.upper(home_city_arr[idx]), home_city_arr[idx])
        bal_txt = np.where(g.random(idx.size) < 0.04, bal.astype(str), bal.astype(object))
        df = pd.DataFrame(dict(
            member_id=mid[idx], member_since=member_since, home_city=city,
            home_region=region_arr[idx], enrollment_channel=channel_arr[idx],
            current_tier=snap_tier, balance_points=bal_txt,
        ))
        dsel = df.sample(frac=0.15, random_state=int(g.integers(1, 1 << 30)))
        dsel = dsel.assign(balance_points=(pd.to_numeric(dsel["balance_points"], errors="coerce")
                                           .fillna(0).mul(0.8).round().astype(np.int64)))
        df = pd.concat([df, dsel, dsel.sample(frac=0.3, random_state=1)], ignore_index=True)
        d0 = month_start_date(m)
        write_raw_csv(df.sample(frac=1.0, random_state=m).reset_index(drop=True),
                      RAW / "skycore" / f"skycore__members_snapshot__{d0.isoformat()}.csv")

    # ---------- SkyCore: point_transactions (monthly, overlap dupes) ----
    banner("raw: SkyCore point_transactions")
    parts = []
    for src, arr in act["earn_by_source"].items():
        ii, mm = np.nonzero(arr)
        if ii.size:
            parts.append(pd.DataFrame(dict(i=ii, m=mm, ttype="earn", src=src,
                                           pts=arr[ii, mm].astype(np.int64),
                                           rname="", val=np.nan)))
    # legacy opening balance -> a one-off issuance txn at the member's enrol month
    lb = members["legacy_bal"].to_numpy()
    lm = np.where(lb > 0)[0]
    if lm.size:
        parts.append(pd.DataFrame(dict(
            i=lm, m=members["enroll_m"].to_numpy()[lm].astype(int),
            ttype="earn", src="legacy_migration", pts=lb[lm].astype(np.int64),
            rname="", val=np.nan)))
    rdf = eng_out["reward_df"]
    if len(rdf):
        parts.append(pd.DataFrame(dict(i=rdf["m_idx"].to_numpy(), m=rdf["mo"].to_numpy(),
                                       ttype="redeem", src="",
                                       pts=-rdf["points"].to_numpy().astype(np.int64),
                                       rname=rdf["reward_name"].to_numpy(),
                                       val=rdf["value_brl"].to_numpy())))
    si = exp["subj"][exp["inc_red"][exp["subj"]]]
    if si.size:
        parts.append(pd.DataFrame(dict(
            i=si, m=np.minimum(18 + exp["inc_week"][si] // 4, 20).astype(int),
            ttype="redeem", src="", pts=-exp["inc_pts"][si].astype(np.int64),
            rname="Flash redemption", val=exp["inc_val"][si])))
    ei, em = np.nonzero(eng_out["expired_m"] > 0)
    if ei.size:
        parts.append(pd.DataFrame(dict(i=ei, m=em, ttype="expire", src="",
                                       pts=-np.round(eng_out["expired_m"][ei, em]).astype(np.int64),
                                       rname="", val=np.nan)))
    T = pd.concat(parts, ignore_index=True)
    nt = len(T)
    T["txn_id"] = "PTX" + pd.Series(np.arange(1, nt + 1)).astype(str).str.zfill(9)
    T["member_id"] = mid[T["i"].to_numpy()]
    days = g.integers(0, 28, nt)
    dts = pd.to_datetime([month_start_date(int(x)) for x in T["m"]]) + pd.to_timedelta(days, "D")
    iso_mask = g.random(nt) < 0.5
    T["txn_date"] = np.where(iso_mask, dts.strftime("%Y-%m-%d"), dts.strftime("%d/%m/%Y"))
    T["_day"] = (dts.day).to_numpy()
    VAR = {"earn": np.array(["earn", "Earn", "ACCRUAL", "acumulo"]),
           "redeem": np.array(["redeem", "redemption", "resgate"]),
           "expire": np.array(["expire", "expiry", "expiração"])}
    ttype_out = np.empty(nt, dtype=object)
    for k, arr in VAR.items():
        msk = (T["ttype"] == k).to_numpy()
        ttype_out[msk] = g.choice(arr, msk.sum())
    T["txn_type"] = ttype_out
    pts = T["pts"].to_numpy()
    text_mask = g.random(nt) < C.DQ["point_txn_text_value_rate"]
    pts_txt = np.char.add(np.where(pts < 0, "-", ""),
                          pd.Series(np.abs(pts)).map(lambda v: f"{v:,}".replace(",", ".")).to_numpy())
    T["points"] = np.where(text_mask, pts_txt, pts.astype(object))
    val = T["val"].to_numpy()
    has_val = ~pd.isna(val)
    money_mask = has_val & (g.random(nt) < 0.5)
    val_out = np.full(nt, "", dtype=object)
    val_out[has_val & ~money_mask] = np.round(val[has_val & ~money_mask], 2).astype(object)
    val_out[money_mask] = [fmt_money_brl(v, "br_symbol") for v in val[money_mask]]
    T["value_brl"] = val_out
    T["earn_source"] = T["src"]
    T["reward_name"] = T["rname"]
    cols = ["txn_id", "member_id", "txn_date", "txn_type", "points", "value_brl",
            "earn_source", "reward_name"]
    for m in range(N_M):
        d0 = month_start_date(m)
        cur = T[T["m"] == m]
        if m + 1 < N_M:
            nxt = T[(T["m"] == m + 1) & (T["_day"] <= C.DQ["point_txn_monthly_overlap_days"])]
            cur = pd.concat([cur, nxt], ignore_index=True)
        write_raw_csv(cur[cols].sample(frac=1.0, random_state=m).reset_index(drop=True),
                      C.RAW_DIR / "skycore" / f"skycore__point_transactions__{d0.year}-{d0.month:02d}.csv.gz",
                      compression="gzip")

    # ---------- SkyCore: tier snapshots + tier change events ----------
    banner("raw: SkyCore tiers")
    snap_rows = []
    for m in range(N_M):
        ex = np.where(act["exists"][:, m])[0]
        drift = g.random(ex.size) < C.TIER_SNAPSHOT_DRIFT_RATE
        ranks = eff[ex, m].astype(int)
        nr = np.clip(ranks + g.choice([-1, 1], ex.size), 1, 4)
        tn = np.where(drift, np.array(["", "Blue", "Silver", "Gold", "Platinum"])[nr], tier_name_m[ex, m])
        snap_rows.append(pd.DataFrame(dict(member_id=mid[ex],
                                           ym=f"{month_start_date(m).year}-{month_start_date(m).month:02d}",
                                           tier=tn)))
    write_raw_csv(pd.concat(snap_rows, ignore_index=True),
                  C.RAW_DIR / "skycore" / "skycore__tier_snapshots_monthly.csv.gz", compression="gzip")

    TN = ["", "Blue", "Silver", "Gold", "Platinum"]
    ev_rows, eid = [], 0
    enroll_m_arr = members["enroll_m"].to_numpy()
    # initial qualification event whenever a member starts above Blue
    for i in np.where(eff[np.arange(len(members)), enroll_m_arr] > 1)[0]:
        eid += 1
        em = int(enroll_m_arr[i]); to = int(eff[i, em])
        ev_rows.append(dict(
            event_id=f"TCE{eid:08d}", member_id=mid[i],
            change_date=(month_start_date(em) + timedelta(days=int(g.integers(0, 5)))).isoformat(),
            from_tier="Blue", to_tier=TN[to], direction="upgrade", trigger="qualification"))
    for m in range(1, N_M):
        chg = np.where((eff[:, m] != eff[:, m - 1]) & act["exists"][:, m] & act["exists"][:, m - 1])[0]
        for i in chg:
            eid += 1
            frm = int(eff[i, m - 1])
            to = int(eff[i, m])
            ev_rows.append(dict(
                event_id=f"TCE{eid:08d}", member_id=mid[i],
                change_date=(month_start_date(m) + timedelta(days=int(g.integers(0, 5)))).isoformat(),
                from_tier=TN[frm], to_tier=TN[to],
                direction=("upgrade" if to > frm else "downgrade"),
                trigger=g.choice(["qualification", "qualification", "soft_landing"]),
            ))
    evdf = pd.DataFrame(ev_rows).sort_values("change_date").reset_index(drop=True)
    dup = evdf.sample(frac=0.01, random_state=7)
    write_raw_csv(pd.concat([evdf, dup], ignore_index=True),
                  C.RAW_DIR / "skycore" / "skycore__tier_change_events.csv")

    # ---------- SkyCore: reward catalog (xlsx) ----------
    cat = pd.DataFrame([dict(
        reward_name=r[0], reward_category=r[1],
        points_price=f"{r[2]:,}".replace(",", "."),
        value_per_point_brl=r[3],
        available_from=to_excel_serial(r[5] if isinstance(r[5], date) else C.WINDOW_START),
    ) for r in C.REWARD_CATALOG])
    cat.to_excel(C.RAW_DIR / "skycore" / "skycore__reward_catalog.xlsx", index=False)

    # ---------- BancoAV ----------
    banner("raw: BancoAV card feed")
    card_idx = np.where(members["card_start_m"].to_numpy() < N_M)[0]
    fake = Faker("pt_BR")
    Faker.seed(C.SEED)
    ca = pd.DataFrame(dict(
        card_id=[f"AVCC{i:07d}" for i in range(card_idx.size)],
        member_id=[mid[i] if g.random() > 0.03 else "" for i in card_idx],
        holder_name=[mojibake(fake.name()) for _ in range(card_idx.size)],
        cidade=[mojibake(c) for c in members["home_city"].to_numpy()[card_idx]],
        abertura=[jitter_date_string(month_start_date(int(members["card_start_m"].iloc[i])), "br", g)
                  for i in card_idx],
        status=g.choice(["ATIVO", "ATIVO", "ATIVO", "BLOQUEADO"], card_idx.size),
    ))
    write_raw_csv(ca, C.RAW_DIR / "bancoav" / "bancoav__card_accounts.csv", encoding="latin-1")

    spend_rows = []
    cs = act["card_spend_m"]
    for k, i in enumerate(card_idx):
        for m in range(N_M):
            if cs[i, m] <= 0:
                continue
            d = month_start_date(m)
            spend_rows.append(dict(
                card_id=f"AVCC{k:07d}",
                competencia=to_excel_serial(d),
                valor_fatura=fmt_money_brl(cs[i, m], "br_symbol"),
                pontos_gerados=int(np.floor(cs[i, m] / C.COBRAND_SPEND_PER_SKYPOINT_BRL)),
            ))
    csdf = pd.DataFrame(spend_rows)
    dupmonth = to_excel_serial(date(2025, 6, 1))
    duprows = csdf[(csdf["competencia"] >= dupmonth) & (csdf["competencia"] < dupmonth + 30)]
    write_raw_csv(pd.concat([csdf, duprows], ignore_index=True),
                  C.RAW_DIR / "bancoav" / "bancoav__card_spend_monthly.csv.gz",
                  encoding="latin-1", compression="gzip")

    # ---------- Reserva ----------
    banner("raw: Reserva bookings + segments")
    seg = act["seg"].copy()
    seg = seg.sort_values(["m_idx", "mo"]).reset_index(drop=True)
    seg["booking_id"] = "BK" + (seg.index // 1).astype(str).str.zfill(9)
    # one booking per segment row here (1 leg); ~30% get a return leg
    ret = seg.sample(frac=0.30, random_state=3).copy()
    ret["is_return_leg"] = True
    seg["is_return_leg"] = False
    allseg = pd.concat([seg, ret], ignore_index=True)
    o = g.integers(0, len(AIRPORTS), len(allseg))
    d_ = (o + 1 + g.integers(0, len(AIRPORTS) - 1, len(allseg))) % len(AIRPORTS)
    allseg["origin"] = np.array(AIRPORTS)[np.where(allseg["is_return_leg"], d_, o)]
    allseg["dest"] = np.array(AIRPORTS)[np.where(allseg["is_return_leg"], o, d_)]
    allseg["flight_dt"] = [month_start_date(int(mo)) + timedelta(days=int(g.integers(0, 28)))
                           for mo in allseg["mo"]]
    # member id with orphan / nonmember injection
    memid = mid[allseg["m_idx"].to_numpy()]
    orphan = g.random(len(allseg)) < C.DQ["reserva_orphan_member_rate"]
    memid = np.where(orphan, np.array([f"SKP{9990000 + j}" for j in range(len(allseg))]), memid)
    seg_out = pd.DataFrame(dict(
        segment_id=[f"SEG{j:09d}" for j in range(len(allseg))],
        booking_id=allseg["booking_id"].to_numpy(),
        loyalty_member_id=memid,
        flight_date=[jitter_date_string(x, "us", g) for x in allseg["flight_dt"]],
        origin=allseg["origin"].to_numpy(),
        dest=allseg["dest"].to_numpy(),
        cabin=g.choice(["ECON", "ECON", "ECON", "PREM"], len(allseg)),
        fare_family=np.where(allseg["is_flex"].to_numpy(), "FLEX", "PROMO"),
        base_fare=allseg["base_fare"].to_numpy().round(2),
        taxes=np.where(g.random(len(allseg)) < 0.5,
                       (allseg["base_fare"].to_numpy() * C.TAXES_SHARE_OF_FARE).round(2), ""),
        is_award="N",
        points_redeemed="",
    ))
    # add award segments from award_flight redemptions
    aw = eng_out["reward_df"]
    aw = aw[aw["reward_category"] == "award_flight"]
    aw_rows = pd.DataFrame(dict(
        segment_id=[f"SEGA{j:08d}" for j in range(len(aw))],
        booking_id=[f"BKA{j:08d}" for j in range(len(aw))],
        loyalty_member_id=mid[aw["m_idx"].to_numpy()],
        flight_date=[jitter_date_string(month_start_date(int(mo)) + timedelta(days=int(g.integers(0, 28))),
                                        "us", g) for mo in aw["mo"]],
        origin=g.choice(AIRPORTS, len(aw)), dest=g.choice(AIRPORTS, len(aw)),
        cabin="ECON", fare_family="AWARD", base_fare="",
        taxes=(g.uniform(40, 120, len(aw))).round(2),
        is_award=g.choice(["Y", "1", "Y"], len(aw)),
        points_redeemed=aw["points"].to_numpy(),
    ))
    seg_final = pd.concat([seg_out, aw_rows], ignore_index=True)
    dupe = seg_final.sample(frac=C.DQ["reserva_dupe_segment_rate"], random_state=9)
    seg_final = pd.concat([seg_final, dupe], ignore_index=True).sample(frac=1.0, random_state=2)
    write_raw_csv(seg_final.reset_index(drop=True),
                  C.RAW_DIR / "reserva" / "reserva__segments.csv.gz", compression="gzip")

    bookings = (seg_final[["booking_id", "loyalty_member_id", "flight_date", "origin", "dest"]]
                .drop_duplicates("booking_id").copy())
    bookings["booking_date"] = bookings["flight_date"]  # approx
    bookings["channel"] = g.choice(["web", "App", "call center", "agency", "OTA", "app"],
                                   len(bookings))
    # non-member bookings (no loyalty id at all)
    n_nonmem = int(len(bookings) * C.DQ["reserva_nonmember_booking_rate"])
    nm = pd.DataFrame(dict(
        booking_id=[f"BKN{j:08d}" for j in range(n_nonmem)],
        loyalty_member_id="",
        flight_date=[jitter_date_string(month_start_date(int(g.integers(0, N_M))) +
                                        timedelta(days=int(g.integers(0, 28))), "us", g)
                     for _ in range(n_nonmem)],
        origin=g.choice(AIRPORTS, n_nonmem), dest=g.choice(AIRPORTS, n_nonmem),
        booking_date="", channel=g.choice(["web", "OTA", "agency"], n_nonmem),
    ))
    write_raw_csv(pd.concat([bookings, nm], ignore_index=True).sample(frac=1.0, random_state=4)
                  .reset_index(drop=True),
                  C.RAW_DIR / "reserva" / "reserva__bookings.csv.gz", compression="gzip")

    # ---------- Aurora CRM ----------
    banner("raw: Aurora CRM")
    has_crm = members["enroll_m"].to_numpy() >= (C.DQ["aurora_crm_golive_month"] - 1)
    ci = np.where(has_crm)[0]
    STAGE_VARIANTS = ["new", "Active", "active", "at risk", "At Risk", "dormant", "engaged"]
    bad_by = g.random(ci.size) < C.DQ["aurora_bad_birthyear_rate"]
    birth = []
    for k in range(ci.size):
        if bad_by[k]:
            birth.append(g.choice(["1900-01-01", "0"]))
        else:
            birth.append((date(1995, 1, 1) - timedelta(days=int(g.integers(-3000, 12000)))).isoformat())
    crm = pd.DataFrame(dict(
        member_id=mid[ci],
        full_name=[fake.name() for _ in range(ci.size)],
        email=[fake.email() for _ in range(ci.size)],
        birth_date=birth,
        lifecycle_stage=g.choice(STAGE_VARIANTS, ci.size),
        cidade=[mojibake(c) for c in members["home_city"].to_numpy()[ci]],
        consent_email=g.choice([True, True, False], ci.size),
    ))
    write_raw_csv(crm, C.RAW_DIR / "aurora" / "aurora__crm_contacts.csv")

    camp_rows = []
    CAMPS = [("CMP01", "Winter Escapes"), ("CMP02", "Double Points Weekend"),
             ("CMP03", "Tier Match"), ("CMP04", "Redeem & Fly"), ("CMP05", "Card Upgrade")]
    for i in ci[g.random(ci.size) < 0.55]:
        for cid, cname in [CAMPS[j] for j in g.choice(len(CAMPS), size=int(g.integers(1, 4)), replace=False)]:
            camp_rows.append(dict(member_id=mid[i], campaign_id=cid,
                                  campaign_name=(cname.upper() if g.random() < 0.3 else cname),
                                  joined_date=(C.WINDOW_START + timedelta(days=int(g.integers(0, 700)))).isoformat(),
                                  status=g.choice(["member", "member", "unsubscribed"])))
    write_raw_csv(pd.DataFrame(camp_rows), C.RAW_DIR / "aurora" / "aurora__campaign_membership.csv")

    # ---------- Flesk ----------
    banner("raw: Flesk experiment platform")
    asg = exp["assignment"].copy()
    asg_out = asg.rename(columns={"m_idx": "_drop"}).drop(columns=["_drop"])
    asg_out.insert(0, "subject_id", [f"SUBJ{i:06d}" for i in range(len(asg_out))])
    asg_out["eligible"] = True
    # append ineligible late corrections
    lc = asg_out.sample(n=C.EXPERIMENT_INELIGIBLE_LATE_CORRECTIONS, random_state=11).copy()
    lc["subject_id"] = [f"SUBJX{i:04d}" for i in range(len(lc))]
    lc["eligible"] = False
    write_raw_csv(pd.concat([asg_out, lc], ignore_index=True),
                  C.RAW_DIR / "flesk" / "flesk__ab_assignments.csv")

    expo = exp["exposure"].copy()
    dupe_e = expo.sample(frac=C.DQ["flesk_exposure_at_least_once_rate"], random_state=13)
    write_raw_csv(pd.concat([expo, dupe_e], ignore_index=True).sample(frac=1.0, random_state=5)
                  .reset_index(drop=True),
                  C.RAW_DIR / "flesk" / "flesk__exposure_log.csv")

    # ---------- Ledger ----------
    banner("raw: Loyalty liability sub-ledger")
    iss = act["earned_m"].sum(axis=0).astype(float)
    lb = members["legacy_bal"].to_numpy()
    lem = members["enroll_m"].to_numpy()
    for m in range(N_M):                       # legacy opening balances issued at enrol month
        iss[m] += lb[lem == m].sum()
    red = eng_out["redeemed_m"].sum(axis=0)
    expd_ = eng_out["expired_m"].sum(axis=0)
    bal = np.cumsum(iss - red - expd_)
    roll_rows = []
    for m in range(N_M):
        d = month_start_date(m)
        roll_rows.append(dict(
            mes=to_excel_serial(d),
            pontos_emitidos=int(iss[m]),
            pontos_resgatados=int(red[m]),
            pontos_expirados=int(round(expd_[m])),
            saldo_pontos_fim=int(round(bal[m])),
            passivo_brl=fmt_money_brl(bal[m] * C.POINT_UNIT_COST_BRL, "ledger"),
            provisao_breakage_brl=fmt_money_brl(bal[m] * C.POINT_UNIT_COST_BRL * C.EXPECTED_BREAKAGE, "ledger"),
        ))
    roll = pd.DataFrame(roll_rows)
    # restate two months: keep a stale copy + corrected copy
    restate_idx = [ (date.fromisoformat(f"{mm}-01") - date(1899, 12, 30)).days
                    for mm in C.DQ["ledger_restated_months"] ]
    stale = roll[roll["mes"].isin(restate_idx)].copy()
    stale["pontos_resgatados"] = (stale["pontos_resgatados"] * 0.9).astype(int)
    roll_final = pd.concat([stale, roll], ignore_index=True)
    roll_final.to_excel(C.RAW_DIR / "ledger" / "ledger__liability_rollforward_monthly.xlsx", index=False)

    rc_rows = []
    for m in range(N_M):
        d = month_start_date(m)
        for catn, share in [("award_flight", 0.55), ("ancillary", 0.15), ("gift_card", 0.2), ("voucher", 0.1)]:
            rc_rows.append(dict(mes=to_excel_serial(d), categoria=catn,
                                custo_caixa_brl=fmt_money_brl(red[m] * C.POINT_UNIT_COST_BRL * share * 0.4,
                                                             "br_symbol")))
    pd.DataFrame(rc_rows).to_excel(C.RAW_DIR / "ledger" / "ledger__reward_cost_monthly.xlsx", index=False)

    # ---------- experiment analyst tables also dropped as a convenience raw ----------
    # (Flesk would not export these, but the weekly/outcome truth is reconstructed
    #  in curated from point_transactions + assignment; we still stash them under
    #  flesk for the pipeline to pick up deterministically.)
    write_raw_csv(exp["weekly"], C.RAW_DIR / "flesk" / "flesk__redemption_week_feed.csv")
    write_raw_csv(exp["outcome"], C.RAW_DIR / "flesk" / "flesk__outcome_feed.csv")


# ======================================================================== #
def main():
    banner("AeroVanti SkyPoints — 01_generate_raw")
    print(f"SEED={C.SEED}  SCALE={C.SCALE}  members={C.N_MEMBERS_ENROLLED_TOTAL:,}")
    members = build_members()
    act = build_activity(members)
    eng_out = run_point_engine(members, act)
    lap = build_lapse(members, act, eng_out)
    exp = build_experiment(members, act, eng_out, lap)

    # quick truth peek (printed only; not persisted)
    o = exp["outcome"]
    rr = o.groupby("arm")["redeemed_in_window"].mean()
    print("\n--- truth peek (not persisted) ---")
    print(f"control redemption rate : {rr.get('control', float('nan')):.4f}")
    print(f"treatment redemption rate: {rr.get('treatment', float('nan')):.4f}")
    print(f"raw lift (pp)           : {100*(rr.get('treatment',0)-rr.get('control',0)):.2f}")
    print(o.groupby(['stratum', 'arm'])['redeemed_in_window'].mean().unstack())

    emit_raw(members, act, eng_out, lap, exp)
    banner("01_generate_raw complete")


if __name__ == "__main__":
    main()

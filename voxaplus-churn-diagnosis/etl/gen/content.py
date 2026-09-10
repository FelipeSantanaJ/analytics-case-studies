"""Clean content catalogue, release schedule, and content-cost model."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from utils import rng, month_start

_GENRES = ["Drama", "Comedy", "Action", "Documentary", "Kids", "Thriller",
           "Romance", "Reality", "Sci-Fi", "Crime"]
_PT = ["Coração", "Sertão", "Maré", "Café com Açúcar", "Última Estação", "Verão",
       "O Príncipe", "Cidade Invisível", "Amanhã é Tarde", "Filhos do Aço"]
_ES = ["El Refugio", "Marea Alta", "Corazón del Norte", "La Frontera", "Días de Sol",
       "Sombras", "Ámbar", "Niños del Río", "Mañana", "Hierro y Fuego"]
_EN = ["Northbound", "The Quiet Coast", "Paper Cities", "Last Signal", "Glasshouse",
       "Ironwood", "Afterlight", "The Long Season", "Downlink", "Saltwater"]


def build_content() -> dict:
    r = rng("content", "catalogue")
    n = C.N_TITLES
    lang = r.choice(["pt", "es", "en"], size=n, p=[0.5, 0.3, 0.2])
    pool = {"pt": _PT, "es": _ES, "en": _EN}
    titles, types, genres, origs, releases, runtimes = [], [], [], [], [], []
    for i in range(n):
        base = str(r.choice(pool[lang[i]]))
        titles.append(f"{base} {r.integers(1, 6)}" if r.random() < 0.35 else base)
        types.append("series" if r.random() < 0.45 else "movie")
        genres.append(str(r.choice(_GENRES)))
        origs.append(bool(r.random() < C.ORIGINAL_SHARE))
        # acquisition/release vintage: from 30 months before the window to month 34
        vint = int(r.integers(-30, C.N_MONTHS - 2))
        d0 = month_start(0) + pd.DateOffset(months=vint)
        releases.append(pd.Timestamp(d0).date())
        runtimes.append(int(r.integers(80, 140)) if types[-1] == "movie" else int(r.integers(280, 620)))
    titles_df = pd.DataFrame({
        "content_id": [f"T{50000 + i}" for i in range(n)],
        "title": titles, "content_type": types, "primary_genre": genres,
        "language": lang, "is_original": origs, "release_date": releases,
        "runtime_min": runtimes,
    })

    # licence windows (licensed titles only) — a couple expire mid-window in BR
    lic_rows = []
    rr = rng("content", "licence")
    for _, t in titles_df.iterrows():
        if t["is_original"]:
            continue
        for mk in C.MARKETS:
            start = pd.Timestamp(t["release_date"])
            term = int(rr.integers(18, 48))
            end = start + pd.DateOffset(months=term)
            if mk == "BR" and rr.random() < 0.03:
                end = month_start(C.BR_LICENCE_EXPIRY_MONTH) + pd.DateOffset(days=int(rr.integers(0, 20)))
            lic_rows.append({"content_id": t["content_id"], "market": mk,
                             "window_start": start.date(),
                             "window_end": pd.Timestamp(end).date()})
    licence_df = pd.DataFrame(lic_rows)

    # release schedule with tentpoles
    rel_rows = []
    rt = rng("content", "releases")
    in_window = titles_df[pd.to_datetime(titles_df["release_date"]) >= pd.Timestamp(month_start(0))]
    for mk, mconf in C.MARKETS.items():
        tps_per_month = C.TENTPOLES_PER_QUARTER[mk] / 3.0
        for idx in range(mconf["active_from_idx"], C.N_MONTHS):
            k = rt.poisson(tps_per_month)
            if k <= 0:
                continue
            picks = in_window.sample(min(int(k), len(in_window)), random_state=int(rt.integers(1, 1e9)))
            for _, t in picks.iterrows():
                rel_rows.append({
                    "content_id": t["content_id"], "market": mk,
                    "release_date": (month_start(idx) + pd.Timedelta(days=int(rt.integers(0, 27)))),
                    "is_tentpole": True,
                    "had_marketing_push": bool(rt.random() < 0.7),
                })
    releases_df = pd.DataFrame(rel_rows)

    # content cost by month (amortisation + lumpy cash)
    cost_rows = []
    rc = rng("content", "cost")
    for _, t in titles_df.iterrows():
        # licence/production cost per title, amortised over its term. Calibrated so
        # total content amortisation lands near ~50-60% of subscription revenue.
        total_usd = float(rc.lognormal(8.15, 0.75))         # median ~ US$3.5k, long right tail
        if t["is_original"]:
            total_usd *= 2.6
        start = pd.Timestamp(t["release_date"])
        term = int(rc.integers(24, 48))
        monthly_amort = total_usd / term
        # cash: 60% around acquisition, rest over first 6 months
        for m in range(term):
            d = start + pd.DateOffset(months=m)
            idx = (d.year - month_start(0).year) * 12 + (d.month - month_start(0).month)
            if idx < 0 or idx >= C.N_MONTHS:
                continue
            cash = 0.0
            if m == 0:
                cash = total_usd * 0.6
            elif m < 6:
                cash = total_usd * 0.4 / 5.0
            cost_rows.append({
                "content_id": t["content_id"], "month_idx": int(idx),
                "amort_usd": round(monthly_amort, 2), "cash_spend_usd": round(cash, 2),
                "mg_local": round(total_usd * 0.5, 2), "currency": "USD",
            })
    cost_df = pd.DataFrame(cost_rows)

    return {"titles": titles_df, "licence_windows": licence_df,
            "releases": releases_df, "content_cost_month": cost_df}

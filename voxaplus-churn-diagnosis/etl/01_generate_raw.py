"""
01_generate_raw.py — build the clean world, then serialise it into messy,
source-shaped exports under data/raw/<source>/.

Every data-quality issue in docs/02 section 8 (Q01..Q15) is injected here and
counted into data/quality/dq_fragments/raw_injection.json.
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import datetime as _dt

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import config as C
from utils import (rng, month_start, month_end, days_in_month, month_label, progress,
                   write_csv, write_text, write_parquet, write_jsonl, write_bytes,
                   to_excel_serial, fmt_date, money_str, maybe_mojibake, add_bom,
                   jitter_category, CATEGORY_VARIANTS, dq_fragment)
from gen.world import build_world
from gen.content import build_content
from gen import economics as E

INJ = {}      # DQ injection counters
CUR = {k: v["currency"] for k, v in C.MARKETS.items()}


def _bump(k, n=1):
    INJ[k] = INJ.get(k, 0) + int(n)


# =========================================================================
# heavy tables: subscriber x day viewing + app events
# =========================================================================
def _explode_days(vm_month: pd.DataFrame, idx: int, r: np.random.Generator):
    """vm_month: subscriber_id, streamed_hours, primary_device_family, ctv_share."""
    dim = days_in_month(idx)
    hours = vm_month["streamed_hours"].to_numpy()
    ndays = np.clip(np.round(hours / 2.6).astype(int), 1, dim)
    total = int(ndays.sum())
    sub = np.repeat(vm_month["subscriber_id"].to_numpy(), ndays)
    prim = np.repeat(vm_month["primary_device_family"].to_numpy(), ndays)
    ctv = np.repeat(vm_month["ctv_share"].to_numpy(), ndays)
    tot_hours = np.repeat(hours, ndays)
    # split each subscriber's monthly hours across their days
    w = r.gamma(2.0, 1.0, total)
    offs = np.concatenate([[0], np.cumsum(ndays)])
    gsum = np.add.reduceat(w, offs[:-1])
    gsum = np.where(gsum == 0, 1.0, gsum)
    hpd = tot_hours * w / np.repeat(gsum, ndays)
    day = r.integers(1, dim + 1, total)
    # device per day: mostly primary, sometimes another family
    swap = r.random(total) < 0.18
    alt = r.choice(C.DEVICE_FAMILIES, total)
    devfam = np.where(swap, alt, prim)
    return sub, day, hpd, devfam, ctv


def gen_viewing_and_app(world: dict, content: dict):
    titles = content["titles"]["content_id"].to_numpy()
    vm = world["viewing_month"]
    (C.RAW / "playlog").mkdir(parents=True, exist_ok=True)
    (C.RAW / "trackpad").mkdir(parents=True, exist_ok=True)
    ctv_first = min(C.APP_V3_ROLLOUT_IDX[f] for f in C.CTV_FAMILIES)

    for idx in range(C.N_MONTHS):
        vmm = vm[vm["month_idx"] == idx]
        if len(vmm) == 0:
            continue
        r = rng("raw", "playlog", idx)
        sub, day, hpd, devfam, ctv = _explode_days(vmm, idx, r)
        m = len(sub)
        base_ts = [month_start(idx) + pd.Timedelta(days=int(d - 1),
                                                   seconds=int(r.integers(0, 86400))) for d in day]

        play_starts = np.maximum(1, np.round(hpd / 0.7 + r.normal(0, 1, m)).astype(int))
        distinct = np.maximum(1, np.round(play_starts * r.uniform(0.4, 0.9, m)).astype(int))

        is_ctv = np.isin(devfam, C.CTV_FAMILIES)
        v3_live = np.array([idx >= C.APP_V3_ROLLOUT_IDX[f] for f in devfam])
        vsf_rate = np.full(m, C.VIDEO_START_FAILURE_RATE_BASE)
        reb_rate = np.full(m, C.REBUFFER_RATIO_BASE)
        pberr_rate = np.full(m, C.PLAYBACK_ERROR_RATE_BASE)
        hit = is_ctv & v3_live & (idx >= ctv_first)
        vsf_rate = np.where(hit, vsf_rate * C.APP_V3_CTV_VSF_MULT, vsf_rate)
        reb_rate = np.where(hit, reb_rate * C.APP_V3_CTV_REBUFFER_MULT, reb_rate)
        pberr_rate = np.where(hit, pberr_rate * C.APP_V3_CTV_PLAYBACK_ERR_MULT, pberr_rate)

        vsf = r.binomial(play_starts, np.clip(vsf_rate, 0, 0.5))
        pberr = r.binomial(play_starts, np.clip(pberr_rate, 0, 0.5))
        rebuffer = np.clip(r.normal(reb_rate, reb_rate * 0.4), 0, 1)

        watch_seconds = hpd * 3600.0
        if idx >= C.PLAYLOG_MS_ERA_START_IDX and C.DQ_INJECT["unit_breaks"]:
            watch_seconds = watch_seconds * 1000.0                       # Q09 seconds -> ms
            _bump("watchtime_ms_era_rows", m)

        # Q08 negative watch batch (clock skew)
        if C.DQ_INJECT["sign_errors"]:
            neg = r.random(m) < C.DQ_RATES["negative_watch_batch_frac"]
            watch_seconds = np.where(neg, -watch_seconds, watch_seconds)
            _bump("negative_watch_rows", int(neg.sum()))

        # Q05 orphan content ids
        cids = r.choice(titles, m)
        if C.DQ_INJECT["orphan_foreign_keys"]:
            orph = r.random(m) < C.DQ_RATES["orphan_content_frac"]
            cids = np.where(orph, np.array([f"T9{r.integers(10000,99999)}" for _ in range(m)]), cids)
            _bump("orphan_content_rows", int(orph.sum()))

        # Q09 CDN byte unit split by edge provider
        bitrate_gb_per_h = np.where(np.isin(devfam, C.CTV_FAMILIES), 3.6, 1.4)
        cdn_gb = np.abs(hpd) * bitrate_gb_per_h * r.uniform(0.85, 1.15, m)
        provider = r.choice(["edge-a", "edge-b"], m, p=[0.6, 0.4])
        cdn_bytes = np.where(provider == "edge-b", cdn_gb * 1024.0, cdn_gb)     # edge-b reports MB
        if C.DQ_INJECT["unit_breaks"]:
            _bump("cdn_mb_rows", int((provider == "edge-b").sum()))

        device_out = np.array([jitter_category(d, r, CATEGORY_VARIANTS) if C.DQ_INJECT["category_noise"] else d
                               for d in devfam])
        df = pd.DataFrame({
            "beacon_id": [f"pl_{idx}_{i}" for i in range(m)],
            "account_ref": sub,
            "event_utc": [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in base_ts],
            "asset_id": cids,
            "device": device_out,
            "watch_time": np.round(watch_seconds, 1),
            "play_starts": play_starts,
            "distinct_assets": distinct,
            "video_start_failures": vsf,
            "playback_errors": pberr,
            "rebuffer_ratio": np.round(rebuffer, 4),
            "cdn_bytes": np.round(cdn_bytes, 3),
            "edge_provider": provider,
        })
        # Q04 duplicate beacons (at-least-once delivery)
        if C.DQ_INJECT["duplicate_events"]:
            d = df.sample(frac=C.DQ_RATES["duplicate_event_frac"], random_state=idx)
            df = pd.concat([df, d], ignore_index=True)
            _bump("dupe_playlog_rows", len(d))
        write_parquet(df, C.RAW / "playlog" / f"playlog__{month_label(idx)}.parquet")

        # ---- trackpad app events (session rollup per account/day/device) ----
        ra = rng("raw", "app", idx)
        sess = np.maximum(1, np.round(2 + hpd / 2.0 + ra.normal(0, 1, m)).astype(int))
        cf_drop = np.where(hit, C.APP_V3_CTV_CRASHFREE_DROP,
                           np.where(v3_live, C.APP_V3_MOBILE_WEB_CRASHFREE_DROP, 0.0))
        crash_rate = np.clip((1 - C.CRASH_FREE_RATE_BASE) + cf_drop, 0, 0.2)
        crashes = ra.binomial(sess, crash_rate)
        app_ver = _app_version(devfam, idx)
        appdf = pd.DataFrame({
            "event_id": [f"ae_{idx}_{i}" for i in range(m)],
            "user_ref": sub,
            "day": [ (month_start(idx) + pd.Timedelta(days=int(d-1))).strftime("%Y-%m-%d") for d in day ],
            "device_family": device_out,
            "app_version": app_ver,
            "session_count": sess,
            "crash_count": crashes,
            "screen_views": np.round(sess * ra.uniform(4, 9, m)).astype(int),
            "ingest_utc": [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in base_ts],
        })
        if C.DQ_INJECT["duplicate_events"]:
            d = appdf.sample(frac=C.DQ_RATES["duplicate_event_frac"], random_state=1000 + idx)
            appdf = pd.concat([appdf, d], ignore_index=True)
            _bump("dupe_app_rows", len(d))
        write_parquet(appdf, C.RAW / "trackpad" / f"app_events__{month_label(idx)}.parquet")
        progress(f"raw: viewing+app month {idx+1:02d}/{C.N_MONTHS}  playlog_rows={m:,}")


def _app_version(devfam, idx):
    out = []
    for d in devfam:
        roll = C.APP_V3_ROLLOUT_IDX.get(d, 30)
        if idx >= roll:
            out.append(f"3.{idx - roll}.0")
        else:
            out.append(f"2.{max(0, 8 - (roll - idx))}.4")
    return out


# =========================================================================
# Ketch billing & subscriptions
# =========================================================================
def gen_ketch(world):
    (C.RAW / "ketch").mkdir(parents=True, exist_ok=True)
    subs = world["subscribers"].set_index("subscriber_id")
    sm = world["subscription_month"]
    events = world["subscription_events"]
    r = rng("raw", "ketch")

    # ---- plan catalog xlsx (Excel serials + text prices) ----
    rows = []
    for tier in C.TIERS:
        for mk in C.MARKETS:
            price_end = C.PRICE_LOCAL_END[tier][mk]
            eff_pre = month_start(0)
            rows.append({"plan_code": f"{tier[:3].upper()}-{mk}", "plan_name": tier, "market": mk,
                         "effective_from": to_excel_serial(eff_pre),
                         "list_price": money_str(price_end / (1.18 if (mk == "BR" and tier != "Basico") else 1.0),
                                                 "br" if mk == "BR" else ("mx" if mk == "MX" else "us")),
                         "billing_period": "monthly"})
            if mk == "BR" and tier in ("Standard", "Premium"):
                rows.append({"plan_code": f"{tier[:3].upper()}-{mk}", "plan_name": tier, "market": mk,
                             "effective_from": to_excel_serial(month_start(C.BR_PRICE_HIKE_IDX)),
                             "list_price": money_str(price_end, "br"), "billing_period": "monthly"})
    pc = pd.DataFrame(rows)
    _write_xlsx({"plans": pc}, C.RAW / "ketch" / "ketch__plan_catalog.xlsx")
    _bump("excel_serial_date_cells", len(pc))

    # ---- invoices, monthly files with overlapping ranges + money strings ----
    bill = world["billing_attempts"].join(subs[["market"]], on="subscriber_id")
    bill["invoice_id"] = [f"INV{r.integers(10**9, 10**10)}" for _ in range(len(bill))]
    for idx in range(C.N_MONTHS):
        cur_rows = bill[bill["month_idx"] == idx].copy()
        if len(cur_rows) == 0:
            continue
        loc = cur_rows["market"].map({"BR": "br", "MX": "mx", "US": "us"})
        out = pd.DataFrame({
            "invoice_id": cur_rows["invoice_id"],
            "account": cur_rows["subscriber_id"],
            "issued": [fmt_date(month_start(idx) + pd.Timedelta(days=int(d) - 1),
                                "br" if m == "BR" else ("us" if m == "US" else "iso"))
                       for d, m in zip(cur_rows["billing_day"], cur_rows["market"])],
            "amount": [money_str(a, "parens_br" if (m == "BR" and r.random() < 0.3) else l)
                       for a, m, l in zip(cur_rows["amount_local"], cur_rows["market"], loc)],
            "currency": cur_rows["market"].map(CUR),
            "status": cur_rows["status"].map({"approved": "paid", "failed": "open"}),
        })
        # Q04 overlapping monthly files: 3% of prior-month invoices re-appear here
        if idx > 0 and C.DQ_INJECT["overlapping_invoice_files"]:
            prev = bill[bill["month_idx"] == idx - 1]
            spill = prev.sample(frac=0.03, random_state=idx)
            sp = pd.DataFrame({
                "invoice_id": spill["invoice_id"], "account": spill["subscriber_id"],
                "issued": [fmt_date(month_end(idx - 1), "br") for _ in range(len(spill))],
                "amount": [money_str(a, "br") for a in spill["amount_local"]],
                "currency": spill["market"].map(CUR),
                "status": spill["status"].map({"approved": "paid", "failed": "open"}),
            })
            out = pd.concat([out, sp], ignore_index=True)
            _bump("overlapping_invoice_rows", len(sp))
        _bump("money_string_cells", len(out))
        write_csv(out, C.RAW / "ketch" / f"ketch__invoices__{month_label(idx)}.csv")

    # ---- daily-ish snapshot: monthly full dump w/ ledger drift ----
    # state as of each month end, rebuilt from sub_month; then perturb.
    for idx in range(C.N_MONTHS):
        state = sm[sm["month_idx"] == idx][["subscriber_id", "status", "tier", "billing_period"]].copy()
        if len(state) == 0:
            continue
        state = state.join(subs[["market", "signup_date"]], on="subscriber_id")
        state["plan_name"] = [jitter_category(t, r, CATEGORY_VARIANTS) if C.DQ_INJECT["category_noise"] else t
                              for t in state["tier"]]
        state["country"] = [jitter_category(m, r, CATEGORY_VARIANTS) if C.DQ_INJECT["category_noise"] else m
                            for m in state["market"]]
        state["snapshot_date"] = fmt_date(month_end(idx), "iso")
        # Q07 snapshot-vs-ledger drift: flip some statuses / drop some cancels
        if C.DQ_INJECT["snapshot_ledger_drift"]:
            d = state.sample(frac=C.DQ_RATES["snapshot_drift_frac"], random_state=idx).index
            state.loc[d, "status"] = state.loc[d, "status"].map(
                {"active": "active", "paused": "active"}).fillna("active")
            _bump("snapshot_drift_rows", len(d))
        # Q04 daily full-dump: duplicate ~2 extra copies with different snapshot_date
        dumps = [state]
        if C.DQ_INJECT["daily_full_dump_snapshot"]:
            for k in (10, 20):
                c = state.copy()
                c["snapshot_date"] = fmt_date(month_start(idx) + pd.Timedelta(days=k), "iso")
                dumps.append(c)
            _bump("snapshot_dump_extra_rows", 2 * len(state))
        alld = pd.concat(dumps, ignore_index=True)[
            ["subscriber_id", "snapshot_date", "status", "plan_name", "billing_period", "country"]]
        alld = alld.rename(columns={"subscriber_id": "account"})
        write_csv(alld, C.RAW / "ketch" / f"ketch__subscriptions_snapshot__{month_label(idx)}.csv")
    progress("raw: ketch done")


# =========================================================================
# PagStream gateway
# =========================================================================
def gen_pagstream(world):
    (C.RAW / "pagstream").mkdir(parents=True, exist_ok=True)
    subs = world["subscribers"].set_index("subscriber_id")
    bill = world["billing_attempts"].join(subs[["market"]], on="subscriber_id").reset_index(drop=True)
    r = rng("raw", "pagstream")
    bill["txn_id"] = [f"pg_{r.integers(10**11, 10**12)}" for _ in range(len(bill))]
    for idx in range(C.N_MONTHS):
        b = bill[bill["month_idx"] == idx].copy()
        if len(b) == 0:
            continue
        fee = [round(a * C.PROC_COST[m]["pct"] + C.PROC_COST[m]["fixed"], 2)
               for a, m in zip(b["amount_local"], b["method"])]
        b["fee"] = fee
        settled = b["status"].to_numpy() == "approved"
        # Q06 mislabel: 'amount' = gross for approved, but net-of-fee for settled subset
        amt = b["amount_local"].to_numpy().astype(float)
        net_mask = settled & (r.random(len(b)) < 0.5)
        amt = np.where(net_mask, amt - np.array(fee), amt)
        _bump("gross_net_mislabeled_rows", int(net_mask.sum()))
        # Q08 refunds: ~1.2% of approved become negative refund rows
        ttype = np.where(b["is_dunning"], "retry", "charge")
        ref = settled & (r.random(len(b)) < 0.012)
        amt = np.where(ref, -amt, amt)
        ttype = np.where(ref, "refund", ttype)
        _bump("negative_refund_rows", int(ref.sum()))
        meta = [json.dumps({"method": m, "attempt": int(an), "dunning": bool(dn),
                            "reason": rr or None})
                for m, an, dn, rr in zip(b["method"], b["attempt_number"],
                                         b["is_dunning"], b["failure_reason"])]
        out = pd.DataFrame({
            "txn_id": b["txn_id"],
            "account_id": b["subscriber_id"],
            "ts": [ (month_start(idx) + pd.Timedelta(days=int(d)-1, seconds=int(r.integers(0,86400))))
                    .strftime("%Y-%m-%dT%H:%M:%SZ") for d in b["billing_day"] ],
            "amount": np.round(amt, 2),
            "fee": b["fee"],
            "currency": b["market"].map(CUR),
            "type": ttype,
            "result": np.where(b["status"].to_numpy() == "approved", "approved", "declined"),
            "meta": meta,
        })
        # Q13 null keys: ~0.3% guest rows
        if C.DQ_INJECT["null_keys"]:
            g = out.sample(frac=C.DQ_RATES["null_billing_key_frac"], random_state=idx).index
            out.loc[g, "account_id"] = None
            _bump("null_account_id_rows", len(g))
        write_csv(out, C.RAW / "pagstream" / f"pagstream__transactions__{month_label(idx)}.csv")

        # settlement batches (carrier billing lags a month)
        b["settle_idx"] = [idx + (1 if mth == "carrier_billing" else 0) for mth in b["method"]]
        s = (b[b["status"] == "approved"].groupby(["method", "settle_idx"])
             .agg(gross=("amount_local", "sum"), fees=("fee", "sum"), n=("txn_id", "count"))
             .reset_index())
        s["batch_id"] = [f"ST{r.integers(10**7,10**8)}" for _ in range(len(s))]
        s["settle_date"] = s["settle_idx"].apply(lambda j: fmt_date(month_start(min(j, C.N_MONTHS-1)) + pd.Timedelta(days=5), "iso"))
        write_csv(s[["batch_id", "settle_date", "method", "gross", "fees", "n"]],
                  C.RAW / "pagstream" / f"pagstream__settlement__{month_label(idx)}.csv")
    progress("raw: pagstream done")


# =========================================================================
# VoxaID identity + Bonsai CRM
# =========================================================================
def gen_identity_crm(world):
    for d in ("voxaid", "bonsai"):
        (C.RAW / d).mkdir(parents=True, exist_ok=True)
    subs = world["subscribers"].copy()
    r = rng("raw", "identity")

    acc = pd.DataFrame({
        "account_id": subs["subscriber_id"],
        "email": [f"user{i}@example.com" for i in range(len(subs))],
        "market": [jitter_category(m, r, CATEGORY_VARIANTS) for m in subs["market"]],
        "created_at": [fmt_date(d, "mon") for d in subs["signup_date"]],
        "primary_device": [jitter_category(x, r, CATEGORY_VARIANTS) for x in subs["primary_device_family"]],
    })
    # Q05 GDPR-deleted omitted; test accounts unflagged (present but a few % are 'test')
    if C.DQ_INJECT["orphan_foreign_keys"]:
        drop = acc.sample(frac=C.DQ_RATES["orphan_subscriber_frac"], random_state=1).index
        acc = acc.drop(index=drop)
        _bump("gdpr_deleted_omitted", len(drop))
    text = acc.to_csv(index=False)
    if C.DQ_INJECT["bom"]:
        text = add_bom(text)
        _bump("bom_files", 1)
    write_text(text, C.RAW / "voxaid" / "voxaid__accounts.csv")

    # device registrations (multi-row, unnormalised, dupes)
    reg_rows = []
    for _, s in subs.iterrows():
        k = 1 + int(r.integers(0, 3))
        fams = r.choice(C.DEVICE_FAMILIES, k)
        for f in fams:
            reg_rows.append({"account_id": s["subscriber_id"],
                             "device_family": jitter_category(f, r, CATEGORY_VARIANTS),
                             "registered_at": fmt_date(s["signup_date"], "iso")})
        if r.random() < 0.05:
            reg_rows.append(reg_rows[-1])
    write_csv(pd.DataFrame(reg_rows), C.RAW / "voxaid" / "voxaid__device_registrations.csv")

    # CRM contacts (Latin-1 mojibake names, free-text lifecycle, birth_year noise,
    # missing early cohorts)
    stages = ["new", "engaged", "at_risk", "winback", "power_user", "Novo", "Engajado"]
    names = ["João Souza", "María Fernández", "André Gonçalves", "Cecília Nuñez",
             "Sofía Rodríguez", "Thiago Araújo", "Núria Peña", "Renée Dubois"]
    crm = subs.copy()
    crm = crm[crm["signup_idx"] >= 2]        # Bonsai joined late -> early cohorts absent
    _bump("crm_missing_early_rows", int((subs["signup_idx"] < 2).sum()))
    out = pd.DataFrame({
        "account_id": crm["subscriber_id"],
        "full_name": [maybe_mojibake(str(r.choice(names)), C.DQ_INJECT["encoding_mojibake"]) for _ in range(len(crm))],
        "lifecycle_stage": [str(r.choice(stages)) for _ in range(len(crm))],
        "birth_year": [int(r.choice([0, 1900, *range(1960, 2006)], p=_byp())) for _ in range(len(crm))],
        "consent_marketing": [bool(r.random() < 0.8) for _ in range(len(crm))],
    })
    if C.DQ_INJECT["encoding_mojibake"]:
        _bump("mojibake_name_rows", len(out))
    txt = out.to_csv(index=False)
    write_bytes(txt.encode("latin-1", errors="replace"), C.RAW / "bonsai" / "bonsai__crm_contacts.csv")

    wb = crm.sample(frac=0.6, random_state=2)
    write_csv(pd.DataFrame({
        "account_id": wb["subscriber_id"],
        "campaign": [str(r.choice(["WB-Q1", "WB-Q2", "winback_email", "WINBACK", "wb push"])) for _ in range(len(wb))],
        "joined_at": [fmt_date(month_start(int(i)) + pd.Timedelta(days=10), "iso") for i in wb["signup_idx"]],
    }), C.RAW / "bonsai" / "bonsai__winback_membership.csv")
    progress("raw: identity + crm done")


def _byp():
    p = np.array([0.03, 0.02] + [1.0] * 46)
    return p / p.sum()


# =========================================================================
# Entitlement ledger
# =========================================================================
def gen_entitlement(world):
    (C.RAW / "entitlement").mkdir(parents=True, exist_ok=True)
    ev = world["subscription_events"].copy()
    r = rng("raw", "entitlement")
    ev = ev.sample(frac=1.0, random_state=7).reset_index(drop=True)   # out-of-order
    recs = []
    for _, e in ev.iterrows():
        rec = {"event_id": f"ent_{r.integers(10**11, 10**12)}",
               "subject": e["subscriber_id"], "kind": e["event_type"],
               "occurred_at": e["event_ts"]}
        for k in ("from_tier", "to_tier", "reason_code"):
            if k in e and pd.notna(e.get(k)):
                rec[k] = e[k]
        recs.append(rec)
    # Q04 at-least-once: duplicate ~1.8%
    if C.DQ_INJECT["duplicate_events"]:
        dup = list(np.random.default_rng(3).choice(len(recs), int(len(recs) * C.DQ_RATES["duplicate_event_frac"])))
        for i in dup:
            recs.append(dict(recs[i]))
        _bump("dupe_entitlement_rows", len(dup))
    np.random.default_rng(9).shuffle(recs)
    write_jsonl(recs, C.RAW / "entitlement" / "entitlement__events.jsonl")
    progress("raw: entitlement done")


# =========================================================================
# Reelbase + Content Finance
# =========================================================================
def gen_content_raw(content):
    for d in ("reelbase", "contentfin"):
        (C.RAW / d).mkdir(parents=True, exist_ok=True)
    t = content["titles"].copy()
    r = rng("raw", "reelbase")
    t["title"] = [maybe_mojibake(x, C.DQ_INJECT["encoding_mojibake"]) for x in t["title"]]
    t["release_date"] = [to_excel_serial(d) if r.random() < 0.5 else fmt_date(d, "br")
                         for d in t["release_date"]]
    t.loc[t.sample(frac=0.04, random_state=1).index, "primary_genre"] = ""
    t["is_original"] = [r.choice(["Y", "N", "", "1", "0"]) if o else r.choice(["N", "0", ""])
                        for o in content["titles"]["is_original"]]
    _bump("reelbase_encoding_rows", len(t))
    _bump("reelbase_mixed_date_rows", len(t))
    _write_xlsx({"titles": t, "meta": pd.DataFrame({"exported_at": [fmt_date(_dt.date.today(), "iso")]})},
                C.RAW / "reelbase" / "reelbase__titles.xlsx")
    lw = content["licence_windows"].copy()
    lw["window_start"] = [fmt_date(d, "iso") for d in lw["window_start"]]
    lw["window_end"] = [fmt_date(d, "iso") for d in lw["window_end"]]
    write_csv(lw, C.RAW / "reelbase" / "reelbase__licence_windows.csv")

    # amort schedule xlsx: month columns as Excel serials, parentheses negatives
    cost = content["content_cost_month"]
    piv = cost.pivot_table(index="content_id", columns="month_idx", values="amort_usd", aggfunc="sum").fillna(0)
    piv.columns = [to_excel_serial(month_start(int(c))) for c in piv.columns]
    piv = piv.reset_index()
    for c in piv.columns[1:]:
        piv[c] = piv[c].apply(lambda v: money_str(-v, "parens_br") if r.random() < 0.15 else round(v, 2))
    _bump("contentfin_parens_negative_cells", int(len(piv) * 0.15 * (len(piv.columns) - 1)))
    _bump("excel_serial_date_cells", len(piv.columns) - 1)
    _write_xlsx({"amort": piv}, C.RAW / "contentfin" / "contentfin__amort_schedule.xlsx")

    cm = (cost[cost["cash_spend_usd"] > 0]
          .groupby("content_id").agg(cash=("cash_spend_usd", "sum")).reset_index())
    cm["milestone_date"] = [fmt_date(month_start(int(r.integers(0, C.N_MONTHS))), "us") for _ in range(len(cm))]
    cm["amount"] = [money_str(v, "us") for v in cm["cash"]]
    _write_xlsx({"cash_milestones": cm[["content_id", "milestone_date", "amount"]]},
                C.RAW / "contentfin" / "contentfin__cash_milestones.xlsx")
    progress("raw: content raw done")


# =========================================================================
# AdBridge + SSP
# =========================================================================
def gen_marketing_raw(mktg):
    for d in ("adbridge", "voxaads"):
        (C.RAW / d).mkdir(parents=True, exist_ok=True)
    sw = mktg["spend_weekly"].copy()
    r = rng("raw", "adbridge")
    sw["channel"] = [jitter_category(c, r, CATEGORY_VARIANTS) for c in sw["channel"]]
    sw["market"] = sw["market"]
    # Q06: for MX rows the 'spend_usd' header actually carries MXN
    mx = sw["market"] == "MX"
    sw.loc[mx, "spend_usd"] = (sw.loc[mx, "spend_usd"] * 17.8).round(2)
    _bump("mxn_in_usd_column_rows", int(mx.sum()))
    # Q06: partner_bundle rows -> 'clicks' actually holds impressions
    pb = sw["channel"].str.lower().str.contains("bundle|partner")
    sw.loc[pb, "clicks"] = sw.loc[pb, "impressions"]
    _bump("clicks_are_impressions_rows", int(pb.sum()))
    sw["week_start"] = [fmt_date(d, "iso") for d in sw["week_start"]]
    write_csv(sw[["week_start", "market", "channel", "campaign_id", "spend_usd",
                  "impressions", "clicks", "signups_attributed", "is_test_campaign"]],
              C.RAW / "adbridge" / "adbridge__spend_weekly.csv")
    at = mktg["attribution"].copy()
    at["touch_ts"] = [fmt_date(month_start(int(i)) + pd.Timedelta(days=int(r.integers(0, 27))), "iso")
                      for i in at["signup_idx"]]
    write_csv(at[["market", "channel", "campaign_id", "touch_ts"]],
              C.RAW / "adbridge" / "adbridge__attribution.csv")
    progress("raw: adbridge done")


def gen_ssp_raw(ads):
    (C.RAW / "voxaads").mkdir(parents=True, exist_ok=True)
    a = ads.copy()
    r = rng("raw", "ssp")
    a["date"] = [fmt_date(d, "us") for d in a["date"]]      # MM/DD/YYYY
    # duplicate ~1% day rows (re-runs)
    dup = a.sample(frac=0.01, random_state=5)
    a = pd.concat([a, dup], ignore_index=True)
    _bump("ssp_duplicate_day_rows", len(dup))
    write_csv(a, C.RAW / "voxaads" / "voxaads__ssp_daily_revenue.csv")
    progress("raw: ssp done")


# =========================================================================
# Support (schema break v1 -> v2)
# =========================================================================
def gen_support_raw(support):
    (C.RAW / "helpline").mkdir(parents=True, exist_ok=True)
    (C.RAW / "helpdesk").mkdir(parents=True, exist_ok=True)
    r = rng("raw", "support")
    v1_reason = {"billing_payment": "Billing", "app_playback": "Cannot play video",
                 "app_crash": "App crash", "content_request": "Missing title",
                 "account_access": "Login problem", "other": "Other"}
    v2_reason = {"billing_payment": "billing.payment_declined", "app_playback": "playback.error",
                 "app_crash": "app.crash", "content_request": "catalog.request",
                 "account_access": "account.login", "other": "misc"}
    s = support.copy()
    v1 = s[s["source_version"] == "v1"]
    v2 = s[s["source_version"] == "v2"]
    o1 = pd.DataFrame({
        "TicketID": v1["ticket_id"], "Account": v1["subscriber_id"],
        "Created": [fmt_date(pd.Timestamp(t), "br") for t in v1["created_ts"]],
        "Reason": v1["reason_category"].map(v1_reason),
        "Channel": v1["contact_channel"].str.capitalize(),
        "ResolutionHrs": v1["resolution_hours"],
        "CSAT": v1["csat_1_5"],       # 1..5
    })
    write_csv(o1, C.RAW / "helpline" / "helpline__v1_tickets.csv")
    o2 = pd.DataFrame({
        "ticket_ref": v2["ticket_id"], "user_id": v2["subscriber_id"],
        "opened_at": [pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ") for t in v2["created_ts"]],
        "reason_code": v2["reason_category"].map(v2_reason),
        "contact_channel": v2["contact_channel"],
        "handle_time_min": (v2["resolution_hours"] * 60).round(1),
        "satisfaction_0_10": (v2["csat_1_5"] * 2).round(1),   # 0..10
        "reopened": v2["is_reopened"],
    })
    # Q11 cutover dupes: ~1.5% of first post-migration month exist in both files
    cut = v2[v2["created_month_idx"] == C.SUPPORT_MIGRATION_IDX].sample(frac=0.15, random_state=8)
    dup1 = pd.DataFrame({
        "TicketID": cut["ticket_id"], "Account": cut["subscriber_id"],
        "Created": [fmt_date(pd.Timestamp(t), "br") for t in cut["created_ts"]],
        "Reason": cut["reason_category"].map(v1_reason), "Channel": cut["contact_channel"].str.capitalize(),
        "ResolutionHrs": cut["resolution_hours"], "CSAT": cut["csat_1_5"],
    })
    o1b = pd.concat([o1, dup1], ignore_index=True)
    write_csv(o1b, C.RAW / "helpline" / "helpline__v1_tickets.csv")
    write_csv(o2, C.RAW / "helpdesk" / "helpdesk__v2_tickets.csv")
    _bump("support_cutover_dupe_rows", len(cut))
    progress("raw: support done")


# =========================================================================
# Ledger GL + FX
# =========================================================================
def gen_ledger_raw(gl, fx):
    (C.RAW / "ledger").mkdir(parents=True, exist_ok=True)
    acct_name = {
        "revenue_subscription": "4000 Subscription Revenue", "revenue_advertising": "4100 Advertising Revenue",
        "revenue_partner": "4200 Partner Revenue", "cost_content_amort": "5000 Content Amortization",
        "cost_cdn": "5100 Streaming Delivery", "cost_payment": "5200 Payment Processing",
        "cost_marketing": "6000 Marketing", "cost_support": "6100 Customer Support",
        "cost_g_and_a": "6900 G&A Allocation",
    }
    for idx in range(C.N_MONTHS):
        g = gl[gl["month_idx"] == idx].copy()
        if len(g) == 0:
            continue
        g["account"] = g["pnl_line"].map(acct_name)
        g["period"] = month_label(idx)
        write_csv(g[["period", "market", "account", "amount_usd"]],
                  C.RAW / "ledger" / f"ledger__gl_trial_balance__{month_label(idx)}.csv")
    fxo = fx.copy()
    fxo["month"] = fxo["month_idx"].apply(month_label)
    fxo = fxo[fxo["currency"] != "USD"]
    # Q12 a few months missing
    miss = fxo.sample(frac=0.05, random_state=4).index
    fxo = fxo.drop(index=miss)
    _bump("fx_missing_month_rows", len(miss))
    write_csv(fxo[["month", "currency", "avg_rate", "eop_rate"]],
              C.RAW / "ledger" / "ledger__fx_rates.csv")
    progress("raw: ledger done")


# =========================================================================
def _write_xlsx(sheets: dict, path):
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
    write_bytes(bio.getvalue(), path)


# =========================================================================
def main():
    t0 = _dt.datetime.now()
    if C.RAW.exists():
        for sub in C.RAW.iterdir():
            if sub.is_dir():
                shutil.rmtree(sub, ignore_errors=True)
    C.RAW.mkdir(parents=True, exist_ok=True)
    progress(f"RAW build  SEED={C.SEED}  POP_SCALE={C.POP_SCALE}")

    world = build_world()
    progress(f"world sizes: subs={len(world['subscribers']):,} "
             f"sub_months={len(world['subscription_month']):,} "
             f"events={len(world['subscription_events']):,} "
             f"billing={len(world['billing_attempts']):,}")
    content = build_content()
    fx = E.build_fx()
    mktg = E.build_marketing(world)
    ads = E.build_ad_revenue(world)
    support = E.build_support(world)
    gl = E.build_gl(world, content, ads, mktg, support, fx)

    gen_ketch(world)
    gen_pagstream(world)
    gen_identity_crm(world)
    gen_entitlement(world)
    gen_content_raw(content)
    gen_marketing_raw(mktg)
    gen_ssp_raw(ads)
    gen_support_raw(support)
    gen_ledger_raw(gl, fx)
    gen_viewing_and_app(world, content)

    # stash a few clean frames the curated layer reconciles against (not a "source")
    (C.RAW / "_truth").mkdir(parents=True, exist_ok=True)
    for k in ("subscribers", "subscription_month", "subscriber_churn"):
        write_parquet(world[k], C.RAW / "_truth" / f"{k}.parquet")
    write_parquet(gl, C.RAW / "_truth" / "gl.parquet")

    dq_fragment("raw_injection", INJ)
    progress(f"RAW build done in {(_dt.datetime.now()-t0).total_seconds():.0f}s")
    print(json.dumps(INJ, indent=2))


if __name__ == "__main__":
    main()

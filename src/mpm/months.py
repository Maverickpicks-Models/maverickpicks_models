r"""Month by month, last season and this one: every angle we can measure, which months it works in, whether it held
up this season, and whether the books over-correct.

  python -m mpm.months --season 2025-26 --season 2026-27 --out C:\MaverickPicks\reports

The first season is where angles are found; the later one (this season to date) is the check. Sections:
  A. the market by month (home / favorite / Over cover, line vs actual totals, ML favorites vs dogs);
  B. our rules by month (v5 rules, C1, C4, P1, P2);
  C. every single condition by month. Beyond the mine.py features it adds schedule and travel (rest days, 3-in-4,
     road-trip and homestand length, first home game after a 3+ game trip, miles travelled, time zones crossed,
     altitude), last game (blowout win/loss, overtime), revenge (lost to this opponent earlier), tip time and
     weekend, team form against the spread and the total, and market structure (ML priced cheaper than the spread
     implies, Pinnacle's line vs the other books, Novig vs Pinnacle);
     lists: held in both seasons; strong in one month; turned on / off;
  D. month-to-month memory and a walk-forward follow vs fade of hot angles (over-correction test);
  E. teams: does a team's record against the spread or total carry into the next month (the market slow to
     re-rate a team), with a walk-forward follow / fade of the hottest and coldest teams;
  F. Novig vs Pinnacle at bet time (the historical version of S1) and Pinnacle vs the other books.
One month is ~200 games; a 60-bet month carries about +-13% of noise.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import datetime as dt
import math
import os
import statistics
import sys
from statistics import NormalDist

from . import mine, quarters as Qm

MON = {10: "Oct", 11: "Nov", 12: "Dec", 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun"}
ET = dt.timezone(dt.timedelta(hours=-5))
SPREAD_NEW = ["b2b_own", "b2b_opp", "three_in_four", "rest_own", "rest_opp", "trip_len", "stand_len", "home_after_trip",
              "travel_km", "tz_moved", "at_altitude", "last_margin", "opp_last_margin", "last_ot", "revenge", "game_no",
              "weekend", "early_tip", "late_tip", "ml_resid", "lean_own", "ats_own", "ats_opp"]
TOTAL_NEW = ["ou_form", "total_lean", "early_tip", "late_tip", "weekend", "altitude_game", "both_rested", "b2b_both", "game_no"]
NEW_BOOL = {"b2b_own", "b2b_opp", "three_in_four", "home_after_trip", "at_altitude", "last_ot", "revenge", "weekend",
            "early_tip", "late_tip", "altitude_game", "both_rested", "b2b_both"}
FEATS = {"spreads": [f for f in mine.FEATS["spreads"] if f != "early"] + SPREAD_NEW,
         "h2h": [f for f in mine.FEATS["h2h"] if f != "early"] + SPREAD_NEW,
         "totals": [f for f in mine.FEATS["totals"] if f != "early"] + TOTAL_NEW}
ALL_BOOL = set(mine.BOOL) | NEW_BOOL


def month_key(d: dt.date) -> str:
    return f"{MON[d.month]} {d:%y}"


def month_order(keys):
    num = {v: k for k, v in MON.items()}
    return sorted(keys, key=lambda m: (2000 + int(m.split()[1]), num[m.split()[0]]))


# ---------------------------------------------------------------- extra features
def _km(a, b):
    if None in (a[0], a[1], b[0], b[1]):
        return 0.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(min(1, h)))


def add_context(db, rows, season):
    teams = {t: (lat, lon, tz, alt) for t, lat, lon, tz, alt in
             db.q("SELECT team_code, lat, lon, utc_offset, altitude_ft FROM core.teams WHERE league='NBA'")}
    log = collections.defaultdict(list)          # team -> [(date, opp, is_home, margin, ot)]
    for t, d, opp, home, pts, opp_pts, mins in db.q(
            "SELECT team_code, game_date, opp_code, is_home, pts, opp_pts, mins FROM nba.team_game_log WHERE season=?", (season,)):
        log[t].append((dt.date.fromisoformat(str(d)[:10]), opp, bool(home),
                       None if pts is None or opp_pts is None else pts - opp_pts, (mins or 240) > 242))
    for t in log:
        log[t].sort()
    dates = {t: [x[0] for x in v] for t, v in log.items()}
    starts = {gid: s for gid, s in db.q("SELECT game_id, start_utc FROM core.games WHERE league='NBA' AND start_utc IS NOT NULL")}
    lines = market_extras(db)

    def prior(t, day):
        return log[t][:bisect.bisect_left(dates.get(t, []), day)]

    def ctx(t, day, home, host):
        p = prior(t, day)
        last = p[-1] if p else None
        rest = min(3, (day - last[0]).days - 1) if last else 3
        b2b = rest == 0
        three4 = sum(1 for x in p if (day - x[0]).days <= 3) >= 2
        run = 0
        for x in reversed(p):
            if x[2] == home:
                run += 1
            else:
                break
        trip_before = 0
        if home and p and not p[-1][2]:
            for x in reversed(p):
                if not x[2]:
                    trip_before += 1
                else:
                    break
        prev_site = (last[1] if not last[2] else t) if last else host
        here, there = teams.get(host, (None,) * 4), teams.get(prev_site, (None,) * 4)
        km = _km(here, there) if last else 0.0
        tzm = abs((here[2] or 0) - (there[2] or 0)) if last else 0
        return dict(rest=rest, b2b=b2b, three4=three4, run=run + 1, trip_before=trip_before, km=km, tz=tzm,
                    last_margin=(last[3] if last and last[3] is not None else 0), last_ot=bool(last and last[4]),
                    p=p, gp=len(p))

    for r in rows:
        g = r["g"]; day, a, h = g["date"], g["away"], g["home"]
        me, opp = (a, h) if r["side"] == "away" else (h, a)
        home = r["side"] == "home"
        cm, co = ctx(me, day, home, h), ctx(opp, day, not home, h)
        r.update(b2b_own=cm["b2b"], b2b_opp=co["b2b"], three_in_four=cm["three4"], rest_own=cm["rest"], rest_opp=co["rest"],
                 trip_len=0 if home else cm["run"], stand_len=cm["run"] if home else 0, home_after_trip=home and cm["trip_before"] >= 3,
                 travel_km=cm["km"], tz_moved=cm["tz"], at_altitude=(not home) and (teams.get(h, (0, 0, 0, 0))[3] or 0) >= 4000,
                 last_margin=cm["last_margin"], opp_last_margin=co["last_margin"], last_ot=cm["last_ot"],
                 revenge=any(x[1] == opp and x[3] is not None and x[3] < 0 for x in cm["p"]), game_no=cm["gp"] + 1,
                 weekend=day.weekday() >= 5, both_rested=cm["rest"] >= 1 and co["rest"] >= 1, b2b_both=cm["b2b"] and co["b2b"],
                 altitude_game=(teams.get(h, (0, 0, 0, 0))[3] or 0) >= 4000)
        s = starts.get(g["id"])
        if s:
            s = s if isinstance(s, dt.datetime) else dt.datetime.fromisoformat(str(s)[:19])
            hr = (s.replace(tzinfo=dt.timezone.utc).astimezone(ET)).hour
            r["early_tip"], r["late_tip"] = hr < 18, hr >= 22
        else:
            r["early_tip"] = r["late_tip"] = False
        # ML priced vs what the spread implies (+ = ML cheaper than the spread says)
        my_sp = -r["spread"] if r["fav"] else r["spread"]
        r["ml_resid"] = NormalDist().cdf(-my_sp / 12.5) - r["ml_nv"]
        x = lines.get(g["id"], {})
        sp = x.get("spreads"); tt = x.get("totals")
        r["lean_own"] = 0.0 if not sp else (sp["cons"] - sp["pin"]) * (1 if r["side"] == "away" else -1)   # + = Pinnacle likes our side more
        r["total_lean"] = 0.0 if not tt else tt["pin"] - tt["cons"]                                       # + = Pinnacle total higher
        r["novig"] = x.get("novig", {})
    return rows


def market_extras(db):
    """Per game at the bet-time snapshot: Pinnacle vs median-of-other-books lines, and Novig vs Pinnacle no-vig."""
    from .backtest import _imp
    rows = db.q("""
        SELECT o.game_id, s.pulled_at_utc, o.bookmaker, o.market, o.side, o.point, o.price_american
        FROM core.odds o JOIN core.odds_snapshots s ON s.snapshot_id = o.snapshot_id JOIN core.games g ON g.game_id = o.game_id
        WHERE s.purpose IN ('hist_bet','hist_early') AND g.league = 'NBA' AND o.market IN ('h2h','spreads','totals')
          AND (g.start_utc IS NULL OR s.pulled_at_utc <= g.start_utc)""")
    latest = {}
    for gid, ts, *_ in rows:
        latest[gid] = max(latest.get(gid, ts), ts)
    book = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(dict)))
    for gid, ts, bk, mk, side, point, price in rows:
        if ts == latest[gid]:
            book[gid][mk][bk][side] = (None if point is None else float(point), int(price))
    out = {}
    for gid, mks in book.items():
        g = {}
        for mk, books in mks.items():
            pair = ("over", "under") if mk == "totals" else ("away", "home")
            full = {b: v for b, v in books.items() if all(s in v for s in pair)}
            if mk != "h2h" and "pinnacle" in full:
                others = [v[pair[0]][0] for b, v in full.items() if b not in ("pinnacle", "novig") and v[pair[0]][0] is not None]
                if others:
                    g[mk] = {"pin": full["pinnacle"][pair[0]][0], "cons": statistics.median(others)}
            if "pinnacle" in full and "novig" in full:
                p, n = full["pinnacle"], full["novig"]
                a, b = _imp(p[pair[0]][1]), _imp(p[pair[1]][1])
                fair = {pair[0]: a / (a + b), pair[1]: b / (a + b)}
                for s in pair:
                    same = mk == "h2h" or p[s][0] == n[s][0]
                    if same:
                        g.setdefault("novig", {})[(mk, s)] = (fair[s] - _imp(n[s][1]), n[s][1], n[s][0])
        out[gid] = g
    return out


# ---------------------------------------------------------------- conditions
def cuts_for(rows):
    c = Qm.cuts_for(rows)
    for f in {f for v in FEATS.values() for f in v} - ALL_BOOL:
        if f not in c:
            v = sorted(r[f] for r in rows if r.get(f) is not None)
            if v:
                c[f] = (v[len(v) // 3], v[2 * len(v) // 3])
    return c


def holds(row, cond, cuts):
    f, v = cond
    x = row.get(f)
    if f in ALL_BOOL:
        return bool(x) == (v == "yes")
    if x is None or f not in cuts:
        return False
    lo, hi = cuts[f]
    if lo == hi:
        return (x < lo) if v == "low" else (x > hi) if v == "high" else (x == lo)
    return (x < lo) if v == "low" else (x >= hi) if v == "high" else (lo <= x < hi)


def single_bets(rows, cuts):
    out = []
    for mk in ("spreads", "h2h", "totals"):
        conds = [(f, v) for f in FEATS[mk] for v in (("yes", "no") if f in ALL_BOOL else ("low", "mid", "high"))]
        for row, s in mine.bets(rows, mk):
            for c in conds:
                if holds(row, c, cuts):
                    out.append((f"{mk}:{s if mk == 'totals' else 'any'} when {c[0]}={c[1]}", row, mk, s))
    return out


def by_month(bets, seasons_of):
    d = collections.defaultdict(lambda: collections.defaultdict(list))
    for key, row, mk, side in bets:
        r = mine.ret(row, mk, side)
        d[key][month_key(row["g"]["date"])].append(r)
        d[key][seasons_of[row["g"]["id"]]].append(r)
    return {k: {m: Qm.stat(v) for m, v in ms.items()} for k, ms in d.items()}


# ---------------------------------------------------------------- report helpers
def market_by_month(rows):
    games = {}
    for r in rows:
        games.setdefault(r["g"]["id"], r)
    M = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in games.values():
        g, L = r["g"], r["L"]; m = month_key(g["date"])
        U, T = L["spreads"]["point"], L["totals"]["point"]
        home_cm = g["hs"] - g["as"] - U; fav_cm = home_cm if U > 0 else -home_cm
        ov = g["as"] + g["hs"] - T
        fav = "away" if L["h2h"]["nv"]["away"] >= .5 else "home"
        x = M[m]
        if home_cm: x["home"].append(home_cm > 0)
        if fav_cm and U: x["fav"].append(fav_cm > 0)
        x["miss"].append(fav_cm); x["line"].append(T); x["act"].append(g["as"] + g["hs"])
        if ov: x["over"].append(ov > 0)
        x["mlf"].append(mine.ret(r, "h2h", fav)[0]); x["mld"].append(mine.ret(r, "h2h", Qm.other("h2h", fav))[0])
        x["n"].append(1)
    ms = month_order(M)
    pct = lambda v: f"{100 * sum(v) / len(v):.0f}%"
    avg = lambda v: f"{statistics.mean(v):+.1f}"
    out = ["| | " + " | ".join(ms) + " |", "|---|" + "---|" * len(ms)]
    for lab, k, f in (("Games", "n", lambda v: str(len(v))), ("Home covers", "home", pct), ("Favorite covers", "fav", pct),
                      ("Fav margin − spread", "miss", avg), ("Total line", "line", lambda v: f"{statistics.mean(v):.1f}"),
                      ("Actual total", "act", lambda v: f"{statistics.mean(v):.1f}"), ("Overs", "over", pct),
                      ("ML favs ROI", "mlf", lambda v: f"{100 * statistics.mean(v):+.0f}%"),
                      ("ML dogs ROI", "mld", lambda v: f"{100 * statistics.mean(v):+.0f}%")):
        out.append(f"| {lab} | " + " | ".join(f(M[m][k]) if M[m][k] else "–" for m in ms) + " |")
    return out, ms


def cell(s):
    return "–" if not s else f"{s['w']}-{s['l']} {100 * s['roi']:+.0f}%"


def table(keys, res, cols, extra=None):
    out = ["| | " + " | ".join(cols) + (" | " + extra[0] if extra else "") + " |", "|---|" + "---|" * (len(cols) + (1 if extra else 0))]
    for k in keys:
        out.append(f"| {k} | " + " | ".join(cell(res[k].get(c)) for c in cols) + (f" | {extra[1](k)}" if extra else "") + " |")
    return out


def follow_fade_months(singles, buckets, lookback=28, min_n=15, z_hot=1.5):
    by_cond = collections.defaultdict(list)
    for key, row, mk, side in singles:
        by_cond[key].append((row["g"]["date"], row, mk, side))
    days = sorted({row["g"]["date"] for _, row, _, _ in singles})
    weeks = sorted({d - dt.timedelta(d.weekday()) for d in days})
    res = {"follow": collections.defaultdict(dict), "fade": collections.defaultdict(dict)}
    for wk in weeks:
        lo = wk - dt.timedelta(lookback)
        for key, L in by_cond.items():
            past = Qm.stat([mine.ret(r, mk, s) for d, r, mk, s in L if lo <= d < wk])
            if not past or past["n"] < min_n or past["z"] < z_hot:
                continue
            for d, r, mk, s in L:
                if wk <= d < wk + dt.timedelta(7):
                    m = month_key(d)
                    res["follow"][m][(r["g"]["id"], mk, s)] = mine.ret(r, mk, s)
                    o = Qm.other(mk, s)
                    res["fade"][m][(r["g"]["id"], mk, o)] = mine.ret(r, mk, o)
    out = ["| | " + " | ".join(buckets) + " | All |", "|---|" + "---|" * (len(buckets) + 1)]
    for name in ("follow", "fade"):
        allv = [v for m in buckets for v in res[name][m].values()]
        s = Qm.stat(allv)
        out.append(f"| {name.title()} hot angles | " + " | ".join(cell(Qm.stat(list(res[name][m].values()))) for m in buckets)
                   + f" | {cell(s)}" + (f" (n {s['n']}, z {s['z']:.2f})" if s else "") + " |")
    return out


def team_section(rows, buckets):
    """Team cover / Over margins by month; does last month predict this month?"""
    seen, T = set(), collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        g, L = r["g"], r["L"]
        if g["id"] in seen:
            continue
        seen.add(g["id"])
        U, Tt = L["spreads"]["point"], L["totals"]["point"]; m = month_key(g["date"])
        T[g["away"]][m].append((g["as"] - g["hs"] + U, g["as"] + g["hs"] - Tt))
        T[g["home"]][m].append((g["hs"] - g["as"] - U, g["as"] + g["hs"] - Tt))
    out = ["| Months | Teams | ATS margin: correlation | Over margin: correlation |", "|---|---|---|---|"]
    for m0, m1 in zip(buckets, buckets[1:]):
        xs, ys, ox, oy = [], [], [], []
        for t, ms in T.items():
            if len(ms.get(m0, [])) >= 5 and len(ms.get(m1, [])) >= 5:
                xs.append(statistics.mean(c for c, _ in ms[m0])); ys.append(statistics.mean(c for c, _ in ms[m1]))
                ox.append(statistics.mean(o for _, o in ms[m0])); oy.append(statistics.mean(o for _, o in ms[m1]))
        if len(xs) >= 8:
            try:
                out.append(f"| {m0}→{m1} | {len(xs)} | {statistics.correlation(xs, ys):+.2f} | {statistics.correlation(ox, oy):+.2f} |")
            except statistics.StatisticsError:
                pass
    # walk-forward: each game, the team's cover margin over its last 10 games (ats_own) top/bottom third -> follow/fade
    return out, T


def team_month_table(T, buckets):
    out = ["| Team | " + " | ".join(buckets) + " | All |", "|---|" + "---|" * (len(buckets) + 1)]
    for t in sorted(T):
        cells, allc = [], []
        for m in buckets:
            v = [c for c, _ in T[t].get(m, [])]
            allc += v
            cells.append(f"{sum(1 for c in v if c > 0)}-{sum(1 for c in v if c < 0)}" if v else "–")
        out.append(f"| {t} | " + " | ".join(cells) + f" | {sum(1 for c in allc if c > 0)}-{sum(1 for c in allc if c < 0)} ({statistics.mean(allc):+.1f}) |")
    return out


def novig_section(rows, buckets):
    """Historical S1: bet Novig when its price is 3%+ (or 2%+) under Pinnacle's fair price, at Novig's own price."""
    from .backtest import grade
    seen, res = set(), collections.defaultdict(lambda: collections.defaultdict(list))
    have = 0
    for r in rows:
        g = r["g"]
        if g["id"] in seen:
            continue
        seen.add(g["id"])
        if r["novig"]:
            have += 1
        for (mk, s), (edge, price, point) in r["novig"].items():
            for thr in (0.02, 0.03, 0.05):
                if edge >= thr:
                    away_pt = None if point is None else (-point if (mk == "spreads" and s == "home") else point)
                    L = {mk: dict(r["L"][mk], point=away_pt)}
                    res_ = grade(g, L, mk, s)
                    from .backtest import _dec
                    v = _dec(price) if res_ == "W" else -1.0 if res_ == "L" else 0.0
                    res[f"Novig {int(thr * 100)}%+ under Pinnacle fair ({mk})"][month_key(g["date"])].append((v, res_))
                    res[f"Novig {int(thr * 100)}%+ under Pinnacle fair ({mk})"]["All"].append((v, res_))
    if not have:
        return ["Novig prices are not in the historical snapshots for these seasons (not in TheOddsAPI's history or not in "
                "ODDS_BOOKMAKERS when pulled), so S1 can only be graded live."]
    out = [f"{have} games with both Novig and Pinnacle at bet time. ROI at Novig's own price.", "",
           "| | " + " | ".join(buckets) + " | All |", "|---|" + "---|" * (len(buckets) + 1)]
    for k in sorted(res):
        out.append(f"| {k} | " + " | ".join(cell(Qm.stat(res[k].get(m, []))) for m in buckets + ["All"]) + " |")
    return out


# ---------------------------------------------------------------- report
def run(db, seasons, out_dir=None, min_gp=1):
    rows, season_of = [], {}
    for s in seasons:
        rs = add_context(db, Qm.add_recent(mine.season_rows(db, s, min_gp)), s)
        for r in rs:
            season_of[r["g"]["id"]] = s
        rows += rs
    disc = seasons[0]
    cuts = cuts_for([r for r in rows if season_of[r["g"]["id"]] == disc])
    L = [f"# Month by month: {', '.join(seasons)}", "",
         f"{len(rows) // 2} games with bet-time Pinnacle no-vig prices. Angles are cut into thirds on {disc}; "
         f"{', '.join(seasons[1:]) or 'no later season'} is the check. W-L and ROI at the no-vig price (≈ Novig). "
         "A 60-bet month has about ±13% of noise.", "", "## A. The market by month", ""]
    mt, months = market_by_month(rows)
    L += mt

    rb = by_month(Qm.rule_bets([r for r in rows if season_of[r["g"]["id"]] == disc], db, disc)
                  + [x for s in seasons[1:] for x in Qm.rule_bets([r for r in rows if season_of[r["g"]["id"]] == s], db, s)], season_of)
    L += ["", "## B. Our rules by month", ""] + table(sorted(rb), rb, months + seasons)

    singles = single_bets(rows, cuts)
    sb = by_month(singles, season_of)
    ids = collections.defaultdict(set)
    for key, row, mk, side in singles:
        ids[key].add((row["g"]["id"], mk, side))

    def distinct(keys, top):                 # drop angles that are 80%+ the same bets as one already listed (e.g. home vs favorite)
        kept = []
        for k in keys:
            if all(len(ids[k] & ids[j]) < 0.8 * min(len(ids[k]), len(ids[j])) for j in kept):
                kept.append(k)
            if len(kept) == top:
                break
        return kept
    later = seasons[1:]
    both, phase, onoff = [], [], []
    for k, ms in sb.items():
        d = ms.get(disc)
        if not d or d["n"] < 60:
            continue
        chk = [ms.get(s) for s in later if ms.get(s)]
        dm = [m for m in months if ms.get(m) and season_of_month(m, rows, season_of) == disc]
        if d["z"] >= 1.5 and chk and all(c["roi"] > 0 for c in chk) and sum(c["n"] for c in chk) >= 25:
            both.append((d["z"] + sum(c["z"] for c in chk), k))
        for m in months:
            s = ms.get(m)
            if s and s["n"] >= 25 and s["z"] >= 2.0:
                phase.append((s["z"], m, k))
        seq = [ms.get(m) for m in dm]
        for i in range(len(seq) - 2):
            a, b, c = seq[i], seq[i + 1], seq[i + 2]
            if all(x and x["n"] >= 20 for x in (a, b, c)):
                if a["roi"] > 0.08 and b["roi"] > 0.08 and c["roi"] < -0.08:
                    onoff.append((a["z"] + b["z"] - c["z"], f"{dm[i]}-{dm[i + 1]} on, {dm[i + 2]} off", k))
                if a["roi"] < -0.08 and b["roi"] > 0.08 and c["roi"] > 0.08:
                    onoff.append((b["z"] + c["z"] - a["z"], f"off in {dm[i]}, on {dm[i + 1]}-{dm[i + 2]}", k))
    n_month_tests = sum(1 for ms in sb.values() for m in months if ms.get(m) and ms[m]["n"] >= 25)
    cols = months + seasons
    L += ["", "## C. Every angle by month", "",
          f"{len(sb)} angles; {n_month_tests} angle-months with 25+ bets, so about {round(n_month_tests * 0.023)} will show z ≥ 2 by luck. "
          f"Thirds cut points: " + "; ".join(f"{f} {lo:.2f}/{hi:.2f}" for f, (lo, hi) in sorted(cuts.items())), "",
          f"### Held in both seasons ({disc} z ≥ 1.5, positive in {', '.join(later)} with 25+ bets) — the shortlist", ""]
    L += table(distinct([k for _, k in sorted(both, key=lambda x: (-x[0], len(x[1]), x[1]))], 40), sb, cols)
    L += ["", "### Strong in one month (z ≥ 2, 25+ bets)", ""]
    L += table(distinct(list(dict.fromkeys(k for _, _, k in sorted(phase, key=lambda x: (-x[0], len(x[2]), x[2])))), 40), sb, cols,
               extra=("Hot in", lambda k: ", ".join(m for _, m, kk in phase if kk == k)))
    L += ["", "### Turned on or off (two good months then a bad one, or the reverse)", ""]
    L += table(distinct(list(dict.fromkeys(k for _, _, k in sorted(onoff, key=lambda x: (-x[0], len(x[2]), x[2])))), 30), sb, cols,
               extra=("Pattern", lambda k: "; ".join(p for _, p, kk in onoff if kk == k)))

    L += ["", "## D. Does a month carry into the next? (over-correction test)", "",
          "| Months | Angles | Correlation of ROI | Hot half next month | Cold half next month |", "|---|---|---|---|---|"]
    for m0, m1 in zip(months, months[1:]):
        pr = [(ms[m0]["roi"], ms[m1]["roi"]) for ms in sb.values() if ms.get(m0) and ms.get(m1) and ms[m0]["n"] >= 25 and ms[m1]["n"] >= 25]
        if len(pr) >= 10:
            xs, ys = zip(*pr); med = statistics.median(xs)
            try:
                c = statistics.correlation(xs, ys)
            except statistics.StatisticsError:
                c = 0.0
            L.append(f"| {m0}→{m1} | {len(pr)} | {c:+.2f} | {100 * statistics.mean(y for x, y in pr if x >= med):+.1f}% | "
                     f"{100 * statistics.mean(y for x, y in pr if x < med):+.1f}% |")
    L += ["", "Walk-forward: each Monday, angles with z ≥ 1.5 over the previous 4 weeks (15+ bets) are hot; follow = bet them, "
          "fade = the other side; each bet once.", ""]
    L += follow_fade_months(singles, months)

    tc, T = team_section(rows, months)
    L += ["", "## E. Teams", "", "Does a team's cover / Over margin in one month predict the next? (+ = the market is slow to "
          "re-rate teams: back last month's covering teams; − = it over-corrects: fade them)", ""] + tc
    L += ["", "Team ATS by month (W-L, season average cover margin):", ""] + team_month_table(T, months)

    L += ["", "## F. Novig vs Pinnacle at bet time (historical S1) and Pinnacle vs the other books", ""]
    L += novig_section(rows, months)
    L += ["", "Pinnacle vs the other books' median line: spread/ML angles `lean_own` (+ = Pinnacle likes our side more) and "
          "totals `total_lean` are in section C."]
    text = "\n".join(L)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        fp = os.path.join(out_dir, f"months_{dt.date.today():%Y%m%d}.md")
        open(fp, "w", encoding="utf-8").write(text)
        print(f"report written to {fp}")
    return text


def season_of_month(m, rows, season_of, _cache={}):
    key = (id(rows), m)
    if key not in _cache:
        _cache[key] = next((season_of[r["g"]["id"]] for r in rows if month_key(r["g"]["date"]) == m), None)
    return _cache[key]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", action="append", required=True, help="first = discovery season, later = checks")
    ap.add_argument("--min-gp", type=int, default=1)
    ap.add_argument("--out", default=r"C:\MaverickPicks\reports")
    a = ap.parse_args(argv)
    from .db import session
    with session() as db:
        print(run(db, a.season, a.out, a.min_gp))


if __name__ == "__main__":
    sys.exit(main())

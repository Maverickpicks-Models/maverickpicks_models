r"""Season in quarters: which rules / conditions work in which part of the season, which work then stop, and
whether the books over-correct.

  python -m mpm.quarters --season 2025-26 --check 2026-27 --out C:\MaverickPicks\reports

Quarters = four equal blocks of games by date (the cut dates are shown). For every bet type it reports:
  A. the market by quarter: home / favorite / Over cover rates, average miss of the line, ML favorite ROI
     (where the books are slow or over-adjust as a group);
  B. our rules by quarter: v5 rules (backtest engine), C1, C4, P1, P2;
  C. single conditions by quarter (the mine.py features plus each team's recent record against the spread and
     the total): strong in one quarter only, steady in 3+ quarters, worked-then-stopped;
  D. persistence: across all conditions, does a quarter's ROI predict the next quarter's? A negative link means
     the market over-corrects (what worked gets priced out and then some); positive means trends carry over;
  E. walk-forward follow vs fade: each week bet the conditions that were hot over the previous 4 weeks, or the
     other side of them. The cleanest test of "books over-correct".
--check grades the quarter-1 findings on the same calendar window of another season (2026-27 to date).
Every quarter has ~300 games; a single quarter's ROI on 100 bets has about +-10% of noise.
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

from . import mine

EXTRA_NUM = ["ats_own", "ats_opp", "ou_form"]
SINGLE = {"spreads": mine.FEATS["spreads"] + ["ats_own", "ats_opp"],
          "h2h": mine.FEATS["h2h"] + ["ats_own"],
          "totals": mine.FEATS["totals"] + ["ou_form"]}


def add_recent(rows, window=10, need=5):
    """Each team's average cover margin and Over margin over its previous `window` games (before the bet)."""
    games = {}
    for r in rows:
        games.setdefault(r["g"]["id"], r)
    hist = collections.defaultdict(list)                  # team -> [(date, cover margin, over margin)]
    for r in sorted(games.values(), key=lambda r: r["g"]["date"]):
        g, L = r["g"], r["L"]
        U, T = L["spreads"]["point"], L["totals"]["point"]
        hist[g["away"]].append((g["date"], g["as"] - g["hs"] + U, g["as"] + g["hs"] - T))
        hist[g["home"]].append((g["date"], g["hs"] - g["as"] - U, g["as"] + g["hs"] - T))
    dates = {t: [x[0] for x in v] for t, v in hist.items()}

    def recent(t, day, k):
        i = bisect.bisect_left(dates[t], day)
        xs = [x[k] for x in hist[t][max(0, i - window):i]]
        return statistics.mean(xs) if len(xs) >= need else None
    for r in rows:
        g = r["g"]
        me, opp = (g["away"], g["home"]) if r["side"] == "away" else (g["home"], g["away"])
        r["ats_own"], r["ats_opp"] = recent(me, g["date"], 1), recent(opp, g["date"], 1)
        a, h = recent(g["away"], g["date"], 2), recent(g["home"], g["date"], 2)
        r["ou_form"] = None if a is None or h is None else (a + h) / 2
    return rows


def cuts_for(rows):
    c = mine.cutpoints(rows)
    for f in EXTRA_NUM:
        v = sorted(r[f] for r in rows if r.get(f) is not None)
        if v:
            c[f] = (v[len(v) // 3], v[2 * len(v) // 3])
    return c


def holds(row, cond, cuts):
    f = cond[0]
    if f not in mine.BOOL and row.get(f) is None:
        return False
    return mine.holds(row, cond, cuts)


def quarter_cuts(rows):
    ds = sorted(r["g"]["date"] for r in rows if r["side"] == "home")
    return [ds[len(ds) * k // 4] for k in (1, 2, 3)]


def qof(day, qc):
    return 1 + bisect.bisect_right(qc, day)


def same_window(day, qc_disc):
    """Map another season's date onto the discovery season's quarters by calendar day (Oct start = same)."""
    shift = dt.date(qc_disc[-1].year, 1, 1) - dt.date(day.year if day.month < 7 else day.year + 1, 1, 1)
    return qof(day + shift, qc_disc)


# ---------------------------------------------------------------- bets
def rule_bets(rows, db, season):
    """(rule, row, market, side) for v5 rules + C1/C4/P1/P2."""
    from .backtest import bets_for_game, schedule
    played, margin = schedule(db, [season])
    out, seen = [], set()
    for r in rows:
        g = r["g"]
        if g["id"] not in seen:
            seen.add(g["id"])
            for rule, mk, side in bets_for_game(g, r["L"], played, margin):
                out.append((rule, r, mk, side))
            if r["model_total_gap"] >= 6:
                out.append(("C4 fade model total 6+", r, "totals", "under"))
            elif r["model_total_gap"] <= -6:
                out.append(("C4 fade model total 6+", r, "totals", "over"))
        my_sp = -r["spread"] if r["fav"] else r["spread"]
        if 3 <= r["model_gap"] < 6 and my_sp > -10:
            out.append(("C1 model spread 3-6 off (no 10+ favs)", r, "spreads", r["side"]))
        if r["model_gap"] >= 1.8 and r["luck_opp"] >= 0.47:
            out.append(("P1 fade 3P-lucky team", r, "spreads", r["side"]))
        if r["model_gap"] >= 1.8 and r["net_gap"] >= 3.63 and r["ml_nv"] <= 0.87:
            out.append(("P2 better-team ML", r, "h2h", r["side"]))
    return out


def single_bets(rows, cuts):
    """(condition label, row, market, side) for every single condition."""
    out = []
    for mk in ("spreads", "h2h", "totals"):
        conds = [c for f in SINGLE[mk] for c in ([(f, "yes"), (f, "no")] if f in mine.BOOL else [(f, "low"), (f, "mid"), (f, "high")])]
        conds = [c for c in conds if c[0] != "early"]
        for row, s in mine.bets(rows, mk):
            for c in conds:
                if holds(row, c, cuts):
                    sd = s if mk == "totals" else "any"
                    out.append((f"{mk}:{sd} when {c[0]}={c[1]}", row, mk, s))
    return out


def other(mk, side):
    return {"away": "home", "home": "away", "over": "under", "under": "over"}[side]


def stat(items):
    """items: [(return, result)] -> n, W, L, roi, z"""
    if not items:
        return None
    rs = [x[0] for x in items]
    n = len(rs); m = statistics.mean(rs); sd = statistics.pstdev(rs) or 1
    return dict(n=n, w=sum(1 for x in items if x[1] == "W"), l=sum(1 for x in items if x[1] == "L"),
                roi=m, z=m / (sd / math.sqrt(n)))


def by_quarter(bets, qc, mapper=qof):
    d = collections.defaultdict(lambda: collections.defaultdict(list))
    for key, row, mk, side in bets:
        q = mapper(row["g"]["date"], qc)
        d[key][q].append(mine.ret(row, mk, side))
        d[key][0].append(mine.ret(row, mk, side))
    return {k: {q: stat(v) for q, v in qs.items()} for k, qs in d.items()}


def fmt(s):
    return "–" if not s else f"{s['w']}-{s['l']} {100 * s['roi']:+.0f}%"


# ---------------------------------------------------------------- market
def market_table(rows, qc):
    games = {}
    for r in rows:
        games.setdefault(r["g"]["id"], r)
    Q = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in games.values():
        g, L = r["g"], r["L"]; q = qof(g["date"], qc)
        U, T = L["spreads"]["point"], L["totals"]["point"]
        home_cm = g["hs"] - g["as"] - U
        fav_home = U > 0
        fav_cm = home_cm if fav_home else -home_cm
        ov = g["as"] + g["hs"] - T
        nvA = L["h2h"]["nv"]["away"]; fav = "away" if nvA >= .5 else "home"
        for qq in (q, 0):
            x = Q[qq]
            if home_cm: x["home_cov"].append(home_cm > 0)
            if fav_cm and U: x["fav_cov"].append(fav_cm > 0)
            x["fav_miss"].append(fav_cm); x["line_tot"].append(T); x["act_tot"].append(g["as"] + g["hs"])
            if ov: x["over"].append(ov > 0)
            x["ml_fav"].append(mine.ret(r, "h2h", fav)[0])
            x["ml_dog"].append(mine.ret(r, "h2h", other("h2h", fav))[0])
    pct = lambda v: f"{100 * sum(v) / len(v):.1f}%" if v else "–"
    out = ["| | Q1 | Q2 | Q3 | Q4 | Season |", "|---|---|---|---|---|---|"]
    for lab, key, f in (("Home covers", "home_cov", pct), ("Favorite covers", "fav_cov", pct),
                        ("Favorite: avg margin minus spread", "fav_miss", lambda v: f"{statistics.mean(v):+.2f}"),
                        ("Avg total line", "line_tot", lambda v: f"{statistics.mean(v):.1f}"),
                        ("Avg actual total", "act_tot", lambda v: f"{statistics.mean(v):.1f}"),
                        ("Over hits", "over", pct),
                        ("ML favorites ROI (no-vig)", "ml_fav", lambda v: f"{100 * statistics.mean(v):+.1f}%"),
                        ("ML dogs ROI (no-vig)", "ml_dog", lambda v: f"{100 * statistics.mean(v):+.1f}%")):
        out.append(f"| {lab} | " + " | ".join(f(Q[q][key]) if Q[q][key] else "–" for q in (1, 2, 3, 4, 0)) + " |")
    return out


# ---------------------------------------------------------------- walk-forward follow / fade
def follow_fade(singles, qc, lookback=28, min_n=15, z_hot=1.5):
    by_cond = collections.defaultdict(list)
    for key, row, mk, side in singles:
        by_cond[key].append((row["g"]["date"], row, mk, side))
    days = sorted({row["g"]["date"] for _, row, _, _ in singles})
    weeks = sorted({d - dt.timedelta(d.weekday()) for d in days})
    res = {"follow": collections.defaultdict(dict), "fade": collections.defaultdict(dict)}
    for wk in weeks[4:]:
        lo = wk - dt.timedelta(lookback)
        for key, L in by_cond.items():
            past = [mine.ret(r, mk, s) for d, r, mk, s in L if lo <= d < wk]
            st = stat(past)
            if not st or st["n"] < min_n or st["z"] < z_hot:
                continue
            for d, r, mk, s in L:
                if wk <= d < wk + dt.timedelta(7):
                    res["follow"][qof(d, qc)][(r["g"]["id"], mk, s)] = mine.ret(r, mk, s)
                    o = other(mk, s)
                    res["fade"][qof(d, qc)][(r["g"]["id"], mk, o)] = mine.ret(r, mk, o)
    out = ["| Strategy | Q1 | Q2 | Q3 | Q4 | Season |", "|---|---|---|---|---|---|"]
    for name in ("follow", "fade"):
        cells, allv = [], []
        for q in (1, 2, 3, 4):
            v = list(res[name][q].values()); allv += v
            s = stat(v); cells.append(fmt(s) + (f" (n {s['n']})" if s else ""))
        s = stat(allv)
        season_cell = f"{fmt(s)} (n {s['n']}, z {s['z']:.2f})" if s else "–"
        out.append(f"| {name.title()} hot conditions | " + " | ".join(cells) + f" | {season_cell} |")
    return out


# ---------------------------------------------------------------- report
def run(db, season, check=None, out_dir=None, min_gp=5):
    rows = add_recent(mine.season_rows(db, season, min_gp))
    cuts = cuts_for(rows)
    qc = quarter_cuts(rows)
    first, last = min(r["g"]["date"] for r in rows), max(r["g"]["date"] for r in rows)
    span = [first] + qc + [last + dt.timedelta(1)]
    qlab = [f"Q{k + 1} {span[k]:%m/%d}-{(span[k + 1] - dt.timedelta(1)):%m/%d}" for k in range(4)]
    L = [f"# {season} by quarter", "",
         f"{len(rows) // 2} games (both teams {min_gp}+ games), bet-time Pinnacle no-vig prices. " + "; ".join(qlab) + ".",
         "W-L and ROI at the no-vig price (≈ Novig). One quarter is ~280 games; 100 bets carry about ±10% of noise, so a "
         "single hot quarter is weak evidence on its own.", "", "## A. The market by quarter", ""]
    L += market_table(rows, qc)

    rb = by_quarter(rule_bets(rows, db, season), qc)
    L += ["", "## B. Our rules by quarter", "", "| Rule | Q1 | Q2 | Q3 | Q4 | Season | n |", "|---|---|---|---|---|---|---|"]
    for k in sorted(rb):
        q = rb[k]
        L.append(f"| {k} | " + " | ".join(fmt(q.get(i)) for i in (1, 2, 3, 4, 0)) + f" | {q[0]['n']} |")

    singles = single_bets(rows, cuts)
    sb = by_quarter(singles, qc)
    steady, phase, flips = [], [], []
    for k, q in sb.items():
        qs = [q.get(i) for i in (1, 2, 3, 4)]
        if any(s is None or s["n"] < 30 for s in qs):
            continue
        pos = sum(1 for s in qs if s["roi"] > 0)
        if pos >= 4 or (pos == 3 and q[0]["z"] >= 1.5):
            steady.append((q[0]["z"], k))
        for i, s in enumerate(qs, 1):
            if s["z"] >= 2.0:
                phase.append((s["z"], i, k))
            if i < 4 and s["z"] >= 2.0 and qs[i]["roi"] < 0:
                flips.append((s["z"] - qs[i]["z"], i, k))
            if i < 4 and s["z"] <= -2.0 and qs[i]["roi"] > 0:
                flips.append((qs[i]["z"] - s["z"], i, k))
    row_q = lambda k: " | ".join(fmt(sb[k].get(i)) for i in (1, 2, 3, 4, 0))
    n_tests = sum(1 for q in sb.values() for i in (1, 2, 3, 4) if q.get(i) and q[i]["n"] >= 30)
    L += ["", "## C. Conditions by quarter (single conditions; thirds of the season's values)", "",
          f"{len(sb)} conditions × 4 quarters = {n_tests} quarter tests; about {round(n_tests * 0.023)} would reach z ≥ 2 by luck alone.", "",
          "### Steady: positive in all 4 quarters, or 3 of 4 with season z ≥ 1.5", "",
          "| Condition | Q1 | Q2 | Q3 | Q4 | Season | n |", "|---|---|---|---|---|---|---|"]
    for z, k in sorted(steady, reverse=True)[:25]:
        L.append(f"| {k} | {row_q(k)} | {sb[k][0]['n']} |")
    L += ["", "### Strong in one quarter (z ≥ 2 in that quarter)", "", "| Condition | Hot in | Q1 | Q2 | Q3 | Q4 | Season |", "|---|---|---|---|---|---|---|"]
    for z, i, k in sorted(phase, reverse=True)[:30]:
        L.append(f"| {k} | Q{i} | {row_q(k)} |")
    L += ["", "### Worked, then stopped (or the reverse): z ≥ 2 one quarter, wrong sign the next", "",
          "| Condition | Turn | Q1 | Q2 | Q3 | Q4 | Season |", "|---|---|---|---|---|---|---|"]
    for sw, i, k in sorted(flips, reverse=True)[:25]:
        L.append(f"| {k} | Q{i}→Q{i + 1} | {row_q(k)} |")

    L += ["", "## D. Does a quarter's result carry into the next one?", "",
          "Correlation, across all conditions with 30+ bets in both quarters, of ROI in one quarter with ROI in the next. "
          "Near 0 = no memory (each quarter is a fresh coin); negative = the market over-corrects; positive = trends carry over.", "",
          "| Quarters | Conditions | Correlation | Hot half (top 50% ROI) next quarter | Cold half next quarter |", "|---|---|---|---|---|"]
    for i in (1, 2, 3):
        pairs = [(q[i]["roi"], q[i + 1]["roi"], q[i + 1]["n"]) for q in sb.values()
                 if q.get(i) and q.get(i + 1) and q[i]["n"] >= 30 and q[i + 1]["n"] >= 30]
        if len(pairs) < 5:
            continue
        xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
        try:
            c = statistics.correlation(xs, ys)
        except statistics.StatisticsError:
            c = 0.0
        med = statistics.median(xs)
        hot = [y for x, y, _ in pairs if x >= med]; cold = [y for x, y, _ in pairs if x < med]
        L.append(f"| Q{i}→Q{i + 1} | {len(pairs)} | {c:+.2f} | {100 * statistics.mean(hot):+.1f}% | {100 * statistics.mean(cold):+.1f}% |")

    L += ["", "## E. Walk-forward: follow or fade what's hot", "",
          "Each Monday, conditions with z ≥ 1.5 over the previous 4 weeks (15+ bets) are 'hot'. Follow = bet them that week; "
          "fade = bet the other side. Each bet counted once.", ""]
    L += follow_fade(singles, qc)

    if check:
        crow = add_recent(mine.season_rows(db, check, min_gp))
        cb = by_quarter(single_bets(crow, cuts), qc, mapper=same_window)
        cr = by_quarter(rule_bets(crow, db, check), qc, mapper=same_window)
        L += ["", f"## Check: {check} to date, same calendar window", "",
              f"{len(crow) // 2} games so far. Quarter-1 findings from {season} graded on {check}'s Q1 window.", "",
              "| Condition / rule | " + f"{season} Q1 | {check} Q1 |", "|---|---|---|"]
        q1 = sorted(((z, k) for z, i, k in phase if i == 1), reverse=True)
        for _, k in q1[:20]:
            L.append(f"| {k} | {fmt(sb[k].get(1))} | {fmt(cb.get(k, {}).get(1))} |")
        for k in sorted(rb):
            L.append(f"| {k} | {fmt(rb[k].get(1))} | {fmt(cr.get(k, {}).get(1))} |")
    text = "\n".join(L)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        fp = os.path.join(out_dir, f"quarters_{season}_{dt.date.today():%Y%m%d}.md")
        open(fp, "w", encoding="utf-8").write(text)
        print(f"report written to {fp}")
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", required=True)
    ap.add_argument("--check")
    ap.add_argument("--min-gp", type=int, default=5)
    ap.add_argument("--out", default=r"C:\MaverickPicks\reports")
    a = ap.parse_args(argv)
    from .db import session
    with session() as db:
        print(run(db, a.season, a.check, a.out, a.min_gp))


if __name__ == "__main__":
    sys.exit(main())

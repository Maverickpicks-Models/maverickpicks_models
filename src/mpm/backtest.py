"""Phase 2 backtest: re-test the market and schedule rules on past seasons (walk-forward, out of sample).

  python -m mpm.backtest --season 2025-26 --season 2024-25 --out C:\\MaverickPicks\\reports

Every rule was found on 2026-27 data, so earlier seasons are a true out-of-sample test. Prices come from the
bet-time historical snapshot (6:30 PM ET, or 30 min before an early tip): Pinnacle when it has the market,
otherwise the median line of the other books. Results are shown at two prices:
  * ROI @ book   - Pinnacle's own price (with vig)
  * ROI @ no-vig - the fair price, close to what Novig charges
CLV (when --close snapshots exist) = closing no-vig probability of our side minus the bet-time one, in % points,
with line moves converted at 3% per point (spreads) / 2.2% (totals).

Rules that need our model's projections (C1, C4, X1, X5, T2, T3, T7) or CraftedNBA / injury inputs
(K1-K4, T6) can't be re-tested until the model itself is rebuilt for past seasons (Phase 3).
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import os
import statistics
import sys

SHARP = "pinnacle"
SLOPE = {"spreads": 0.03, "totals": 0.022}


def _imp(p):
    return -p / (100 - p) if p < 0 else 100 / (100 + p)


def _dec(p):
    return 100 / -p if p < 0 else p / 100


# ---------------------------------------------------------------- data
def load_lines(db, purposes: tuple[str, ...]) -> dict:
    """{game_id: {market: {...}}} from the latest snapshot of the given purposes taken before tip."""
    ph = ",".join("?" * len(purposes))
    rows = db.q(f"""
        SELECT o.game_id, s.pulled_at_utc, o.bookmaker, o.market, o.side, o.point, o.price_american
        FROM core.odds o JOIN core.odds_snapshots s ON s.snapshot_id = o.snapshot_id
        JOIN core.games g ON g.game_id = o.game_id
        WHERE s.purpose IN ({ph}) AND g.league = 'NBA' AND o.market IN ('h2h','spreads','totals')
          AND (g.start_utc IS NULL OR s.pulled_at_utc <= g.start_utc)""", purposes)
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
            pair = ("away", "home") if mk != "totals" else ("over", "under")
            usable = {b: v for b, v in books.items() if all(s in v for s in pair)}
            if not usable:
                continue
            if SHARP in usable:
                v = usable[SHARP]; src = SHARP
            else:                                   # consensus: the median line, its books' prices averaged
                pts = [v[pair[0]][0] for v in usable.values()]
                med = statistics.median(pts) if pts[0] is not None else None
                cand = [v for v in usable.values() if v[pair[0]][0] == med] or list(usable.values())
                v = cand[len(cand) // 2]; src = "consensus"
            a, b = _imp(v[pair[0]][1]), _imp(v[pair[1]][1])
            g[mk] = {"point": v[pair[0]][0], "price": {pair[0]: v[pair[0]][1], pair[1]: v[pair[1]][1]},
                     "nv": {pair[0]: a / (a + b), pair[1]: b / (a + b)}, "src": src}
        out[gid] = g
    return out


def load_games(db, seasons: list[str]) -> list[dict]:
    rng = {s: (str(a)[:10], str(b)[:10]) for s, a, b in
           db.q("SELECT season, MIN(game_date), MAX(game_date) FROM nba.team_game_log GROUP BY season")}
    games = []
    for s in seasons:
        if s not in rng:
            print(f"no game log for {s}"); continue
        for gid, d, a, h, asc, hsc in db.q("SELECT game_id, game_date, away_code, home_code, away_score, home_score FROM core.games "
                                           "WHERE league='NBA' AND status='final' AND game_date BETWEEN ? AND ?", rng[s]):
            if asc is None or hsc is None:
                continue
            games.append({"id": gid, "date": dt.date.fromisoformat(str(d)[:10]), "away": a, "home": h,
                          "as": int(asc), "hs": int(hsc), "season": s})
    return games


def schedule(db, seasons):
    played, margin = collections.defaultdict(set), collections.defaultdict(list)
    ph = ",".join("?" * len(seasons))
    for s, t, d, pts, opp in db.q(f"SELECT season, team_code, game_date, pts, opp_pts FROM nba.team_game_log WHERE season IN ({ph})", seasons):
        d = dt.date.fromisoformat(str(d)[:10])
        played[(s, t)].add(d)
        if pts is not None and opp is not None:
            margin[(s, t)].append((d, pts - opp))
    return played, margin


def fatigue(played, s, t, day):
    L = played.get((s, t), set())
    b2b = (day - dt.timedelta(1)) in L
    g4 = 1 + sum(1 for x in L if day - dt.timedelta(3) <= x < day)
    g6 = 1 + sum(1 for x in L if day - dt.timedelta(5) <= x < day)
    return int(b2b) + int(g4 >= 3) + int(g6 >= 4), b2b


def tiers(margin, s, day, min_games=10):
    """Top-10 / bottom-10 by point differential per game before `day` (stand-in for the CraftedNBA rating rank)."""
    pd = {}
    for (ss, t), L in margin.items():
        if ss != s:
            continue
        prior = [m for d, m in L if d < day]
        if len(prior) >= min_games:
            pd[t] = sum(prior) / len(prior)
    if len(pd) < 25:
        return {}
    order = sorted(pd, key=lambda t: -pd[t])
    return {t: ("top" if i < 10 else "bot" if i >= len(order) - 10 else "mid") for i, t in enumerate(order)}


# ---------------------------------------------------------------- rules
def bets_for_game(g, L, played, margin):
    """Yield (rule, market, side) the market/schedule rules would bet (or the avoid rules flag)."""
    s, day = g["season"], g["date"]
    sp, tot, ml = L.get("spreads"), L.get("totals"), L.get("h2h")
    U = sp["point"] if sp else None                      # away spread
    fa, ab2b = fatigue(played, s, g["away"], day)
    fh, hb2b = fatigue(played, s, g["home"], day)
    out = []
    if sp:
        if U < 0 and -U <= 4.5 and not (hb2b and not ab2b):
            out.append(("C2 road fav <=4.5", "spreads", "away"))
        if 0 < U <= 4.5:
            out.append(("T11 home fav <=4.5", "spreads", "home"))
        if hb2b and not ab2b:
            out.append(("T9 home B2B vs rested road", "spreads", "home"))
        if ab2b and not hb2b:
            out.append(("T4 rested home vs road B2B (paper)", "spreads", "home"))
        if abs(fa - fh) >= 1:
            out.append(("T12 more tired team", "spreads", "away" if fa > fh else "home"))
        tr = tiers(margin, s, day)
        if tr.get(g["away"]) == "top" and tr.get(g["home"]) == "bot":
            out.append(("T5 top-10 vs bottom-10", "spreads", "away"))
        if tr.get(g["home"]) == "top" and tr.get(g["away"]) == "bot":
            out.append(("T5 top-10 vs bottom-10", "spreads", "home"))
        if U < 0 and 0.5 <= -U <= 4.5:
            out.append(("X2 home dog 0.5-4.5 (avoid)", "spreads", "home"))
        fav_side = "away" if U < 0 else "home"
        size = abs(U)
        band = "0.5-4.5" if size <= 4.5 else "5-9.5" if size <= 9.5 else "10+"
        if size > 0:
            out.append((f"Fav ATS {band} ({fav_side})", "spreads", fav_side))
    if ml:
        nvA = ml["nv"]["away"]; fav = "away" if nvA >= .5 else "home"; fv = max(nvA, 1 - nvA)
        sz = abs(U) if U is not None else 0
        if (0.60 <= fv < 0.65 or 0.75 <= fv <= 0.87) and not (5 <= sz <= 9.5):
            out.append(("C3 ML fav 60-65/75-87%", "h2h", fav))
        if 0.65 <= fv < 0.75:
            out.append(("C3 leak: ML fav 65-75% (excluded)", "h2h", fav))
        if fv > 0.87:
            out.append(("X7 ML fav over 87% (avoid)", "h2h", fav))
        if sz <= 4.5 and 0.5 <= fv < 0.60:
            out.append(("T10 ML fav 50-60%, spread <=4.5", "h2h", fav))
        dog = "home" if fav == "away" else "away"
        if ml["price"][dog] >= 200:
            out.append(("X3 dog +200 or longer (avoid)", "h2h", dog))
        band = "0.5-4.5" if sz <= 4.5 else "5-9.5" if sz <= 9.5 else "10+"
        out.append((f"Fav ML {band}", "h2h", fav))
    if tot:
        if tot["point"] >= 235:
            out.append(("T8 total 235+ -> Under", "totals", "under"))
        if tot["nv"]["over"] >= 0.52:
            out.append(("T1 juiced Over -> Under", "totals", "under"))
    return out


def grade(g, L, mk, side):
    a, h = g["as"], g["hs"]
    if mk == "spreads":
        m = (a - h + L["spreads"]["point"]) if side == "away" else (h - a - L["spreads"]["point"])
    elif mk == "totals":
        m = (a + h - L["totals"]["point"]) if side == "over" else (L["totals"]["point"] - a - h)
    else:
        m = (a - h) if side == "away" else (h - a)
    return "W" if m > 0 else "L" if m < 0 else "P"


def clv(L, C, mk, side):
    if not C or mk not in C or mk not in L:
        return None
    b, c = L[mk], C[mk]
    p_close = c["nv"][side]
    if mk != "h2h" and b["point"] != c["point"]:
        diff = (b["point"] - c["point"])
        if mk == "spreads":
            gain = diff if side == "away" else -diff        # away line is the stored point; home is its negative
        else:
            gain = -diff if side == "over" else diff
        if abs(diff) > 3:
            return None
        p_close = p_close + SLOPE[mk] * gain
    return p_close - b["nv"][side]


# ---------------------------------------------------------------- report
def run(db, seasons, out_dir=None) -> str:
    bet = load_lines(db, ("hist_bet", "hist_early"))
    close = load_lines(db, ("hist_close",))
    games = load_games(db, seasons)
    played, margin = schedule(db, seasons)
    agg = collections.defaultdict(lambda: {"n": 0, "W": 0, "L": 0, "P": 0, "book": 0.0, "fair": 0.0, "clv": []})
    covered = 0
    for g in games:
        L = bet.get(g["id"])
        if not L:
            continue
        covered += 1
        half = "Oct-Dec" if g["date"].month >= 10 else "Jan-Apr"
        for rule, mk, side in bets_for_game(g, L, played, margin):
            r = grade(g, L, mk, side)
            price, nv = L[mk]["price"][side], L[mk]["nv"][side]
            c = clv(L, close.get(g["id"]), mk, side)
            for key in ((rule, g["season"]), (rule, f"{g['season']} {half}"), (rule, "ALL")):
                x = agg[key]; x["n"] += 1; x[r] += 1
                if r == "W":
                    x["book"] += _dec(price); x["fair"] += (1 - nv) / nv
                elif r == "L":
                    x["book"] -= 1; x["fair"] -= 1
                if c is not None:
                    x["clv"].append(c)
    rules = sorted({k[0] for k in agg})
    cols = ["ALL"] + seasons + [f"{s} {h}" for s in seasons for h in ("Oct-Dec", "Jan-Apr")]
    lines = [f"# Backtest: market and schedule rules ({', '.join(seasons)})", "",
             f"Run {dt.date.today()} · {covered} of {len(games)} final games have bet-time odds · "
             f"{sum(1 for g in games if g['id'] in close)} have a close.", "",
             "| Rule | Period | Bets | W-L-P | ROI @ book | ROI @ no-vig | Avg CLV |", "|---|---|---|---|---|---|---|"]
    for rule in rules:
        for c in cols:
            x = agg.get((rule, c))
            if not x or not x["n"]:
                continue
            dec = x["W"] + x["L"]
            roi_b = x["book"] / dec if dec else 0
            roi_f = x["fair"] / dec if dec else 0
            cl = f"{100 * statistics.mean(x['clv']):+.2f}% (n {len(x['clv'])})" if x["clv"] else "–"
            lines.append(f"| {rule if c == 'ALL' else ''} | {c} | {x['n']} | {x['W']}-{x['L']}-{x['P']} | "
                         f"{100 * roi_b:+.1f}% | {100 * roi_f:+.1f}% | {cl} |")
    lines += ["", "Not testable on past seasons yet (need our model's projections, CraftedNBA or injury reports for those "
              "seasons): C1, C4, X1, X5, T2, T3, T6, T7, K1-K4. T5 uses point differential per game as a stand-in for the "
              "CraftedNBA rating rank."]
    text = "\n".join(lines)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"backtest_{dt.date.today():%Y%m%d}.md")
        open(path, "w", encoding="utf-8").write(text)
        print(f"report written to {path}")
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", action="append", required=True)
    ap.add_argument("--out", default=r"C:\MaverickPicks\reports")
    a = ap.parse_args(argv)
    from .db import session
    with session() as db:
        print(run(db, a.season, a.out))


if __name__ == "__main__":
    sys.exit(main())

"""NBA projection model in Python (Phase 3), built from the database instead of the workbook.

Replicates the workbook model once both teams have played `Assumptions!C9` (20) games, when the
current-season weight reaches 1 and the roster prior (and with it the injury adjustment) drops out:

  team offense/defense = season-to-date ORtg / DRtg (possession-weighted, from nba.team_box_adv),
                         minus 3-point shooting luck (TeamShooting sheet formula)
  pace   = league pace + 0.5 x ((away pace - lg) + (home pace - lg))
  points = pace/100 x (own ORtg + opp DRtg - league baseline), +-1 home court, back-to-back -2.5 margin
  margin SD 12.5, total SD 18

Before 20 games the workbook leans on a roster prior built from last season's player ratings, which we
don't have for past seasons, so the backtest uses games where both teams have 20+ games (option --min-gp).

  python -m mpm.model --season 2025-26 --out C:\\MaverickPicks\\reports      # back-test C1 / C4 on a past season
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

A = dict(games_trust=20, pace_w=0.5, hca=2.0, b2b=2.5, margin_sd=12.5, total_sd=18.0,
         skill_off=0.015, skill_def=0.008, remove_luck=True)


def _d(v) -> dt.date:
    return v if isinstance(v, dt.date) and not isinstance(v, dt.datetime) else dt.date.fromisoformat(str(v)[:10])


class SeasonState:
    """Per-team game rows for one date range, with season-to-date ratings as of any date."""

    def __init__(self, db, d0: str, d1: str):
        adv = db.q("SELECT team_code, game_date, off_rtg, def_rtg, pace, mins FROM nba.team_box_adv WHERE game_date BETWEEN ? AND ?", (d0, d1))
        box = {(t, str(d)[:10]): (fga, oreb, tov, fta, f3m, f3a, mu) for t, d, fga, oreb, tov, fta, f3m, f3a, mu in
               db.q("SELECT team_code, game_date, fga, oreb, tov, fta, fg3m, fg3a, matchup FROM nba.team_box WHERE game_date BETWEEN ? AND ?", (d0, d1))}
        self.rows = collections.defaultdict(list)          # team -> [(date, ortg, drtg, pace, poss, 3pm, 3pa, opp3pm, opp3pa)]
        for t, d, o, dr, pace, mins in adv:
            ds = str(d)[:10]
            b = box.get((t, ds))
            if b is None or o is None or dr is None or pace is None:
                continue
            fga, oreb, tov, fta, f3m, f3a, mu = b
            opp = mu.replace(" vs. ", " @ ").split(" @ ")[1].strip()
            ob = box.get((opp, ds))
            poss = 0.98 * ((fga or 0) - (oreb or 0) + (tov or 0) + 0.44 * (fta or 0))
            self.rows[t].append((_d(ds), float(o), float(dr), float(pace), poss, f3m or 0, f3a or 0,
                                 (ob[4] or 0) if ob else 0, (ob[5] or 0) if ob else 0))
        for t in self.rows:
            self.rows[t].sort()
        self.dates = {t: [r[0] for r in rs] for t, rs in self.rows.items()}
        self._lg = {}

    def prior(self, t, day):
        i = bisect.bisect_left(self.dates.get(t, []), day)
        return self.rows.get(t, [])[:i]

    def league(self, day):
        if day not in self._lg:
            allr = [r for t in self.rows for r in self.prior(t, day)]
            w = sum(r[4] for r in allr) or 1
            o = sum(r[1] * r[4] for r in allr) / w
            dd = sum(r[2] * r[4] for r in allr) / w
            p = statistics.mean(r[3] for r in allr) if allr else 99.0
            m3 = sum(r[5] for r in allr); a3 = sum(r[6] for r in allr)
            self._lg[day] = dict(o=o, d=dd, base=(o + dd) / 2, pace=p, p3=m3 / a3 if a3 else 0.36)
        return self._lg[day]

    def team(self, t, day):
        rs = self.prior(t, day)
        if not rs:
            return None
        w = sum(r[4] for r in rs) or 1
        o = sum(r[1] * r[4] for r in rs) / w
        dd = sum(r[2] * r[4] for r in rs) / w
        pace = statistics.mean(r[3] for r in rs)
        if A["remove_luck"]:
            lg = self.league(day)["p3"]
            m3, a3, om3, oa3 = (sum(r[k] for r in rs) for k in (5, 6, 7, 8))
            var = lg * (1 - lg)
            ko = (var / a3) / (var / a3 + A["skill_off"] ** 2) if a3 else 0
            kd = (var / oa3) / (var / oa3 + A["skill_def"] ** 2) if oa3 else 0
            o -= ko * (m3 - lg * a3) * 3 / w * 100
            dd -= kd * (om3 - lg * oa3) * 3 / w * 100
        return dict(o=o, d=dd, pace=pace, gp=len(rs))


def project(st: SeasonState, away, home, day, away_b2b=False, home_b2b=False):
    a, h, lg = st.team(away, day), st.team(home, day), st.league(day)
    if not a or not h:
        return None
    pace = lg["pace"] + A["pace_w"] * ((a["pace"] - lg["pace"]) + (h["pace"] - lg["pace"]))
    ra = pace / 100 * (a["o"] + h["d"] - lg["base"])
    rh = pace / 100 * (h["o"] + a["d"] - lg["base"])
    ta = -(A["b2b"] if away_b2b else 0); th = -(A["b2b"] if home_b2b else 0)
    ap = max(80, ra + (ta - th) / 2 - A["hca"] / 2); hp = max(80, rh + (th - ta) / 2 + A["hca"] / 2)
    return dict(ap=ap, hp=hp, gp=min(a["gp"], h["gp"]))


# ---------------------------------------------------------------- back-test of the model rules
def backtest(db, season: str, min_gp: int = 20, out_dir: str | None = None) -> str:
    from .backtest import load_lines, load_games, schedule, fatigue, grade, _dec
    rng = db.one("SELECT MIN(game_date), MAX(game_date) FROM nba.team_game_log WHERE season=?", (season,))
    st = SeasonState(db, str(rng[0])[:10], str(rng[1])[:10])
    bet = load_lines(db, ("hist_bet", "hist_early"))
    played, _ = schedule(db, [season])
    agg = collections.defaultdict(lambda: {"n": 0, "W": 0, "L": 0, "P": 0, "fair": 0.0, "book": 0.0})
    err = collections.defaultdict(list)
    n_games = 0
    for g in load_games(db, [season]):
        L = bet.get(g["id"])
        if not L or "spreads" not in L or "totals" not in L:
            continue
        _, ab = fatigue(played, season, g["away"], g["date"]); _, hb = fatigue(played, season, g["home"], g["date"])
        p = project(st, g["away"], g["home"], g["date"], ab, hb)
        if not p or p["gp"] < min_gp:
            continue
        n_games += 1
        U, T = L["spreads"]["point"], L["totals"]["point"]
        mg, mt = p["ap"] - p["hp"], p["ap"] + p["hp"]
        act_m, act_t = g["as"] - g["hs"], g["as"] + g["hs"]
        err["model margin"].append(mg - act_m); err["market margin"].append(-U - act_m)
        err["model total"].append(mt - act_t); err["market total"].append(T - act_t)
        gap = mg - (-U)                                    # model away margin minus market's
        half = "Oct-Dec" if g["date"].month >= 10 else "Jan-Apr"
        picks = []
        side = "away" if gap > 0 else "home"
        band = "<1" if abs(gap) < 1 else "1-3" if abs(gap) < 3 else "3-6" if abs(gap) < 6 else "6+"
        picks.append((f"Model spread side, gap {band}", "spreads", side))
        if 3 <= abs(gap) < 6:
            picks.append(("C1 model spread 3-6 off", "spreads", side))
            my = U if side == "away" else -U
            picks.append((f"C1 by size: {'fav 10+' if my <= -10 else 'fav 5-9.5' if my <= -5 else 'fav <5' if my < 0 else 'dog'}", "spreads", side))
        tg = mt - T
        tband = "<3" if abs(tg) < 3 else "3-6" if abs(tg) < 6 else "6+"
        picks.append((f"Model total side, gap {tband}", "totals", "over" if tg > 0 else "under"))
        if abs(tg) >= 6:
            picks.append(("C4 fade model total 6+", "totals", "under" if tg > 0 else "over"))
        for rule, mk, sd in picks:
            r = grade(g, L, mk, sd)
            nv, price = L[mk]["nv"][sd], L[mk]["price"][sd]
            for key in ((rule, "ALL"), (rule, half)):
                x = agg[key]; x["n"] += 1; x[r] += 1
                if r == "W":
                    x["fair"] += (1 - nv) / nv; x["book"] += _dec(price)
                elif r == "L":
                    x["fair"] -= 1; x["book"] -= 1
    rmse = {k: math.sqrt(statistics.mean(e * e for e in v)) for k, v in err.items()}
    bias = {k: statistics.mean(v) for k, v in err.items()}
    lines = [f"# Model backtest {season} (both teams {min_gp}+ games)", "",
             f"{n_games} games with bet-time odds. Model = season-to-date ratings, shooting-luck removed, pace, home court, B2B "
             "(the workbook model once its current-season weight reaches 1).", "",
             "| | RMSE | Avg error (model/market minus actual) |", "|---|---|---|"]
    for k in ("model margin", "market margin", "model total", "market total"):
        if k in rmse:
            lines.append(f"| {k} | {rmse[k]:.2f} | {bias[k]:+.2f} |")
    lines += ["", "| Rule | Period | Bets | W-L-P | ROI @ no-vig | ROI @ book |", "|---|---|---|---|---|---|"]
    for rule in sorted({k[0] for k in agg}):
        for per in ("ALL", "Oct-Dec", "Jan-Apr"):
            x = agg.get((rule, per))
            if not x or not x["n"]:
                continue
            dec = x["W"] + x["L"]
            lines.append(f"| {rule if per == 'ALL' else ''} | {per} | {x['n']} | {x['W']}-{x['L']}-{x['P']} | "
                         f"{100 * x['fair'] / dec:+.1f}% | {100 * x['book'] / dec:+.1f}% |")
    text = "\n".join(lines)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"model_backtest_{season}_{dt.date.today():%Y%m%d}.md")
        open(path, "w", encoding="utf-8").write(text)
        print(f"report written to {path}")
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", required=True)
    ap.add_argument("--min-gp", type=int, default=20)
    ap.add_argument("--out", default=r"C:\MaverickPicks\reports")
    a = ap.parse_args(argv)
    from .db import session
    with session() as db:
        print(backtest(db, a.season, a.min_gp, a.out))


if __name__ == "__main__":
    sys.exit(main())

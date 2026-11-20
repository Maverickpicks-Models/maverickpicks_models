r"""Rule mining with a held-out season: discover on one season, freeze the list, validate on another.

  python -m mpm.mine --discover 2025-26 --validate 2026-27 --out C:\MaverickPicks\reports

1. Every game gives six candidate bets (both spreads, both totals sides, both moneylines) at the bet-time line
   (Pinnacle no-vig, else the median book). Each bet gets pregame features from its own side's point of view:
   home/road, favorite/dog, spread and total size, rest and fatigue, season-to-date net rating gap, our model's
   gap to the line, recent form, 3-point shooting luck, pace, early/late season. Numbers are cut into thirds
   using the discovery season only.
2. Every single condition and every pair of conditions (same market) is scored on the discovery season:
   bets, record, ROI at the no-vig price (about Novig's), and a z-score. Kept: 80+ bets, positive in both halves,
   z >= 2; ranked by z; the false-discovery rate (Benjamini-Hochberg) is shown so you can see how many are
   expected to be luck.
3. The kept list is written to disk *before* the validation season is looked at, then each rule is graded on
   the validation season exactly as frozen. Only rules that are also positive there go to paper/test.

Honest power check: a real 3% edge needs ~1,000 bets to show z = 1. Most "discoveries" will be noise; the
validation season is what separates them.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import itertools
import json
import math
import os
import statistics
import sys

MIN_N, MIN_Z, TOP = 80, 2.0, 40


# ---------------------------------------------------------------- features
def season_rows(db, season: str, min_gp: int = 8):
    from .backtest import load_lines, load_games, schedule, fatigue
    from .model import SeasonState, project
    rng = db.one("SELECT MIN(game_date), MAX(game_date) FROM nba.team_game_log WHERE season=?", (season,))
    if not rng or not rng[0]:
        raise SystemExit(f"no game log for {season}: run mpm.history boxfile / fromdb first")
    d0, d1 = str(rng[0])[:10], str(rng[1])[:10]
    st = SeasonState(db, d0, d1)
    lines = load_lines(db, ("hist_bet", "hist_early"))
    played, margin = schedule(db, [season])
    out = []
    for g in load_games(db, [season]):
        L = lines.get(g["id"])
        if not L or not all(k in L for k in ("spreads", "totals", "h2h")):
            continue
        day, a, h = g["date"], g["away"], g["home"]
        fa, ab = fatigue(played, season, a, day); fh, hb = fatigue(played, season, h, day)
        rest = {}
        for t in (a, h):
            prev = [d for d in played.get((season, t), ()) if d < day]
            rest[t] = min(3, (day - max(prev)).days - 1) if prev else 3
        ta, th = st.team(a, day), st.team(h, day)
        if not ta or not th or min(ta["gp"], th["gp"]) < min_gp:
            continue
        p = project(st, a, h, day, ab, hb)
        form = {}
        for t in (a, h):
            ms = [m for d, m in sorted(margin.get((season, t), [])) if d < day]
            form[t] = (statistics.mean(ms[-5:]) - statistics.mean(ms)) if len(ms) >= 8 else 0.0
        lg = st.league(day)
        luck = {}
        from . import model as M
        for t, tt in ((a, ta), (h, th)):
            M.A["remove_luck"] = False; raw = st.team(t, day); M.A["remove_luck"] = True
            luck[t] = (raw["o"] - tt["o"]) - (raw["d"] - tt["d"])        # + = lucky (made threes / opponents missed)
        U, T = L["spreads"]["point"], L["totals"]["point"]
        common = dict(g=g, L=L, early=day.month >= 10, total=T, pace=ta["pace"] + th["pace"] - 2 * lg["pace"],
                      model_total_gap=(p["ap"] + p["hp"]) - T, luck_sum=luck[a] + luck[h], b2b_any=ab or hb)
        for side, me, opp, my_sp in (("away", a, h, U), ("home", h, a, -U)):
            mine, theirs = (ta, th) if side == "away" else (th, ta)
            mg = (p["ap"] - p["hp"]) if side == "away" else (p["hp"] - p["ap"])
            out.append(dict(common, side=side, home=side == "home", fav=my_sp < 0, spread=abs(my_sp),
                            fatigue_diff=(fa - fh) if side == "away" else (fh - fa),
                            rest_diff=rest[me] - rest[opp], net_gap=(mine["o"] - mine["d"]) - (theirs["o"] - theirs["d"]),
                            model_gap=mg + my_sp, form_own=form[me], form_opp=form[opp], luck_own=luck[me], luck_opp=luck[opp],
                            ml_nv=L["h2h"]["nv"][side]))
    return out


NUM = ["spread", "total", "pace", "model_total_gap", "luck_sum", "fatigue_diff", "rest_diff", "net_gap", "model_gap",
       "form_own", "form_opp", "luck_own", "luck_opp", "ml_nv"]
BOOL = ["home", "fav", "early", "b2b_any"]
FEATS = {"spreads": ["home", "fav", "early", "spread", "fatigue_diff", "rest_diff", "net_gap", "model_gap", "form_own",
                     "form_opp", "luck_own", "luck_opp", "total"],
         "h2h": ["home", "fav", "early", "ml_nv", "fatigue_diff", "rest_diff", "net_gap", "model_gap", "form_own", "luck_own"],
         "totals": ["early", "total", "pace", "model_total_gap", "luck_sum", "b2b_any"]}


def cutpoints(rows):
    cuts = {}
    for f in NUM:
        v = sorted(r[f] for r in rows if r.get(f) is not None)
        if v:
            cuts[f] = (v[len(v) // 3], v[2 * len(v) // 3])
    return cuts


def conditions(market):
    out = []
    for f in FEATS[market]:
        if f in BOOL:
            out += [(f, "yes"), (f, "no")]
        else:
            out += [(f, "low"), (f, "mid"), (f, "high")]
    return out


def holds(row, cond, cuts):
    f, v = cond
    if f in BOOL:
        return bool(row[f]) == (v == "yes")
    lo, hi = cuts[f]
    x = row[f]
    if lo == hi:                      # mostly-zero features (rest, fatigue difference): less / equal / more
        return (x < lo) if v == "low" else (x > hi) if v == "high" else (x == lo)
    return (x < lo) if v == "low" else (x >= hi) if v == "high" else (lo <= x < hi)


def bets(rows, market):
    """(row, side_key) for the market: spreads/h2h use the row's side; totals: both over and under from one row per game."""
    if market != "totals":
        return [(r, r["side"]) for r in rows]
    seen, out = set(), []
    for r in rows:
        if r["g"]["id"] in seen:
            continue
        seen.add(r["g"]["id"])
        out += [(r, "over"), (r, "under")]
    return out


def ret(row, market, side):
    key = (market, side)
    cache = row.setdefault("_ret", {})
    if key in cache:
        return cache[key]
    from .backtest import grade
    res = grade(row["g"], row["L"], market, side)
    nv = row["L"][market]["nv"][side]
    cache[key] = ((1 - nv) / nv if res == "W" else -1.0 if res == "L" else 0.0, res)
    return cache[key]


def score(items):
    rs = [x[0] for x in items]
    n = len(rs)
    if n < 2:
        return None
    m = statistics.mean(rs); sd = statistics.pstdev(rs) or 1
    halves = collections.defaultdict(list)
    for r, res, early in items:
        halves[early].append(r)
    hm = {k: statistics.mean(v) for k, v in halves.items() if v}
    return dict(n=n, w=sum(1 for x in items if x[1] == "W"), l=sum(1 for x in items if x[1] == "L"),
                roi=m, z=m / (sd / math.sqrt(n)), early=hm.get(True), late=hm.get(False))


def label(market, side_label, conds):
    return f"{market}:{side_label} when " + " & ".join(f"{f}={v}" for f, v in conds)


def evaluate(rows, cuts, rules=None, ids=None):
    """Score all single/pair conditions (or the given frozen rules) -> {key: stats}; `ids` collects each rule's bets."""
    res = {}
    for market in ("spreads", "h2h", "totals"):
        bl = bets(rows, market)
        conds = conditions(market)
        combos = [(c,) for c in conds] + [p for p in itertools.combinations(conds, 2) if p[0][0] != p[1][0]]
        sides = ["over", "under"] if market == "totals" else ["any"]
        for combo in combos:
            for sd in sides:
                key = label(market, sd, combo)
                if rules is not None and key not in rules:
                    continue
                items, which = [], set()
                for row, s in bl:
                    if market == "totals" and s != sd:
                        continue
                    if all(holds(row, c, cuts) for c in combo):
                        r, outc = ret(row, market, s)
                        items.append((r, outc, row["early"])); which.add((row["g"]["id"], market, s))
                st = score(items)
                if st:
                    res[key] = st
                    if ids is not None:
                        ids[key] = which
    return res


def bh(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m; prev = 1.0
    for rank, i in reversed(list(enumerate(order, 1))):
        prev = min(prev, pvals[i] * m / rank); q[i] = prev
    return q


def pooled(rows, cuts, kept):
    """Every validation bet that any frozen rule makes, counted once per (game, market, side)."""
    seen, items = set(), []
    for k in kept:
        mk, rest = k.split(":", 1)
        sd, conds = rest.split(" when ", 1)
        combo = [tuple(c.split("=")) for c in conds.split(" & ")]
        for row, s in bets(rows, mk):
            if (mk == "totals" and s != sd) or not all(holds(row, c, cuts) for c in combo):
                continue
            uid = (row["g"]["id"], mk, s)
            if uid not in seen:
                seen.add(uid); r, o = ret(row, mk, s); items.append((r, o, row["early"]))
    return score(items)


def run(db, discover: str, validate: str | None, out_dir: str | None, min_gp: int = 8) -> str:
    rows = season_rows(db, discover, min_gp)
    cuts = cutpoints(rows)
    ids = {}
    allres = evaluate(rows, cuts, ids=ids)
    keys = list(allres)
    from statistics import NormalDist
    p = [1 - NormalDist().cdf(allres[k]["z"]) for k in keys]
    q = dict(zip(keys, bh(p)))
    kept = [k for k in keys if allres[k]["n"] >= MIN_N and allres[k]["z"] >= MIN_Z
            and (allres[k]["early"] or 0) > 0 and (allres[k]["late"] or 0) > 0]
    kept.sort(key=lambda k: (-allres[k]["z"], len(k)))
    distinct = []                     # the same bets under another name (e.g. "home" vs "home & fav") count once
    for k in kept:
        if all(len(ids[k] & ids[j]) < 0.8 * min(len(ids[k]), len(ids[j])) for j in distinct):
            distinct.append(k)
        if len(distinct) == TOP:
            break
    kept = distinct
    frozen = {"discover": discover, "made": dt.datetime.now().isoformat(timespec="seconds"), "cuts": cuts,
              "rules": {k: dict(allres[k], q=q[k]) for k in kept}}
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        fp = os.path.join(out_dir, f"mined_rules_{discover}_{dt.date.today():%Y%m%d}.json")
        json.dump(frozen, open(fp, "w"), indent=1, default=str)
        print(f"frozen rule list written to {fp}")
    val = {}
    if validate:
        vrows = season_rows(db, validate, min_gp)
        val = evaluate(vrows, cuts, set(kept))
        pool = pooled(vrows, cuts, kept)
    title = f"# Rule mining: discover {discover}" + (f", validate {validate}" if validate else "")
    lines = [title,
             "", f"Discovery: {len(rows) // 2} games, {len(keys):,} conditions tested; {sum(1 for k in keys if q[k] < 0.10)} pass a 10% false-discovery rate. "
             f"Kept for validation: n >= {MIN_N}, z >= {MIN_Z}, positive in both halves, not 80%+ the same bets as a stronger rule "
             f"(top {TOP}).",
             "", "| Rule | Disc. bets | Disc. W-L | Disc. ROI | z | FDR q | Valid. bets | Valid. W-L | Valid. ROI |", "|---|---|---|---|---|---|---|---|---|"]
    passed = 0
    for k in kept:
        d, v = allres[k], val.get(k)
        vs = f"{v['n']} | {v['w']}-{v['l']} | {100 * v['roi']:+.1f}%" if v else "0 | – | –"
        passed += 1 if v and v["roi"] > 0 else 0
        lines.append(f"| {k} | {d['n']} | {d['w']}-{d['l']} | {100 * d['roi']:+.1f}% | {d['z']:.2f} | {q[k]:.2f} | {vs} |")
    if validate:
        lines += ["", f"Validation: {len(vrows) // 2} games. {passed} of {len(kept)} kept rules are positive on {validate}; "
                  "by chance alone about half would be."]
        if pool:
            lines.append(f"All kept rules together (each bet once): {pool['n']} bets, {pool['w']}-{pool['l']}, "
                         f"{100 * pool['roi']:+.1f}% ROI at no-vig, z {pool['z']:.2f}.")
    lines += ["", "Feature cut points (thirds of the discovery season): " +
              "; ".join(f"{f} {lo:.2f}/{hi:.2f}" for f, (lo, hi) in cuts.items())]
    text = "\n".join(lines)
    if out_dir:
        fp = os.path.join(out_dir, f"mined_rules_{discover}_{dt.date.today():%Y%m%d}.md")
        open(fp, "w", encoding="utf-8").write(text)
        print(f"report written to {fp}")
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", required=True)
    ap.add_argument("--validate")
    ap.add_argument("--min-gp", type=int, default=8, help="both teams need this many games (features use season-to-date stats)")
    ap.add_argument("--out", default=r"C:\MaverickPicks\reports")
    a = ap.parse_args(argv)
    from .db import session
    with session() as db:
        print(run(db, a.discover, a.validate, a.out, a.min_gp))


if __name__ == "__main__":
    sys.exit(main())

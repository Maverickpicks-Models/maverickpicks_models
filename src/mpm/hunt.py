r"""The angle hunt: everything we can measure, found on one season, frozen, then graded on another.

  python -m mpm.hunt --discover 2025-26 --validate 2026-27 --out C:\MaverickPicks\reports

About 120 pregame features per bet, from the market (spread/total/ML size, key numbers, ML vs spread pricing, how high tonight's total is vs the season), the schedule (rest, back-to-backs, 3-in-4, games in 7 days,
road trip / homestand, travel, time zones, altitude, days until the next game and how good the next opponent is, tip time,
weekend, month), the teams (net rating, our model's gap to the line, record, Pythagorean luck, close-game luck, 3P luck,
win/loss streak, ATS streak, recent cover and Over form, last game's margin and total, four factors for and against:
shooting, turnovers, offensive rebounding, free-throw rate, 3-point attempt rate, pace and pace mismatch) and the matchup
(conference / division game, revenge, previous meeting).

1. Discovery season: every single condition and every pair of conditions (numbers cut into thirds) is scored on spreads,
   moneylines and totals at the bet-time no-vig price; Benjamini-Hochberg false-discovery rate across all of them.
2. Freeze: the strongest distinct angles (60+ bets, z >= 2.5 for singles / 3.0 for pairs, positive in both halves) are
   written to JSON before the validation season is touched.
3. Validation season: each frozen angle graded exactly as frozen, plus the pooled result.
4. A multivariate model (ridge logistic regression on all features, fit on the discovery season, regularisation chosen by
   month-blocked cross-validation) predicts cover / Over / win probability; validation bets where it beats the no-vig
   price by 2-3-5%+.
5. The reverse check: angles strong on the validation season, with what the discovery season said about them.
Only angles that hold on both seasons earn paper status; nothing here is bet until it does.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import datetime as dt
import itertools
import json
import math
import os
import statistics
import sys

import numpy as np

from . import mine, months as Mo, quarters as Qm

CONF = {"E": "ATL BOS BKN CHA CHI CLE DET IND MIA MIL NYK ORL PHI TOR WAS".split(),
        "W": "DAL DEN GSW HOU LAC LAL MEM MIN NOP OKC PHX POR SAC SAS UTA".split()}
DIV = ["BOS BKN NYK PHI TOR", "CHI CLE DET IND MIL", "ATL CHA MIA ORL WAS", "DEN MIN OKC POR UTA",
       "GSW LAC LAL PHX SAC", "DAL HOU MEM NOP SAS"]
CONF_OF = {t: c for c, ts in CONF.items() for t in ts}
DIV_OF = {t: i for i, d in enumerate(DIV) for t in d.split()}


# ---------------------------------------------------------------- more features
def add_more(db, rows, season):
    log = collections.defaultdict(list)   # team -> [(date, gid, is_home, opp, pts, opp_pts, box)]
    by_gid = collections.defaultdict(dict)
    for (gid, d, t, o, home, pts, opp_pts, fga, fg3a, fg3m, fgm, fta, ftm, oreb, dreb, tov) in db.q(
            "SELECT nba_game_id, game_date, team_code, opp_code, is_home, pts, opp_pts, fga, fg3a, fg3m, fgm, fta, ftm, oreb, dreb, tov "
            "FROM nba.team_game_log WHERE season=?", (season,)):
        b = dict(fga=fga or 0, fg3a=fg3a or 0, fg3m=fg3m or 0, fgm=fgm or 0, fta=fta or 0, ftm=ftm or 0, oreb=oreb or 0,
                 dreb=dreb or 0, tov=tov or 0)
        by_gid[gid][t] = b
        log[t].append((dt.date.fromisoformat(str(d)[:10]), gid, bool(home), o, pts, opp_pts, b))
    for t in log:
        log[t].sort(key=lambda x: x[0])
    dates = {t: [x[0] for x in v] for t, v in log.items()}

    # lines per game for ATS / OU streaks
    gl = {}
    for r in rows:
        g, L = r["g"], r["L"]
        gl[(g["date"], g["away"], g["home"])] = (L["spreads"]["point"], L["totals"]["point"])
    season_tot = collections.defaultdict(list)
    for (d, a, h), (U, T) in gl.items():
        season_tot[d].append(T)
    tot_days = sorted(season_tot)

    cache = {}

    def team_state(t, day):
        k = (t, day)
        if k in cache:
            return cache[k]
        i = bisect.bisect_left(dates.get(t, []), day)
        p = log[t][:i] if t in log else []
        nxt = None
        if t in log and i < len(log[t]):
            j = i + 1 if log[t][i][0] == day else i
            nxt = log[t][j] if j < len(log[t]) else None
        s = {}
        if p:
            w = sum(1 for x in p if x[4] is not None and x[5] is not None and x[4] > x[5])
            gp = len(p); pf = sum((x[4] or 0) for x in p) / gp; pa = sum((x[5] or 0) for x in p) / gp
            py = pf ** 14 / (pf ** 14 + pa ** 14) if pf and pa else 0.5
            close = [x for x in p if x[4] is not None and x[5] is not None and abs(x[4] - x[5]) <= 5]
            s["win_pct"] = w / gp
            s["pyth_luck"] = w / gp - py
            s["close_luck"] = (sum(1 for x in close if x[4] > x[5]) - sum(1 for x in close if x[4] < x[5])) / gp
            streak = 0
            for x in reversed(p):
                won = x[4] > x[5]
                if streak == 0:
                    streak = 1 if won else -1
                elif (streak > 0) == won:
                    streak += 1 if won else -1
                else:
                    break
            s["streak"] = streak
            own = collections.Counter(); opp = collections.Counter()
            for x in p:
                for kk, v in x[6].items():
                    own[kk] += v
                ob = by_gid[x[1]].get(x[3])
                if ob:
                    for kk, v in ob.items():
                        opp[kk] += v
            def ff(b, ob):
                poss = b["fga"] - b["oreb"] + b["tov"] + 0.44 * b["fta"] or 1
                return dict(efg=(b["fgm"] + 0.5 * b["fg3m"]) / (b["fga"] or 1), tovp=b["tov"] / poss,
                            orbp=b["oreb"] / ((b["oreb"] + ob["dreb"]) or 1), ftr=b["ftm"] / (b["fga"] or 1),
                            par3=b["fg3a"] / (b["fga"] or 1))
            fo, fd = ff(own, opp), ff(opp, own)
            for kk in fo:
                s[f"{kk}_o"], s[f"{kk}_d"] = fo[kk], fd[kk]
            s["g7"] = sum(1 for x in p if (day - x[0]).days <= 7)
            # ATS / OU streaks and last game
            ats, ou = [], []
            for x in p:
                key = (x[0], x[3], t) if x[2] else (x[0], t, x[3])
                if key in gl and x[4] is not None:
                    U, T = gl[key]
                    my_sp = -U if x[2] else U
                    ats.append(x[4] - x[5] + my_sp); ou.append(x[4] + x[5] - T)
            sk = 0
            for c in reversed(ats):
                if c == 0:
                    break
                if sk == 0:
                    sk = 1 if c > 0 else -1
                elif (sk > 0) == (c > 0):
                    sk += 1 if c > 0 else -1
                else:
                    break
            s["ats_streak"] = sk
            s["last_ou"] = ou[-1] if ou else None
            s["last3_ats"] = statistics.mean(ats[-3:]) if len(ats) >= 3 else None
            s["season_ats"] = statistics.mean(ats) if len(ats) >= 5 else None
        if nxt:
            s["next_days"] = min(4, (nxt[0] - day).days)
            s["next_opp"] = nxt[3]
        cache[k] = s
        return s

    netm = {}

    def net_asof(t, day):
        k = (t, day)
        if k not in netm:
            i = bisect.bisect_left(dates.get(t, []), day)
            p = log[t][:i] if t in log else []
            ms = [x[4] - x[5] for x in p if x[4] is not None and x[5] is not None]
            netm[k] = statistics.mean(ms) if len(ms) >= 3 else None
        return netm[k]

    for r in rows:
        g = r["g"]; day = g["date"]; a, h = g["away"], g["home"]
        me, opp = (a, h) if r["side"] == "away" else (h, a)
        sm, so = team_state(me, day), team_state(opp, day)
        for kk in ("win_pct", "pyth_luck", "close_luck", "streak", "ats_streak", "last_ou", "last3_ats", "season_ats", "g7",
                   "efg_o", "efg_d", "tovp_o", "tovp_d", "orbp_o", "orbp_d", "ftr_o", "ftr_d", "par3_o", "par3_d", "next_days"):
            r[f"{kk}_me"] = sm.get(kk); r[f"{kk}_opp"] = so.get(kk)
        r["win_pct_gap"] = (sm.get("win_pct") or 0) - (so.get("win_pct") or 0)
        r["record_vs_rating"] = r["win_pct_gap"] * 30 - r["net_gap"] if r.get("net_gap") is not None else None   # + = record better than rating
        for side_, s_ in (("me", sm), ("opp", so)):
            no = s_.get("next_opp")
            r[f"next_opp_net_{side_}"] = net_asof(no, day) if no else None
        r["same_conf"] = CONF_OF.get(a) == CONF_OF.get(h)
        r["same_div"] = DIV_OF.get(a) == DIV_OF.get(h)
        U, T = r["L"]["spreads"]["point"], r["L"]["totals"]["point"]
        sp = abs(U)
        r["key3"] = 2.5 <= sp <= 3.5
        r["key7"] = 6.5 <= sp <= 7.5
        r["pickem"] = sp <= 1.5
        i = bisect.bisect_left(tot_days, day)
        prev = [x for d in tot_days[max(0, i - 14):i] for x in season_tot[d]]
        r["total_vs_recent"] = T - statistics.mean(prev) if len(prev) >= 20 else None
        r["par3_sum"] = None if None in (sm.get("par3_o"), so.get("par3_o")) else sm["par3_o"] + so["par3_o"]
        r["ftr_sum"] = None if None in (sm.get("ftr_o"), so.get("ftr_o")) else sm["ftr_o"] + so["ftr_o"]
        r["efg_sum"] = None if None in (sm.get("efg_o"), so.get("efg_o")) else sm["efg_o"] + so["efg_o"]
        r["tov_sum"] = None if None in (sm.get("tovp_o"), so.get("tovp_o")) else sm["tovp_o"] + so["tovp_o"]
        for kk in ("efg", "tovp", "orbp", "ftr", "par3"):
            a_, b_ = sm.get(f"{kk}_o"), so.get(f"{kk}_d")
            r[f"{kk}_edge"] = None if None in (a_, b_) else a_ - b_      # my offense vs their defense allowed
        r["month"] = day.month
    return rows


SIDE_FEATS = (["home", "fav", "spread", "net_gap", "model_gap", "form_own", "form_opp", "luck_own", "luck_opp", "ml_nv",
               "fatigue_diff", "rest_diff", "total"]
              + Mo.SPREAD_NEW
              + [f"{k}_{s}" for k in ("win_pct", "pyth_luck", "close_luck", "streak", "ats_streak", "last_ou", "last3_ats",
                                      "season_ats", "g7", "efg_o", "efg_d", "tovp_o", "tovp_d", "orbp_o", "orbp_d", "ftr_o",
                                      "ftr_d", "par3_o", "par3_d", "next_days") for s in ("me", "opp")]
              + ["win_pct_gap", "record_vs_rating", "next_opp_net_me", "next_opp_net_opp", "same_conf", "same_div", "key3",
                 "key7", "pickem", "efg_edge", "tovp_edge", "orbp_edge", "ftr_edge", "par3_edge", "month_early", "month_mid"])
TOT_FEATS = (["total", "pace", "model_total_gap", "luck_sum", "b2b_any"] + Mo.TOTAL_NEW
             + ["total_vs_recent", "par3_sum", "ftr_sum", "efg_sum", "tov_sum", "same_conf", "same_div", "last_ou_me",
                "last_ou_opp", "g7_me", "g7_opp", "month_early", "month_mid"])
BOOLS = set(Mo.ALL_BOOL) | {"same_conf", "same_div", "key3", "key7", "pickem", "month_early", "month_mid", "b2b_any"}


def finish(rows):
    for r in rows:
        r["month_early"] = r["g"]["date"].month in (10, 11, 12)
        r["month_mid"] = r["g"]["date"].month in (1, 2)
    return rows


# ---------------------------------------------------------------- vectorised scoring
class Market:
    """All bets of one market as arrays; conditions as boolean masks."""

    def __init__(self, rows, mk, feats, cuts):
        self.mk = mk
        pairs = mine.bets(rows, mk)
        self.bets = pairs
        self.ret = np.array([mine.ret(r, mk, s)[0] for r, s in pairs])
        self.res = np.array([mine.ret(r, mk, s)[1] for r, s in pairs])
        self.nv = np.array([r["L"][mk]["nv"][s] for r, s in pairs])
        self.early = np.array([r["g"]["date"].month >= 10 for r, s in pairs])
        self.side = np.array([s for r, s in pairs])
        self.ids = [(r["g"]["id"], mk, s) for r, s in pairs]
        self.masks = {}
        self.vals = {}
        for f in feats:
            x = [r.get(f) for r, s in pairs]
            if f in BOOLS:
                v = np.array([bool(t) for t in x])
                self.masks[(f, "yes")] = v; self.masks[(f, "no")] = ~v
                self.vals[f] = v.astype(float)
            else:
                if f not in cuts:
                    continue
                lo, hi = cuts[f]
                arr = np.array([np.nan if t is None else float(t) for t in x])
                ok = ~np.isnan(arr)
                if lo == hi:
                    self.masks[(f, "low")] = ok & (arr < lo); self.masks[(f, "mid")] = ok & (arr == lo); self.masks[(f, "high")] = ok & (arr > hi)
                else:
                    self.masks[(f, "low")] = ok & (arr < lo); self.masks[(f, "mid")] = ok & (arr >= lo) & (arr < hi); self.masks[(f, "high")] = ok & (arr >= hi)
                self.vals[f] = arr
        if mk == "totals":
            self.sidemask = {"over": self.side == "over", "under": self.side == "under"}
        else:
            self.sidemask = {"any": np.ones(len(pairs), bool)}

    def score(self, m):
        n = int(m.sum())
        if n < 2:
            return None
        r = self.ret[m]; mu = r.mean(); sd = r.std() or 1
        e, l = self.early & m, ~self.early & m
        return dict(n=n, w=int((self.res[m] == "W").sum()), l=int((self.res[m] == "L").sum()), roi=float(mu),
                    z=float(mu / (sd / math.sqrt(n))), early=float(self.ret[e].mean()) if e.any() else None,
                    late=float(self.ret[l].mean()) if l.any() else None)


def cuts_for(rows, feats):
    c = {}
    for f in feats:
        if f in BOOLS:
            continue
        v = sorted(float(r[f]) for r in rows if r.get(f) is not None)
        if len(v) >= 30:
            c[f] = (v[len(v) // 3], v[2 * len(v) // 3])
    return c


def label(mk, sd, conds):
    return f"{mk}:{sd} when " + " & ".join(f"{f}={v}" for f, v in conds)


def search(M: Market, min_n=60):
    res = {}
    keys = list(M.masks)
    for sd, smask in M.sidemask.items():
        for c in keys:
            m = smask & M.masks[c]
            if m.sum() >= min_n:
                res[label(M.mk, sd, (c,))] = (M.score(m), m)
        for c1, c2 in itertools.combinations(keys, 2):
            if c1[0] == c2[0]:
                continue
            m = smask & M.masks[c1] & M.masks[c2]
            if m.sum() >= min_n:
                res[label(M.mk, sd, (c1, c2))] = (M.score(m), m)
    return res


def parse(key):
    mk, rest = key.split(":", 1)
    sd, conds = rest.split(" when ", 1)
    return mk, sd, [tuple(c.split("=")) for c in conds.split(" & ")]


def apply(M: Market, key):
    mk, sd, conds = parse(key)
    m = M.sidemask[sd].copy()
    for c in conds:
        if c not in M.masks:
            return None
        m &= M.masks[c]
    return m


def bh(p):
    p = np.asarray(p); n = len(p); o = np.argsort(p)
    q = np.empty(n); prev = 1.0
    for rank in range(n, 0, -1):
        i = o[rank - 1]; prev = min(prev, p[i] * n / rank); q[i] = prev
    return q


# ---------------------------------------------------------------- multivariate model
def design(M: Market, feats, stats=None):
    cols, X = [], []
    for f in feats:
        if f not in M.vals:
            continue
        v = M.vals[f].copy()
        if stats is None or f not in stats:
            mu = float(np.nanmean(v)) if np.isfinite(np.nanmean(v)) else 0.0
            sd = float(np.nanstd(v)) or 1.0
        else:
            mu, sd = stats[f]
        v = np.where(np.isnan(v), mu, v)
        X.append((v - mu) / sd); cols.append((f, mu, sd))
    side = np.array([1.0 if s in ("away", "over") else -1.0 for s in M.side])
    if X and M.mk == "totals":          # the same game features point opposite ways for the Over and the Under
        X = [x * side for x in X]
    X = np.column_stack(X + [side]) if X else side[:, None]
    return X, cols


def fit_logit(X, y, lam, iters=300):
    w = np.zeros(X.shape[1]); b = 0.0
    lr = 0.5
    for _ in range(iters):
        z = X @ w + b; p = 1 / (1 + np.exp(-z))
        g = X.T @ (p - y) / len(y) + lam * w; gb = float((p - y).mean())
        w -= lr * g; b -= lr * gb
    return w, b


def model_section(Md, Mv, feats):
    out = []
    keep = [r != "P" for r in Md.res]
    Xd, cols = design(Md, feats)
    yd = np.array([1.0 if r == "W" else 0.0 for r in Md.res])
    stats = {f: (mu, sd) for f, mu, sd in cols}
    months_d = np.array([r["g"]["date"].month for r, s in Md.bets])
    best = None
    for lam in (0.3, 0.1, 0.03, 0.01):
        ll = []
        for mo in sorted(set(months_d)):
            tr = (months_d != mo) & np.array(keep); te = (months_d == mo) & np.array(keep)
            if te.sum() < 20:
                continue
            w, b = fit_logit(Xd[tr], yd[tr], lam)
            p = np.clip(1 / (1 + np.exp(-(Xd[te] @ w + b))), 1e-4, 1 - 1e-4)
            ll.append(float(-np.mean(yd[te] * np.log(p) + (1 - yd[te]) * np.log(1 - p))))
        score = statistics.mean(ll) if ll else 9
        if best is None or score < best[0]:
            best = (score, lam)
    lam = best[1]
    w, b = fit_logit(Xd[np.array(keep)], yd[np.array(keep)], lam)
    Xv, _ = design(Mv, [f for f, _, _ in cols], stats)
    pv = 1 / (1 + np.exp(-(Xv @ w + b)))
    edge = pv - Mv.nv
    out.append(f"Ridge logistic on {Xd.shape[1] - 1} features, penalty {lam} (month-blocked CV log-loss {best[0]:.4f}; a coin is 0.6931).")
    out += ["", "| Validation bets where the model beats the no-vig price by | Bets | W-L | ROI |", "|---|---|---|---|"]
    for thr in (0.02, 0.03, 0.05, 0.08):
        m = edge >= thr
        s = Mv.score(m)
        if s:
            out.append(f"| {int(thr * 100)}%+ | {s['n']} | {s['w']}-{s['l']} | {100 * s['roi']:+.1f}% (z {s['z']:.2f}) |")
    imp = sorted(zip([f for f, _, _ in cols] + ["side"], w), key=lambda t: -abs(t[1]))[:12]
    out += ["", "Largest weights (standardised): " + "; ".join(f"{f} {v:+.3f}" for f, v in imp)]
    return out


# ---------------------------------------------------------------- report
def run(db, discover, validate, out_dir=None, min_gp=5):
    def rows_for(season):
        rs = mine.season_rows(db, season, min_gp)
        rs = Qm.add_recent(rs)
        rs = Mo.add_context(db, rs, season)
        rs = add_more(db, rs, season)
        return finish(rs)
    D = rows_for(discover)
    V = rows_for(validate) if validate else []
    feats = {"spreads": SIDE_FEATS, "h2h": SIDE_FEATS, "totals": TOT_FEATS}
    allf = sorted(set(SIDE_FEATS) | set(TOT_FEATS))
    cuts = cuts_for(D, allf)
    L = [f"# Angle hunt: discover {discover}" + (f", validate {validate}" if validate else ""),
         "", f"Discovery {len(D) // 2} games, validation {len(V) // 2} games, bet-time Pinnacle no-vig prices (≈ Novig). "
         f"{len(allf)} features, cut into thirds on {discover}.", ""]
    frozen, found = {}, {}
    mk_objs = {}
    for mk in ("spreads", "h2h", "totals"):
        Md = Market(D, mk, feats[mk], cuts); Mv = Market(V, mk, feats[mk], cuts) if V else None
        mk_objs[mk] = (Md, Mv)
        res = search(Md)
        found.update({k: v[0] for k, v in res.items()})
        L.append(f"- {mk}: {len(Md.ret)} bets, {len(Md.masks)} conditions, {len(res):,} singles + pairs with 60+ bets tested.")
    keys = list(found)
    from statistics import NormalDist
    pv = [1 - NormalDist().cdf(found[k]["z"]) for k in keys]
    q = dict(zip(keys, bh(pv)))
    ntests = len(keys)
    L += ["", f"**{ntests:,} angles tested.** By luck alone about {round(ntests * 0.0062):,} would reach z ≥ 2.5 and "
          f"{round(ntests * 0.00135):,} z ≥ 3.0. Actually reached: {sum(1 for k in keys if found[k]['z'] >= 2.5):,} and "
          f"{sum(1 for k in keys if found[k]['z'] >= 3.0):,}. Pass a 10% false-discovery rate: "
          f"{sum(1 for k in keys if q[k] < 0.10)}; 25%: {sum(1 for k in keys if q[k] < 0.25)}.", ""]
    # freeze
    cand = []
    for k in keys:
        s = found[k]; pair = " & " in k
        if s["n"] >= 60 and s["z"] >= (3.0 if pair else 2.5) and (s["early"] or 0) > 0 and (s["late"] or 0) > 0:
            if pair:                       # a pair must add something over each of its halves on their own
                mk_, sd_, cs = parse(k)
                parts = [found.get(label(mk_, sd_, (c,))) for c in cs]
                if any(p_ and s["roi"] < p_["roi"] + 0.03 for p_ in parts):
                    continue
            cand.append(k)
    cand.sort(key=lambda k: (-found[k]["z"], len(k)))
    distinct, masks = [], {}
    for k in cand:
        mk = k.split(":")[0]
        m = apply(mk_objs[mk][0], k)
        if m is None:
            continue
        ids = set(i for i, x in zip(mk_objs[mk][0].ids, m) if x)
        if all(len(ids & masks[j]) < 0.7 * min(len(ids), len(masks[j])) for j in distinct):
            distinct.append(k); masks[k] = ids
        if len(distinct) >= 60:
            break
    frozen = {k: dict(found[k], q=float(q[k])) for k in distinct}
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        json.dump({"discover": discover, "made": dt.datetime.now().isoformat(timespec="seconds"), "cuts": cuts, "angles": frozen},
                  open(os.path.join(out_dir, f"hunt_frozen_{discover}_{dt.date.today():%Y%m%d}.json"), "w"), indent=1, default=str)
    L += ["## 1. Frozen angles (found on " + discover + ", graded on " + (validate or "–") + ")", "",
          "Rules: 60+ bets, z ≥ 2.5 (single) or 3.0 (pair), positive in both halves, a pair at least 3 ROI points better than "
          "each of its halves alone, not 70%+ the same bets as a stronger angle.", "",
          "| Angle | Disc. bets | Disc. W-L | Disc. ROI | z | FDR q | Valid. bets | Valid. W-L | Valid. ROI | Valid. z |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    held, pooled_ids = [], {}
    for k in distinct:
        d = found[k]; mk = k.split(":")[0]
        v = None
        if V:
            mv = apply(mk_objs[mk][1], k)
            v = mk_objs[mk][1].score(mv) if mv is not None else None
            if mv is not None:
                for i, x, r in zip(mk_objs[mk][1].ids, mv, mk_objs[mk][1].ret):
                    if x:
                        pooled_ids[i] = r
        vs = f"{v['n']} | {v['w']}-{v['l']} | {100 * v['roi']:+.1f}% | {v['z']:+.2f}" if v else "0 | – | – | –"
        if v and v["n"] >= 25 and v["roi"] > 0 and v["z"] >= 1.0:
            held.append((d["z"] + v["z"], k, d, v))
        L.append(f"| {k} | {d['n']} | {d['w']}-{d['l']} | {100 * d['roi']:+.1f}% | {d['z']:.2f} | {q[k]:.2f} | {vs} |")
    if V:
        pos = sum(1 for k in distinct if (lambda m: m is not None and (mk_objs[k.split(':')[0]][1].score(m) or {}).get('roi', -1) > 0)(apply(mk_objs[k.split(':')[0]][1], k)))
        pr = list(pooled_ids.values())
        L += ["", f"{pos} of {len(distinct)} frozen angles are positive on {validate} (about half would be by luck). "
              + (f"All frozen angles together, each bet once: {len(pr)} bets, {100 * statistics.mean(pr):+.1f}% "
                 f"(z {statistics.mean(pr) / (statistics.pstdev(pr) / math.sqrt(len(pr))):.2f})." if len(pr) > 2 else "")]
        L += ["", "## 2. Held on both seasons (validation 25+ bets, positive, z ≥ 1)", ""]
        if held:
            L += ["| Angle | " + discover + " | " + validate + " |", "|---|---|---|"]
            for _, k, d, v in sorted(held, reverse=True):
                L.append(f"| {k} | {d['w']}-{d['l']} {100 * d['roi']:+.1f}% (z {d['z']:.1f}) | {v['w']}-{v['l']} {100 * v['roi']:+.1f}% (z {v['z']:.1f}) |")
        else:
            L.append("None.")
        L += ["", "## 3. Multivariate model (all features at once)", ""]
        for mk in ("spreads", "totals", "h2h"):
            L += [f"### {mk}", ""] + model_section(*mk_objs[mk], feats[mk]) + [""]
        # reverse check
        L += ["## 4. Reverse check: strongest single angles on " + validate + " (not validated; what " + discover + " said)", "",
              "| Angle | " + validate + " | " + discover + " |", "|---|---|---|"]
        rv = []
        for mk in ("spreads", "h2h", "totals"):
            Md, Mv = mk_objs[mk]
            for sd, sm in Mv.sidemask.items():
                for c, m in Mv.masks.items():
                    s = Mv.score(sm & m)
                    if s and s["n"] >= 40 and s["z"] >= 2.0:
                        dk = label(mk, sd, (c,))
                        rv.append((s["z"], dk, s, Md.score(Md.sidemask[sd] & Md.masks[c]) if c in Md.masks else None))
        for z, k, s, d in sorted(rv, reverse=True)[:25]:
            ds = f"{d['w']}-{d['l']} {100 * d['roi']:+.1f}% (z {d['z']:.1f})" if d else "–"
            L.append(f"| {k} | {s['w']}-{s['l']} {100 * s['roi']:+.1f}% (z {s['z']:.1f}) | {ds} |")
    L += ["", "Cut points (thirds of " + discover + "): " + "; ".join(f"{f} {lo:.3g}/{hi:.3g}" for f, (lo, hi) in sorted(cuts.items()))]
    text = "\n".join(L)
    if out_dir:
        fp = os.path.join(out_dir, f"hunt_{discover}_{dt.date.today():%Y%m%d}.md")
        open(fp, "w", encoding="utf-8").write(text)
        print(f"report written to {fp}")
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", required=True)
    ap.add_argument("--validate")
    ap.add_argument("--min-gp", type=int, default=5)
    ap.add_argument("--out", default=r"C:\MaverickPicks\reports")
    a = ap.parse_args(argv)
    from .db import session
    with session() as db:
        print(run(db, a.discover, a.validate, a.out, a.min_gp))


if __name__ == "__main__":
    sys.exit(main())

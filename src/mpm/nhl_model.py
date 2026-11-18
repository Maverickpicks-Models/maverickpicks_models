"""NHL pricing engine: goal lambdas from MoneyPuck team rates + goalie factors, then an exact score
matrix (Poisson, empty-net and late-tie adjustments, OT/shootout) that prices moneyline, game totals and
team totals the way Novig settles them (official final score: the OT or shootout winner gets +1 goal).

This is the same engine as the Excel workbook (Calculations + ScoreMatrix sheets).

Inputs come from the database (nhl.team_season / nhl.goalie_season / nhl.model_settings, loaded by
mpm.nhl_workbook) or straight from the workbook (Model.from_workbook) for checks.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import NormalDist

N = NormalDist()

# nhl.model_settings name -> attribute, default
SETTINGS = {
    "Games to trust current season": ("trust", 20.0), "Finishing weight": ("fin", 0.15),
    "Possession tilt": ("tilt", 0.15), "Home ice": ("hi", 0.25), "OT scoring rate": ("ot", 0.14),
    "Shootout home win": ("so", 0.52), "Empty-Net Rate": ("pEN", 0.41), "Late tying rate": ("pTie", 0.15),
    "Lambda trim": ("trim", 0.973), "C22": ("K", 100.0), "Model weight on game totals": ("tot_wt", 0.5),
}


# ---------------------------------------------------------------- odds helpers
def implied(price: float) -> float:
    return -price / (100 - price) if price < 0 else 100 / (100 + price)


def american(p: float) -> int:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return round(-100 * p / (1 - p)) if p > 0.5 else (100 if p == 0.5 else round(100 * (1 - p) / p))


def payout(price: float) -> float:
    return 100 / -price if price < 0 else price / 100


def no_vig(price_a: float, price_b: float) -> float:
    a, b = implied(price_a), implied(price_b)
    return a / (a + b)


def ev(p: float, price: float) -> float:
    return p * payout(price) - (1 - p)


# ---------------------------------------------------------------- model
@dataclass
class Model:
    cur: dict                      # team_code -> dict(gp, gf, ga, xgf, xga, cf)
    pri: dict
    goalies: list                  # dict(name, team_code, gp, ga, xga)
    trust: float = 20.0
    fin: float = 0.15
    tilt: float = 0.15
    hi: float = 0.25
    ot: float = 0.14
    so: float = 0.52
    pEN: float = 0.41
    pTie: float = 0.15
    trim: float = 0.973
    K: float = 100.0
    tot_wt: float = 0.5
    r: float = field(init=False)

    def __post_init__(self):
        xga = sum(g["xga"] for g in self.goalies)
        self.r = (sum(g["ga"] for g in self.goalies) / xga) if xga else 1.0

    # ---- construction
    @classmethod
    def from_db(cls, db, season: int | None = None, prefer_download: bool = True):
        if season is None:
            season = db.one("SELECT MAX(season) FROM nhl.team_season")[0]
        cols = "team_code, games_played, goals_for, goals_against, expected_goals_for, expected_goals_against, shot_attempts_pct_corsi_pct"

        def teams_for(s):
            rows = db.q(f"SELECT {cols} FROM nhl.team_season WHERE season=? AND snapshot_date=(SELECT MAX(snapshot_date) "
                        "FROM nhl.team_season WHERE season=?)", (s, s))
            return {r[0]: dict(gp=float(r[1] or 0), gf=float(r[2] or 0), ga=float(r[3] or 0), xgf=float(r[4] or 0),
                               xga=float(r[5] or 0), cf=float(r[6]) if r[6] is not None else None) for r in rows}
        cur, pri = teams_for(season), teams_for(season - 1)
        gs = db.q("SELECT goalie, team_code, games_played, goals_against, expected_goals_against FROM nhl.goalie_season "
                  "WHERE season=? AND snapshot_date=(SELECT MAX(snapshot_date) FROM nhl.goalie_season WHERE season=?)",
                  (season, season))
        goalies = [dict(name=g[0], team_code=g[1], gp=float(g[2] or 0), ga=float(g[3] or 0), xga=float(g[4] or 0)) for g in gs]
        # A MoneyPuck download (mpm.moneypuck, situation all) from the same day or later replaces the pasted workbook tables
        wb_date = db.one("SELECT MAX(snapshot_date) FROM nhl.team_season WHERE season=?", (season,))[0]
        mp_date = db.one("SELECT MAX(snapshot_date) FROM nhl.mp_stat WHERE source='moneypuck' AND season=? AND entity='team'",
                         (season,))[0]
        if prefer_download and mp_date and (not wb_date or str(mp_date) >= str(wb_date)):   # same day: the download is fresher
            cur = _mp_teams(db, season, mp_date) or cur
            gmp = _mp_goalies(db, season, mp_date)
            goalies = gmp or goalies
        kw = {}
        for name, val in db.q("SELECT setting, value_num FROM nhl.model_settings"):
            if name in SETTINGS and val is not None:
                kw[SETTINGS[name][0]] = float(val)
        return cls(cur, pri, goalies, **kw)

    @classmethod
    def from_workbook(cls, path: str):
        import openpyxl
        from .nhl_workbook import slug
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

        def tab(name):
            it = wb[name].iter_rows(values_only=True)
            hdr = [slug(h) if h else "" for h in next(it)]
            ix = {h: i for i, h in enumerate(hdr)}
            out = {}
            for r in it:
                if not r or not r[ix["team"]]:
                    continue
                g = lambda k: float(r[ix[k]] or 0)
                out[str(r[ix["team"]])] = dict(gp=g("games_played"), gf=g("goals_for"), ga=g("goals_against"),
                                               xgf=g("expected_goals_for"), xga=g("expected_goals_against"),
                                               cf=r[ix["shot_attempts_pct_corsi_pct"]])
            return out
        cur, pri = tab("Data_2026_27"), tab("Data_2025_26")
        full2ab = {r[3]: r[2] for r in wb["Teams"].iter_rows(min_row=2, values_only=True) if r and r[3]}
        goalies = [dict(name=r[2], team_code=full2ab.get(r[1]), gp=float(r[3] or 0), ga=float(r[4] or 0), xga=float(r[5] or 0))
                   for r in wb["Goalies"].iter_rows(min_row=2, values_only=True) if r and r[2]]
        kw = {}
        for rn, r in enumerate(wb["Assumptions"].iter_rows(min_row=5, max_col=3, values_only=True), start=5):
            name = r[1] or (f"C{rn}" if isinstance(r[2], (int, float)) else None)
            if name in SETTINGS:
                try:
                    kw[SETTINGS[name][0]] = float(r[2])
                except (TypeError, ValueError):
                    pass
        return cls(cur, pri, goalies, **kw)

    # ---- pieces
    def goalie_factor(self, name: str | None, team_code: str | None) -> float:
        """((GA + K*r) / (xGA + K)) / r, shrunk toward league average; 1.0 = average or unknown."""
        if not name:
            return 1.0
        ga = sum(g["ga"] for g in self.goalies if g["name"] == name and g["team_code"] == team_code)
        xga = sum(g["xga"] for g in self.goalies if g["name"] == name and g["team_code"] == team_code)
        return ((ga + self.K * self.r) / (xga + self.K)) / self.r

    def rates(self, team: str) -> dict:
        P = self.pri.get(team, dict(gp=0)); C = self.cur.get(team, dict(gp=0))
        w = 0 if C["gp"] <= 0 else (1 if P["gp"] <= 0 else min(1, C["gp"] / self.trust))
        f = lambda k: (1 - w) * (P[k] / P["gp"] if P["gp"] else 0) + w * (C[k] / C["gp"] if C["gp"] else 0)
        cf = (1 - w) * (P.get("cf") or 0) + w * (C.get("cf") or 0)
        return dict(xgf=f("xgf"), xga=f("xga"), gf=f("gf"), ga=f("ga"), cf=cf, w=w)

    def lambdas(self, away: str, home: str, g_away: str | None = None, g_home: str | None = None):
        """Projected goals. g_away / g_home are the starting goalies (g_home faces the away team)."""
        a, h = self.rates(away), self.rates(home)
        la = ((a["xgf"] + h["xga"]) / 2) * (1 - self.fin) + ((a["gf"] + h["ga"]) / 2) * self.fin
        lh = ((h["xgf"] + a["xga"]) / 2) * (1 - self.fin) + ((h["gf"] + a["ga"]) / 2) * self.fin
        fa = self.goalie_factor(g_home, home); fh = self.goalie_factor(g_away, away)
        la = max(0.2, la * (1 + self.tilt * (a["cf"] - h["cf"])) * fa - self.hi / 2)
        lh = max(0.2, lh * (1 + self.tilt * (h["cf"] - a["cf"])) * fh + self.hi / 2)
        return la, lh

    def price(self, la: float, lh: float) -> "Prices":
        return Prices(self, la, lh)

    # ---- ranks used by the rules
    def offense_rank(self) -> dict:
        R = {t: self.rates(t) for t in self.cur}
        return {t: i + 1 for i, t in enumerate(sorted(R, key=lambda t: -R[t]["xgf"]))}

    def defense_rank(self) -> dict:
        R = {t: self.rates(t) for t in self.cur}
        return {t: i + 1 for i, t in enumerate(sorted(R, key=lambda t: R[t]["xga"]))}

    def goalie_rank(self, min_gp: int = 5) -> dict:
        gl = sorted((self.goalie_factor(g["name"], g["team_code"]), g["name"]) for g in self.goalies if g["gp"] >= min_gp)
        return {n: i + 1 for i, (f, n) in enumerate(gl)}

    def finishing(self, team: str) -> float:
        C = self.cur.get(team)
        return (C["gf"] - C["xgf"]) / C["gp"] if C and C["gp"] else 0.0

    def fair_from_market(self, home_win_p: float, over_p: float, total_line: float):
        """Solve lambdas so the score matrix matches the no-vig moneyline and game total (for XM)."""
        x = [3.0, 3.2]
        f = lambda la, lh: (lambda p: (p.ml_home - home_win_p, p.total_over(total_line) - over_p))(self.price(la, lh))
        for _ in range(40):
            r = f(*x)
            if abs(r[0]) < 1e-7 and abs(r[1]) < 1e-7:
                break
            h = 1e-4
            j00 = (f(x[0] + h, x[1])[0] - r[0]) / h; j10 = (f(x[0] + h, x[1])[1] - r[1]) / h
            j01 = (f(x[0], x[1] + h)[0] - r[0]) / h; j11 = (f(x[0], x[1] + h)[1] - r[1]) / h
            det = j00 * j11 - j01 * j10
            if abs(det) < 1e-12:
                break
            dx = (r[0] * j11 - r[1] * j01) / det; dy = (j00 * r[1] - j10 * r[0]) / det
            x = [min(6, max(1, x[0] - dx)), min(6, max(1, x[1] - dy))]
        return self.price(*x)


def _mp(db, season, snap, entity, stats):
    rows = db.q("SELECT entity_id, entity_name, team_code, stat, value FROM nhl.mp_stat WHERE source='moneypuck' AND season=? "
                f"AND snapshot_date=? AND entity=? AND situation='all' AND stat IN ({','.join('?' * len(stats))})",
                (season, snap, entity, *stats))
    out = {}
    for eid, name, team, stat, val in rows:
        d = out.setdefault(eid, {"name": name, "team": team})
        d[stat] = float(val) if val is not None else 0.0
    return out


def _mp_teams(db, season, snap) -> dict:
    t = _mp(db, season, snap, "team", ["games_played", "goalsFor", "goalsAgainst", "xGoalsFor", "xGoalsAgainst", "corsiPercentage"])
    return {d["team"]: dict(gp=d.get("games_played", 0), gf=d.get("goalsFor", 0), ga=d.get("goalsAgainst", 0),
                            xgf=d.get("xGoalsFor", 0), xga=d.get("xGoalsAgainst", 0), cf=d.get("corsiPercentage"))
            for d in t.values() if d["team"]}


def _mp_goalies(db, season, snap) -> list:
    g = _mp(db, season, snap, "goalie", ["games_played", "goals", "xGoals"])
    return [dict(name=d["name"], team_code=d["team"], gp=d.get("games_played", 0), ga=d.get("goals", 0), xga=d.get("xGoals", 0))
            for d in g.values() if d["name"]]


class Prices:
    """Score matrix for one game. Rows = away goals, columns = home goals (regulation, before OT)."""
    n = 13

    def __init__(self, m: Model, la: float, lh: float):
        a, b = la * m.trim, lh * m.trim
        n = self.n
        po = lambda k, l: math.exp(-l) * l ** k / math.factorial(k)
        raw = [[po(i, a) * po(j, b) for j in range(n)] for i in range(n)]
        R = lambda i, j: raw[i][j] if 0 <= i < n and 0 <= j < n else 0.0
        mm = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                v = R(i, j) * (1 - m.pEN - m.pTie) if abs(i - j) == 1 else R(i, j)
                if i - j == 2: v += m.pEN * R(i - 1, j)
                if j - i == 2: v += m.pEN * R(i, j - 1)
                if i == j and i > 0: v += m.pTie * (R(i - 1, j) + R(i, j - 1))
                mm[i][j] = v
        self.m = mm
        self.la, self.lh = la, lh
        self.f_ot = 1 - math.exp(-(a + b) * m.ot)             # P(OT goal | tie)
        self.h_ot = b / (a + b)                                 # P(home scores it | goal)
        self.h_tie = self.f_ot * self.h_ot + (1 - self.f_ot) * m.so   # P(home wins | tied after regulation)
        ra = sum(mm[i][j] for i in range(n) for j in range(n) if i > j)
        rh = sum(mm[i][j] for i in range(n) for j in range(n) if j > i)
        tie = sum(mm[i][i] for i in range(n))
        self.ml_away = ra + tie * (1 - self.h_tie)
        self.ml_home = rh + tie * self.h_tie

    def team_over(self, line: float, side: str) -> float:
        """P(team's official final goals > line); side 'a' or 'h'. The OT/SO winner is credited one goal."""
        n, m, k = self.n, self.m, int(line + 0.5)
        if side == "a":
            p = sum(m[i][j] for i in range(n) for j in range(n) if i >= k); t = m[k - 1][k - 1] * (1 - self.h_tie)
        else:
            p = sum(m[i][j] for i in range(n) for j in range(n) if j >= k); t = m[k - 1][k - 1] * self.h_tie
        return p + t

    def total_over(self, line: float) -> float:
        n, m = self.n, self.m
        p = sum(m[i][j] for i in range(n) for j in range(n) if i + j > line)
        if (line - 0.5) % 2 == 0:                               # a tie at line-0.5 always gets the extra goal
            k = int((line - 0.5) / 2); p += m[k][k]
        return p


def cross_prop_gap(away_line, away_over_p, home_line, home_over_p, total_line, over_p) -> float:
    """Sum of the two team-total implied means minus the game total's (normal approximation to Poisson)."""
    mean = lambda L, p: L + 0.5 + N.inv_cdf(min(max(p, 1e-6), 1 - 1e-6)) * (L + 0.5) ** 0.5
    return mean(away_line, away_over_p) + mean(home_line, home_over_p) - mean(total_line, over_p)

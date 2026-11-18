"""NHL rulebook (see the project's betting-rules doc) and bankroll sizing.

evaluate(slate, game) applies every rule to one game and returns the plays with dollar stakes and the
minimum Novig price for each; size_slate() applies the per-game and nightly caps.

Rule codes: core A B D E X HU; tests C H F G2 BB GU LR OD UU XM (XMB when priced off the books) RF; shadow XU.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .nhl_model import Model, american, cross_prop_gap, ev, no_vig

RULEBOOK = "nhl-2026-11-18"
CORE_RULES = {"A", "B", "D", "E", "X", "HU"}

# ---- bankroll plan (Nov 18, 2026): $1,000, quarter-Kelly on shrunk rule edges. Tracker units = $10.
BANKROLL = 1000
STAKE = {"E": 20, "XM": 20, "GU": 15, "HU": 15, "X-under": 15, "UU": 10, "BB": 10, "OD": 10, "D": 10,
         "B": 5, "A": 5, "RF": 5, "XMB": 5}
# XMB = XM measured against the books' team totals (Novig team totals are not in the odds feed). XM was found on
# Novig's thin team totals, so the book-priced version is tracked separately at a small stake until it proves itself.
TRACK_ONLY = {"X-over", "C", "H", "F", "LR", "G2", "G1", "G3", "XU", "T"}
MAX_BET, GAME_CAP, NIGHT_CAP = 30, 40, 120
VIG_ALLOW = 0.02          # min Novig price = fair no-vig probability + 2 points


@dataclass
class Game:
    away: str
    home: str
    g_away: str | None
    g_home: str | None
    ml_away: int
    ml_home: int
    total_line: float
    over_price: int
    under_price: int
    away_tts: list                 # [(line, over_price, under_price), ...]
    home_tts: list
    start_et: str = ""
    tt_source: str = "novig"       # 'novig' or 'consensus' (books, no-vig + estimated Novig vig)


@dataclass
class Play:
    market: str                    # 'TT Away' / 'TT Home' / 'Total' / 'ML'
    side: str                      # Over / Under / Home / Away
    point: float | None
    price: int
    rules: list
    fair_p: float                  # no-vig probability of this side (market)
    model_p: float
    stake: float = 0.0
    min_price: int | None = None
    note: str = ""

    @property
    def core(self) -> bool:
        return bool(set(self.rules) & CORE_RULES)

    @property
    def code(self) -> str:
        return ",".join(self.rules)

    @property
    def ev(self) -> float:
        return ev(self.model_p, self.price)


@dataclass
class Result:
    game: Game
    la: float
    lh: float
    prices: object
    plays: list
    notes: list = field(default_factory=list)
    info: dict = field(default_factory=dict)


class Slate:
    """Slate-wide context: ranks and the top-8 goalie set."""

    def __init__(self, model: Model, confirmed: set = frozenset(), b2b: set = frozenset()):
        self.m = model
        self.OR, self.DR, self.GR = model.offense_rank(), model.defense_rank(), model.goalie_rank()
        self.top8 = {n for n, r in self.GR.items() if r <= 8}
        self.confirmed, self.b2b = set(confirmed), set(b2b)


def main_line(tts):
    return min(tts, key=lambda t: abs(no_vig(t[1], t[2]) - 0.5))


def stake(rules, side) -> float:
    tags = [("X-under" if side == "Under" else "X-over") if t == "X" else t for t in rules]
    s = sorted((STAKE.get(t, 0) for t in tags), reverse=True)
    if not s or s[0] == 0:
        return 0.0
    return float(min(MAX_BET, s[0] + 0.5 * sum(x for x in s[1:] if x > 0)))


def evaluate(sl: Slate, g: Game) -> Result:
    m = sl.m
    A, H = g.away, g.home
    TA, TH = main_line(g.away_tts), main_line(g.home_tts)
    la, lh = m.lambdas(A, H, g.g_away, g.g_home); p = m.price(la, lh)
    la0, lh0 = m.lambdas(A, H, None, None); p0 = m.price(la0, lh0)
    nvh = no_vig(g.ml_home, g.ml_away); g22 = no_vig(g.over_price, g.under_price)
    sd = {}
    for k, tm, opp, (L, o, u), lam, gopp, fav in (("a", A, H, TA, la, g.g_home, nvh < .5), ("h", H, A, TH, lh, g.g_away, nvh >= .5)):
        F, F0 = p.team_over(L, k), p0.team_over(L, k)
        sd[k] = dict(tm=tm, opp=opp, L=L, o=o, u=u, lam=lam, gopp=gopp, fav=fav, F=F, G=no_vig(o, u),
                     evO=ev(F, o), evU=ev(1 - F, u), evU0=ev(1 - F0, u), mk="TT Away" if k == "a" else "TT Home")
    a, h = sd["a"], sd["h"]
    gap = cross_prop_gap(a["L"], a["G"], h["L"], h["G"], g.total_line, g22)
    F22 = g22 + m.tot_wt * (p.total_over(g.total_line) - g22)
    fair = m.fair_from_market(nvh, g22, g.total_line)
    xmd = {"a": a["G"] - fair.team_over(a["L"], "a"), "h": h["G"] - fair.team_over(h["L"], "h")}
    bets: dict = {}
    notes, uflags = [], set()

    def add(market, side, point, price, rules, fair_p, model_p):
        key = (market, side)
        if key in bets:
            bets[key].rules += [r for r in rules if r not in bets[key].rules]
        else:
            bets[key] = Play(market, side, point, price, list(rules), fair_p, model_p)

    for k, s in sd.items():
        topO = sl.OR.get(s["tm"], 99) <= 10
        gr = sl.GR.get(s["gopp"])
        block = topO and not (gr and gr <= 8)          # no unders on a top-10 offense unless vs a top-8 goalie
        under = lambda rules: add(s["mk"], "Under", s["L"], s["u"], rules, 1 - s["G"], 1 - s["F"])
        over = lambda rules: add(s["mk"], "Over", s["L"], s["o"], rules, s["G"], s["F"])
        ur = []
        if s["G"] - s["F"] >= .04: ur.append("A")
        if s["L"] == 3.5 and 3.25 < s["lam"] <= 3.5: ur.append("B")
        if k == "h" and gap <= .31: ur.append("X")
        hu = k == "h" and nvh < .5
        if ur and s["evU"] <= 0:
            ur = []
        if hu:
            ur.append("HU")
        if ur:
            if block: notes.append(f"{s['tm']} under {ur} blocked: top-10 offense (#{sl.OR[s['tm']]}) vs goalie #{gr}")
            else: under(ur); uflags.add(k)
        orr = []
        if s["L"] == 3.5 and s["lam"] > 3.5: orr.append("D")
        if k == "a" and gap <= .31:
            if g.ml_away < 200: orr.append("X")
            else: notes.append(f"X away over blocked: {A} {g.ml_away:+d}")
        if orr and s["evO"] > 0:
            over(orr)
        tu = []
        if s["tm"] in sl.b2b and s["opp"] not in sl.b2b: tu.append("BB")
        if s["gopp"] in sl.top8 and s["gopp"] in sl.confirmed: tu.append("GU")
        if m.finishing(s["tm"]) >= .6: tu.append("LR")
        if xmd[k] >= .03: tu.append("XM")
        if tu:
            if block: notes.append(f"{s['tm']} under tests {tu} blocked by the offense/goalie filter")
            else: under(tu); uflags.add(k)
        if k == "a" and gap > .31 and not block:
            uflags.add(k); notes.append(f"{s['tm']} XU shadow flag (counts for UU)")
        if topO and gr and gr <= 8 and 11 <= sl.DR.get(s["opp"], 0) <= 22:
            notes.append(f"WATCH {s['tm']} under: top-10 offense vs top-8 goalie behind a middle defense")
        to = []
        if k == "a" and s["L"] == 2.5 and s["lam"] > 3 and s["evO"] > 0: to.append("C")
        if k == "a" and nvh < .5 and s["L"] == 3.5: to.append("RF")
        if xmd[k] <= -.03: to.append("XM")
        if topO and gr and gr >= 9 and sl.DR.get(s["opp"], 0) >= 11 and s["L"] == 3.5: to.append("OD")
        if m.finishing(s["tm"]) <= -.6: to.append("LR")
        if to:
            over(to)
    if g.total_line == 6.5 and la + lh > 6.5:
        add("Total", "Over", g.total_line, g.over_price, ["E"], g22, F22)
    if h["L"] > a["L"] and h["F"] > .45:
        add("ML", "Home", None, g.ml_home, ["H"], nvh, p.ml_home)
    if .60 <= p.ml_home <= .70 and g.ml_home < -200:
        add("ML", "Home", None, g.ml_home, ["F"], nvh, p.ml_home)
    if g.total_line == 5.5 and h["L"] > a["L"]:
        add("Total", "Under", g.total_line, g.under_price, ["G2"], 1 - g22, 1 - F22)
    uu = uflags == {"a", "h"}
    if uu:
        add("Total", "Under", g.total_line, g.under_price, ["UU"], 1 - g22, 1 - F22)

    plays = list(bets.values())
    if g.tt_source != "novig":
        for pl in plays:
            pl.rules = ["XMB" if r == "XM" else r for r in pl.rules]
    # --- conflicts: a test play never leans against a core play; in UU games team-total overs are dropped
    def leans(pl):            # +1 more goals / -1 fewer, per team ('a','h','both')
        if pl.market == "Total": return ("both", 1 if pl.side == "Over" else -1)
        if pl.market.startswith("TT"): return ("a" if pl.market == "TT Away" else "h", 1 if pl.side == "Over" else -1)
        return (None, 0)
    core_dirs = [leans(pl) for pl in plays if pl.core]
    keep = []
    for pl in plays:
        if not pl.core:
            who, d = leans(pl)
            clash = any(d and cd and cd == -d and (w == who or "both" in (w, who)) for w, cd in core_dirs)
            if uu and pl.market.startswith("TT") and pl.side == "Over":
                clash = True
            if uu and pl.market.startswith("TT") and pl.side == "Under" and pl.point == 3.5 and \
                    sd["a" if pl.market == "TT Away" else "h"]["fav"] and "XM" not in pl.rules:
                notes.append(f"UU side preference: skip favorite's 3.5 under {pl.code}"); continue
            if clash:
                notes.append(f"dropped test {pl.market} {pl.side} [{pl.code}]: leans against another play"); continue
        keep.append(pl)
    for pl in keep:
        pl.stake = stake(pl.rules, pl.side)
        pl.min_price = american(min(0.97, pl.fair_p + VIG_ALLOW))
        if pl.market.startswith("TT") and g.tt_source != "novig":
            pl.note = f"team total priced from the books; bet only if Novig is {pl.min_price:+d} or better"
    tot = sum(pl.stake for pl in keep)
    if tot > GAME_CAP:
        for pl in keep:
            pl.stake = round(pl.stake * GAME_CAP / tot, 2)
    info = dict(gap=gap, nv_home=nvh, over_nv=g22, blend_over=F22, xm=xmd, TA=TA, TH=TH,
                OR=(sl.OR.get(A), sl.OR.get(H)), DR=(sl.DR.get(A), sl.DR.get(H)),
                GR=(sl.GR.get(g.g_away), sl.GR.get(g.g_home)))
    return Result(g, la, lh, p, keep, notes, info)


def size_slate(results) -> float:
    """Nightly cap: if the night's stakes exceed NIGHT_CAP, scale every stake down proportionally."""
    day = sum(pl.stake for r in results for pl in r.plays)
    if day > NIGHT_CAP:
        f = NIGHT_CAP / day
        for r in results:
            for pl in r.plays:
                pl.stake = round(pl.stake * f, 2)
        day = NIGHT_CAP
    return day

"""Stale-line scanner: find Novig prices that lag the sharp market.

After every odds pull, for each game that hasn't started, compare Novig's price with Pinnacle's no-vig
fair price on the same market. Novig is an exchange whose prices are set by users, so it is often slow
to follow a sharp move. When Novig gives a side at least STALE_MIN_EDGE (default 3%) more than the fair
price, the row is stored in core.stale_lines. Since 11/20 (S1 v2) the alert pops up only when the gap is a lag:
Pinnacle's fair price for that side rose at least STALE_MIN_SHARP_MOVE (1.5%) since the previous pull and Novig's
price moved less than half as much (set STALE_REQUIRE_MOVE = 0 to alert on any gap):

  STALE NOVIG: Pacers +8.5 at 51.0% · fair 55.2% (Pinnacle +7.5) · edge +4.2% · IND@HOU 7:00 PM

Lines that differ (Novig +8.5 vs Pinnacle +7.5) are converted at about 3% per point for NBA spreads and
2.2% per point for NBA totals, only within 1.5 points. NHL compares identical lines only.

  python -m mpm.stale                 # scan the latest snapshot of each league now
"""
from __future__ import annotations

import datetime as dt
import sys

SLOPE = {("NBA", "spreads"): 0.030, ("NBA", "totals"): 0.022}
MAX_GAP = 1.5


def _pairs(rows):
    """{(game, market, point_key): {side: (point, price, prob)}} for one book."""
    out = {}
    for gid, mk, side, point, price, prob in rows:
        key = (gid, mk, None if mk == "h2h" else abs(float(point)) if mk == "spreads" else float(point))
        out.setdefault(key, {})[side] = (None if point is None else float(point), int(price), float(prob))
    return out


def _fair(pair, side):
    other = {"away": "home", "home": "away", "over": "under", "under": "over"}[side]
    if side not in pair or other not in pair:
        return None
    a, b = pair[side][2], pair[other][2]
    return a / (a + b) if a + b > 0 else None


def _fair_at(sharp_by_game, sp, league, gid, mk, side, point):
    """Pinnacle's no-vig probability for our side at Novig's line (converted within 1.5 points) -> (fair, sharp point)."""
    cands = []
    for s_side, s_point, _ in sharp_by_game.get((gid, mk), []):
        if s_side != side:
            continue
        key = (gid, mk, None if mk == "h2h" else abs(s_point) if mk == "spreads" else s_point)
        f = _fair(sp.get(key, {}), side)
        if f is None:
            continue
        if mk == "h2h" or s_point == point:
            cands.append((f, s_point, 0.0))
            continue
        slope = SLOPE.get((league, mk))
        if slope is None or point is None or abs(point - s_point) > MAX_GAP:
            continue
        # more points for our side = better: spreads +; totals: Over wants a lower line, Under a higher one
        gain = (point - s_point) if mk == "spreads" else (s_point - point if side == "over" else point - s_point)
        cands.append((min(max(f + slope * gain, 0.01), 0.99), s_point, abs(point - s_point)))
    if not cands:
        return None
    f, s_point, _ = min(cands, key=lambda c: c[2])
    return f, s_point


def scan(db, snapshot_id: int, league: str, min_edge: float | None = None, notify: bool = True, now=None) -> list[str]:
    min_edge = float(db.config("STALE_MIN_EDGE", "0.03")) if min_edge is None else min_edge
    sharp = db.config("STALE_SHARP_BOOK", "pinnacle")
    require_move = db.config("STALE_REQUIRE_MOVE", "1") not in ("0", "no", "false")
    min_move = float(db.config("STALE_MIN_SHARP_MOVE", "0.015"))
    now = now or dt.datetime.utcnow()
    q = ("SELECT o.game_id, o.market, o.side, o.point, o.price_american, o.implied_prob FROM core.odds o "
         "JOIN core.games g ON g.game_id = o.game_id WHERE o.snapshot_id=? AND o.bookmaker=? AND o.market IN ('h2h','spreads','totals') "
         "AND (g.start_utc IS NULL OR g.start_utc > ?)")
    nv = db.q(q, (snapshot_id, "novig", now.isoformat(sep=" ")[:19]))
    sh = db.q(q, (snapshot_id, sharp, now.isoformat(sep=" ")[:19]))
    if not nv or not sh:
        return []
    sharp_by_game = {}
    for gid, mk, side, point, price, prob in sh:
        sharp_by_game.setdefault((gid, mk), []).append((side, None if point is None else float(point), float(prob)))
    sp = _pairs(sh)
    prev = db.one("SELECT MAX(snapshot_id) FROM core.odds_snapshots WHERE league=? AND snapshot_id<?", (league, snapshot_id))
    prev_id = prev[0] if prev else None
    games = {r[0]: r[1:] for r in db.q("SELECT game_id, away_code, home_code, start_utc FROM core.games WHERE game_id IN "
                                        f"({','.join(str(int(g)) for g in {r[0] for r in nv})})")}
    out = []
    for gid, mk, side, point, price, prob in nv:
        point = None if point is None else float(point)
        got = _fair_at(sharp_by_game, sp, league, gid, mk, side, point)
        if got is None:
            continue
        fair, s_point = got
        edge = fair - float(prob)
        if edge < min_edge:
            continue
        sharp_move = novig_move = None
        if prev_id:
            pr = db.one("SELECT implied_prob FROM core.odds WHERE snapshot_id=? AND game_id=? AND bookmaker='novig' AND market=? "
                        "AND side=? AND COALESCE(point, -999)=COALESCE(?, -999)", (prev_id, gid, mk, side, point))
            novig_move = float(prob) - float(pr[0]) if pr else None
            ps = db.q("SELECT game_id, market, side, point, price_american, implied_prob FROM core.odds "
                      "WHERE snapshot_id=? AND bookmaker=? AND game_id=? AND market=?", (prev_id, sharp, gid, mk))
            pg = {}
            for g2, m2, s2, p2, _, pb in ps:
                pg.setdefault((g2, m2), []).append((s2, None if p2 is None else float(p2), float(pb)))
            before = _fair_at(pg, _pairs(ps), league, gid, mk, side, point)
            sharp_move = None if before is None else round(fair - before[0], 4)
        # S1 v2 (11/20): alert only when Pinnacle moved toward our side since the last pull and Novig did not follow.
        # A gap with no Pinnacle move is usually Novig reacting to news first (2025-26 at 6:30 PM: such gaps went 3-15).
        lagging = (not require_move) or (sharp_move is not None and sharp_move >= min_move
                                         and novig_move is not None and novig_move <= sharp_move / 2)
        seen = db.one("SELECT MAX(edge) FROM core.stale_lines WHERE game_id=? AND market=? AND side=? AND alerted=1 "
                      "AND COALESCE(novig_point, -999)=COALESCE(?, -999)", (gid, mk, side, point))
        first = lagging and (not seen or seen[0] is None or edge >= float(seen[0]) + 0.02)   # new, or 2% better than last alert
        db.x("INSERT INTO core.stale_lines (snapshot_id, game_id, market, side, novig_point, novig_price, novig_prob, sharp_point, "
             "fair_prob, edge, sharp_move, novig_move, alerted) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
             (snapshot_id, gid, mk, side, point, int(price), round(float(prob), 4), s_point, round(fair, 4), round(edge, 4),
              sharp_move, None if novig_move is None else round(novig_move, 4), 1 if first else 0))
        if first:
            aw, hm, start = games.get(gid, ("?", "?", None))
            team = aw if side == "away" else hm if side == "home" else side.capitalize()
            what = (f"{team} ML" if mk == "h2h" else f"{team} {point:+g}" if mk == "spreads" else f"{team} {point:g}")
            ref = "" if mk == "h2h" or s_point == point else f" (Pinnacle {s_point:+g})" if mk == "spreads" else f" (Pinnacle {s_point:g})"
            tip = ""
            if start:
                st = start if isinstance(start, dt.datetime) else dt.datetime.fromisoformat(str(start))
                from zoneinfo import ZoneInfo
                tip = " · " + st.replace(tzinfo=dt.timezone.utc).astimezone(ZoneInfo("America/New_York")).strftime("%I:%M %p").lstrip("0")
            mv = "" if sharp_move is None else f" · Pinnacle moved {sharp_move:+.1%}, Novig {(novig_move or 0):+.1%}"
            line = (f"{what} at {float(prob):.1%} on Novig · fair {fair:.1%}{ref} · edge +{edge:.1%}{mv} · {aw}@{hm}{tip}")
            out.append(line)
    for line in out:
        print("STALE NOVIG:", line)
        if notify:
            from .watch import toast, _log
            _log("STALE NOVIG: " + line)
            toast("MaverickPicks: stale Novig line", line)
    if not out:
        print(f"{league} stale scan: nothing at {min_edge:.0%}+")
    return out


def main(argv=None):
    from .db import session
    with session() as db:
        for lg in ("NBA", "NHL"):
            r = db.one("SELECT MAX(snapshot_id) FROM core.odds_snapshots WHERE league=?", (lg,))
            if r and r[0]:
                scan(db, int(r[0]), lg)


if __name__ == "__main__":
    sys.exit(main())

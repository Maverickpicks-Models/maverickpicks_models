"""Phase 2: past seasons - results from NBA.com and bet-time / closing odds from TheOddsAPI historical.

  python -m mpm.history games --season 2025-26 --season 2024-25   # team game logs + final scores (free)
  python -m mpm.history estimate --season 2025-26                 # credits it would cost (free)
  python -m mpm.history odds --season 2025-26 --max-credits 7000  # bet-time lines, resumable
  python -m mpm.history odds --season 2025-26 --close             # + a closing snapshot per tip time
  python -m mpm.history status

Historical odds cost 10 credits per market per region: one snapshot of moneyline + spread + total from up to
10 books = 30 credits; the list of that day's events = 1 credit.

Per game day it pulls:
  * events  - 10 AM ET list of the day's games and tip times (1 credit)
  * bet     - 6:30 PM ET, when we bet (30 credits); games that tip before then get
  * early   - one extra snapshot 30 minutes before the earliest early tip (30 credits, weekends/holidays)
  * close   - with --close, 10 minutes before each distinct tip time (30 credits each)
Every snapshot is stored like a live pull (core.odds_snapshots purpose hist_bet / hist_early / hist_close,
pulled_at_utc = the historical timestamp), so the CLV views and the backtest read them the same way.
Done days are logged in core.hist_pulls and skipped on the next run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
SNAP_CREDITS = 30
STATS_URL = "https://stats.nba.com/stats/leaguegamelog"
STATS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com", "Accept": "application/json, text/plain, */*",
    "x-nba-stats-origin": "stats", "x-nba-stats-token": "true", "Accept-Language": "en-US,en;q=0.9",
}
LOG_COLS = ["mins", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "reb", "ast", "stl", "blk", "tov", "pf", "pts", "plus_minus"]
NBA_KEYS = {"mins": "MIN", "fgm": "FGM", "fga": "FGA", "fg3m": "FG3M", "fg3a": "FG3A", "ftm": "FTM", "fta": "FTA", "oreb": "OREB",
            "dreb": "DREB", "reb": "REB", "ast": "AST", "stl": "STL", "blk": "BLK", "tov": "TOV", "pf": "PF", "pts": "PTS",
            "plus_minus": "PLUS_MINUS"}


# ---------------------------------------------------------------- game logs
def fetch_game_log(season: str, season_type: str = "Regular Season", http=None) -> list[dict]:
    import requests
    http = http or requests
    params = dict(Counter=0, DateFrom="", DateTo="", Direction="ASC", LeagueID="00", PlayerOrTeam="T", Season=season,
                  SeasonType=season_type, Sorter="DATE")
    for attempt in range(4):
        try:
            r = http.get(STATS_URL, params=params, headers=STATS_HEADERS, timeout=60)
            if r.status_code == 200:
                rs = r.json()["resultSets"][0]
                return [dict(zip(rs["headers"], row)) for row in rs["rowSet"]]
            print(f"stats.nba.com HTTP {r.status_code}, retrying")
        except Exception as e:                       # stats.nba.com is slow and sometimes drops connections
            print(f"stats.nba.com {type(e).__name__}, retrying")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("stats.nba.com did not answer; try again later (or from another network)")


def _gdate(v) -> dt.date:
    s = str(v)[:10]
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return dt.datetime.strptime(str(v).strip().title(), "%b %d, %Y").date()


def store_game_log(db, season: str, rows: list[dict], league: str = "NBA") -> dict:
    db.x("DELETE FROM nba.team_game_log WHERE season=?", (season,))
    recs, games = [], {}
    for r in rows:
        m = r["MATCHUP"]
        home = " vs. " in m
        team, opp = r["TEAM_ABBREVIATION"], m.split(" vs. " if home else " @ ")[1].strip()
        d = _gdate(r["GAME_DATE"])
        vals = {k: r.get(v) for k, v in NBA_KEYS.items()}
        opp_pts = (vals["pts"] - vals["plus_minus"]) if vals["pts"] is not None and vals["plus_minus"] is not None else None
        recs.append((season, str(r["GAME_ID"]), d.isoformat(), team, opp, 1 if home else 0, r.get("WL"),
                     *[None if vals[c] is None else int(round(float(vals[c]))) for c in LOG_COLS], opp_pts))
        g = games.setdefault(str(r["GAME_ID"]), {"date": d})
        g["home" if home else "away"] = (team, vals["pts"])
    db.many("INSERT INTO nba.team_game_log (season, nba_game_id, game_date, team_code, opp_code, is_home, wl, "
            + ", ".join(LOG_COLS) + ", opp_pts) VALUES (" + ",".join("?" * (7 + len(LOG_COLS) + 1)) + ")", recs)
    n_new = 0
    for g in games.values():
        if "home" not in g or "away" not in g:
            continue
        (a, ap), (h, hp) = g["away"], g["home"]
        row = db.one("SELECT game_id FROM core.games WHERE league=? AND game_date=? AND away_code=? AND home_code=?",
                     (league, g["date"].isoformat(), a, h))
        if row:
            db.x("UPDATE core.games SET away_score=?, home_score=?, status='final' WHERE game_id=?", (ap, hp, row[0]))
        else:
            db.insert_id("core.games", {"league": league, "game_date": g["date"].isoformat(), "away_code": a, "home_code": h,
                                        "away_score": ap, "home_score": hp, "status": "final"}, "game_id")
            n_new += 1
    return {"team_rows": len(recs), "games": len(games), "new_games": n_new}


# ---------------------------------------------------------------- odds
def season_days(db, season: str) -> list[dt.date]:
    return [dt.date.fromisoformat(str(r[0])[:10]) for r in
            db.q("SELECT DISTINCT game_date FROM nba.team_game_log WHERE season=? ORDER BY game_date", (season,))]


def _et(day: dt.date, hh: int, mm: int) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET).astimezone(UTC)


def _iso(t: dt.datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _done(db, league, day, kind, snap):
    return db.one("SELECT 1 FROM core.hist_pulls WHERE league=? AND game_date=? AND kind=? AND snap_utc=?",
                  (league, day.isoformat(), kind, snap.replace(tzinfo=None).isoformat(sep=" ")[:19])) is not None


def _mark(db, league, day, kind, snap, snapshot_id, games, credits):
    db.x("INSERT INTO core.hist_pulls (league, game_date, kind, snap_utc, snapshot_id, games, credits_used) VALUES (?,?,?,?,?,?,?)",
         (league, day.isoformat(), kind, snap.replace(tzinfo=None).isoformat(sep=" ")[:19], snapshot_id, games, credits))


def day_events(db, api, league: str, day: dt.date) -> tuple[list[dict], int]:
    """Events tipping on `day` (ET), from the 10 AM ET historical event list (1 credit), cached in core.games.
    Returns (events, credits used)."""
    from .oddsapi import SPORT
    snap = _et(day, 10, 0)
    cached = db.q("SELECT odds_event_id, start_utc FROM core.games WHERE league=? AND game_date=? AND odds_event_id IS NOT NULL",
                  (league, day.isoformat()))
    if _done(db, league, day, "events", snap) and cached:
        return [{"id": e, "start": (s if isinstance(s, dt.datetime) else dt.datetime.fromisoformat(str(s))).replace(tzinfo=UTC)}
                for e, s in cached], 0
    res = api.get(f"/historical/sports/{SPORT[league]}/events", date=_iso(snap), dateFormat="iso")
    out = []
    from .oddsapi import ensure_game
    for ev in res.get("data", []):
        start = dt.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        if start.astimezone(ET).date() != day:
            continue
        ensure_game(db, league, ev)
        out.append({"id": ev["id"], "start": start})
    _mark(db, league, day, "events", snap, None, len(out), api.last_cost)
    return out, api.last_cost or 0


def snapshot(db, api, league: str, day: dt.date, kind: str, when: dt.datetime, books: str) -> int:
    """One historical snapshot (h2h, spreads, totals) stored like a live pull. Returns credits used."""
    from .oddsapi import SPORT, FEATURED, ensure_game, parse_event
    if _done(db, league, day, kind, when):
        return 0
    res = api.get(f"/historical/sports/{SPORT[league]}/odds", date=_iso(when), bookmakers=books, markets=FEATURED,
                  oddsFormat="american", dateFormat="iso")
    ts = dt.datetime.fromisoformat(res.get("timestamp", _iso(when)).replace("Z", "+00:00"))
    sid = db.insert_id("core.odds_snapshots", {"league": league, "purpose": f"hist_{kind}", "source": "theoddsapi-hist",
                                               "pulled_at_utc": ts.replace(tzinfo=None).isoformat(sep=" ")[:19],
                                               "endpoint": f"/historical/sports/{SPORT[league]}/odds",
                                               "credits_used": api.last_cost, "credits_remaining": api.remaining}, "snapshot_id")
    rows, n = [], 0
    for ev in res.get("data", []):
        start = dt.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        if start.astimezone(ET).date() != day or start <= ts:
            continue                                  # other days, or games already under way
        gid = ensure_game(db, league, ev)
        rows += [(sid, *r) for r in parse_event(db, league, ev, gid)]
        n += 1
    db.many("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, team_code, point, price_american, "
            "implied_prob, book_update_utc) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    _mark(db, league, day, kind, when, sid, n, api.last_cost)
    return api.last_cost or 0


def plan_day(day: dt.date, events: list[dict], close: bool) -> list[tuple[str, dt.datetime]]:
    bet = _et(day, 18, 30)
    plan = [("bet", bet)]
    early = sorted(e["start"] for e in events if e["start"] <= bet)
    if early:
        plan.append(("early", early[0] - dt.timedelta(minutes=30)))
    if close:
        for t in sorted({e["start"] for e in events}):
            plan.append(("close", t - dt.timedelta(minutes=10)))
    return plan


def pull_season(db, api, season: str, league: str = "NBA", max_credits: int = 7000, reserve: int = 5000,
                close: bool = False, books: str | None = None, start: str | None = None) -> dict:
    books = books or db.config("ODDS_BOOKMAKERS", "pinnacle,draftkings,fanduel")
    used, days = 0, 0
    for day in season_days(db, season):
        if start and day < dt.date.fromisoformat(start):
            continue
        if used + SNAP_CREDITS * (3 if close else 2) > max_credits:
            print(f"stopping before {day}: credit cap {max_credits} reached ({used} used)"); break
        if api.remaining is not None and api.remaining - SNAP_CREDITS * 3 < reserve:
            print(f"stopping before {day}: {api.remaining} credits left, keeping {reserve} for the live jobs"); break
        evs, c = day_events(db, api, league, day)
        used += c
        for kind, when in plan_day(day, evs, close):
            used += snapshot(db, api, league, day, kind, when, books)
        db.commit()
        days += 1
        print(f"{day}: {len(evs)} games, {used} credits so far, {api.remaining} left")
    return {"days": days, "credits": used}


def estimate(db, season: str, close: bool) -> str:
    days = season_days(db, season)
    if not days:
        return f"No {season} game log yet: run  python -m mpm.history games --season {season}  first."
    per_day = 1 + SNAP_CREDITS
    early = sum(1 for d in days if d.weekday() >= 5) + 6           # weekends + a few holidays
    tips = 3 if close else 0
    total = len(days) * per_day + early * SNAP_CREDITS + len(days) * tips * SNAP_CREDITS
    return (f"{season}: {len(days)} game days -> about {total:,} credits "
            f"({len(days)} x {per_day} + ~{early} early snapshots x {SNAP_CREDITS}"
            + (f" + {tips} closing snapshots a day" if close else "") + ")")


def status(db) -> str:
    out = []
    for season, n, d0, d1 in db.q("SELECT season, COUNT(DISTINCT nba_game_id), MIN(game_date), MAX(game_date) "
                                  "FROM nba.team_game_log GROUP BY season ORDER BY season"):
        out.append(f"game log {season}: {n} games {d0} to {d1}")
    for kind, n, c, d0, d1 in db.q("SELECT kind, COUNT(*), SUM(credits_used), MIN(game_date), MAX(game_date) "
                                   "FROM core.hist_pulls GROUP BY kind ORDER BY kind"):
        out.append(f"odds {kind}: {n} pulls, {c or 0} credits, {d0} to {d1}")
    return "\n".join(out) or "nothing loaded yet"


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("games"); g.add_argument("--season", action="append", required=True)
    e = sub.add_parser("estimate"); e.add_argument("--season", action="append", required=True); e.add_argument("--close", action="store_true")
    o = sub.add_parser("odds"); o.add_argument("--season", required=True); o.add_argument("--max-credits", type=int, default=7000)
    o.add_argument("--reserve", type=int, default=5000); o.add_argument("--close", action="store_true")
    o.add_argument("--start", help="first date to pull (YYYY-MM-DD)"); o.add_argument("--bookmakers")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    from .db import session
    with session() as db:
        if a.cmd == "games":
            for s in a.season:
                print(s, store_game_log(db, s, fetch_game_log(s)))
                db.commit()
        elif a.cmd == "estimate":
            for s in a.season:
                print(estimate(db, s, a.close))
        elif a.cmd == "odds":
            from .oddsapi import OddsAPI
            print(pull_season(db, OddsAPI(db), a.season, max_credits=a.max_credits, reserve=a.reserve, close=a.close,
                              books=a.bookmakers, start=a.start))
        else:
            print(status(db))


if __name__ == "__main__":
    sys.exit(main())

"""TheOddsAPI pulls -> core.odds_snapshots / core.odds.

Cost rules (TheOddsAPI v4 docs):
  /sports/{sport}/odds              = markets x regions  (h2h,spreads,totals = 3 for the whole slate)
  /sports/{sport}/events/{id}/odds  = unique markets returned x regions (team_totals = 1 per game)
  /sports/{sport}/events            = free
  Up to 10 named bookmakers count as 1 region.

Usage (from the repo root, PowerShell):
  python -m mpm.oddsapi --league NBA --purpose pregame
  python -m mpm.oddsapi --league NHL --purpose close --no-team-totals
  python -m mpm.oddsapi --league NBA --test          # one cheap call: does Novig return team totals?
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

import requests

from . import teams
from .db import DB, connect, session

BASE = "https://api.the-odds-api.com/v4"
SPORT = {"NBA": "basketball_nba", "NHL": "icehockey_nhl"}
ET = ZoneInfo("America/New_York")
FEATURED = "h2h,spreads,totals"


def implied(price: int) -> float:
    return -price / (100 - price) if price < 0 else 100 / (100 + price)


class OddsAPI:
    def __init__(self, db: DB, key: str | None = None, session_=None):
        self.db = db
        self.key = key or db.config("ODDS_API_KEY")
        if not self.key or self.key.startswith("PASTE"):
            raise RuntimeError("Set ODDS_API_KEY in core.config (sql/003_config.sql)")
        self.http = session_ or requests.Session()
        self.last_cost = None
        self.remaining = None

    def get(self, path: str, **params):
        params["apiKey"] = self.key
        r = self.http.get(f"{BASE}{path}", params=params, timeout=30)
        self.last_cost = _int(r.headers.get("x-requests-last"))
        self.remaining = _int(r.headers.get("x-requests-remaining"))
        self.db.x("INSERT INTO core.api_usage (endpoint, http_status, credits_used, credits_remaining) VALUES (?,?,?,?)",
                  (path, r.status_code, self.last_cost, self.remaining))
        if r.status_code != 200:
            raise RuntimeError(f"{path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json()


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
def ensure_game(db: DB, league: str, ev: dict) -> int:
    start = dt.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
    gdate = start.astimezone(ET).date()
    away, home = teams.code(db, league, ev["away_team"]), teams.code(db, league, ev["home_team"])
    row = db.one("SELECT game_id FROM core.games WHERE league=? AND game_date=? AND away_code=? AND home_code=?",
                 (league, gdate.isoformat(), away, home))
    if row:
        db.x("UPDATE core.games SET odds_event_id=?, start_utc=? WHERE game_id=?",
             (ev["id"], start.replace(tzinfo=None).isoformat(sep=" "), row[0]))
        return int(row[0])
    return db.insert_id("core.games", {"league": league, "game_date": gdate.isoformat(),
                                       "start_utc": start.replace(tzinfo=None).isoformat(sep=" "),
                                       "away_code": away, "home_code": home, "odds_event_id": ev["id"]}, "game_id")


def parse_event(db: DB, league: str, ev: dict, game_id: int):
    """Yield core.odds rows (without snapshot_id) for one event payload."""
    away, home = ev["away_team"], ev["home_team"]
    for bk in ev.get("bookmakers", []):
        for m in bk.get("markets", []):
            mk = m["key"]
            upd = (m.get("last_update") or bk.get("last_update") or "").replace("Z", "").replace("T", " ")[:19] or None
            for o in m.get("outcomes", []):
                name, price, point = o.get("name"), o.get("price"), o.get("point")
                if price is None:
                    continue
                price = int(round(price))
                team_code = None
                if mk in ("h2h", "spreads"):
                    side = "away" if name == away else "home" if name == home else None
                elif mk == "totals":
                    side = (name or "").lower()
                elif mk == "team_totals":
                    side = (name or "").lower()
                    desc = o.get("description") or ""
                    team_code = teams.code(db, league, desc) if desc else None
                else:
                    continue
                if side not in ("away", "home", "over", "under"):
                    continue
                yield (game_id, bk["key"], mk, side, team_code, point, price, round(implied(price), 5), upd)


def pull(db: DB, api: OddsAPI, league: str, purpose: str, team_totals: bool = True,
         bookmakers: str | None = None) -> int:
    sport = SPORT[league]
    books = bookmakers or db.config("ODDS_BOOKMAKERS", "novig")
    snap = db.insert_id("core.odds_snapshots", {"league": league, "purpose": purpose, "source": "theoddsapi",
                                                "endpoint": f"/sports/{sport}/odds"}, "snapshot_id")
    events = api.get(f"/sports/{sport}/odds", bookmakers=books, markets=FEATURED, oddsFormat="american", dateFormat="iso")
    used = api.last_cost or 0
    rows = []
    today_et = dt.datetime.now(ET).date()
    for ev in events:
        gid = ensure_game(db, league, ev)
        rows += [(snap, *r) for r in parse_event(db, league, ev, gid)]
        start_et = dt.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).astimezone(ET)
        if team_totals and start_et.date() == today_et:
            evo = api.get(f"/sports/{sport}/events/{ev['id']}/odds", bookmakers=books, markets="team_totals",
                          oddsFormat="american", dateFormat="iso")
            used += api.last_cost or 0
            rows += [(snap, *r) for r in parse_event(db, league, evo, gid)]
    db.many("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, team_code, point, price_american, "
            "implied_prob, book_update_utc) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    db.x("UPDATE core.odds_snapshots SET credits_used=?, credits_remaining=? WHERE snapshot_id=?",
         (used, api.remaining, snap))
    print(f"{league} {purpose}: {len(events)} events, {len(rows)} prices, {used} credits used, {api.remaining} remaining")
    return snap


def pull_closing(db: DB, api: OddsAPI, league: str, window_min: int = 20, team_totals: bool = True,
                 bookmakers: str | None = None) -> int | None:
    """Closing snapshot: only games tipping within `window_min` minutes, one per-event call each
    (markets h2h,spreads,totals[,team_totals] = 3-4 credits per game). Run every 10-15 minutes in the evening;
    games already captured for 'close' are skipped."""
    sport = SPORT[league]
    books = bookmakers or db.config("ODDS_BOOKMAKERS", "novig")
    now = dt.datetime.now(dt.timezone.utc)
    evs = api.get(f"/sports/{sport}/events", dateFormat="iso")          # free
    soon = []
    for ev in evs:
        start = dt.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        if 0 <= (start - now).total_seconds() <= window_min * 60:
            gid = ensure_game(db, league, ev)
            done = db.one("SELECT 1 FROM core.odds o JOIN core.odds_snapshots s ON s.snapshot_id=o.snapshot_id "
                          "WHERE s.purpose='close' AND o.game_id=?", (gid,))
            if not done:
                soon.append((ev, gid))
    if not soon:
        print(f"{league} close: no games tipping in the next {window_min} min")
        return None
    snap = db.insert_id("core.odds_snapshots", {"league": league, "purpose": "close", "source": "theoddsapi",
                                                "endpoint": f"/sports/{sport}/events/{{id}}/odds"}, "snapshot_id")
    mkts = FEATURED + (",team_totals" if team_totals else "")
    rows, used = [], 0
    for ev, gid in soon:
        evo = api.get(f"/sports/{sport}/events/{ev['id']}/odds", bookmakers=books, markets=mkts,
                      oddsFormat="american", dateFormat="iso")
        used += api.last_cost or 0
        rows += [(snap, *r) for r in parse_event(db, league, evo, gid)]
    db.many("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, team_code, point, price_american, "
            "implied_prob, book_update_utc) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    db.x("UPDATE core.odds_snapshots SET credits_used=?, credits_remaining=? WHERE snapshot_id=?", (used, api.remaining, snap))
    print(f"{league} close: {len(soon)} games, {len(rows)} prices, {used} credits, {api.remaining} remaining")
    return snap


def test_call(db: DB, api: OddsAPI, league: str):
    """Cheap check (<=2 credits): list events (free), then ONE game with moneyline + team totals from
    every configured book, so we can see which books (Novig included) carry each market."""
    sport = SPORT[league]
    evs = api.get(f"/sports/{sport}/events", dateFormat="iso")
    print(f"{len(evs)} upcoming {league} events (free call). Remaining credits: {api.remaining}")
    if not evs:
        return
    ev = evs[0]
    books = db.config("ODDS_BOOKMAKERS", "novig")
    out = api.get(f"/sports/{sport}/events/{ev['id']}/odds", bookmakers=books, markets="h2h,team_totals",
                  oddsFormat="american", dateFormat="iso")
    print(f"{ev['away_team']} @ {ev['home_team']} (tip {ev['commence_time']}): cost {api.last_cost}; remaining {api.remaining}")
    got = {b["key"]: [m["key"] for m in b.get("markets", [])] for b in out.get("bookmakers", [])}
    for bk in books.split(","):
        print(f"  {bk:15s} {', '.join(got.get(bk, [])) or '-'}")
    nv = next((b for b in out.get("bookmakers", []) if b["key"] == "novig"), None)
    if nv:
        print(json.dumps(nv, indent=1)[:1200])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", choices=SPORT, required=True)
    ap.add_argument("--purpose", default="pregame")
    ap.add_argument("--no-team-totals", action="store_true")
    ap.add_argument("--bookmakers")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--close-window", type=int, help="closing snapshot for games tipping within N minutes")
    a = ap.parse_args(argv)
    with session() as db:
        api = OddsAPI(db)
        tt = not a.no_team_totals and db.config("ODDS_TEAM_TOTALS", "1") == "1"
        if a.test:
            test_call(db, api, a.league)
        elif a.close_window:
            pull_closing(db, api, a.league, a.close_window, team_totals=tt, bookmakers=a.bookmakers)
        else:
            pull(db, api, a.league, a.purpose, team_totals=tt, bookmakers=a.bookmakers)


if __name__ == "__main__":
    sys.exit(main())

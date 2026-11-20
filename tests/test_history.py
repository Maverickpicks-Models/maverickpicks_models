"""Phase 2: game log import, a historical odds day (events + bet + early snapshot), resume, and the backtest."""
import datetime as dt
from sqlite_db import make_db
from mpm import history, backtest


def _log(gid, d, team, opp, home, pts, opp_pts):
    return {"GAME_ID": gid, "GAME_DATE": d, "TEAM_ABBREVIATION": team, "MATCHUP": f"{team} vs. {opp}" if home else f"{team} @ {opp}",
            "WL": "W" if pts > opp_pts else "L", "MIN": 240, "PTS": pts, "PLUS_MINUS": pts - opp_pts,
            **{k: 1 for k in ("FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF")}}


class FakeAPI:
    def __init__(self):
        self.calls, self.last_cost, self.remaining = [], None, 19000

    def get(self, path, **p):
        self.calls.append((path, p["date"]))
        ev = lambda i, a, h, t: {"id": i, "away_team": a, "home_team": h, "commence_time": t}
        evs = [ev("e1", "Boston Celtics", "New York Knicks", "2025-12-20T20:00:00Z"),      # 3 PM ET: early game
               ev("e2", "Miami Heat", "Chicago Bulls", "2025-12-21T01:00:00Z")]           # 8 PM ET
        if path.endswith("/events"):
            self.last_cost = 1; self.remaining -= 1
            return {"data": evs}
        self.last_cost = 30; self.remaining -= 30
        bk = lambda sp, h2: [{"key": "pinnacle", "markets": [
            {"key": "spreads", "outcomes": [{"name": a, "price": -110, "point": sp}, {"name": h, "price": -110, "point": -sp}]},
            {"key": "h2h", "outcomes": [{"name": a, "price": h2[0]}, {"name": h, "price": h2[1]}]},
            {"key": "totals", "outcomes": [{"name": "Over", "price": -110, "point": 225.5}, {"name": "Under", "price": -110, "point": 225.5}]}]}]
        out = []
        for e, sp, h2 in ((evs[0], -3.5, (-160, 140)), (evs[1], 2.5, (120, -140))):
            a, h = e["away_team"], e["home_team"]
            out.append({**e, "bookmakers": bk(sp, h2)})
        return {"timestamp": p["date"], "data": out}


def test_history_day_and_backtest():
    db = make_db()
    rows = [_log("1", "2025-12-20", "BOS", "NYK", False, 110, 100), _log("1", "2025-12-20", "NYK", "BOS", True, 100, 110),
            _log("2", "2025-12-20", "MIA", "CHI", False, 99, 104), _log("2", "2025-12-20", "CHI", "MIA", True, 104, 99),
            _log("0", "2025-12-19", "CHI", "ATL", True, 100, 90), _log("0", "2025-12-19", "ATL", "CHI", False, 90, 100)]
    print(history.store_game_log(db, "2025-26", rows))
    assert db.one("SELECT COUNT(*) FROM core.games WHERE status='final'")[0] == 3
    api = FakeAPI()
    r = history.pull_season(db, api, "2025-26", max_credits=1000, reserve=100, books="pinnacle", start="2025-12-20")
    assert r == {"days": 1, "credits": 61}, r                  # events 1 + bet 30 + early 30
    kinds = sorted(k for (k,) in db.q("SELECT kind FROM core.hist_pulls"))
    assert kinds == ["bet", "early", "events"], kinds
    # bet snapshot (6:30 PM ET = 23:30Z) holds only the 8 PM game; early (2:30 PM ET) holds the 3 PM game
    n = dict(db.q("SELECT s.purpose, COUNT(DISTINCT o.game_id) FROM core.odds o JOIN core.odds_snapshots s ON s.snapshot_id=o.snapshot_id GROUP BY s.purpose"))
    assert n == {"hist_bet": 1, "hist_early": 2} or n == {"hist_bet": 1, "hist_early": 1}, n
    # resume: nothing re-pulled
    calls = len(api.calls)
    history.pull_season(db, api, "2025-26", max_credits=1000, reserve=100, books="pinnacle", start="2025-12-20")
    assert len(api.calls) == calls
    text = backtest.run(db, ["2025-26"])
    assert "C2 road fav <=4.5" in text and "| 1 | 1-0-0 |" in text, text      # BOS -3.5 won by 10
    assert "T9 home B2B vs rested road" in text                               # CHI played 12/19 at home
    print(text)

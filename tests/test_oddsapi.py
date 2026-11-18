import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sqlite_db import make_db
from mpm import oddsapi

class FakeResp:
    def __init__(self, data, cost):
        self._d = data; self.status_code = 200; self.text = json.dumps(data)
        self.headers = {"x-requests-last": str(cost), "x-requests-remaining": "480"}
    def json(self): return self._d

def iso(minutes):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

EV = {"id": "ev1", "sport_key": "basketball_nba", "commence_time": iso(15),
      "home_team": "Toronto Raptors", "away_team": "New York Knicks",
      "bookmakers": [{"key": "novig", "title": "Novig", "last_update": "2026-11-17T22:05:00Z", "markets": [
          {"key": "h2h", "outcomes": [{"name": "New York Knicks", "price": -127}, {"name": "Toronto Raptors", "price": 104}]},
          {"key": "spreads", "outcomes": [{"name": "New York Knicks", "price": -102, "point": -2.5}, {"name": "Toronto Raptors", "price": -102, "point": 2.5}]},
          {"key": "totals", "outcomes": [{"name": "Over", "price": 100, "point": 215.5}, {"name": "Under", "price": -102, "point": 215.5}]}]}]}
TT = {"id": "ev1", "home_team": "Toronto Raptors", "away_team": "New York Knicks", "commence_time": EV["commence_time"],
      "bookmakers": [{"key": "novig", "markets": [{"key": "team_totals", "outcomes": [
          {"name": "Over", "description": "New York Knicks", "price": -113, "point": 108.5},
          {"name": "Under", "description": "New York Knicks", "price": 104, "point": 108.5}]}]}]}

class FakeHTTP:
    def __init__(self): self.calls = []
    def get(self, url, params, timeout):
        self.calls.append((url, dict(params)))
        if url.endswith("/odds") and "/events/" in url:
            return FakeResp(TT if params["markets"] == "team_totals" else {**EV, "bookmakers": EV["bookmakers"] + TT["bookmakers"]}, 1 if params["markets"] == "team_totals" else 4)
        if url.endswith("/events"):
            return FakeResp([{k: EV[k] for k in ("id", "commence_time", "home_team", "away_team")}], 0)
        return FakeResp([EV], 3)

def test_pull_and_close():
    db = make_db()
    db.x("INSERT INTO core.config VALUES ('ODDS_API_KEY','k',1,NULL)")
    db.x("INSERT INTO core.config VALUES ('ODDS_BOOKMAKERS','novig',0,NULL)")
    http = FakeHTTP()
    api = oddsapi.OddsAPI(db, session_=http)
    snap = oddsapi.pull(db, api, "NBA", "pregame")
    rows = db.q("SELECT market, side, team_code, point, price_american FROM core.odds WHERE snapshot_id=? ORDER BY market, side", (snap,))
    assert ("h2h", "away", None, None, -127) in rows
    assert ("spreads", "home", None, 2.5, -102) in rows
    assert ("team_totals", "over", "NYK", 108.5, -113) in rows
    assert db.one("SELECT credits_used FROM core.odds_snapshots WHERE snapshot_id=?", (snap,))[0] == 4   # 3 featured + 1 team total
    g = db.one("SELECT league, away_code, home_code, odds_event_id FROM core.games")
    assert g == ("NBA", "NYK", "TOR", "ev1")
    # closing snapshot: game tips in 15 min -> one per-event call; second run skips it
    c1 = oddsapi.pull_closing(db, api, "NBA", window_min=20)
    assert c1 and db.one("SELECT COUNT(*) FROM core.odds WHERE snapshot_id=?", (c1,))[0] == 8
    assert oddsapi.pull_closing(db, api, "NBA", window_min=20) is None
    assert db.one("SELECT COUNT(*) FROM core.api_usage")[0] == len(http.calls)

if __name__ == "__main__":
    test_pull_and_close(); print("test_oddsapi OK")

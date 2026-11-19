"""Novig lags Pinnacle: Pinnacle moves IND from +8.5 to +7.5 (-125) while Novig still has IND +8.5 at 51%."""
import datetime as dt
from sqlite_db import make_db
from mpm import stale
from mpm.oddsapi import implied


def _snap(db, rows):
    sid = db.insert_id("core.odds_snapshots", {"league": "NBA", "purpose": "scan", "source": "t"}, "snapshot_id")
    db.many("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, team_code, point, price_american, implied_prob) "
            "VALUES (?,?,?,?,?,?,?,?,?)", [(sid, 1, b, m, s, None, p, pr, round(implied(pr), 5)) for b, m, s, p, pr in rows])
    return sid


def test_stale_spread_and_ml():
    db = make_db()
    db.x("INSERT INTO core.games (game_id, league, game_date, start_utc, away_code, home_code) VALUES (1,'NBA','2026-11-18','2026-11-19 00:00:00','HOU','IND')")
    now = dt.datetime(2026, 11, 18, 23, 0)
    s1 = _snap(db, [("novig", "spreads", "away", -8.5, -104), ("novig", "spreads", "home", 8.5, -104),
                    ("pinnacle", "spreads", "away", -8.5, -108), ("pinnacle", "spreads", "home", 8.5, -102),
                    ("novig", "h2h", "away", None, -300), ("novig", "h2h", "home", None, 300),
                    ("pinnacle", "h2h", "away", None, -320), ("pinnacle", "h2h", "home", None, 270)])
    assert stale.scan(db, s1, "NBA", notify=False, now=now) == []
    s2 = _snap(db, [("novig", "spreads", "away", -8.5, -104), ("novig", "spreads", "home", 8.5, -104),
                    ("pinnacle", "spreads", "away", -7.5, 105), ("pinnacle", "spreads", "home", 7.5, -125),
                    ("novig", "h2h", "away", None, -300), ("novig", "h2h", "home", None, 300),
                    ("pinnacle", "h2h", "away", None, -250), ("pinnacle", "h2h", "home", None, 215)])
    got = stale.scan(db, s2, "NBA", notify=False, now=now)
    assert any(g.startswith("IND +8.5") and "Pinnacle +7.5" in g for g in got), got
    assert any(g.startswith("IND ML") for g in got), got
    assert not any(g.startswith("HOU") for g in got), got
    # same prices again: stored, but no repeat alert
    s3 = _snap(db, [("novig", "spreads", "home", 8.5, -104), ("novig", "spreads", "away", -8.5, -104),
                    ("pinnacle", "spreads", "away", -7.5, 105), ("pinnacle", "spreads", "home", 7.5, -125)])
    assert stale.scan(db, s3, "NBA", notify=False, now=now) == []
    # game started: nothing
    assert stale.scan(db, s2, "NBA", notify=False, now=dt.datetime(2026, 11, 19, 0, 30)) == []

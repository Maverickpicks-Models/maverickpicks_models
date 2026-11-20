"""Rule mining: game log from nba.team_box (fromdb), discovery on one season, frozen list graded on the next."""
import datetime as dt
import json
import os
import random
from sqlite_db import make_db
from mpm import history, mine

TEAMS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]


def _season(db, start, days, rnd):
    """Three games a day; home teams win by 8 +- noise while the line says home -2: 'home' should be found."""
    snap = db.insert_id("core.odds_snapshots", {"league": "NBA", "pulled_at_utc": f"{start.year - 1}-01-01 00:00:00",
                                                 "purpose": "hist_bet", "source": "test"}, "snapshot_id")
    games = []
    for i in range(days):
        d = (start + dt.timedelta(i)).isoformat()
        order = TEAMS[:]; rnd.shuffle(order)
        for a, h in ((order[0], order[1]), (order[2], order[3]), (order[4], order[5])):
            hp = 110 + rnd.randint(0, 8); ap = hp - 8 + rnd.randint(-9, 9)
            if ap == hp:
                ap -= 1
            for t, o, pts, opp, home in ((a, h, ap, hp, False), (h, a, hp, ap, True)):
                mu = f"{t} vs. {o}" if home else f"{t} @ {o}"
                db.x("INSERT INTO nba.team_box (team_code, game_date, matchup, wl, mins, pts, fga, oreb, tov, fta, fg3m, fg3a, plus_minus) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (t, d, mu, "W" if pts > opp else "L", 240, pts, 88, 10, 13, 22, 12, 35, pts - opp))
                db.x("INSERT INTO nba.team_box_adv (team_code, matchup, game_date, mins, off_rtg, def_rtg, pace) VALUES (?,?,?,?,?,?,?)",
                     (t, mu, d, 48, pts, opp, 100))
            games.append((d, a, h))
    return snap, games


def _odds(db, snap, games):
    for d, a, h in games:
        gid = db.one("SELECT game_id FROM core.games WHERE game_date=? AND away_code=? AND home_code=?", (d, a, h))[0]
        for mk, side, pt, pr in (("spreads", "away", 2.0, -110), ("spreads", "home", -2.0, -110), ("h2h", "away", None, 120),
                                 ("h2h", "home", None, -140), ("totals", "over", 220.0, -110), ("totals", "under", 220.0, -110)):
            db.x("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, point, price_american) VALUES (?,?,?,?,?,?,?)",
                 (snap, gid, "pinnacle", mk, side, pt, pr))


def test_mine_discover_and_validate(tmp_path):
    db = make_db(); rnd = random.Random(7)
    s1, g1 = _season(db, dt.date(2025, 12, 10), 40, rnd)      # spans both halves (Oct-Dec / Jan-Apr)
    s2, g2 = _season(db, dt.date(2026, 11, 1), 30, rnd)
    r1 = history.log_from_db(db, "2025-26", "2025-10-01", "2026-06-30")
    r2 = history.log_from_db(db, "2026-27", "2026-10-01", "2027-06-30")
    assert r1["games"] == 120 and r2["games"] == 90, (r1, r2)
    assert db.one("SELECT COUNT(*) FROM core.games WHERE status='final'")[0] == 210
    _odds(db, s1, g1); _odds(db, s2, g2)
    mine.MIN_N, mine.MIN_Z = 20, 2.0
    text = mine.run(db, "2025-26", "2026-27", str(tmp_path), min_gp=4)
    print(text)
    frozen = json.load(open(next(os.path.join(tmp_path, f) for f in os.listdir(tmp_path) if f.endswith(".json"))))
    # planted edge found on discovery (home teams are always the favorite here, so "home" and "fav" are the same
    # bets and the duplicate filter keeps one of them) ...
    found = [k for k in frozen["rules"] if k in ("spreads:any when home=yes", "spreads:any when fav=yes")]
    assert len(found) == 1, frozen["rules"].keys()
    row = next(l for l in text.splitlines() if l.startswith(f"| {found[0]} |"))
    assert float(row.split("|")[-2].strip().rstrip("%")) > 0              # ... and it holds on the validation season
    assert not any("home=no" in k or "fav=no" in k for k in frozen["rules"])

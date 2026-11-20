"""Phase 3 model: ratings, luck removal and projection on a tiny synthetic season."""
import datetime as dt
from sqlite_db import make_db
from mpm import model


def _add(db, t, opp, d, home, o, dr, pace, f3m, f3a):
    mu = f"{t} vs. {opp}" if home else f"{t} @ {opp}"
    db.x("INSERT INTO nba.team_box (team_code, game_date, matchup, fga, oreb, tov, fta, fg3m, fg3a) VALUES (?,?,?,?,?,?,?,?,?)",
         (t, d, mu, 88, 10, 13, 22, f3m, f3a))
    db.x("INSERT INTO nba.team_box_adv (team_code, matchup, game_date, mins, off_rtg, def_rtg, pace) VALUES (?,?,?,?,?,?,?)",
         (t, mu, d, 48, o, dr, pace))


def test_project():
    db = make_db()
    for i in range(3):
        d = f"2025-11-0{i + 1}"
        _add(db, "AAA", "BBB", d, True, 120, 110, 100, 12, 35)
        _add(db, "BBB", "AAA", d, False, 110, 120, 100, 12, 35)
    st = model.SeasonState(db, "2025-10-01", "2026-04-30")
    day = dt.date(2025, 11, 5)
    lg = st.league(day)
    assert abs(lg["base"] - 115) < 1e-9 and abs(lg["p3"] - 12 / 35) < 1e-9
    a = st.team("AAA", day)
    assert a["gp"] == 3 and abs(a["o"] - 120) < 1e-6          # 3P% equals the league's, so no luck adjustment
    p = model.project(st, "BBB", "AAA", day)                  # AAA at home: 120+120-115 = 125 vs 105, +-1 home court
    assert abs(p["hp"] - 126) < 1e-6 and abs(p["ap"] - 104) < 1e-6
    p2 = model.project(st, "BBB", "AAA", day, home_b2b=True)
    assert abs((p2["ap"] - p2["hp"]) - (p["ap"] - p["hp"]) - 2.5) < 1e-6
    assert st.team("AAA", dt.date(2025, 11, 1)) is None        # nothing before the first game

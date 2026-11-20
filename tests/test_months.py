"""Month-by-month report runs end to end on a synthetic two-season database (with Novig prices for section F)."""
import datetime as dt
import random
from sqlite_db import make_db
from mpm import history, months
from test_mine import _season, _odds, TEAMS


def test_months_report(tmp_path):
    db = make_db(); rnd = random.Random(5)
    for i, t in enumerate(TEAMS):
        db.x("INSERT INTO core.teams VALUES ('NBA',?,?,?,?,?,?)", (t, t, 30 + i * 2, -120 + i * 8, -8 + i // 2, 5280 if t == "AAA" else 100))
    s1, g1 = _season(db, dt.date(2025, 11, 1), 70, rnd)
    s2, g2 = _season(db, dt.date(2026, 10, 25), 25, rnd)
    history.log_from_db(db, "2025-26", "2025-10-01", "2026-06-30")
    history.log_from_db(db, "2026-27", "2026-10-01", "2027-06-30")
    _odds(db, s1, g1); _odds(db, s2, g2)
    for d, a, h in g1[:60]:           # Novig a little off Pinnacle on some games
        gid = db.one("SELECT game_id FROM core.games WHERE game_date=? AND away_code=? AND home_code=?", (d, a, h))[0]
        for side, pt, pr in (("away", 2.0, 115), ("home", -2.0, -135)):
            db.x("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, point, price_american) VALUES (?,?,?,?,?,?,?)",
                 (s1, gid, "novig", "spreads", side, pt, pr))
    assert months.month_order(["Jan 26", "Oct 26", "Nov 25", "Dec 25"]) == ["Nov 25", "Dec 25", "Jan 26", "Oct 26"]
    text = months.run(db, ["2025-26", "2026-27"], str(tmp_path))
    print(text[:6000])
    for part in ("## A. The market by month", "## B. Our rules", "### Held in both seasons", "## D.", "## E. Teams", "## F. Novig"):
        assert part in text, part
    assert "| Nov 25 |" in text or "Nov 25 |" in text
    assert "Novig 3%+ under Pinnacle fair (spreads)" in text
    assert "spreads:any when fav=yes" in text or "spreads:any when home=yes" in text

"""Replays 11/18: Cade Cunningham went Questionable (6:30 PM report) -> Out, with a Pistons bet on the watch list."""
import datetime as dt, os
from sqlite_db import make_db
from mpm import injuries, watch

FX = os.path.join(os.path.dirname(__file__), "fixtures")


def test_cunningham_alert():
    db = make_db()
    db.many("INSERT INTO nba.player_box (player, team_code, game_date, mins) VALUES (?,?,?,?)",
            [("Cade Cunningham", "DET", "2026-11-10", 37.0), ("Isaiah Joe", "DET", "2026-11-10", 12.0)])
    watch.set_list(db, "2026-11-18", ["DET@NOP|Pistons -4.5 ($13)|8:05PM", "WAS@TOR|Raptors -4.5 ($13)|7:35PM"])
    injuries.store(db, os.path.join(FX, "Injury-Report_2026-11-18_06_30PM.pdf"))
    rid = db.one("SELECT report_id FROM core.injury_reports WHERE report_time_et LIKE '%20:15%'")
    assert rid is None
    db.x("DELETE FROM core.injury_alerts")
    injuries_store = injuries.store
    # load the 8:15 report but pretend it is 7:40 PM (before the 8:05 tip, after WAS@TOR's 7:35 tip)
    real_check = watch.check
    got = []
    watch_check = lambda d, r, lg="NBA": got.extend(real_check(d, r, lg, now=dt.datetime(2026, 11, 18, 19, 40), notify=False))
    import mpm.watch as mw
    mw.check, saved = watch_check, mw.check
    try:
        injuries_store(db, os.path.join(FX, "Injury-Report_2026-11-18_08_15PM.pdf"))
    finally:
        mw.check = saved
    assert any("Cade Cunningham" in g and "OUT" in g and "Pistons -4.5" in g for g in got), got
    assert not any("Isaiah Joe" in g for g in got)            # 12 mpg, below the 20-minute cutoff
    assert not any("WAS@TOR" in g for g in got)               # that game had already tipped
    # same report again: no duplicate alert
    again = real_check(db, None, now=dt.datetime(2026, 11, 18, 19, 41), notify=False)
    assert again == [], again


def test_names():
    assert watch._norm("Cunningham, Cade") == watch._norm("Cade Cunningham") == "cade cunningham"
    assert watch._norm("Pippen Jr., Scotty") == "scotty pippen"
    assert watch._time("8:05PM").hour == 20

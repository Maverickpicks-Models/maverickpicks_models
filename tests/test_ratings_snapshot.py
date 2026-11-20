"""Ratings snapshot: header row detection, repeated header rows skipped, L10 dates undone, same-day re-run replaces."""
import datetime as dt, json, openpyxl
from sqlite_db import make_db
from mpm import load_workbook as lw


def _wb():
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Ratings_2026_27"
    ws.append(["#", "Team", "W", "L", "L10", "NRtg", None, "notes"])
    ws.append([1, "San Antonio Spurs", 13, 3, dt.datetime(2026, 9, 1), 11.3, None, "x"])
    p = wb.create_sheet("26-27NBAPlayer")
    p.append(["Rk", "Player", "Team", "MP"]); p.append([1, "Trae Young", "WAS", 560])
    p.append(["Rk", "Player", "Team", "MP"]); p.append([2, "Nique Clifford", "2TM", 300])
    return wb


def test_snapshot():
    db = make_db()
    wb = _wb()
    assert lw.load_ratings(db, wb, dt.date(2026, 11, 20)) == {"Ratings_2026_27": 1, "26-27NBAPlayer": 2}
    lw.load_ratings(db, wb, dt.date(2026, 11, 20))
    assert db.one("SELECT COUNT(*) FROM nba.sheet_rows")[0] == 3
    d = json.loads(db.one("SELECT data FROM nba.sheet_rows WHERE sheet='Ratings_2026_27'")[0])
    assert d["L10"] == "9-1" and d["NRtg"] == 11.3 and "notes" not in d
    assert db.q("SELECT entity, team_code FROM nba.sheet_rows WHERE sheet='26-27NBAPlayer' ORDER BY row_num") == \
        [("Trae Young", "WAS"), ("Nique Clifford", None)]
    lw.load_ratings(db, wb, dt.date(2026, 11, 21))
    assert db.one("SELECT COUNT(DISTINCT snapshot_id) FROM nba.sheet_rows")[0] == 2

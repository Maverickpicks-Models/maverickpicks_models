import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sqlite_db import make_db
from mpm import injuries

PDF = os.path.join(os.path.dirname(__file__), "fixtures", "Injury-Report_2026-11-16_05_30PM.pdf")

def test_parse_and_store():
    t, rows = injuries.parse(PDF)
    assert str(t) == "2026-11-16 17:30:00" and len(rows) == 99
    by = {(r["matchup"], r["player"]): r for r in rows}
    assert by[("HOU@MIA", "Thompson, Amen")]["status"] == "Questionable"
    assert by[("MEM@WAS", "Jackson, GG")]["reason"] == "Injury/Illness - Left 5th Metatarsal Fracture"   # wraps over a page break
    assert by[("ORL@BOS", "Queta, Neemias")]["team"] == "Boston Celtics"
    assert any(r["status"] == "NOT YET SUBMITTED" for r in rows)
    db = make_db(seed_teams=False)
    rid = injuries.store(db, PDF)
    assert db.one("SELECT COUNT(*) FROM core.injury_status WHERE report_id=?", (rid,))[0] == 99
    injuries.store(db, PDF)   # re-load replaces, no duplicates
    assert db.one("SELECT COUNT(*) FROM core.injury_status")[0] == 99

if __name__ == "__main__":
    test_parse_and_store(); print("test_injuries OK")

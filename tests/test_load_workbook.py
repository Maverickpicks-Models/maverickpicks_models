import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sqlite_db import make_db
import openpyxl
from mpm import load_workbook as lw

WB = os.environ.get("MPM_TEST_WORKBOOK")

def test_load_real_workbook():
    if not WB or not os.path.exists(WB):
        print("skip: set MPM_TEST_WORKBOOK to a copy of the workbook"); return
    db = make_db()
    wb = openpyxl.load_workbook(WB, read_only=True, data_only=True)
    s = lw.load_tracking(db, wb["Tracking"])
    b = lw.load_box(db, wb)
    print(s, b)
    n, w, l, units, risk = db.one("SELECT COUNT(*), SUM(result='W'), SUM(result='L'), SUM(profit_units), SUM(units) FROM core.bets WHERE result IS NOT NULL")
    print(f"graded bets {n}: {w}-{l}, {units:+.2f}u, ROI {100*units/risk:+.1f}%")
    assert s["bets"] > 50 and b["nba.team_box"] > 300
    # idempotent
    s2 = lw.load_tracking(db, wb["Tracking"]); assert s2["bets"] == s["bets"]
    assert db.one("SELECT COUNT(*) FROM core.bets")[0] == s["bets"]
    clv = db.q("SELECT price_american, close_price FROM core.bets WHERE close_price IS NOT NULL")
    print("bets with close price:", len(clv))

if __name__ == "__main__":
    test_load_real_workbook(); print("test_load_workbook OK")

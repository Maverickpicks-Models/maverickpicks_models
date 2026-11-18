import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sqlite_db import make_db
import openpyxl
from mpm import nhl_workbook as nw

REAL = os.environ.get("MPM_TEST_WORKBOOK_NHL")
HDR = list(nw.TRACK)


def _row(**kv):
    base = {h: None for h in HDR}
    base.update({"Away λ": 3.0, "Home λ": 3.2, "Away wt": 1, "Home wt": 1, "ML away": 0.45, "ML home": 0.55,
                 "ML away odds": 120, "ML home odds": -140, "Total line": 6.5, "Total proj": 6.2, "Over %": 0.47,
                 "Over odds": 105, "Under odds": -125, "Away PL %": 0.25, "Away −1.5 odds": 230, "Home PL %": 0.33,
                 "Home −1.5 odds": 180, "Away TT line": 2.5, "Away TT over": 0.58, "Away TT Over": -140,
                 "Away TT Under": 115, "Home TT line": 3.5, "Home TT over": 0.44, "Home TT Over": 120,
                 "Home TT Under": -145, "Card": "TT Home Under [HU]", "Away Goalie": "A Goalie", "Home Goalie": "H Goalie"})
    base.update(kv)
    return [base[h] for h in HDR]


def make_workbook(path):
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Tracking"
    for c, h in enumerate(HDR, 1):
        ws.cell(12, c, h)
    d1, d2 = dt.datetime(2026, 11, 9), dt.datetime(2026, 11, 10)
    rows = [
        # shootout game: 2-2 after OT, home wins the shootout -> official 2-3; two bets on it
        _row(**{"Game date": d1, "Away": "New York Islanders", "Home": "San Jose Sharks", "Bet market": "TT Home",
                "Bet side": "Under", "Odds taken": 125, "Units": 0.5, "Away goals": 2, "Home goals": 2, "SO winner": "Home",
                "Grade": "L", "Profit u": -0.5, "Close odds": 118, "Rule": "HU"}),
        _row(**{"Game date": d1, "Away": "New York Islanders", "Home": "San Jose Sharks", "Bet market": "Total",
                "Bet side": "Under", "Odds taken": -125, "Units": 0, "Away goals": 2, "Home goals": 2, "SO winner": "Home",
                "Grade": "W", "Profit u": 0, "Close odds": -130, "Rule": "UU,G2"}),
        # card-only row (no bet)
        _row(**{"Game date": d1, "Away": "Boston Bruins", "Home": "Los Angeles Kings", "Away goals": 3, "Home goals": 1}),
        # own pick, untagged bet, and a typo-looking close
        _row(**{"Game date": d2, "Away": "Dallas Stars", "Home": "Vegas Golden Knights", "Bet market": "ML", "Bet side": "Home",
                "Odds taken": -140, "Units": 2, "Away goals": 4, "Home goals": 3, "Grade": "L", "Profit u": -2,
                "Close odds": 140, "Rule": "Off"}),
        _row(**{"Game date": d2, "Away": "Dallas Stars", "Home": "Vegas Golden Knights", "Bet market": "TT Away",
                "Bet side": "Over", "Odds taken": -140, "Units": 1, "Away goals": 4, "Home goals": 3, "Grade": "W",
                "Profit u": 0.714, "Close odds": -150, "Rule": None}),
    ]
    for i, r in enumerate(rows):
        for c, v in enumerate(r, 1):
            ws.cell(13 + i, c, v)
    t = wb.create_sheet("Data_2026_27")
    t.append(["Team", "Games Played", "Goals For", "Goals Against", "Expected Goals For", "Expected Goals Against",
              "Shot Attempts % (Corsi %)"])
    t.append(["SJS", 20, 60, 70, 55.5, 68.2, 0.47]); t.append(["NYI", 21, 62, 58, 59.1, 61.0, 0.5])
    p = wb.create_sheet("Data_2025_26")
    p.append(["Team", "Games Played", "Goals For"]); p.append(["SJS", 82, 220])
    g = wb.create_sheet("Goalies")
    g.append([None, "Team", "Name", "Games Played", "Goals Against", "Expected Goals Against"])
    g.append([None, "San Jose Sharks", "Yaroslav Askarov", 14, 40, 41.5])
    g.append([None, "Some Old Team", "Unknown Guy", 2, 7, 6.0])
    s = wb.create_sheet("Data")
    s.append(["team", "season", "name", "team2", "position", "situation", "games_played", "xGoalsFor", "goalsFor"])
    s.append(["SJS", 2025, "SJS", "SJS", "Team Level", "all", 82, 210.5, 220])
    s.append(["SJS", 2025, "SJS", "SJS", "Team Level", "5on4", 82, 40.2, 41])
    a = wb.create_sheet("Assumptions")
    a.append(["NHL MODEL ASSUMPTIONS"]); a.append([]); a.append([])
    a.append(["Section", "Setting", "Value", "Unit / choices"])
    a.append(["Blend", "Games to trust current season", "20", "games"])
    a.append([None, "Empty-Net Rate", 0.41, None])
    a.append(["Books", "Sportsbook", "draftkings", "draftkings / caesars"])
    wb.save(path)


def test_synthetic_workbook(tmp_path=None):
    import tempfile
    path = os.path.join(tmp_path or tempfile.mkdtemp(), "nhl.xlsx")
    make_workbook(path)
    db = make_db()
    out = nw.load(db, path, dt.date(2026, 11, 18), verbose=False)
    t = out["tracking"]
    assert (t["rows"], t["games"], t["bets"], t["staked_bets"], t["zero_unit_bets"]) == (5, 3, 4, 3, 1), t
    assert (t["wins"], t["losses"], t["shootouts"], t["untagged"], t["warnings"]) == (2, 2, 1, 1, 1), t
    # official final score credits the shootout winner; the tied score is kept in nhl.game_results
    g = db.one("SELECT g.away_score, g.home_score, g.went_ot, r.reg_ot_away, r.reg_ot_home, r.shootout, r.so_winner "
               "FROM core.games g JOIN nhl.game_results r ON r.game_id=g.game_id WHERE g.home_code='SJS'")
    assert tuple(g) == (2, 3, 1, 2, 2, 1, "home"), g
    codes = sorted(r[0] for r in db.q("SELECT rule_codes FROM core.bets"))
    assert codes == ["HU", "OFF", "UNTAGGED", "UU,G2"], codes
    assert db.one("SELECT point FROM core.bets WHERE market='TT Home'")[0] == 3.5
    assert db.one("SELECT COUNT(*) FROM core.projections")[0] == 3
    assert db.one("SELECT COUNT(*) FROM nhl.projection_detail")[0] == 3
    assert db.one("SELECT COUNT(*) FROM core.odds")[0] == 30          # 10 prices x 3 games
    tt = db.q("SELECT team_code, side, point, price_american FROM core.odds WHERE market='team_totals' AND team_code='SJS'")
    assert sorted(tt) == [("SJS", "over", 3.5, 120), ("SJS", "under", 3.5, -145)]
    # stats tables
    assert out["stats"] == {"team_season 2026": 2, "team_season 2025": 1, "goalie_season": 2,
                            "mp_stat (Data sheet)": 6, "model_settings": 3}, out["stats"]
    assert db.one("SELECT expected_goals_for FROM nhl.team_season WHERE season=2026 AND team_code='NYI'")[0] == 59.1
    assert db.one("SELECT snapshot_date FROM nhl.team_season WHERE season=2025")[0] == "2026-06-30"
    assert db.one("SELECT team_code FROM nhl.goalie_season WHERE goalie='Unknown Guy'")[0] is None
    assert db.one("SELECT value FROM nhl.mp_stat WHERE situation='5on4' AND stat='goalsFor'")[0] == 41
    assert db.one("SELECT value_num FROM nhl.model_settings WHERE setting='Games to trust current season'")[0] == 20
    # idempotent: a second load replaces, a new as-of date adds a current-season snapshot only
    nw.load(db, path, dt.date(2026, 11, 18), verbose=False)
    for table, n in (("core.bets", 4), ("core.games", 3), ("nhl.game_results", 3), ("core.odds", 30),
                     ("core.odds_snapshots", 2), ("core.projections", 3), ("nhl.team_season", 3), ("nhl.mp_stat", 6)):
        assert db.one(f"SELECT COUNT(*) FROM {table}")[0] == n, table
    nw.load(db, path, dt.date(2026, 11, 19), verbose=False)
    assert db.one("SELECT COUNT(*) FROM nhl.team_season")[0] == 5      # 2 + 2 current snapshots, 1 prior
    assert db.one("SELECT COUNT(*) FROM nhl.goalie_season")[0] == 4


def test_rule_codes():
    assert nw.rule_codes("Off") == "OFF"
    assert nw.rule_codes(" HU, GU ") == "HU,GU"
    assert nw.rule_codes("A+B") == "A,B"
    assert nw.rule_codes(None) == "UNTAGGED" and nw.rule_codes("") == "UNTAGGED"
    assert nw.season_of(dt.date(2026, 11, 18)) == 2026 and nw.season_of(dt.date(2027, 4, 1)) == 2026


def test_load_real_workbook():
    if not REAL or not os.path.exists(REAL):
        print("skip: set MPM_TEST_WORKBOOK_NHL to a copy of the NHL workbook"); return
    db = make_db()
    out = nw.load(db, REAL, dt.date(2026, 11, 18))
    print(out)
    n = db.one("SELECT COUNT(*) FROM core.bets")[0]
    assert n == out["tracking"]["bets"] and n > 300
    out2 = nw.load(db, REAL, dt.date(2026, 11, 18), verbose=False)
    assert db.one("SELECT COUNT(*) FROM core.bets")[0] == n
    assert out2["tracking"] == {**out["tracking"]}


if __name__ == "__main__":
    test_rule_codes(); test_synthetic_workbook(); test_load_real_workbook(); print("test_nhl_workbook OK")

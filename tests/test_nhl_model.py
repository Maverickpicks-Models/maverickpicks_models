import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sqlite_db import make_db
from mpm import nhl_workbook as nw, nhl_slate, nhl_card
from mpm.nhl_model import Model, american, no_vig
from mpm.nhl_rules import Game, Slate, evaluate, stake, size_slate

REAL = os.environ.get("MPM_TEST_WORKBOOK_NHL")


def toy_model():
    cur = {"SJS": dict(gp=20, gf=60, ga=70, xgf=55.5, xga=68.2, cf=0.47), "NYI": dict(gp=21, gf=62, ga=58, xgf=59.1, xga=61.0, cf=0.50)}
    pri = {"SJS": dict(gp=82, gf=220, ga=280, xgf=215, xga=275, cf=0.46), "NYI": dict(gp=82, gf=240, ga=240, xgf=235, xga=236, cf=0.49)}
    gs = [dict(name="Yaroslav Askarov", team_code="SJS", gp=14, ga=40, xga=41.5), dict(name="Ilya Sorokin", team_code="NYI", gp=15, ga=30, xga=42.0)]
    return Model(cur, pri, gs)


def test_prices_are_coherent():
    m = toy_model()
    la, lh = m.lambdas("NYI", "SJS", "Ilya Sorokin", "Yaroslav Askarov")
    p = m.price(la, lh)
    assert abs(p.ml_away + p.ml_home - 1) < 1e-3          # 13x13 matrix, same truncation as the workbook
    # over/under at a half-goal line are complementary and decrease with the line
    assert 1 > p.total_over(5.5) > p.total_over(6.5) > 0
    assert p.team_over(2.5, "a") > p.team_over(3.5, "a")
    # solving lambdas from the market reproduces the market
    f = m.fair_from_market(0.55, 0.48, 6.5)
    assert abs(f.ml_home - 0.55) < 1e-4 and abs(f.total_over(6.5) - 0.48) < 1e-4
    assert american(0.6) == -150 and american(0.4) == 150 and abs(no_vig(-110, -110) - 0.5) < 1e-9


def test_stakes():
    assert stake(["HU", "GU"], "Under") == 22.5
    assert stake(["X"], "Over") == 0 and stake(["X"], "Under") == 15
    assert stake(["C"], "Over") == 0 and stake(["E", "XM", "GU"], "Over") == 30


def test_home_dog_under_and_caps():
    m = toy_model(); sl = Slate(m)
    g = Game("NYI", "SJS", "Ilya Sorokin", "Yaroslav Askarov", -150, 130, 6.5, 105, -125,
             [(2.5, -150, 125), (3.5, 140, -170)], [(2.5, 120, -145), (3.5, 230, -300)])
    r = evaluate(sl, g)
    hu = [pl for pl in r.plays if pl.market == "TT Home" and pl.side == "Under"]
    assert hu and "HU" in hu[0].rules and hu[0].stake >= 15 and hu[0].min_price is not None
    assert sum(pl.stake for pl in r.plays) <= 40
    assert size_slate([r] * 5) == 120


def _seed_odds(db, gdate):
    gid = db.insert_id("core.games", {"league": "NHL", "game_date": gdate.isoformat(), "start_utc": f"{gdate.isoformat()} 23:00:00",
                                      "away_code": "NYI", "home_code": "SJS"}, "game_id")
    snap = db.insert_id("core.odds_snapshots", {"league": "NHL", "purpose": "pregame", "source": "theoddsapi"}, "snapshot_id")
    rows = [("novig", "h2h", "away", None, None, -150), ("novig", "h2h", "home", None, None, 130),
            ("novig", "totals", "over", None, 6.5, 105), ("novig", "totals", "under", None, 6.5, -125)]
    for bk, o25, u25 in (("pinnacle", -152, 128), ("draftkings", -160, 130), ("fanduel", -155, 125)):
        rows += [(bk, "team_totals", "over", "NYI", 2.5, o25), (bk, "team_totals", "under", "NYI", 2.5, u25),
                 (bk, "team_totals", "over", "SJS", 2.5, 118), (bk, "team_totals", "under", "SJS", 2.5, -142)]
    db.many("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, team_code, point, price_american, implied_prob) "
            "VALUES (?,?,?,?,?,?,?,?,0.5)", [(snap, gid, *r) for r in rows])
    return gid


def test_slate_from_database(tmp_path=None):
    import tempfile
    from test_nhl_workbook import make_workbook
    d = tmp_path or tempfile.mkdtemp()
    path = os.path.join(d, "nhl.xlsx"); make_workbook(path)
    db = make_db()
    nw.load(db, path, dt.date(2026, 11, 18), verbose=False)
    gdate = dt.date(2026, 11, 19)
    _seed_odds(db, gdate)
    out = nhl_slate.build(db, gdate, ["SJS=Askarov!"])
    r = out["results"][0]
    assert r.game.tt_source == "consensus" and r.game.g_home == "Yaroslav Askarov"
    # consensus uses Pinnacle's no-vig price when Pinnacle has the line
    assert abs(no_vig(*r.game.away_tts[0][1:]) - no_vig(-152, 128)) < 0.02
    rid = nhl_slate.save(db, out, "test")
    assert db.one("SELECT COUNT(*) FROM core.recommendations WHERE run_id=?", (rid,))[0] == len(r.plays) > 0
    html = nhl_card.html_game(r, "THU · NOV 19, 2026", {}, {"NYI": "New York Islanders"})
    assert "PROJECTED GOALS" in html and "bet at" in html
    assert "Tonight's Card" in nhl_card.html_tonight(out["results"], "THU", {})


def test_real_workbook_parity():
    if not REAL or not os.path.exists(REAL):
        print("skip: set MPM_TEST_WORKBOOK_NHL"); return
    import openpyxl
    m = Model.from_workbook(REAL)
    ws = openpyxl.load_workbook(REAL, read_only=True, data_only=True)["Tracking"]
    row = next(ws.iter_rows(min_row=11, max_row=11, values_only=True))
    full = {"boston bruins": "BOS", "los angeles kings": "LAK"}
    away, home = full.get(str(row[1]).lower()), full.get(str(row[2]).lower())
    if away and home:
        la, lh = m.lambdas(away, home, row[33], row[34])
        assert abs(la - row[3]) < 1e-9 and abs(lh - row[4]) < 1e-9, (la, lh, row[3], row[4])
    # database path gives the same model as the workbook path
    db = make_db(); nw.load(db, REAL, dt.date(2026, 11, 18), verbose=False)
    md = Model.from_db(db)
    assert md.K == m.K == 100 and abs(md.lambdas("CGY", "SJS", "Dustin Wolf", "Yaroslav Askarov")[0]
                                      - m.lambdas("CGY", "SJS", "Dustin Wolf", "Yaroslav Askarov")[0]) < 1e-6


if __name__ == "__main__":
    test_prices_are_coherent(); test_stakes(); test_home_dog_under_and_caps(); test_slate_from_database(); test_real_workbook_parity()
    print("test_nhl_model OK")

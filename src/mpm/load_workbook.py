"""Import the Excel model (MaverickPicks_NBA_Simulations.xlsx) into SQL Server.

Loads, idempotently (re-running replaces what it loaded before):
  * Tracking rows 13+  -> core.games (with scores), core.bets (one row per bet, incl. close odds/CLV),
                          legacy projections -> core.model_runs ('excel-legacy') + core.projections
  * TeamBoxAdvanced A:X -> nba.team_box
  * BoxScores A:Z       -> nba.player_box
  * Ratings and stats sheets (Ratings_2026_27, TeamRatings, TeamShooting, PlayerRatings, PlayerDefense,
    26-27NBAPlayer, CraftedNBA) -> one dated snapshot per import in nba.snapshots / nba.sheet_rows
    (each row stored as JSON; re-running on the same day replaces that day's snapshot)

Usage:
  python -m mpm.load_workbook "C:\\path\\MaverickPicks_NBA_Simulations.xlsx"
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys

import openpyxl

from . import teams
from .db import DB, session

TRACK_FIRST_ROW = 13
# 1-based Tracking columns (see the header row 12 of the sheet)
C = dict(date=1, aw=2, hm=3, ap=4, hp=5, ml_away_p=8, ml_away=10, ml_home=11, total=16, total_proj=17, over_p=18,
         over_odds=19, under_odds=20, away_spread=21, away_cover_p=22, away_spr_odds=23, home_spread=24, home_spr_odds=26,
         away_tt=27, home_tt=31, market=36, side=37, odds=38, units=39, away_pts=40, home_pts=41, grade=45,
         profit=46, close=47, rules=49)


def _date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, (int, float)) and v > 40000:
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
    return None


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def game_id(db: DB, league, gdate, away, home, away_pts=None, home_pts=None) -> int:
    row = db.one("SELECT game_id FROM core.games WHERE league=? AND game_date=? AND away_code=? AND home_code=?",
                 (league, gdate.isoformat(), away, home))
    if row:
        gid = int(row[0])
        if away_pts is not None and home_pts is not None:
            db.x("UPDATE core.games SET away_score=?, home_score=?, status='final' WHERE game_id=?", (away_pts, home_pts, gid))
        return gid
    cols = {"league": league, "game_date": gdate.isoformat(), "away_code": away, "home_code": home}
    if away_pts is not None and home_pts is not None:
        cols.update(away_score=away_pts, home_score=home_pts, status="final")
    return db.insert_id("core.games", cols, "game_id")


def bet_point(market, side, r):
    m = (market or "").lower()
    if m == "spread":
        return _num(r[C["away_spread"] - 1]) if side == "Away" else _num(r[C["home_spread"] - 1])
    if m == "total":
        return _num(r[C["total"] - 1])
    if m == "tt away":
        return _num(r[C["away_tt"] - 1])
    if m == "tt home":
        return _num(r[C["home_tt"] - 1])
    return None


def _rules(r) -> str:
    """Tracking column AW ('Rules'), e.g. 'C2+T5'. Empty -> UNTAGGED."""
    v = r[C["rules"] - 1] if len(r) >= C["rules"] else None
    s = str(v).strip().upper().replace(" ", "") if v is not None else ""
    return s.replace(",", "+") or "UNTAGGED"


def load_tracking(db: DB, ws, league="NBA") -> dict:
    db.x("DELETE FROM core.bets WHERE source_row IS NOT NULL AND league=?", (league,))
    run_ids: dict[dt.date, int] = {}
    stats = dict(games=0, bets=0, projections=0)
    seen = set()
    for i, r in enumerate(ws.iter_rows(min_row=TRACK_FIRST_ROW, values_only=True), start=TRACK_FIRST_ROW):
        gdate = _date(r[C["date"] - 1])
        if not gdate or not r[C["aw"] - 1] or not r[C["hm"] - 1]:
            continue
        away, home = teams.code(db, league, r[C["aw"] - 1]), teams.code(db, league, r[C["hm"] - 1])
        apts, hpts = _num(r[C["away_pts"] - 1]), _num(r[C["home_pts"] - 1])
        gid = game_id(db, league, gdate, away, home, apts, hpts)
        key = (gdate, away, home)
        if key not in seen:
            seen.add(key); stats["games"] += 1
            if _num(r[C["ap"] - 1]) is not None:
                if gdate not in run_ids:
                    run_ids[gdate] = _legacy_run(db, league, gdate)
                db.x("DELETE FROM core.projections WHERE run_id=? AND game_id=?", (run_ids[gdate], gid))
                db.x("INSERT INTO core.projections (run_id, game_id, away_pts, home_pts, away_win_p, away_cover_p, over_p) "
                     "VALUES (?,?,?,?,?,?,?)", (run_ids[gdate], gid, _num(r[C["ap"] - 1]), _num(r[C["hp"] - 1]),
                                               _num(r[C["ml_away_p"] - 1]), _num(r[C["away_cover_p"] - 1]), _num(r[C["over_p"] - 1])))
                stats["projections"] += 1
        market, side, odds, units = r[C["market"] - 1], r[C["side"] - 1], _num(r[C["odds"] - 1]), _num(r[C["units"] - 1])
        if market and side and odds is not None and units:
            grade = r[C["grade"] - 1] if r[C["grade"] - 1] in ("W", "L", "P") else None
            db.x("INSERT INTO core.bets (league, game_id, market, side, point, price_american, units, close_price, result, "
                 "profit_units, rule_codes, source_row) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (league, gid, market, side, bet_point(market, side, r), int(odds), float(units),
                  int(r[C["close"] - 1]) if _num(r[C["close"] - 1]) is not None else None, grade,
                  _num(r[C["profit"] - 1]), _rules(r), i))
            stats["bets"] += 1
    return stats


def _legacy_run(db: DB, league, gdate) -> int:
    ver = f"excel-legacy {gdate.isoformat()}"
    row = db.one("SELECT run_id FROM core.model_runs WHERE league=? AND model_version=?", (league, ver))
    if row:
        return int(row[0])
    return db.insert_id("core.model_runs", {"league": league, "model_version": ver, "rulebook": "excel",
                                            "run_at_utc": f"{gdate.isoformat()} 23:00:00"}, "run_id")


TEAM_COLS = ["team_code", "matchup", "game_date", "wl", "mins", "pts", "fgm", "fga", None, "fg3m", "fg3a", None,
             "ftm", "fta", None, "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "pf", "plus_minus"]
PLAYER_COLS = ["player", "team_code", "matchup", "game_date", "wl", "mins", "pts", "fgm", "fga", None, "fg3m", "fg3a", None,
               "ftm", "fta", None, "oreb", "dreb", "reb", "ast", "stl", "blk", "tov", "pf", "plus_minus"]


def _box_rows(ws, cols, first_row=2, ncol=None):
    keep = [(i, c) for i, c in enumerate(cols) if c]
    seen = set()
    for r in ws.iter_rows(min_row=first_row, max_col=ncol or len(cols), values_only=True):
        if not r[0] or not r[1]:
            continue
        rec = {c: r[i] for i, c in keep}
        d = _date(rec["game_date"])
        if not d:
            continue
        rec["game_date"] = d.isoformat()
        k = (rec.get("player"), rec["team_code"], rec["game_date"])
        if k in seen:          # the workbook has had pasted duplicates before
            continue
        seen.add(k)
        yield rec


def load_box(db: DB, wb) -> dict:
    out = {}
    for sheet, table, cols in (("TeamBoxAdvanced", "nba.team_box", TEAM_COLS), ("BoxScores", "nba.player_box", PLAYER_COLS)):
        if sheet not in wb.sheetnames:
            continue
        recs = list(_box_rows(wb[sheet], cols))
        names = [c for c in cols if c]
        db.x(f"DELETE FROM {table}")
        db.many(f"INSERT INTO {table} ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})",
                [tuple(rec[c] for c in names) for rec in recs])
        out[table] = len(recs)
    return out


# sheet -> (header row, entity column header, team column header or None)
RATING_SHEETS = {
    "Ratings_2026_27": (1, "Team", "Team"),
    "TeamRatings":     (5, "Team", "Team"),
    "TeamShooting":    (6, "Team", "Code"),
    "PlayerRatings":   (5, "Player", "BBRef team"),
    "PlayerDefense":   (1, "Name", None),
    "26-27NBAPlayer":  (1, "Player", "Team"),
    "CraftedNBA":      (1, "Matchup", None),
}


def _json_val(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat()[:10] if isinstance(v, dt.datetime) and v.time() == dt.time(0) else v.isoformat()
    if isinstance(v, float) and v != v:
        return None
    return v


def _l10(col, v):
    """Excel turns a pasted L10 record like 9-1 into a date (Sep 1); turn it back into "9-1"."""
    return f"{v.month}-{v.day}" if isinstance(v, (dt.datetime, dt.date)) else _json_val(v)


def _team_or_none(db, league, name):
    if not name or not isinstance(name, str):
        return None
    try:
        return teams.code(db, league, name.strip())
    except KeyError:
        n = name.strip().upper()
        row = db.one("SELECT team_code FROM core.teams WHERE league=? AND team_code=?", (league, n)) if len(n) == 3 else None
        return row[0] if row else None


def load_ratings(db: DB, wb, snap_date: dt.date, source: str = "", league: str = "NBA") -> dict:
    import json
    old = db.one("SELECT snapshot_id FROM nba.snapshots WHERE snapshot_date=?", (snap_date.isoformat(),))
    if old:
        sid = int(old[0])
        db.x("DELETE FROM nba.sheet_rows WHERE snapshot_id=?", (sid,))
    else:
        sid = db.insert_id("nba.snapshots", {"snapshot_date": snap_date.isoformat(), "source_file": source[:400]}, "snapshot_id")
    out = {}
    for sheet, (hrow, ent_col, team_col) in RATING_SHEETS.items():
        if sheet not in wb.sheetnames:
            continue
        rows = wb[sheet].iter_rows(min_row=hrow, values_only=True)
        header = next(rows, None) or ()
        cols, seen = [], {}
        for h in header:                                  # headers up to the first blank one
            if h is None or str(h).strip() == "":
                break
            h = str(h).strip()
            seen[h] = seen.get(h, 0) + 1
            cols.append(h if seen[h] == 1 else f"{h} ({seen[h]})")
        if ent_col not in cols:
            print(f"{sheet}: no '{ent_col}' column in row {hrow}, skipped")
            continue
        ei, ti = cols.index(ent_col), (cols.index(team_col) if team_col in cols else None)
        recs = []
        for i, r in enumerate(rows, start=hrow + 1):
            ent = r[ei] if ei < len(r) else None
            if ent is None or str(ent).strip() == "" or str(ent).strip() == ent_col:   # blank or a repeated header row
                continue
            data = {c: _l10(c, r[j]) if c == "L10" else _json_val(r[j]) for j, c in enumerate(cols) if j < len(r) and r[j] is not None and r[j] != ""}
            tc = _team_or_none(db, league, r[ti]) if ti is not None and ti < len(r) else None
            recs.append((sid, sheet, i, str(ent).strip()[:80], tc, json.dumps(data, ensure_ascii=False, default=str)))
        db.many("INSERT INTO nba.sheet_rows (snapshot_id, sheet, row_num, entity, team_code, data) VALUES (?,?,?,?,?,?)", recs)
        out[sheet] = len(recs)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--league", default="NBA")
    ap.add_argument("--snapshot-date", help="date to file the ratings snapshot under (default: today)")
    ap.add_argument("--no-ratings", action="store_true", help="skip the ratings/stats snapshot")
    a = ap.parse_args(argv)
    wb = openpyxl.load_workbook(a.workbook, read_only=True, data_only=True)
    with session() as db:
        s1 = load_tracking(db, wb["Tracking"], a.league)
        s2 = load_box(db, wb)
        s3 = {} if a.no_ratings else load_ratings(
            db, wb, dt.date.fromisoformat(a.snapshot_date) if a.snapshot_date else dt.date.today(), a.workbook)
    print(f"Tracking: {s1}  Box: {s2}")
    if s3:
        print(f"Ratings snapshot {a.snapshot_date or dt.date.today().isoformat()}: {s3}")


if __name__ == "__main__":
    sys.exit(main())

"""Import the NHL Excel model (MaverickPicks_NHL_Simulations_v2.xlsx) into SQL Server.

Loads, idempotently (re-running replaces what it loaded before):
  * Tracking rows 13+   -> core.games (official final score), nhl.game_results (score before the shootout,
                           shootout winner), core.bets (every bet incl. $0 track-only bets, close odds, rule codes),
                           legacy projections -> core.model_runs ('excel-legacy <date>') + core.projections
                           + nhl.projection_detail, and the bet-time board -> core.odds (source 'excel-tracking')
  * Data_YYYY_YY tables -> nhl.team_season   (MoneyPuck team table; current season kept per --as-of date)
  * Goalies             -> nhl.goalie_season (current season, per --as-of date)
  * Data                -> nhl.mp_stat       (2025-26 MoneyPuck teams.csv by situation)
  * Assumptions         -> nhl.model_settings

Tracking columns are found by their header text in row 12, so inserting a column in the sheet does not break it.

Usage:
  python -m mpm.nhl_workbook "C:\\path\\MaverickPicks_NHL_Simulations_v2.xlsx"
  python -m mpm.nhl_workbook "...xlsx" --as-of 2026-11-18      # date the pasted MoneyPuck tables were taken
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from zoneinfo import ZoneInfo

import openpyxl

from . import teams
from .db import DB, session
from .load_workbook import _date, _legacy_run, _num, game_id

LEAGUE = "NHL"
TRACK_HEADER_ROW = 12
TRACK_FIRST_ROW = 13
ODDS_SOURCE = "excel-tracking"

# Tracking header text -> field name. Every header must be present.
TRACK = {
    "Game date": "date", "Away": "away", "Home": "home", "Away λ": "away_lambda", "Home λ": "home_lambda",
    "Away wt": "away_wt", "Home wt": "home_wt", "ML away": "ml_away_p", "ML home": "ml_home_p",
    "ML away odds": "ml_away_odds", "ML home odds": "ml_home_odds", "ML away edge": "ml_away_edge",
    "ML home edge": "ml_home_edge", "Total line": "total_line", "Total proj": "total_proj", "Over %": "over_p",
    "Over odds": "over_odds", "Under odds": "under_odds", "Away PL %": "away_pl_p", "Away −1.5 odds": "away_pl_odds",
    "Home PL %": "home_pl_p", "Home −1.5 odds": "home_pl_odds", "Away TT line": "away_tt_line",
    "Away TT over": "away_tt_over_p", "Away TT Over": "away_tt_over_odds", "Away TT Under": "away_tt_under_odds",
    "Home TT line": "home_tt_line", "Home TT over": "home_tt_over_p", "Home TT Over": "home_tt_over_odds",
    "Home TT Under": "home_tt_under_odds", "Card": "card", "Away Goalie": "away_goalie", "Home Goalie": "home_goalie",
    "Bet market": "market", "Bet side": "side", "Odds taken": "odds", "Units": "units", "Away goals": "away_goals",
    "Home goals": "home_goals", "SO winner": "so_winner", "Grade": "grade", "Profit u": "profit",
    "Close odds": "close", "Rule": "rule",
}

TEAM_STATS = ['games_played', 'icetime_minutes', 'goals_pct', 'xgoals_pct', 'shot_attempts_pct_corsi_pct', 'unblocked_shot_attempts_pct_fenwick_pct', 'goals_for', 'goals_against', 'goal_differential', 'expected_goals_for', 'expected_goals_against', 'expected_goal_differential', 'goals_for_above_expected', 'goals_against_above_expected', 'goals_differential_above_expected', 'pdo_sh_pct_sv_pct', 'shooting_pct_on_shots_on_goal', 'shooting_pct_on_unblocked_shots', 'shooting_pct_on_all_shot_attempts', 'pct_of_shot_attempts_for_that_are_blocked', 'pct_of_unblocked_shot_attempts_for_that_miss_net', 'expected_pct_of_unblocked_shot_attempts_for_that_miss_net', 'pct_of_net_misses_above_expected', 'save_pct_on_shots_on_goal', 'save_pct_on_unblocked_shots', 'expected_save_pct_on_unblocked_shots', 'save_pct_above_expected_on_unblocked_shots', 'penalty_minutes_taken_per_60', 'penalty_minutes_drawn_per_60', 'share_of_penalty_minutes_taken', 'goals_for_per_60', 'goals_against_per_60_gaa', 'goals_differential_per_60', 'expected_goals_for_per_60', 'expected_goals_against_per_60', 'expected_goal_differential_per_60', 'shots_on_goal_for', 'shots_on_goal_against', 'unblocked_shots_attempts_for', 'unblocked_shots_attempts_against', 'pim_against', 'pim_taken_by_opponents', 'pct_of_pim_taken', 'faceoff_win_pct', 'score_adjusted_expected_goals_pct', 'flurry_adjusted_expected_goals_pct', 'score_and_flurry_adjusted_expected_goals_pct', 'score_adjusted_shot_attempts_pct_corsi_pct', 'score_adjusted_unblocked_shot_attempts_pct_fenwick_pct', 'rebound_shots_for', 'rebound_shots_against', 'rebound_goals_for', 'pct_of_goals_for_from_rebounds', 'rebound_goals_against', 'pct_of_goals_against_from_rebounds', 'high_danger_shots_for', 'medium_danger_shots_for', 'low_danger_shots_for', 'high_danger_shots_against', 'medium_danger_shots_against', 'low_danger_shots_against', 'takeaways_from_opponent', 'takeaways_to_opponent', 'share_of_takeaways', 'giveaways_to_opponent', 'defensive_zone_giveaways_to_opponent', 'pct_of_giveaways_in_defensive_zone', 'shots_blocked', 'hits_given', 'hits_taken', 'pct_of_hits_given']
GOALIE_STATS = ['games_played', 'goals_against', 'expected_goals_against', 'goals_saved_above_expected', 'goals_saved_above_expected_per_60', 'pct_of_expected_goals_saved_above_average', 'save_pct_on_unblocked_shots', 'xsave_pct_on_unblocked_shots', 'save_pct_above_expected', 'save_pct_on_shots_on_goal', 'gaa', 'xgaa', 'gaa_better_than_expected', 'wins_above_replacement', 'icetime_minutes', 'rebounds_per_save', 'puck_freezes_per_save', 'xrebounds_per_save', 'rebounds_above_expected', 'expected_puck_freeze', 'puck_freezes_above_expected', 'puck_freezes_above_expected_per_shot_on_goal', 'goals_against2', 'saves_on_shots_on_goal', 'saves_on_unblocked_shot_attempts', 'pct_of_shot_attempts_blocked_by_teammates', 'pct_of_unblocked_shot_attempts_against_on_goal', 'expected_pct_of_unblocked_shot_attempts_against_on_goal', 'on_goal_pct_above_expected', 'low_danger_unblocked_shot_attempt_save_pct', 'xlow_danger_unblocked_shot_attempt_save_pct', 'low_danger_unblocked_shot_attempt_save_pct_above_expected', 'medium_danger_unblocked_shot_attempt_save_pct', 'xmedium_danger_unblocked_shot_attempt_save_pct', 'medium_danger_unblocked_shot_attemptsave_pct_above_expected', 'high_danger_unblocked_shot_attempt_save_pct', 'xhigh_danger_unblocked_shot_attempt_save_pct', 'high_danger_unblocked_shot_attempt_save_pct_above_expected']

# MoneyPuck CSV text columns (everything else is a numeric stat)
MP_TEXT = {"team", "season", "name", "team2", "position", "situation", "playerid", "teamfullname"}
SUSPECT_CLV = 0.08   # |close - taken| above 8 probability points is almost always a typo


def slug(h: str) -> str:
    s = str(h).strip().replace("%", " pct ").replace("&", " and ").replace("#", " num ")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return re.sub(r"_+", "_", s)


def implied(price) -> float:
    return -price / (100 - price) if price < 0 else 100 / (100 + price)


def season_of(d: dt.date) -> int:
    """MoneyPuck labels a season by its first year (Oct 2026 - Jun 2027 = 2026)."""
    return d.year if d.month >= 8 else d.year - 1


def rule_codes(v) -> str:
    s = str(v).strip() if v is not None else ""
    if not s:
        return "UNTAGGED"
    out = []
    for c in s.replace("+", ",").split(","):
        c = c.strip()
        if c:
            out.append("OFF" if c.lower() == "off" else c)
    return ",".join(out) or "UNTAGGED"


def _int(v):
    n = _num(v)
    if n is None and isinstance(v, str):
        try:
            n = float(v.strip())
        except ValueError:
            n = None
    return int(round(n)) if n is not None else None


def _header_map(ws) -> dict:
    hdr = next(ws.iter_rows(min_row=TRACK_HEADER_ROW, max_row=TRACK_HEADER_ROW, values_only=True))
    pos = {}
    for i, h in enumerate(hdr):
        if h is not None and str(h).strip() in TRACK and TRACK[str(h).strip()] not in pos:
            pos[TRACK[str(h).strip()]] = i
    missing = [h for h, f in TRACK.items() if f not in pos]
    if missing:
        raise ValueError(f"Tracking row {TRACK_HEADER_ROW} is missing headers: {missing}")
    return pos


def bet_point(market: str, f: dict):
    m = (market or "").strip().lower()
    if m == "total":
        return _num(f["total_line"])
    if m == "tt away":
        return _num(f["away_tt_line"])
    if m == "tt home":
        return _num(f["home_tt_line"])
    return None


def _clear_tracking(db: DB):
    db.x("DELETE FROM core.bets WHERE league=? AND source_row IS NOT NULL", (LEAGUE,))
    db.x("DELETE FROM core.odds WHERE snapshot_id IN (SELECT snapshot_id FROM core.odds_snapshots WHERE league=? AND source=?)",
         (LEAGUE, ODDS_SOURCE))
    db.x("DELETE FROM core.odds_snapshots WHERE league=? AND source=?", (LEAGUE, ODDS_SOURCE))
    db.x("DELETE FROM nhl.game_results WHERE source='workbook'")
    db.x("DELETE FROM nhl.projection_detail WHERE run_id IN (SELECT run_id FROM core.model_runs "
         "WHERE league=? AND model_version LIKE 'excel-legacy %')", (LEAGUE,))


def _odds_rows(snap: int, gid: int, away: str, home: str, f: dict):
    """The board the row was priced from (Novig at bet time)."""
    def row(market, side, team, point, price):
        p = _int(price)
        if p is None or p == 0:
            return None
        return (snap, gid, "novig", market, side, team, point, p, round(implied(p), 5), None)
    tl = _num(f["total_line"])
    cand = [row("h2h", "away", None, None, f["ml_away_odds"]), row("h2h", "home", None, None, f["ml_home_odds"]),
            row("totals", "over", None, tl, f["over_odds"]), row("totals", "under", None, tl, f["under_odds"]),
            row("spreads", "away", None, -1.5, f["away_pl_odds"]), row("spreads", "home", None, -1.5, f["home_pl_odds"]),
            row("team_totals", "over", away, _num(f["away_tt_line"]), f["away_tt_over_odds"]),
            row("team_totals", "under", away, _num(f["away_tt_line"]), f["away_tt_under_odds"]),
            row("team_totals", "over", home, _num(f["home_tt_line"]), f["home_tt_over_odds"]),
            row("team_totals", "under", home, _num(f["home_tt_line"]), f["home_tt_under_odds"])]
    return [c for c in cand if c and (c[3] in ("h2h",) or c[6] is not None)]


def load_tracking(db: DB, ws, verbose: bool = True) -> dict:
    pos = _header_map(ws)
    _clear_tracking(db)
    stats = dict(rows=0, games=0, bets=0, staked_bets=0, zero_unit_bets=0, graded=0, wins=0, losses=0,
                 profit_units=0.0, risked_units=0.0, close_odds=0, shootouts=0, projections=0, odds_prices=0,
                 untagged=0, no_cache=0)
    warnings = []
    seen, run_ids, snaps = {}, {}, {}
    odds_rows = []
    for i, r in enumerate(ws.iter_rows(min_row=TRACK_FIRST_ROW, values_only=True), start=TRACK_FIRST_ROW):
        f = {k: (r[p] if p < len(r) else None) for k, p in pos.items()}
        gdate = _date(f["date"])
        if not gdate or not f["away"] or not f["home"]:
            continue
        stats["rows"] += 1
        away, home = teams.code(db, LEAGUE, f["away"]), teams.code(db, LEAGUE, f["home"])
        ag, hg = _int(f["away_goals"]), _int(f["home_goals"])
        so = str(f["so_winner"] or "").strip().lower()
        so = so if so in ("away", "home") else None
        fa = fh = None
        if ag is not None and hg is not None:
            fa, fh = ag + (so == "away"), hg + (so == "home")
        gid = game_id(db, LEAGUE, gdate, away, home, fa, fh)
        key = (gdate, away, home)
        if key not in seen:
            seen[key] = gid
            stats["games"] += 1
            if ag is not None and hg is not None:
                db.x("UPDATE core.games SET went_ot=? WHERE game_id=?", (1 if so else None, gid))
                db.x("INSERT INTO nhl.game_results (game_id, reg_ot_away, reg_ot_home, shootout, so_winner, source) "
                     "VALUES (?,?,?,?,?,'workbook')", (gid, ag, hg, 1 if so else 0, so))
                stats["shootouts"] += 1 if so else 0
            if _num(f["away_lambda"]) is not None:
                if gdate not in run_ids:
                    run_ids[gdate] = _legacy_run(db, LEAGUE, gdate)
                rid = run_ids[gdate]
                db.x("DELETE FROM core.projections WHERE run_id=? AND game_id=?", (rid, gid))
                db.x("INSERT INTO core.projections (run_id, game_id, away_pts, home_pts, away_win_p, away_cover_p, over_p) "
                     "VALUES (?,?,?,?,?,?,?)", (rid, gid, _num(f["away_lambda"]), _num(f["home_lambda"]),
                                                _num(f["ml_away_p"]), _num(f["away_pl_p"]), _num(f["over_p"])))
                db.x("INSERT INTO nhl.projection_detail (run_id, game_id, away_lambda, home_lambda, away_cur_wt, home_cur_wt, "
                     "ml_home_p, ml_away_edge, ml_home_edge, total_line, total_proj, home_pl_p, away_tt_line, away_tt_over_p, "
                     "home_tt_line, home_tt_over_p, away_goalie, home_goalie, card) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (rid, gid, _num(f["away_lambda"]), _num(f["home_lambda"]), _num(f["away_wt"]), _num(f["home_wt"]),
                      _num(f["ml_home_p"]), _num(f["ml_away_edge"]), _num(f["ml_home_edge"]), _num(f["total_line"]),
                      _num(f["total_proj"]), _num(f["home_pl_p"]), _num(f["away_tt_line"]), _num(f["away_tt_over_p"]),
                      _num(f["home_tt_line"]), _num(f["home_tt_over_p"]), f["away_goalie"] or None,
                      f["home_goalie"] or None, (str(f["card"])[:600] if f["card"] else None)))
                stats["projections"] += 1
            if gdate not in snaps:
                snaps[gdate] = db.insert_id("core.odds_snapshots", {
                    "league": LEAGUE, "purpose": "workbook", "source": ODDS_SOURCE,
                    "pulled_at_utc": f"{gdate.isoformat()} 22:00:00", "endpoint": "Tracking sheet"}, "snapshot_id")
            odds_rows += _odds_rows(snaps[gdate], gid, away, home, f)
        market, side, odds, units = f["market"], f["side"], _int(f["odds"]), _num(f["units"])
        if not (market and side and odds is not None and units is not None):
            continue
        grade = f["grade"] if f["grade"] in ("W", "L", "P") else None
        if grade is None and ag is not None and hg is not None and f["rule"] is None:
            stats["no_cache"] += 1
        close = _int(f["close"])
        profit = _num(f["profit"])
        codes = rule_codes(f["rule"])
        db.x("INSERT INTO core.bets (league, game_id, book, market, side, point, price_american, units, rule_codes, "
             "close_price, result, profit_units, source_row) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
             (LEAGUE, gid, "novig", str(market).strip(), str(side).strip(), bet_point(market, f), odds, float(units),
              codes, close, grade, profit, i))
        stats["bets"] += 1
        stats["staked_bets" if units > 0 else "zero_unit_bets"] += 1
        stats["untagged"] += codes == "UNTAGGED"
        if grade:
            stats["graded"] += 1
            stats["wins"] += grade == "W"
            stats["losses"] += grade == "L"
            stats["profit_units"] += profit or 0.0
            stats["risked_units"] += float(units)
        if close is not None:
            stats["close_odds"] += 1
            if abs(implied(close) - implied(odds)) > SUSPECT_CLV:
                warnings.append(f"row {i}: {gdate} {away}@{home} {market} {side} taken {odds:+d}, close {close:+d} "
                                f"({100 * (implied(close) - implied(odds)):+.1f} pts) - check for a typo")
    if stats["bets"] >= 10 and (stats["bets"] - stats["graded"]) > max(5, stats["bets"] // 4) and stats["no_cache"] > 5:
        raise SystemExit(f"{stats['no_cache']} bets have scores but no Grade/Rule values: the workbook was saved without "
                         "Excel recalculating it (e.g. by a script). Open it in Excel, let it calculate, Save, close it, "
                         "and run the import again. Nothing was committed.")
    stats["odds_prices"] = db.many("INSERT INTO core.odds (snapshot_id, game_id, bookmaker, market, side, team_code, point, "
                                   "price_american, implied_prob, book_update_utc) VALUES (?,?,?,?,?,?,?,?,?,?)", odds_rows)
    stats["profit_units"] = round(stats["profit_units"], 3)
    stats["risked_units"] = round(stats["risked_units"], 3)
    if verbose:
        for w in warnings:
            print("WARNING", w)
    stats["warnings"] = len(warnings)
    stats.pop("no_cache", None)
    return stats


# ---------------------------------------------------------------------------
def _table_rows(ws):
    it = ws.iter_rows(values_only=True)
    hdr = None
    for row in it:
        if row and any(v is not None for v in row):
            hdr = list(row)
            break
    if hdr is None:
        return [], []
    return hdr, [list(r) for r in it if r and any(v is not None for v in r)]


def load_team_tables(db: DB, wb, as_of: dt.date) -> dict:
    """Data_YYYY_YY sheets -> nhl.team_season. The current season is kept per snapshot date;
    finished seasons keep one copy (re-loads replace it)."""
    cur = season_of(as_of)
    out = {}
    for name in wb.sheetnames:
        m = re.fullmatch(r"Data_(\d{4})_(\d{2})", name)
        if not m:
            continue
        season = int(m.group(1))
        hdr, rows = _table_rows(wb[name])
        idx = {slug(h): i for i, h in enumerate(hdr) if h is not None}
        if "team" not in idx:
            raise ValueError(f"{name}: no 'Team' column")
        snap = as_of if season == cur else dt.date(season + 1, 6, 30)
        if season == cur:
            db.x("DELETE FROM nhl.team_season WHERE season=? AND snapshot_date=? AND source='workbook'", (season, snap.isoformat()))
        else:
            db.x("DELETE FROM nhl.team_season WHERE season=? AND source='workbook'", (season,))
        cols = [c for c in TEAM_STATS if c in idx]
        recs = []
        for r in rows:
            t = r[idx["team"]]
            if not t:
                continue
            code = teams.code(db, LEAGUE, str(t))
            recs.append((season, snap.isoformat(), code, "workbook", *[_num(r[idx[c]]) for c in cols]))
        names = ["season", "snapshot_date", "team_code", "source", *cols]
        db.many(f"INSERT INTO nhl.team_season ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})", recs)
        out[f"team_season {season}"] = len(recs)
    return out


def load_goalies(db: DB, wb, as_of: dt.date) -> int:
    if "Goalies" not in wb.sheetnames:
        return 0
    season = season_of(as_of)
    hdr, rows = _table_rows(wb["Goalies"])
    idx = {slug(h): i for i, h in enumerate(hdr) if h is not None}
    db.x("DELETE FROM nhl.goalie_season WHERE season=? AND snapshot_date=? AND source='workbook'", (season, as_of.isoformat()))
    cols = [c for c in GOALIE_STATS if c in idx]
    recs, seen = [], set()
    for r in rows:
        name, team = r[idx["name"]], r[idx["team"]]
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            code = teams.code(db, LEAGUE, str(team)) if team else None
        except KeyError:
            code = None
        recs.append((season, as_of.isoformat(), str(name).strip(), code, team, "workbook", *[_num(r[idx[c]]) for c in cols]))
    names = ["season", "snapshot_date", "goalie", "team_code", "team_name", "source", *cols]
    return db.many(f"INSERT INTO nhl.goalie_season ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})", recs)


def mp_long_rows(db: DB, header, rows, entity: str, snap: dt.date, source: str, season_default: int):
    """MoneyPuck CSV layout (teams.csv / goalies.csv) -> nhl.mp_stat tuples."""
    h = [str(x).strip() if x is not None else "" for x in header]
    low = [x.lower() for x in h]
    ix = {k: low.index(k) for k in ("team", "season", "name", "situation", "playerid") if k in low}
    out, seen = [], set()
    for r in rows:
        if not r or ix.get("situation") is None or r[ix["situation"]] in (None, ""):
            continue
        season = _int(r[ix["season"]]) if "season" in ix else None
        season = season or season_default
        team_raw = str(r[ix["team"]]).strip() if "team" in ix and r[ix["team"]] else None
        try:
            code = teams.code(db, LEAGUE, team_raw) if team_raw else None
        except KeyError:
            code = None
        if entity == "team":
            eid, ename = code or (team_raw or "?"), team_raw
        else:
            pid = _int(r[ix["playerid"]]) if "playerid" in ix else None
            eid = str(pid) if pid is not None else str(r[ix["name"]])
            ename = r[ix["name"]] if "name" in ix else None
        sit = str(r[ix["situation"]]).strip()
        for j, col in enumerate(h):
            if not col or col.lower() in MP_TEXT or j >= len(r):
                continue
            v = r[j]
            if isinstance(v, str):
                try:
                    v = float(v) if v.strip() else None
                except ValueError:
                    continue
            if v is not None and not isinstance(v, (int, float)):
                continue
            k = (season, eid, sit, col)
            if k in seen:
                continue
            seen.add(k)
            out.append((season, snap.isoformat(), source, entity, eid[:20], ename, code, sit, col[:80], v))
    return out


def store_mp(db: DB, recs, source: str) -> int:
    for season, snap, ent in {(r[0], r[1], r[3]) for r in recs}:
        db.x("DELETE FROM nhl.mp_stat WHERE season=? AND snapshot_date=? AND source=? AND entity=?", (season, snap, source, ent))
    return db.many("INSERT INTO nhl.mp_stat (season, snapshot_date, source, entity, entity_id, entity_name, team_code, "
                   "situation, stat, value) VALUES (?,?,?,?,?,?,?,?,?,?)", recs)


def load_situation_data(db: DB, wb) -> int:
    """'Data' sheet = last season's MoneyPuck teams.csv (one row per team x situation)."""
    if "Data" not in wb.sheetnames:
        return 0
    hdr, rows = _table_rows(wb["Data"])
    seasons = {_int(r[1]) for r in rows if len(r) > 1 and _int(r[1])}
    season = max(seasons) if seasons else 2025
    db.x("DELETE FROM nhl.mp_stat WHERE source='workbook' AND entity='team' AND season=?", (season,))
    recs = mp_long_rows(db, hdr, rows, "team", dt.date(season + 1, 6, 30), "workbook", season)
    return store_mp(db, recs, "workbook")


def load_settings(db: DB, wb) -> int:
    if "Assumptions" not in wb.sheetnames:
        return 0
    ws = wb["Assumptions"]
    recs, section = {}, None
    for rn, r in enumerate(ws.iter_rows(min_row=5, max_col=4, values_only=True), start=5):
        sec, name, val, unit = (list(r) + [None] * 4)[:4]
        section = sec or section
        if not name and _num(val) is not None:
            name = f"C{rn}"          # unlabeled input (C22 = goalie shrinkage K)
        if not name:
            continue
        num = _num(val)
        if num is None and isinstance(val, str):
            try:
                num = float(val)
            except ValueError:
                num = None
        recs[str(name).strip()[:80]] = (str(name).strip()[:80], section, num, None if num is not None else str(val)[:60], unit)
    db.x("DELETE FROM nhl.model_settings")
    return db.many("INSERT INTO nhl.model_settings (setting, section, value_num, value_text, unit) VALUES (?,?,?,?,?)",
                   list(recs.values()))


def load(db: DB, path: str, as_of: dt.date | None = None, verbose: bool = True) -> dict:
    as_of = as_of or dt.datetime.now(ZoneInfo("America/New_York")).date()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {"tracking": load_tracking(db, wb["Tracking"], verbose)}
    out["stats"] = load_team_tables(db, wb, as_of)
    out["stats"]["goalie_season"] = load_goalies(db, wb, as_of)
    out["stats"]["mp_stat (Data sheet)"] = load_situation_data(db, wb)
    out["stats"]["model_settings"] = load_settings(db, wb)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--as-of", help="date the pasted MoneyPuck tables were taken (YYYY-MM-DD, default today ET)")
    a = ap.parse_args(argv)
    as_of = dt.date.fromisoformat(a.as_of) if a.as_of else None
    with session() as db:
        out = load(db, a.workbook, as_of)
    t = out["tracking"]
    roi = 100 * t["profit_units"] / t["risked_units"] if t["risked_units"] else 0
    print(f"Tracking: {t['rows']} rows, {t['games']} games ({t['shootouts']} shootouts), {t['bets']} bets "
          f"({t['staked_bets']} staked, {t['zero_unit_bets']} at $0, {t['untagged']} untagged), "
          f"{t['wins']}-{t['losses']}, {t['profit_units']:+.2f}u on {t['risked_units']:.2f}u (ROI {roi:+.1f}%), "
          f"{t['close_odds']} with close odds, {t['projections']} projections, {t['odds_prices']} bet-time prices, "
          f"{t['warnings']} warnings")
    print("Stats:", out["stats"])


if __name__ == "__main__":
    sys.exit(main())

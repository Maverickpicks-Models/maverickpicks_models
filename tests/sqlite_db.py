"""SQLite stand-in for SQL Server so the Python logic can be tested anywhere.
Table/column names match sql/001_schema.sql; types are simplified."""
import sqlite3, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mpm.db import DB

DDL = """
CREATE TABLE core.config (config_key TEXT PRIMARY KEY, config_value TEXT, is_secret INT, updated_at TEXT);
CREATE TABLE core.teams (league TEXT, team_code TEXT, team_name TEXT, lat REAL, lon REAL, utc_offset INT, altitude_ft INT, PRIMARY KEY(league,team_code));
CREATE TABLE core.team_aliases (league TEXT, alias TEXT, team_code TEXT, PRIMARY KEY(league, alias));
CREATE TABLE core.games (game_id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, game_date TEXT, start_utc TEXT, away_code TEXT, home_code TEXT,
  odds_event_id TEXT, away_score INT, home_score INT, went_ot INT, status TEXT DEFAULT 'scheduled', UNIQUE(league,game_date,away_code,home_code));
CREATE TABLE core.odds_snapshots (snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, pulled_at_utc TEXT DEFAULT CURRENT_TIMESTAMP,
  purpose TEXT, source TEXT, endpoint TEXT, credits_used INT, credits_remaining INT);
CREATE TABLE core.odds (odds_id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id INT, game_id INT, bookmaker TEXT, market TEXT, side TEXT, team_code TEXT,
  point REAL, price_american INT, implied_prob REAL, book_update_utc TEXT);
CREATE TABLE core.injury_reports (report_id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, report_time_et TEXT, source_file TEXT, loaded_at_utc TEXT,
  UNIQUE(league, report_time_et));
CREATE TABLE core.injury_status (report_id INT, game_date TEXT, matchup TEXT, team_name TEXT, player TEXT, status TEXT, reason TEXT,
  PRIMARY KEY(report_id, matchup, team_name, player));
CREATE TABLE core.model_runs (run_id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, run_at_utc TEXT, model_version TEXT, rulebook TEXT, snapshot_id INT, injury_report_id INT);
CREATE TABLE core.projections (run_id INT, game_id INT, away_pts REAL, home_pts REAL, away_win_p REAL, away_cover_p REAL, over_p REAL, PRIMARY KEY(run_id, game_id));
CREATE TABLE core.bets (bet_id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, game_id INT, rec_id INT, placed_at_utc TEXT, book TEXT DEFAULT 'novig',
  market TEXT, side TEXT, point REAL, price_american INT, units REAL, rule_codes TEXT, close_point REAL, close_price INT, result TEXT, profit_units REAL, source_row INT);
CREATE TABLE core.api_usage (call_id INTEGER PRIMARY KEY AUTOINCREMENT, called_at_utc TEXT, endpoint TEXT, http_status INT, credits_used INT, credits_remaining INT);
CREATE TABLE nba.team_box (team_code TEXT, game_date TEXT, matchup TEXT, wl TEXT, mins INT, pts INT, fgm INT, fga INT, fg3m INT, fg3a INT, ftm INT, fta INT,
  oreb INT, dreb INT, reb INT, ast INT, tov INT, stl INT, blk INT, pf INT, plus_minus INT, PRIMARY KEY(team_code, game_date));
CREATE TABLE nba.player_box (player TEXT, team_code TEXT, game_date TEXT, matchup TEXT, wl TEXT, mins REAL, pts INT, fgm INT, fga INT, fg3m INT, fg3a INT,
  ftm INT, fta INT, oreb INT, dreb INT, reb INT, ast INT, stl INT, blk INT, tov INT, pf INT, plus_minus INT, PRIMARY KEY(player, team_code, game_date));
"""

def make_db(seed_teams=True):
    c = sqlite3.connect(":memory:")
    for s in ("core", "nba", "nhl"):
        c.execute(f"ATTACH ':memory:' AS {s}")
    c.executescript(DDL)
    db = DB(c, "sqlite")
    if seed_teams:
        import re
        sql = open(os.path.join(os.path.dirname(__file__), "..", "sql", "002_seed_teams.sql"), encoding="utf-8").read()
        for blk in re.findall(r"USING \(VALUES\s*(.*?)\n\) AS s\((.*?)\)", sql, re.S):
            vals, cols = blk
            table = "core.teams" if "lat" in cols else "core.team_aliases"
            for tup in re.findall(r"\((.*?)\)(?:,|$)", vals, re.M):
                parts = [p.strip() for p in re.findall(r"N?'(?:[^']|'')*'|[-\d.]+|NULL", tup)]
                vals_ = [None if p == "NULL" else (p.lstrip("N")[1:-1].replace("''", "'") if "'" in p else float(p)) for p in parts]
                c.execute(f"INSERT INTO {table} VALUES ({','.join('?' * len(vals_))})", vals_)
    return db

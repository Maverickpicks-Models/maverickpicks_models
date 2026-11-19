"""SQLite stand-in for SQL Server so the Python logic can be tested anywhere.
Table/column names match sql/001_schema.sql and sql/010_nhl_schema.sql; types are simplified."""
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
CREATE TABLE core.recommendations (rec_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INT, game_id INT, market TEXT, side TEXT, point REAL,
  price_american INT, units REAL, section TEXT, rule_codes TEXT, note TEXT);
CREATE TABLE core.bets (bet_id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, game_id INT, rec_id INT, placed_at_utc TEXT, book TEXT DEFAULT 'novig',
  market TEXT, side TEXT, point REAL, price_american INT, units REAL, rule_codes TEXT, close_point REAL, close_price INT, result TEXT, profit_units REAL, source_row INT);
CREATE TABLE core.watchlist (watch_id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT DEFAULT 'NBA', game_date TEXT, matchup TEXT, bet_label TEXT, tip_et TEXT, created_at TEXT);
CREATE TABLE core.injury_alerts (league TEXT, game_date TEXT, matchup TEXT, player TEXT, status TEXT, report_id INT, sent_at TEXT, PRIMARY KEY(league, game_date, matchup, player, status));
CREATE TABLE core.api_usage (call_id INTEGER PRIMARY KEY AUTOINCREMENT, called_at_utc TEXT, endpoint TEXT, http_status INT, credits_used INT, credits_remaining INT);
CREATE TABLE nba.team_box (team_code TEXT, game_date TEXT, matchup TEXT, wl TEXT, mins INT, pts INT, fgm INT, fga INT, fg3m INT, fg3a INT, ftm INT, fta INT,
  oreb INT, dreb INT, reb INT, ast INT, tov INT, stl INT, blk INT, pf INT, plus_minus INT, PRIMARY KEY(team_code, game_date));
CREATE TABLE nba.player_box (player TEXT, team_code TEXT, game_date TEXT, matchup TEXT, wl TEXT, mins REAL, pts INT, fgm INT, fga INT, fg3m INT, fg3a INT,
  ftm INT, fta INT, oreb INT, dreb INT, reb INT, ast INT, stl INT, blk INT, tov INT, pf INT, plus_minus INT, PRIMARY KEY(player, team_code, game_date));
CREATE TABLE nhl.game_results (game_id INT PRIMARY KEY, reg_ot_away INT, reg_ot_home INT, shootout INT DEFAULT 0, so_winner TEXT, source TEXT DEFAULT 'workbook', loaded_at_utc TEXT);
CREATE TABLE nhl.projection_detail (run_id INT, game_id INT, away_lambda REAL, home_lambda REAL, away_cur_wt REAL, home_cur_wt REAL, ml_home_p REAL,
  ml_away_edge REAL, ml_home_edge REAL, total_line REAL, total_proj REAL, home_pl_p REAL, away_tt_line REAL, away_tt_over_p REAL, home_tt_line REAL,
  home_tt_over_p REAL, away_goalie TEXT, home_goalie TEXT, card TEXT, PRIMARY KEY(run_id, game_id));
CREATE TABLE nhl.team_season (season INT, snapshot_date TEXT, team_code TEXT, source TEXT, games_played REAL, icetime_minutes REAL, goals_pct REAL, xgoals_pct REAL, shot_attempts_pct_corsi_pct REAL, unblocked_shot_attempts_pct_fenwick_pct REAL, goals_for REAL, goals_against REAL, goal_differential REAL, expected_goals_for REAL, expected_goals_against REAL, expected_goal_differential REAL, goals_for_above_expected REAL, goals_against_above_expected REAL, goals_differential_above_expected REAL, pdo_sh_pct_sv_pct REAL, shooting_pct_on_shots_on_goal REAL, shooting_pct_on_unblocked_shots REAL, shooting_pct_on_all_shot_attempts REAL, pct_of_shot_attempts_for_that_are_blocked REAL, pct_of_unblocked_shot_attempts_for_that_miss_net REAL, expected_pct_of_unblocked_shot_attempts_for_that_miss_net REAL, pct_of_net_misses_above_expected REAL, save_pct_on_shots_on_goal REAL, save_pct_on_unblocked_shots REAL, expected_save_pct_on_unblocked_shots REAL, save_pct_above_expected_on_unblocked_shots REAL, penalty_minutes_taken_per_60 REAL, penalty_minutes_drawn_per_60 REAL, share_of_penalty_minutes_taken REAL, goals_for_per_60 REAL, goals_against_per_60_gaa REAL, goals_differential_per_60 REAL, expected_goals_for_per_60 REAL, expected_goals_against_per_60 REAL, expected_goal_differential_per_60 REAL, shots_on_goal_for REAL, shots_on_goal_against REAL, unblocked_shots_attempts_for REAL, unblocked_shots_attempts_against REAL, pim_against REAL, pim_taken_by_opponents REAL, pct_of_pim_taken REAL, faceoff_win_pct REAL, score_adjusted_expected_goals_pct REAL, flurry_adjusted_expected_goals_pct REAL, score_and_flurry_adjusted_expected_goals_pct REAL, score_adjusted_shot_attempts_pct_corsi_pct REAL, score_adjusted_unblocked_shot_attempts_pct_fenwick_pct REAL, rebound_shots_for REAL, rebound_shots_against REAL, rebound_goals_for REAL, pct_of_goals_for_from_rebounds REAL, rebound_goals_against REAL, pct_of_goals_against_from_rebounds REAL, high_danger_shots_for REAL, medium_danger_shots_for REAL, low_danger_shots_for REAL, high_danger_shots_against REAL, medium_danger_shots_against REAL, low_danger_shots_against REAL, takeaways_from_opponent REAL, takeaways_to_opponent REAL, share_of_takeaways REAL, giveaways_to_opponent REAL, defensive_zone_giveaways_to_opponent REAL, pct_of_giveaways_in_defensive_zone REAL, shots_blocked REAL, hits_given REAL, hits_taken REAL, pct_of_hits_given REAL, loaded_at_utc TEXT, PRIMARY KEY(season, snapshot_date, team_code));
CREATE TABLE nhl.goalie_season (season INT, snapshot_date TEXT, goalie TEXT, team_code TEXT, team_name TEXT, source TEXT, games_played REAL, goals_against REAL, expected_goals_against REAL, goals_saved_above_expected REAL, goals_saved_above_expected_per_60 REAL, pct_of_expected_goals_saved_above_average REAL, save_pct_on_unblocked_shots REAL, xsave_pct_on_unblocked_shots REAL, save_pct_above_expected REAL, save_pct_on_shots_on_goal REAL, gaa REAL, xgaa REAL, gaa_better_than_expected REAL, wins_above_replacement REAL, icetime_minutes REAL, rebounds_per_save REAL, puck_freezes_per_save REAL, xrebounds_per_save REAL, rebounds_above_expected REAL, expected_puck_freeze REAL, puck_freezes_above_expected REAL, puck_freezes_above_expected_per_shot_on_goal REAL, goals_against2 REAL, saves_on_shots_on_goal REAL, saves_on_unblocked_shot_attempts REAL, pct_of_shot_attempts_blocked_by_teammates REAL, pct_of_unblocked_shot_attempts_against_on_goal REAL, expected_pct_of_unblocked_shot_attempts_against_on_goal REAL, on_goal_pct_above_expected REAL, low_danger_unblocked_shot_attempt_save_pct REAL, xlow_danger_unblocked_shot_attempt_save_pct REAL, low_danger_unblocked_shot_attempt_save_pct_above_expected REAL, medium_danger_unblocked_shot_attempt_save_pct REAL, xmedium_danger_unblocked_shot_attempt_save_pct REAL, medium_danger_unblocked_shot_attemptsave_pct_above_expected REAL, high_danger_unblocked_shot_attempt_save_pct REAL, xhigh_danger_unblocked_shot_attempt_save_pct REAL, high_danger_unblocked_shot_attempt_save_pct_above_expected REAL, loaded_at_utc TEXT, PRIMARY KEY(season, snapshot_date, goalie));
CREATE TABLE nhl.mp_stat (season INT, snapshot_date TEXT, source TEXT, entity TEXT, entity_id TEXT, entity_name TEXT, team_code TEXT, situation TEXT,
  stat TEXT, value REAL, PRIMARY KEY(season, snapshot_date, source, entity, entity_id, situation, stat));
CREATE TABLE nhl.model_settings (setting TEXT PRIMARY KEY, section TEXT, value_num REAL, value_text TEXT, unit TEXT, loaded_at_utc TEXT);
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

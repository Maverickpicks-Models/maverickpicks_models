/* MaverickPicks Models - NHL tables (SQL Server 2019+). Idempotent: safe to re-run.
   Run after 001_schema.sql:  sqlcmd -S ECG-L028 -E -b -I -i sql\010_nhl_schema.sql
   Games, odds, bets, model runs and projections stay in the shared core.* tables (league = 'NHL').
   This file adds what only the NHL model uses. */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO
USE MaverickPicks;
GO
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO
IF SCHEMA_ID('nhl') IS NULL EXEC('CREATE SCHEMA nhl');
GO

/* ---------- how each game ended (core.games holds the official final score) ----------
   Novig settles NHL totals and team totals on the official final score, which credits the
   shootout winner with one goal. The Tracking sheet records the regulation+OT score (tied
   after a shootout) plus the shootout winner; both are kept here. */
IF OBJECT_ID('nhl.game_results') IS NULL
CREATE TABLE nhl.game_results (
    game_id      int          NOT NULL PRIMARY KEY REFERENCES core.games(game_id),
    reg_ot_away  smallint     NULL,          -- goals after regulation + OT (before the shootout)
    reg_ot_home  smallint     NULL,
    shootout     bit          NOT NULL DEFAULT 0,
    so_winner    varchar(4)   NULL,          -- 'away' / 'home' when shootout = 1
    source       varchar(20)  NOT NULL DEFAULT 'workbook',
    loaded_at_utc datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

/* ---------- legacy (Excel) projection detail, one row per game ----------
   core.projections gets away_pts/home_pts = goal lambdas, away_win_p, away_cover_p (away -1.5), over_p.
   The NHL-only fields live here. */
IF OBJECT_ID('nhl.projection_detail') IS NULL
CREATE TABLE nhl.projection_detail (
    run_id          int          NOT NULL REFERENCES core.model_runs(run_id),
    game_id         int          NOT NULL REFERENCES core.games(game_id),
    away_lambda     decimal(7,4) NULL,
    home_lambda     decimal(7,4) NULL,
    away_cur_wt     decimal(5,3) NULL,       -- current-season weight in the blend
    home_cur_wt     decimal(5,3) NULL,
    ml_home_p       decimal(6,4) NULL,
    ml_away_edge    decimal(7,4) NULL,
    ml_home_edge    decimal(7,4) NULL,
    total_line      decimal(4,1) NULL,
    total_proj      decimal(6,3) NULL,
    home_pl_p       decimal(6,4) NULL,       -- home -1.5
    away_tt_line    decimal(4,1) NULL,
    away_tt_over_p  decimal(6,4) NULL,
    home_tt_line    decimal(4,1) NULL,
    home_tt_over_p  decimal(6,4) NULL,
    away_goalie     nvarchar(80) NULL,       -- goalie the projection used
    home_goalie     nvarchar(80) NULL,
    card            nvarchar(600) NULL,      -- card text, including rule tags
    CONSTRAINT PK_nhl_projection_detail PRIMARY KEY (run_id, game_id)
);
GO

/* ---------- MoneyPuck team table (website layout, one row per team) ----------
   Snapshots are kept by date so models can use point-in-time stats.
   season = first year (2026 = 2026-27). Column names are the sheet headers in snake_case. */
IF OBJECT_ID('nhl.team_season') IS NULL
CREATE TABLE nhl.team_season (
    season          smallint     NOT NULL,
    snapshot_date   date         NOT NULL,
    team_code       varchar(5)   NOT NULL,
    source          varchar(20)  NOT NULL DEFAULT 'workbook',
    games_played                                                 decimal(12,4) NULL,
    icetime_minutes                                              decimal(12,4) NULL,
    goals_pct                                                    decimal(12,4) NULL,
    xgoals_pct                                                   decimal(12,4) NULL,
    shot_attempts_pct_corsi_pct                                  decimal(12,4) NULL,
    unblocked_shot_attempts_pct_fenwick_pct                      decimal(12,4) NULL,
    goals_for                                                    decimal(12,4) NULL,
    goals_against                                                decimal(12,4) NULL,
    goal_differential                                            decimal(12,4) NULL,
    expected_goals_for                                           decimal(12,4) NULL,
    expected_goals_against                                       decimal(12,4) NULL,
    expected_goal_differential                                   decimal(12,4) NULL,
    goals_for_above_expected                                     decimal(12,4) NULL,
    goals_against_above_expected                                 decimal(12,4) NULL,
    goals_differential_above_expected                            decimal(12,4) NULL,
    pdo_sh_pct_sv_pct                                            decimal(12,4) NULL,
    shooting_pct_on_shots_on_goal                                decimal(12,4) NULL,
    shooting_pct_on_unblocked_shots                              decimal(12,4) NULL,
    shooting_pct_on_all_shot_attempts                            decimal(12,4) NULL,
    pct_of_shot_attempts_for_that_are_blocked                    decimal(12,4) NULL,
    pct_of_unblocked_shot_attempts_for_that_miss_net             decimal(12,4) NULL,
    expected_pct_of_unblocked_shot_attempts_for_that_miss_net    decimal(12,4) NULL,
    pct_of_net_misses_above_expected                             decimal(12,4) NULL,
    save_pct_on_shots_on_goal                                    decimal(12,4) NULL,
    save_pct_on_unblocked_shots                                  decimal(12,4) NULL,
    expected_save_pct_on_unblocked_shots                         decimal(12,4) NULL,
    save_pct_above_expected_on_unblocked_shots                   decimal(12,4) NULL,
    penalty_minutes_taken_per_60                                 decimal(12,4) NULL,
    penalty_minutes_drawn_per_60                                 decimal(12,4) NULL,
    share_of_penalty_minutes_taken                               decimal(12,4) NULL,
    goals_for_per_60                                             decimal(12,4) NULL,
    goals_against_per_60_gaa                                     decimal(12,4) NULL,
    goals_differential_per_60                                    decimal(12,4) NULL,
    expected_goals_for_per_60                                    decimal(12,4) NULL,
    expected_goals_against_per_60                                decimal(12,4) NULL,
    expected_goal_differential_per_60                            decimal(12,4) NULL,
    shots_on_goal_for                                            decimal(12,4) NULL,
    shots_on_goal_against                                        decimal(12,4) NULL,
    unblocked_shots_attempts_for                                 decimal(12,4) NULL,
    unblocked_shots_attempts_against                             decimal(12,4) NULL,
    pim_against                                                  decimal(12,4) NULL,
    pim_taken_by_opponents                                       decimal(12,4) NULL,
    pct_of_pim_taken                                             decimal(12,4) NULL,
    faceoff_win_pct                                              decimal(12,4) NULL,
    score_adjusted_expected_goals_pct                            decimal(12,4) NULL,
    flurry_adjusted_expected_goals_pct                           decimal(12,4) NULL,
    score_and_flurry_adjusted_expected_goals_pct                 decimal(12,4) NULL,
    score_adjusted_shot_attempts_pct_corsi_pct                   decimal(12,4) NULL,
    score_adjusted_unblocked_shot_attempts_pct_fenwick_pct       decimal(12,4) NULL,
    rebound_shots_for                                            decimal(12,4) NULL,
    rebound_shots_against                                        decimal(12,4) NULL,
    rebound_goals_for                                            decimal(12,4) NULL,
    pct_of_goals_for_from_rebounds                               decimal(12,4) NULL,
    rebound_goals_against                                        decimal(12,4) NULL,
    pct_of_goals_against_from_rebounds                           decimal(12,4) NULL,
    high_danger_shots_for                                        decimal(12,4) NULL,
    medium_danger_shots_for                                      decimal(12,4) NULL,
    low_danger_shots_for                                         decimal(12,4) NULL,
    high_danger_shots_against                                    decimal(12,4) NULL,
    medium_danger_shots_against                                  decimal(12,4) NULL,
    low_danger_shots_against                                     decimal(12,4) NULL,
    takeaways_from_opponent                                      decimal(12,4) NULL,
    takeaways_to_opponent                                        decimal(12,4) NULL,
    share_of_takeaways                                           decimal(12,4) NULL,
    giveaways_to_opponent                                        decimal(12,4) NULL,
    defensive_zone_giveaways_to_opponent                         decimal(12,4) NULL,
    pct_of_giveaways_in_defensive_zone                           decimal(12,4) NULL,
    shots_blocked                                                decimal(12,4) NULL,
    hits_given                                                   decimal(12,4) NULL,
    hits_taken                                                   decimal(12,4) NULL,
    pct_of_hits_given                                            decimal(12,4) NULL,
    loaded_at_utc   datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_nhl_team_season PRIMARY KEY (season, snapshot_date, team_code)
);
GO

/* ---------- MoneyPuck goalie table (website layout, one row per goalie) ---------- */
IF OBJECT_ID('nhl.goalie_season') IS NULL
CREATE TABLE nhl.goalie_season (
    season          smallint     NOT NULL,
    snapshot_date   date         NOT NULL,
    goalie          nvarchar(80) NOT NULL,
    team_code       varchar(5)   NULL,        -- NULL if the team name is not in core.team_aliases
    team_name       nvarchar(60) NULL,        -- as written by MoneyPuck
    source          varchar(20)  NOT NULL DEFAULT 'workbook',
    games_played                                                 decimal(12,4) NULL,
    goals_against                                                decimal(12,4) NULL,
    expected_goals_against                                       decimal(12,4) NULL,
    goals_saved_above_expected                                   decimal(12,4) NULL,
    goals_saved_above_expected_per_60                            decimal(12,4) NULL,
    pct_of_expected_goals_saved_above_average                    decimal(12,4) NULL,
    save_pct_on_unblocked_shots                                  decimal(12,4) NULL,
    xsave_pct_on_unblocked_shots                                 decimal(12,4) NULL,
    save_pct_above_expected                                      decimal(12,4) NULL,
    save_pct_on_shots_on_goal                                    decimal(12,4) NULL,
    gaa                                                          decimal(12,4) NULL,
    xgaa                                                         decimal(12,4) NULL,
    gaa_better_than_expected                                     decimal(12,4) NULL,
    wins_above_replacement                                       decimal(12,4) NULL,
    icetime_minutes                                              decimal(12,4) NULL,
    rebounds_per_save                                            decimal(12,4) NULL,
    puck_freezes_per_save                                        decimal(12,4) NULL,
    xrebounds_per_save                                           decimal(12,4) NULL,
    rebounds_above_expected                                      decimal(12,4) NULL,
    expected_puck_freeze                                         decimal(12,4) NULL,
    puck_freezes_above_expected                                  decimal(12,4) NULL,
    puck_freezes_above_expected_per_shot_on_goal                 decimal(12,4) NULL,
    goals_against2                                               decimal(12,4) NULL,
    saves_on_shots_on_goal                                       decimal(12,4) NULL,
    saves_on_unblocked_shot_attempts                             decimal(12,4) NULL,
    pct_of_shot_attempts_blocked_by_teammates                    decimal(12,4) NULL,
    pct_of_unblocked_shot_attempts_against_on_goal               decimal(12,4) NULL,
    expected_pct_of_unblocked_shot_attempts_against_on_goal      decimal(12,4) NULL,
    on_goal_pct_above_expected                                   decimal(12,4) NULL,
    low_danger_unblocked_shot_attempt_save_pct                   decimal(12,4) NULL,
    xlow_danger_unblocked_shot_attempt_save_pct                  decimal(12,4) NULL,
    low_danger_unblocked_shot_attempt_save_pct_above_expected    decimal(12,4) NULL,
    medium_danger_unblocked_shot_attempt_save_pct                decimal(12,4) NULL,
    xmedium_danger_unblocked_shot_attempt_save_pct               decimal(12,4) NULL,
    medium_danger_unblocked_shot_attemptsave_pct_above_expected  decimal(12,4) NULL,
    high_danger_unblocked_shot_attempt_save_pct                  decimal(12,4) NULL,
    xhigh_danger_unblocked_shot_attempt_save_pct                 decimal(12,4) NULL,
    high_danger_unblocked_shot_attempt_save_pct_above_expected   decimal(12,4) NULL,
    loaded_at_utc   datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_nhl_goalie_season PRIMARY KEY (season, snapshot_date, goalie)
);
GO

/* ---------- MoneyPuck CSV downloads (teams.csv / goalies.csv), long format ----------
   One row per entity x situation x stat, so header changes on MoneyPuck's side never break a load.
   Also holds the workbook's "Data" sheet (2025-26 teams.csv by situation). */
IF OBJECT_ID('nhl.mp_stat') IS NULL
CREATE TABLE nhl.mp_stat (
    season        smallint     NOT NULL,
    snapshot_date date         NOT NULL,
    source        varchar(20)  NOT NULL,      -- moneypuck / workbook
    entity        varchar(10)  NOT NULL,      -- team / goalie
    entity_id     varchar(20)  NOT NULL,      -- team code, or MoneyPuck playerId
    entity_name   nvarchar(80) NULL,
    team_code     varchar(5)   NULL,
    situation     varchar(10)  NOT NULL,      -- all / 5on5 / 5on4 / 4on5 / other
    stat          varchar(80)  NOT NULL,
    value         float        NULL,
    CONSTRAINT PK_nhl_mp_stat PRIMARY KEY (season, snapshot_date, source, entity, entity_id, situation, stat)
);
GO

/* ---------- model settings (Assumptions sheet) ---------- */
IF OBJECT_ID('nhl.model_settings') IS NULL
CREATE TABLE nhl.model_settings (
    setting       nvarchar(80)  NOT NULL PRIMARY KEY,
    section       nvarchar(40)  NULL,
    value_num     float         NULL,
    value_text    nvarchar(60)  NULL,
    unit          nvarchar(80)  NULL,
    loaded_at_utc datetime2(0)  NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

/* ---------- views ---------- */
/* Latest team stats per season */
CREATE OR ALTER VIEW nhl.v_team_latest AS
SELECT t.* FROM nhl.team_season t
WHERE t.snapshot_date = (SELECT MAX(snapshot_date) FROM nhl.team_season x WHERE x.season = t.season);
GO
CREATE OR ALTER VIEW nhl.v_goalie_latest AS
SELECT g.* FROM nhl.goalie_season g
WHERE g.snapshot_date = (SELECT MAX(snapshot_date) FROM nhl.goalie_season x WHERE x.season = g.season);
GO
/* Rule record with flat ROI (1 unit per bet), so $0 track-only bets still show a record.
   NHL rule codes are comma-separated ('HU,GU'); OFF = picks made outside the rules. */
CREATE OR ALTER VIEW nhl.v_rule_record AS
SELECT LTRIM(RTRIM(r.value)) AS rule_code,
       COUNT(*) AS bets,
       SUM(CASE WHEN c.units > 0 THEN 1 ELSE 0 END) AS staked_bets,
       SUM(CASE WHEN c.result='W' THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN c.result='L' THEN 1 ELSE 0 END) AS losses,
       SUM(c.profit_units) AS units, SUM(c.units) AS risked,
       SUM(c.profit_units)/NULLIF(SUM(c.units),0) AS roi_units,
       AVG(CASE WHEN c.result='W' THEN (CASE WHEN c.price_american < 0 THEN 100.0/-c.price_american ELSE c.price_american/100.0 END)
                WHEN c.result='L' THEN -1.0 ELSE 0.0 END) AS roi_flat,
       AVG(c.clv_prob_pts) AS avg_clv
FROM core.v_bet_clv c
CROSS APPLY STRING_SPLIT(ISNULL(c.rule_codes,'UNTAGGED'), ',') r
WHERE c.league = 'NHL' AND c.result IS NOT NULL
GROUP BY LTRIM(RTRIM(r.value));
GO

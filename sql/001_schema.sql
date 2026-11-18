/* MaverickPicks Models - core schema (SQL Server 2019+ / Developer edition)
   Run in SSMS against server ECG-L028. Idempotent: safe to re-run. */

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;   -- required for the filtered index; sqlcmd defaults this OFF
GO
IF DB_ID('MaverickPicks') IS NULL CREATE DATABASE MaverickPicks;
GO
USE MaverickPicks;
GO
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO
IF SCHEMA_ID('core') IS NULL EXEC('CREATE SCHEMA core');
IF SCHEMA_ID('nba')  IS NULL EXEC('CREATE SCHEMA nba');
IF SCHEMA_ID('nhl')  IS NULL EXEC('CREATE SCHEMA nhl');
GO

/* ---------- configuration & secrets (API keys live here) ---------- */
IF OBJECT_ID('core.config') IS NULL
CREATE TABLE core.config (
    config_key   varchar(100)  NOT NULL PRIMARY KEY,
    config_value nvarchar(400) NOT NULL,
    is_secret    bit           NOT NULL DEFAULT 0,
    updated_at   datetime2(0)  NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

/* ---------- teams & aliases (one row per league/team) ---------- */
IF OBJECT_ID('core.teams') IS NULL
CREATE TABLE core.teams (
    league     varchar(5)   NOT NULL,          -- NBA / NHL
    team_code  varchar(5)   NOT NULL,          -- BOS, LAL, ...
    team_name  varchar(60)  NOT NULL,          -- canonical full name
    lat        decimal(8,4) NULL,
    lon        decimal(8,4) NULL,
    utc_offset smallint     NULL,              -- standard time
    altitude_ft int         NULL,
    CONSTRAINT PK_teams PRIMARY KEY (league, team_code)
);
IF OBJECT_ID('core.team_aliases') IS NULL
CREATE TABLE core.team_aliases (
    league    varchar(5)  NOT NULL,
    alias     varchar(60) NOT NULL,            -- 'LA Clippers', 'Los Angeles Clippers', 'LAC'
    team_code varchar(5)  NOT NULL,
    CONSTRAINT PK_team_aliases PRIMARY KEY (league, alias)
);
GO

/* ---------- games ---------- */
IF OBJECT_ID('core.games') IS NULL
CREATE TABLE core.games (
    game_id       int IDENTITY(1,1) PRIMARY KEY,
    league        varchar(5)   NOT NULL,
    game_date     date         NOT NULL,       -- local (ET) game date
    start_utc     datetime2(0) NULL,
    away_code     varchar(5)   NOT NULL,
    home_code     varchar(5)   NOT NULL,
    odds_event_id varchar(64)  NULL,           -- TheOddsAPI event id
    away_score    smallint     NULL,
    home_score    smallint     NULL,
    went_ot       bit          NULL,
    status        varchar(12)  NOT NULL DEFAULT 'scheduled',  -- scheduled/final/postponed
    CONSTRAINT UQ_games UNIQUE (league, game_date, away_code, home_code)
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_games_event')
    CREATE INDEX IX_games_event ON core.games(odds_event_id) WHERE odds_event_id IS NOT NULL;
GO

/* ---------- odds snapshots (every pull is a snapshot; every price is a row) ---------- */
IF OBJECT_ID('core.odds_snapshots') IS NULL
CREATE TABLE core.odds_snapshots (
    snapshot_id       int IDENTITY(1,1) PRIMARY KEY,
    league            varchar(5)   NOT NULL,
    pulled_at_utc     datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    purpose           varchar(20)  NOT NULL,   -- open / pregame / injury_1730 / close / manual / screenshot
    source            varchar(30)  NOT NULL DEFAULT 'theoddsapi',
    endpoint          varchar(200) NULL,
    credits_used      int          NULL,       -- x-requests-last
    credits_remaining int          NULL        -- x-requests-remaining
);
IF OBJECT_ID('core.odds') IS NULL
CREATE TABLE core.odds (
    odds_id          bigint IDENTITY(1,1) PRIMARY KEY,
    snapshot_id      int          NOT NULL REFERENCES core.odds_snapshots(snapshot_id),
    game_id          int          NOT NULL REFERENCES core.games(game_id),
    bookmaker        varchar(30)  NOT NULL,     -- novig, draftkings, fanduel, ...
    market           varchar(20)  NOT NULL,     -- h2h / spreads / totals / team_totals
    side             varchar(10)  NOT NULL,     -- away / home / over / under
    team_code        varchar(5)   NULL,         -- for team_totals: which team
    point            decimal(6,1) NULL,         -- spread or total line
    price_american   int          NOT NULL,
    implied_prob     decimal(7,5) NOT NULL,
    book_update_utc  datetime2(0) NULL
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_odds_game')
    CREATE INDEX IX_odds_game ON core.odds(game_id, market, bookmaker) INCLUDE (point, price_american, implied_prob);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_odds_snapshot')
    CREATE INDEX IX_odds_snapshot ON core.odds(snapshot_id);
GO

/* ---------- injury reports ---------- */
IF OBJECT_ID('core.injury_reports') IS NULL
CREATE TABLE core.injury_reports (
    report_id       int IDENTITY(1,1) PRIMARY KEY,
    league          varchar(5)   NOT NULL,
    report_time_et  datetime2(0) NOT NULL,     -- e.g. 2026-11-17 18:00
    source_file     nvarchar(260) NULL,
    loaded_at_utc   datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_injury_reports UNIQUE (league, report_time_et)
);
IF OBJECT_ID('core.injury_status') IS NULL
CREATE TABLE core.injury_status (
    report_id   int          NOT NULL REFERENCES core.injury_reports(report_id),
    game_date   date         NOT NULL,
    matchup     varchar(15)  NOT NULL,          -- 'NYK@TOR'
    team_name   varchar(60)  NOT NULL,
    player      nvarchar(80) NOT NULL,          -- 'Last, First' as printed
    status      varchar(20)  NOT NULL,          -- Out/Doubtful/Questionable/Probable/Available/NOT YET SUBMITTED
    reason      nvarchar(200) NULL,
    CONSTRAINT PK_injury_status PRIMARY KEY (report_id, matchup, team_name, player)
);
GO

/* ---------- model output, recommendations, bets ---------- */
IF OBJECT_ID('core.model_runs') IS NULL
CREATE TABLE core.model_runs (
    run_id         int IDENTITY(1,1) PRIMARY KEY,
    league         varchar(5)   NOT NULL,
    run_at_utc     datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    model_version  varchar(40)  NOT NULL,       -- git commit or tag
    rulebook       varchar(20)  NOT NULL,       -- 'v5'
    snapshot_id    int          NULL REFERENCES core.odds_snapshots(snapshot_id),
    injury_report_id int        NULL REFERENCES core.injury_reports(report_id)
);
IF OBJECT_ID('core.projections') IS NULL
CREATE TABLE core.projections (
    run_id      int NOT NULL REFERENCES core.model_runs(run_id),
    game_id     int NOT NULL REFERENCES core.games(game_id),
    away_pts    decimal(6,2) NULL,
    home_pts    decimal(6,2) NULL,
    away_win_p  decimal(6,4) NULL,
    away_cover_p decimal(6,4) NULL,
    over_p      decimal(6,4) NULL,
    CONSTRAINT PK_projections PRIMARY KEY (run_id, game_id)
);
IF OBJECT_ID('core.recommendations') IS NULL
CREATE TABLE core.recommendations (
    rec_id      int IDENTITY(1,1) PRIMARY KEY,
    run_id      int          NOT NULL REFERENCES core.model_runs(run_id),
    game_id     int          NOT NULL REFERENCES core.games(game_id),
    market      varchar(20)  NOT NULL,          -- spread / total / ml / team_total
    side        varchar(10)  NOT NULL,
    point       decimal(6,1) NULL,
    price_american int       NULL,
    units       decimal(5,2) NOT NULL,          -- 0 = paper
    section     varchar(10)  NOT NULL,          -- CORE / CRAFTED / TEST / PAPER / PASS
    rule_codes  varchar(100) NOT NULL,          -- 'C1+T5'
    note        nvarchar(300) NULL
);
IF OBJECT_ID('core.bets') IS NULL
CREATE TABLE core.bets (
    bet_id         int IDENTITY(1,1) PRIMARY KEY,
    league         varchar(5)   NOT NULL,
    game_id        int          NOT NULL REFERENCES core.games(game_id),
    rec_id         int          NULL REFERENCES core.recommendations(rec_id),
    placed_at_utc  datetime2(0) NULL,
    book           varchar(30)  NOT NULL DEFAULT 'novig',
    market         varchar(20)  NOT NULL,       -- Spread / Total / ML / TT Away / TT Home
    side           varchar(10)  NOT NULL,       -- Away / Home / Over / Under
    point          decimal(6,1) NULL,
    price_american int          NOT NULL,
    units          decimal(5,2) NOT NULL,
    rule_codes     varchar(100) NULL,
    close_point    decimal(6,1) NULL,
    close_price    int          NULL,
    result         char(1)      NULL,           -- W / L / P
    profit_units   decimal(7,3) NULL,
    source_row     int          NULL            -- Tracking row it came from (history import)
);
GO

/* ---------- NBA box scores (mirrors the workbook tables) ---------- */
IF OBJECT_ID('nba.team_box') IS NULL
CREATE TABLE nba.team_box (
    team_code varchar(5) NOT NULL, game_date date NOT NULL, matchup varchar(20) NOT NULL, wl char(1) NULL,
    mins smallint NULL, pts smallint, fgm smallint, fga smallint, fg3m smallint, fg3a smallint,
    ftm smallint, fta smallint, oreb smallint, dreb smallint, reb smallint, ast smallint, tov smallint,
    stl smallint, blk smallint, pf smallint, plus_minus smallint,
    CONSTRAINT PK_nba_team_box PRIMARY KEY (team_code, game_date)
);
IF OBJECT_ID('nba.player_box') IS NULL
CREATE TABLE nba.player_box (
    player nvarchar(80) NOT NULL, team_code varchar(5) NOT NULL, game_date date NOT NULL, matchup varchar(20) NULL,
    wl char(1) NULL, mins decimal(5,1) NULL, pts smallint NULL, fgm smallint NULL, fga smallint NULL,
    fg3m smallint NULL, fg3a smallint NULL, ftm smallint NULL, fta smallint NULL, oreb smallint NULL, dreb smallint NULL,
    reb smallint NULL, ast smallint NULL, stl smallint NULL, blk smallint NULL, tov smallint NULL, pf smallint NULL, plus_minus smallint NULL,
    CONSTRAINT PK_nba_player_box PRIMARY KEY (player, team_code, game_date)
);
GO

/* ---------- API usage log ---------- */
IF OBJECT_ID('core.api_usage') IS NULL
CREATE TABLE core.api_usage (
    call_id       int IDENTITY(1,1) PRIMARY KEY,
    called_at_utc datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    endpoint      varchar(300) NOT NULL,
    http_status   smallint     NOT NULL,
    credits_used  int          NULL,
    credits_remaining int      NULL
);
GO

/* ---------- views ---------- */
CREATE OR ALTER VIEW core.v_bet_clv AS
SELECT b.*, g.game_date, g.away_code, g.home_code,
       CASE WHEN b.close_price IS NULL THEN NULL
            ELSE (CASE WHEN b.close_price < 0 THEN -b.close_price*1.0/(100-b.close_price) ELSE 100.0/(100+b.close_price) END)
               - (CASE WHEN b.price_american < 0 THEN -b.price_american*1.0/(100-b.price_american) ELSE 100.0/(100+b.price_american) END)
       END AS clv_prob_pts
FROM core.bets b JOIN core.games g ON g.game_id = b.game_id;
GO
CREATE OR ALTER VIEW core.v_rule_record AS
SELECT c.league, r.value AS rule_code, COUNT(*) AS bets,
       SUM(CASE WHEN c.result='W' THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN c.result='L' THEN 1 ELSE 0 END) AS losses,
       SUM(c.profit_units) AS units, SUM(c.units) AS risked,
       SUM(c.profit_units)/NULLIF(SUM(c.units),0) AS roi,
       AVG(c.clv_prob_pts) AS avg_clv
FROM core.v_bet_clv c
CROSS APPLY STRING_SPLIT(REPLACE(ISNULL(c.rule_codes,'UNTAGGED'),'+',','), ',') r
WHERE c.result IS NOT NULL
GROUP BY c.league, r.value;
GO
/* Latest price per game/book/market/side before a given snapshot purpose (e.g. close) */
CREATE OR ALTER VIEW core.v_closing_odds AS
SELECT o.*, s.pulled_at_utc
FROM core.odds o
JOIN core.odds_snapshots s ON s.snapshot_id = o.snapshot_id
WHERE s.purpose = 'close';
GO

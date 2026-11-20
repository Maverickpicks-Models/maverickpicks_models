/* Phase 2: past-season game logs and the historical odds pull log. Re-runnable. */
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
USE MaverickPicks;
GO
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
IF OBJECT_ID('nba.team_game_log') IS NULL
CREATE TABLE nba.team_game_log (
    season      varchar(7)   NOT NULL,     -- 2025-26
    nba_game_id varchar(12)  NOT NULL,
    game_date   date         NOT NULL,
    team_code   char(3)      NOT NULL,
    opp_code    char(3)      NOT NULL,
    is_home     bit          NOT NULL,
    wl          char(1)      NULL,
    mins        smallint     NULL,
    pts smallint NULL, opp_pts smallint NULL, fgm smallint NULL, fga smallint NULL, fg3m smallint NULL, fg3a smallint NULL,
    ftm smallint NULL, fta smallint NULL, oreb smallint NULL, dreb smallint NULL, reb smallint NULL, ast smallint NULL,
    stl smallint NULL, blk smallint NULL, tov smallint NULL, pf smallint NULL, plus_minus smallint NULL,
    CONSTRAINT PK_team_game_log PRIMARY KEY (nba_game_id, team_code)
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_team_game_log_team')
    CREATE INDEX IX_team_game_log_team ON nba.team_game_log (team_code, game_date);
GO
IF OBJECT_ID('core.hist_pulls') IS NULL
CREATE TABLE core.hist_pulls (
    league        varchar(5)   NOT NULL,
    game_date     date         NOT NULL,
    kind          varchar(12)  NOT NULL,   -- events / bet / early / close
    snap_utc      datetime2(0) NOT NULL,   -- requested historical timestamp
    snapshot_id   int          NULL,
    games         int          NULL,
    credits_used  int          NULL,
    pulled_at     datetime2(0) NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT PK_hist_pulls PRIMARY KEY (league, game_date, kind, snap_utc)
);
GO

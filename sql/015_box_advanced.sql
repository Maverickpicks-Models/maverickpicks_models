/* Advanced box scores (second table on the BoxScores and TeamBoxAdvanced sheets). Re-runnable. */
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
USE MaverickPicks;
GO
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
IF OBJECT_ID('nba.player_box_adv') IS NULL
CREATE TABLE nba.player_box_adv (
    player nvarchar(80) NOT NULL, team_code char(3) NOT NULL, matchup varchar(20) NULL, game_date date NOT NULL,
    wl char(1) NULL, mins float NULL, off_rtg float NULL, def_rtg float NULL, net_rtg float NULL,
    ast_pct float NULL, ast_to float NULL, ast_ratio float NULL, oreb_pct float NULL, dreb_pct float NULL,
    reb_pct float NULL, tov_ratio float NULL, efg_pct float NULL, ts_pct float NULL, usg_pct float NULL,
    pace float NULL, pie float NULL,
    CONSTRAINT PK_player_box_adv PRIMARY KEY (player, team_code, game_date)
);
GO
IF OBJECT_ID('nba.team_box_adv') IS NULL
CREATE TABLE nba.team_box_adv (
    team_code char(3) NOT NULL, matchup varchar(20) NULL, game_date date NOT NULL, wl char(1) NULL, mins float NULL,
    off_rtg float NULL, def_rtg float NULL, net_rtg float NULL, ast_pct float NULL, ast_to float NULL,
    ast_ratio float NULL, oreb_pct float NULL, dreb_pct float NULL, reb_pct float NULL, tov_pct float NULL,
    efg_pct float NULL, ts_pct float NULL, pace float NULL, pie float NULL,
    CONSTRAINT PK_team_box_adv PRIMARY KEY (team_code, game_date)
);
GO

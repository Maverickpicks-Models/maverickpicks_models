/* Daily snapshots of the workbook's ratings and stats sheets. Re-runnable.
   Each import stores every row of each sheet as JSON (header -> value), so a layout change in a sheet
   never breaks the load; the views below pull out the columns we use. */
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
USE MaverickPicks;
GO
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
IF OBJECT_ID('nba.snapshots') IS NULL
CREATE TABLE nba.snapshots (
    snapshot_id    int IDENTITY(1,1) PRIMARY KEY,
    snapshot_date  date          NOT NULL,           -- the day the workbook was imported (ratings through the night before)
    source_file    nvarchar(400) NULL,
    loaded_at      datetime2(0)  NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_nba_snapshots_date UNIQUE (snapshot_date)
);
GO
IF OBJECT_ID('nba.sheet_rows') IS NULL
CREATE TABLE nba.sheet_rows (
    snapshot_id  int            NOT NULL,
    sheet        varchar(40)    NOT NULL,
    row_num      int            NOT NULL,
    entity       nvarchar(80)   NOT NULL,          -- team or player name (CraftedNBA: matchup)
    team_code    char(3)        NULL,
    data         nvarchar(max)  NOT NULL,          -- JSON: {"header": value, ...}
    CONSTRAINT PK_sheet_rows PRIMARY KEY (snapshot_id, sheet, row_num)
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_sheet_rows_entity')
    CREATE INDEX IX_sheet_rows_entity ON nba.sheet_rows (sheet, entity, snapshot_id);
GO
CREATE OR ALTER VIEW nba.v_team_ratings AS
SELECT s.snapshot_date, r.team_code, r.entity AS team,
       TRY_CAST(JSON_VALUE(r.data, '$.W') AS int)          AS w,
       TRY_CAST(JSON_VALUE(r.data, '$.L') AS int)          AS l,
       TRY_CAST(JSON_VALUE(r.data, '$.NRtg') AS float)     AS site_nrtg,
       TRY_CAST(JSON_VALUE(r.data, '$.ORtg') AS float)     AS site_ortg,
       TRY_CAST(JSON_VALUE(r.data, '$.DRtg') AS float)     AS site_drtg,
       TRY_CAST(JSON_VALUE(r.data, '$.Pace') AS float)     AS pace,
       TRY_CAST(JSON_VALUE(t.data, '$."Roster ORtg"') AS float) AS roster_ortg,
       TRY_CAST(JSON_VALUE(t.data, '$."Roster DRtg"') AS float) AS roster_drtg,
       TRY_CAST(JSON_VALUE(t.data, '$."Roster NRtg"') AS float) AS roster_nrtg,
       TRY_CAST(JSON_VALUE(t.data, '$."Lost min"') AS float)    AS lost_min,
       TRY_CAST(JSON_VALUE(h.data, '$."Net luck /100"') AS float) AS shooting_luck
FROM nba.sheet_rows r
JOIN nba.snapshots s ON s.snapshot_id = r.snapshot_id
LEFT JOIN nba.sheet_rows t ON t.snapshot_id = r.snapshot_id AND t.sheet = 'TeamRatings'  AND t.team_code = r.team_code
LEFT JOIN nba.sheet_rows h ON h.snapshot_id = r.snapshot_id AND h.sheet = 'TeamShooting' AND h.team_code = r.team_code
WHERE r.sheet = 'Ratings_2026_27';
GO
CREATE OR ALTER VIEW nba.v_player_ratings AS
SELECT s.snapshot_date, r.entity AS player, r.team_code,
       TRY_CAST(JSON_VALUE(r.data, '$."Exp MPG"') AS float)     AS exp_mpg,
       JSON_VALUE(r.data, '$.Status')                           AS status,
       TRY_CAST(JSON_VALUE(r.data, '$."Off rating"') AS float)  AS off_rating,
       TRY_CAST(JSON_VALUE(r.data, '$."Def rating"') AS float)  AS def_rating,
       TRY_CAST(JSON_VALUE(r.data, '$."MP 26-27"') AS float)    AS mp_season,
       TRY_CAST(JSON_VALUE(r.data, '$."OBPM 26-27"') AS float)  AS obpm,
       TRY_CAST(JSON_VALUE(r.data, '$."DBPM 26-27"') AS float)  AS dbpm
FROM nba.sheet_rows r JOIN nba.snapshots s ON s.snapshot_id = r.snapshot_id
WHERE r.sheet = 'PlayerRatings';
GO

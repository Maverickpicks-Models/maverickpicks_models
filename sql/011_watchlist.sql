/* Watch list for tonight's bets and the injury alerts already sent. Re-runnable. */
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
USE MaverickPicks;
GO
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
IF OBJECT_ID('core.watchlist') IS NULL
CREATE TABLE core.watchlist (
    watch_id    int IDENTITY(1,1) PRIMARY KEY,
    league      varchar(5)    NOT NULL DEFAULT 'NBA',
    game_date   date          NOT NULL,
    matchup     varchar(12)   NOT NULL,          -- as printed on the injury report, e.g. DET@NOP
    bet_label   nvarchar(120) NOT NULL,          -- e.g. Pistons -4.5 ($13)
    tip_et      time(0)       NULL,
    created_at  datetime2(0)  NOT NULL DEFAULT SYSDATETIME()
);
GO
IF OBJECT_ID('core.injury_alerts') IS NULL
CREATE TABLE core.injury_alerts (
    league     varchar(5)    NOT NULL,
    game_date  date          NOT NULL,
    matchup    varchar(12)   NOT NULL,
    player     nvarchar(80)  NOT NULL,
    status     varchar(20)   NOT NULL,
    report_id  int           NOT NULL,
    sent_at    datetime2(0)  NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT PK_injury_alerts PRIMARY KEY (league, game_date, matchup, player, status)
);
GO

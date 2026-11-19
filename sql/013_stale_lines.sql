/* Stale-line scanner: Novig prices that lag the sharp market (Pinnacle no-vig). Re-runnable. */
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
USE MaverickPicks;
GO
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
IF OBJECT_ID('core.stale_lines') IS NULL
CREATE TABLE core.stale_lines (
    stale_id      int IDENTITY(1,1) PRIMARY KEY,
    snapshot_id   int           NOT NULL,
    game_id       int           NOT NULL,
    market        varchar(20)   NOT NULL,      -- h2h / spreads / totals
    side          varchar(10)   NOT NULL,      -- away / home / over / under
    novig_point   decimal(6,1)  NULL,
    novig_price   int           NOT NULL,
    novig_prob    decimal(6,4)  NOT NULL,
    sharp_point   decimal(6,1)  NULL,
    fair_prob     decimal(6,4)  NOT NULL,      -- Pinnacle no-vig, moved to Novig's line
    edge          decimal(6,4)  NOT NULL,      -- fair_prob - novig_prob
    sharp_move    decimal(6,4)  NULL,          -- change in Pinnacle fair prob since the previous scan
    novig_move    decimal(6,4)  NULL,          -- change in Novig prob since the previous scan
    alerted       bit           NOT NULL DEFAULT 0,
    found_at_utc  datetime2(0)  NOT NULL DEFAULT SYSUTCDATETIME()
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_stale_lines_game')
    CREATE INDEX IX_stale_lines_game ON core.stale_lines (game_id, market, side, found_at_utc);
GO
INSERT INTO core.config (config_key, config_value, is_secret)
SELECT v.k, v.val, 0 FROM (VALUES ('STALE_MIN_EDGE', '0.03'), ('STALE_SHARP_BOOK', 'pinnacle')) v(k, val)
WHERE NOT EXISTS (SELECT 1 FROM core.config c WHERE c.config_key = v.k);
GO

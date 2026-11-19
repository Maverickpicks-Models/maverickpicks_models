/* Remove exchange placeholder prices stored before the 11/19 parser fix (empty Novig books show up as
   lines like Over 280.5 at -99900). Safe to re-run. */
USE MaverickPicks;
GO
DELETE FROM core.odds WHERE market <> 'h2h' AND ABS(price_american) >= 1000;
DELETE FROM core.odds WHERE ABS(price_american) >= 50000;
GO
/* Closing line per game: the last 'close' snapshot taken before tip. Novig if it has a sane price,
   otherwise Pinnacle, otherwise the median of the other books. */
CREATE OR ALTER VIEW core.v_closing_line AS
WITH c AS (
    SELECT o.game_id, o.bookmaker, o.market, o.side, o.team_code, o.point, o.price_american, o.implied_prob,
           ROW_NUMBER() OVER (PARTITION BY o.game_id, o.bookmaker, o.market, o.side, ISNULL(o.team_code, '')
                              ORDER BY s.pulled_at_utc DESC) AS rn
    FROM core.odds o
    JOIN core.odds_snapshots s ON s.snapshot_id = o.snapshot_id
    JOIN core.games g ON g.game_id = o.game_id
    WHERE s.purpose IN ('close', 'pregame') AND (g.start_utc IS NULL OR s.pulled_at_utc <= g.start_utc)
)
SELECT game_id, bookmaker, market, side, team_code, point, price_american, implied_prob
FROM c WHERE rn = 1;
GO

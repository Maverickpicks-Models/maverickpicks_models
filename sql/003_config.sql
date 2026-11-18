/* Store the Odds API key in the database (run once; replace the placeholder).
   The key is read by the Python jobs through Windows authentication, so no password lives in the code.
   Keep the database on your machine and limit logins to your Windows account. */
USE MaverickPicks;
GO
MERGE core.config AS t
USING (VALUES
  ('ODDS_API_KEY',      N'PASTE-YOUR-KEY-HERE', 1),
  ('ODDS_BOOKMAKERS',   N'novig,draftkings,fanduel,betmgm,williamhill_us,espnbet,betrivers,fanatics,hardrockbet,pinnacle', 0),
  ('ODDS_TEAM_TOTALS',  N'1', 0),   -- 1 = pull team totals per game (1 credit per game per snapshot)
  ('RULEBOOK_VERSION',  N'v5', 0)
) AS s(config_key, config_value, is_secret)
ON t.config_key = s.config_key
WHEN MATCHED AND s.config_key <> 'ODDS_API_KEY' THEN UPDATE SET config_value = s.config_value, updated_at = SYSUTCDATETIME()
WHEN NOT MATCHED THEN INSERT (config_key, config_value, is_secret) VALUES (s.config_key, s.config_value, s.is_secret);
GO
/* Set or rotate the key later with:
   UPDATE core.config SET config_value = N'<your key>', updated_at = SYSUTCDATETIME() WHERE config_key = 'ODDS_API_KEY'; */

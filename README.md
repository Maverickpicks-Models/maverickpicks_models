# MaverickPicks Models

Data pipeline and models for the MaverickPicks NBA and NHL betting models.
SQL Server holds the data, Python does the work, Power BI and Excel are the views.

## Phase 1 (this release)

| Piece | What it does | Command |
|---|---|---|
| `sql/001_schema.sql` | Database `MaverickPicks`: games, odds snapshots, injury reports, model runs, recommendations, bets, box scores, config, API usage; CLV and rule-record views | run once (setup script) |
| `sql/002_seed_teams.sql` | NBA and NHL teams and name aliases (Odds API, NBA injury report, workbook spellings) | run once |
| `sql/003_config.sql` | Config table: Odds API key, bookmaker list, team-total switch, rulebook version | run once, then set the key |
| `mpm.oddsapi` | Pulls Novig + up to 9 other books from TheOddsAPI, stores every price as a timestamped snapshot, logs credits | `python -m mpm.oddsapi --league NBA --purpose pregame` |
| `mpm.oddsapi --close-window 15` | Closing snapshot for each game tipping within 15 minutes (once per game) | scheduled every 10 min in the evening |
| `mpm.injuries` | Downloads and parses the official NBA injury report PDF into rows | `python -m mpm.injuries --fetch C:\MaverickPicks\injury_reports` |
| `mpm.load_workbook` | Imports the Excel model: Tracking (games, scores, every bet, close odds), legacy projections, team and player box scores | `python -m mpm.load_workbook "C:\path\MaverickPicks_NBA_Simulations.xlsx"` |

## Setup (Windows, one time)

```powershell
git clone https://github.com/Maverickpicks-Models/maverickpicks_models.git
cd maverickpicks_models
.\scripts\setup.ps1 -Server ECG-L028
sqlcmd -S ECG-L028 -E -d MaverickPicks -Q "UPDATE core.config SET config_value=N'<YOUR ODDS API KEY>' WHERE config_key='ODDS_API_KEY'"
python -m mpm.oddsapi --league NBA --test        # costs at most 1 credit
python -m mpm.load_workbook "C:\...\MaverickPicks_NBA_Simulations.xlsx"
.\scripts\register_tasks.ps1                      # or -FreePlan while on the 500-credit plan
```

Windows authentication is used for the database, so no passwords are stored anywhere.
The Odds API key lives only in `core.config` (`is_secret = 1`).

## Odds API credits

| Job | Credits | Per month (both leagues, ~7.5 games/night) |
|---|---|---|
| Open, 10:30 AM (moneyline/spread/total) | 3 per league | ~180 |
| Pregame, 6:00 PM (+ team totals per game) | 3 + 1 per game | ~630 |
| Close, each game ~15 min before tip (4 markets) | 4 per game | ~1,800 |
| **Total** | | **~2,600** (20K plan) |

`register_tasks.ps1 -FreePlan` schedules only the NBA pregame pull with the main markets (about 90 credits a month).
Check `core.api_usage` or `credits_remaining` on `core.odds_snapshots` to track usage.

## Useful queries

```sql
-- latest Novig prices for tonight
SELECT g.away_code, g.home_code, o.market, o.side, o.team_code, o.point, o.price_american
FROM core.odds o JOIN core.games g ON g.game_id = o.game_id
WHERE o.snapshot_id = (SELECT MAX(snapshot_id) FROM core.odds_snapshots WHERE league='NBA')
  AND o.bookmaker = 'novig' ORDER BY g.game_id, o.market, o.side;

-- record, ROI and CLV by rule
SELECT * FROM core.v_rule_record ORDER BY bets DESC;

-- who is out tonight (latest report)
SELECT matchup, team_name, player, status, reason FROM core.injury_status
WHERE report_id = (SELECT MAX(report_id) FROM core.injury_reports) AND status IN ('Out','Doubtful','Questionable');
```

Power BI: Get Data → SQL Server → `ECG-L028`, database `MaverickPicks`, DirectQuery or Import. Start with
`core.v_bet_clv` and `core.v_rule_record`.

## Tests

```powershell
python -m pytest tests -q
```
The tests use an in-memory SQLite stand-in for SQL Server, so they run without the database.

## Roadmap

1. **Phase 1, foundation**: schema, odds pull, injury parser, workbook import (this release)
2. **Phase 2, history**: 2 past seasons with closing lines; re-test every rule walk-forward
3. **Phase 3, automation**: nightly projections, rules engine, cards and Tracking from the database; Power BI dashboard
4. **Phase 4, market-error model**: model the line's miss, quarter-Kelly sizing
5. **Phase 5, expansion**: line movement, lineups/on-off, first half, team totals, NHL model migration

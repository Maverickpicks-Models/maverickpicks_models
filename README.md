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
| `sql/010_nhl_schema.sql` | NHL tables: `nhl.game_results` (score before the shootout, shootout winner), `nhl.projection_detail`, MoneyPuck `nhl.team_season` / `nhl.goalie_season` (dated snapshots), `nhl.mp_stat` (MoneyPuck CSVs, long format), `nhl.model_settings`; view `nhl.v_rule_record` (flat ROI, so $0 track-only bets still show) | run once (setup script) |
| `mpm.nhl_workbook` | Imports the NHL Excel model: Tracking (games with official final scores, every bet incl. $0 track-only, close odds, rule codes), legacy projections, the bet-time Novig board, MoneyPuck team/goalie tables, Assumptions | `python -m mpm.nhl_workbook "C:\path\MaverickPicks_NHL_Simulations_v2.xlsx"` |
| `mpm.moneypuck` | Downloads MoneyPuck `teams.csv` + `goalies.csv` into dated snapshots (`nhl.mp_stat`) | `python -m mpm.moneypuck --fetch C:\MaverickPicks\moneypuck` |
| `mpm.nhl_slate` | Tonight's NHL card from the database: latest odds snapshot (Novig moneyline/total; team totals from Novig or the books' consensus), MoneyPuck tables, rulebook + $1,000 bankroll stakes, a minimum Novig price for every play; saves `core.recommendations` and renders the Discord graphics | `python -m mpm.nhl_slate --goalie "BOS=Swayman!" --goalie "DET=Talbot!"` |
| `mpm.stale` | After every odds pull, flags Novig prices that lag Pinnacle's no-vig fair price by 3%+ (Windows alert, `core.stale_lines`); a 10-minute scan job runs 4-11 PM | runs automatically; `python -m mpm.stale` to scan now |
| `mpm.watch` | Tonight's bets; after every injury report it pops up a Windows alert when a 20+ mpg player in one of those games goes Out/Doubtful or comes back before tip | `python -m mpm.watch set "DET@NOP\|Pistons -4.5 ($13)\|8:05PM" ...` |
| `mpm.load_workbook` | Imports the Excel model: Tracking (games, scores, every bet, close odds, rule codes), legacy projections, team and player box scores (basic + advanced), and a dated snapshot of the ratings/stats sheets (`nba.v_team_ratings`, `nba.v_player_ratings`) | `python -m mpm.load_workbook "C:\path\MaverickPicks_NBA_Simulations.xlsx"` |

## Setup (Windows, one time)

```powershell
git clone https://github.com/Maverickpicks-Models/maverickpicks_models.git
cd maverickpicks_models
.\scripts\setup.ps1 -Server ECG-L028
sqlcmd -S ECG-L028 -E -d MaverickPicks -Q "UPDATE core.config SET config_value=N'<YOUR ODDS API KEY>' WHERE config_key='ODDS_API_KEY'"
py -m mpm.oddsapi --league NBA --test            # costs at most 1 credit
py -m mpm.load_workbook "C:\...\MaverickPicks_NBA_Simulations.xlsx"
.\scripts\register_tasks.ps1                      # or -FreePlan while on the 500-credit plan
py -m mpm.watch test                               # should pop up a test notification
```

If `python` opens the Microsoft Store, use the `py` launcher (as above) or set `$env:MPM_PYTHON` to your python.exe.
Windows authentication is used for the database, so no passwords are stored anywhere.
The Odds API key lives only in `core.config` (`is_secret = 1`).

## NHL notes

- Scores: `core.games` holds the **official final** (the shootout winner is credited one goal), which is how Novig settles
  totals and team totals. `nhl.game_results` keeps the regulation+OT score and the shootout winner as typed in Tracking.
- Rule codes are comma-separated as in the workbook (`HU,GU`). `OFF` = picks made outside the rules, `UNTAGGED` = a bet
  with no code. Query `nhl.v_rule_record` for NHL (it adds `roi_flat` and `staked_bets`).
- `--as-of` on the NHL importer stamps the pasted MoneyPuck tables with the date they were taken (default today);
  each date is kept, so history builds up for point-in-time testing. Finished seasons keep one copy.
- MoneyPuck data: free for non-commercial use; other uses need MoneyPuck's permission, and MoneyPuck should be credited
  where its data feeds published picks. `register_tasks.ps1` only schedules the download with `-MoneyPuck`.

### Nightly NHL card

```powershell
& $py -m mpm.nhl_slate --dry-run --goalie "BOS=Swayman!" --goalie "DET=Talbot"   # print only
& $py -m mpm.nhl_slate --goalie "BOS=Swayman!" --goalie "DET=Talbot!"            # save + graphics
```
`!` marks a goalie confirmed on goaliepost (the GU rule needs it); last names are enough. Back-to-backs are found from
yesterday's games in `core.games`; add others with `--b2b TEAM,TEAM`. Graphics go to `C:\MaverickPicks\cards\<date>`
(PNG needs `pip install playwright` then `python -m playwright install chromium`; otherwise HTML).
Engine: `mpm.nhl_model` (same math as the workbook; checked to match it exactly). Rules and stakes: `mpm.nhl_rules`.

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

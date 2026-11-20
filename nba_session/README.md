# NBA nightly engine (Claude session scripts)

These are the scripts Claude runs in the **NBA Model** project to build the nightly card from the Excel workbook,
copied here so a new conversation can pick them up (`git clone` the repo, then work from this folder).
They are the "Phase 0" engine: the NBA model still lives in Excel; Phase 3 moves it into `src/mpm`.
Paths in the scripts are relative to this folder (`work/...`, `inMMDD/...`).

| File | What it does |
|---|---|
| `work/prod.py` | Python port of the workbook's projection (roster ratings, injuries, B2B, pace). `Prod('inMMDD/s3.xlsx')` |
| `work/runMMDD.py` | One night's projections: Novig lines in `G`, B2B set, outs from `work/outs_MMDD.py` -> `work/runMMDD.json` |
| `work/rules.py` | Rulebook v5.1 engine (C1-C4, K1-K4, T1-T12, X1-X8, ROI unit pricing; P1/P2 $5 from 11/20, needs WB set to the workbook) -> `work/runMMDD_recs.json` |
| `work/cards_v7.py`, `work/summary_card.py` | Game cards and the recommended card (Playwright PNG) |
| `work/add_tracking_MMDD.py` | Writes a night's games, bets (one row per bet, rule codes in AW) and scores into Tracking |
| `work/rule_tags_backfill.py` | Rule codes for bets since 11/12 from the saved engine outputs |
| `work/rules_sheet_v5.py` | Writes the Rules tab |
| `audit/*.py` | Research: CLV, favorite-size curve, fatigue (T12), luck/style, angles 3-4 |

## Nightly card
1. `mkdir in1120 && cp <workbook> in1120/s3.xlsx`
2. Outs: parse the official PDF with `python -c "from mpm.injuries import parse"`; write `work/outs_MMDD.py`
   (`OUTS={'First Last': 1 | 0.5}`: Out/Doubtful 1, Questionable 0.5, skip G League).
3. Copy `work/run1119.py` to `work/runMMDD.py`; set the workbook/outs/output paths, `B2B`, and `G`:
   `(away, home, (away_spread, away%, home%), (total, over%, under%), (ml_away%, ml_home%), (away_tt, o%, u%), (home_tt, o%, u%))`
   with Novig prices as decimals. Run it.
4. `work/cfg_MMDD.json`: `{"date", "b2b": [...], "stars_out": [teams missing a 30+ mpg player], "crafted": {"Away|Home": {"home_margin", "total"}}}`
5. `WB=inMMDD/s3.xlsx python3 work/rules.py work/runMMDD.json work/cfg_MMDD.json`
6. Size in dollars per `claude/nba-bankroll.md` (project doc): 1u = 2% of bankroll, $20/bet, $30/game, $120/night,
   C1 not on 10+ favorites, no test/K1 spreads on 5-9.5 or 10+ favorites, X5-flagged test totals passed,
   Questionable 30+ mpg starter -> half stake, max price +1.5 (sides) / +1.0 (totals).
7. Cards: write `work/recs_MMDD.json` and `work/summary_MMDD.json` (see the 1119 files), then
   `CARD_DATE=MM/DD/YY python3 work/cards_v7.py work/runMMDD.json cards_MMDD work/recs_MMDD.json` and
   `python3 work/summary_card.py work/summary_MMDD.json cards_MMDD/00_recommended_card.png`
8. Give the watch-list line: `& $py -m mpm.watch set "AWY@HOM|Bet ($x)|8:05PM" ...`

## Results
1. Scores from the sports data tool; `work/bets_MMDD.json` (what was placed: price %, stake, rules).
2. Copy `work/add_tracking_1119.py`: scores `SC`, first empty Tracking row, Excel date serial
   (`(date - 1899-12-30).days`), run json. `python3 work/add_tracking_MMDD.py <in.xlsx> <out.xlsx>`
3. Recalculate with LibreOffice (`soffice --headless --convert-to xlsx`) and check grades/profit (AS/AT).
4. Update `claude/nba-daily-log-bankroll.md` and the ledger in `claude/nba-bankroll.md`.

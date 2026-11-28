# MaverickPicks NBA · bankroll plan (CEO mandate, from 11/18)

User mandate 11/18: run the NBA betting as a business with a $1,000 starting bankroll, size every bet in dollars to maximize long-run profit, rebase on the balance the user sends each Monday, keep searching for new rules and close rules that stop earning.

## Current: Rulebook v5.3 (from 11/28) = v5.2 + the 11/28 changes
User, 11/28: "Analyze the results and make changes to rules if necessary." The live card is the engine `nba_session/work/rules.py`.

**v5.3 changes (11/28), from the live Tracking record since 11/18 and the season replay:**
1. **T11 (home favorite ≤4.5 spread) → paper.** Live 2-9, −63% (0-4 on 11/27: Knicks, Wolves, Suns and Clippers all lost outright). The replay had it +19% (24-16), but 0-2 since 11/18 there too.
2. **T10 (ML favorite 50-60%, spread ≤4.5) → paper.** It is the moneyline twin of T11. Live 5-7, −25% (3-7 since 11/18).
3. **T6 (team missing a star) → paper.** Live 7-8, −9%; replay 3-9, −51% (1-7 since 11/18).
4. **One bet per team per game.** We never bet a team's ML when we already back that team on the spread, at any spread size. This extends the v5.2 rule for spreads under 2. On 11/27 the spread+ML pairs went 0-8 and lost ≈ $43.
5. **C4 (fade the model total, 6+ off) $15 → $20.** Live 9-4, +38%; replay 25-10, +42%.
6. **P1 and P3 $5 → $10.** P3 live 8-3, +46% (replay 30-20, +20%); P1 live 5-3, +23% (replay 19-12, +21%). P2 stays at $5.
- **Kept, not cut:** T2 stays at $10. Live it is 16-11, +18%, although the replay showed 10-19 since 11/18; this split is the reason to watch it. K1 (10-12, −11% live) stays as confirmation; K1 alone is watched.
- **Backtest of 11/27 under v5.3:** 9-6, +$37.52 on $120.50, vs the card as played at 10-11, +$2.44. That is in-sample, chosen after seeing the night, so it doesn't prove v5.3; the changes rest on the 11-night live record.

**v5.2 changes (11/23), still in force:**
1. **T7 (both team-total Overs) → paper.** 0-5 live.
2. **Injury cuts only when CraftedNBA also disagrees.** Our model can't see injuries after ~20 games. Cut a model bet on a team missing two or more 30+ mpg players **only if CraftedNBA's line is on the other side or no better than the market**. (Card-building rule, applied by Claude; not coded.)
3. Spread under 2: no ML on the same team (now widened to all spreads by v5.3 #4).

Rulebook v6.1 is **parked**, not live. Evidence: `claude/nba-backtest-2025-26.md`, `claude/nba-season-quarters.md`, `claude/nba-season-months.md`, `claude/nba-season-replay.md`.

## Sizing policy
- **1 unit = 2% of the current bankroll: $20 at $989 (rebased 11/23); $21 from Monday 11/30 if the balance is still ≈ $1,031 (2% = $20.63).** Recalculated every Monday from the balance the user reports, rounded to the dollar.
- **Caps:** single bet $20 (1u); same game $30; night $120. If the card is bigger, cut big-favorite MLs (75%+) first, then scale the rest down in proportion.
- **Rule caps:** core 1u, CraftedNBA 0.75u, test 0.5u (P1/P2/P3 add on top, below).
- **Max price:** spreads/ML current Novig % + 1.5; totals current + 1.0.
- **Questionable starters:** a 30+ mpg starter Questionable at bet time → half stake on bets backing that team, or wait for the last report.
- **Injury alerts:** every bet goes on the watch list (`mpm.watch set`); 15-minute report checks alert when a 20+ mpg player in one of those games changes before tip.
- **Stale Novig lines (S1 v2, test, from 11/20):** alert only when Novig gives a side 3%+ more than Pinnacle's no-vig fair price **and** Pinnacle's fair price for that side rose 1.5%+ since the previous pull while Novig moved less than half as much. $5 after confirming the price, up to $20 a night outside the night cap.
- **CLV benchmarks:** Pinnacle no-vig close judges rules; Novig close judges execution and timing.
- **Drawdown brakes:** 20% below the last peak → 1.5%; 35% below → 1% and favorites only; back up after a new peak.

## Rule sizing (dollars at 1u = $20)
| Group | Rule | Units | $ |
|---|---|---|---|
| Core | C1 model spread 3-6 off (10+ point favorites → paper) | 0.75 | $15 |
| | C2 road fav ≤4.5 ATS | 0.75 | $15 |
| | C3 ML fav 60%+ (not 65-75%, not with a 5-9.5 spread, X7 over 87%) | to win 0.25u, max risk 1u | win $5, risk ≤ $20 |
| | **C4 fade model total 6+ off** | **1.0** | **$20** |
| CraftedNBA | K1 favorites | 0.5 | $10 |
| | K2 dogs we agree with; K3 Unders 2+ below the line | 0.25 | $5 |
| | K4 skip their Overs | — | — |
| Test | T1 juiced Over → Under, T2 turnovers, T3 fav TT U + dog TT O, T5 top-10 vs bottom-10, T9 home B2B vs rested road | 0.5 | $10 |
| | T8 total 235+, T12 more tired team | 0.25 | $5 |
| | **P1 fade the 3P-lucky team** (spread) | flat | **$10** |
| | P2 ML on the clearly better team | flat risk | $5 |
| | **P3 Under when both teams play slow** | flat | **$10** |
- **Paper:** T4, T7 (11/23), **T6, T10, T11 (11/28)**, C1 on 10+ point favorites.
- Stacking (v4): core spread + T5/T9 → 1u; stacked totals get no bonus; T8 with T2/T3 Unders → 0.25u; an X1/X5 flag drops one tier.
- **Avoid rules:** X1 model 6+ off the spread, X2 home dogs 0.5-4.5, X3 dogs +200 or longer, X5 core Under when the model is 3+ below the line (one tier down for tests), X6 opposite CraftedNBA's side, X7 ML favs over 87%, X8 C3 ML when a spread rule backs the other team, **one bet per team per game (v5.3)**. Two-sided markets pass.

## P1, P2, P3 (added 11/20)
Inputs come from the workbook: Ratings_2026_27 (season ORtg/DRtg/pace) minus TeamShooting luck, i.e. season-only ratings with no roster prior.
- **P1 fade the 3P-lucky team:** bet the spread against a team whose Net luck/100 is +0.47 or more, when our season-only margin is 1.8+ points better than the line for our side (both teams 8+ games). 2025-26: 214-161, +14%; 2026-27: 46-39, +8%. Live 5-3. **$10 from 11/28.**
- **P2 ML on the clearly better team:** luck-adjusted net-rating gap +3.63 or more and season-only margin 1.8+ better than the line → that team's ML, $5 risk. Skipped above 87% (X7) and, from 11/28, when we already back that team on the spread. Live 3-1.
- **P3 slow-pace Under:** pace sum −1.15 or lower → Under. 2025-26: 222-177, +11%; 2026-27: 40-34, +8%. Live 8-3. **$10 from 11/28.**
- Alone: their stake. On the same side as another play: that play's stake + their stake (inside the $30 game cap).
- Review after 30 bets each: keep if ROI and Pinnacle CLV are positive, otherwise back to paper.

## Calendar proposals (pending 2024-25 confirmation; not live)
- 12/12-1/20 (2025-26 dog window): C1 full stake, C3 off.
- From 3/1 (2025-26 Mar: C2 8-22, home teams 58-59% Mar-Apr): C2 off; home team / favorites test.
- Confirm on 2024-25 (box tables + 12/1/2024-1/31/2025 odds, ~1,800 credits) before 12/12.

## Rule lifecycle (reviewed every Monday)
- **Paper → test:** 30+ graded paper plays, shrunk ROI > +5%, positive in both halves, not negative out of sample.
- **Test → core:** positive on a past season out of sample, or 60+ live bets with Pinnacle CLV > 0 (t > 1.5).
- **Demote one tier:** Pinnacle CLV ≤ 0 after 30 bets, shrunk ROI < 0 after 40 bets, or negative out of sample.
- **Close:** shrunk ROI < 0 after 60 bets, or two demotions.
- The season replay (`work/replay_season.py`) is re-run weekly to grade every rule on every game, not only the ones bet.

## Odds API budget (20K credits/month)
Live jobs ≈ 10,000/month. 2024-25 December-January window (~1,800) next.

## Ledger
| Week of | Start | Unit | Bets | Risked | P/L | End | Notes |
|---|---|---|---|---|---|---|---|
| 11/18 | $1,000 | $20 | 49 | ≈ $475 | −$82.80 tracked | **$989 reported 11/23** | Tracked $917.20 vs Novig balance $989 (+$71.80 unreconciled). Rebased on $989. |
| 11/23 | $989 | $20 | 31 | $237 | +$42.41 | **$1,031.41 (user confirmed 11/28: Novig balance matches tracked)** | 11/23 +$39.97 (v5.2); 11/24 no bets (user confirmed); 11/25 paper only (11-6, +$11.28, not in bankroll); 11/27 all 21 played, +$2.44. v5.3 from 11/28. |

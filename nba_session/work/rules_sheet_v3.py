import re,os,sys
from xml.sax.saxutils import escape
d=sys.argv[1]
R=[('RULES FOR RECOMMENDATIONS  (updated 11/15)','','','',''),
('Each night: CORE plays first (0.5u; ML to win 0.25u, max risk 1u), TEST plays at 0.25u, CRAFTED plays at 0.5u. When two rules point at opposite sides of the same market, pass. AVOID rules override everything.','','','',''),
('','','','',''),
('Section','Rule','How to apply','Record','Size'),
('CORE','C1 Model spread 3-6 pts off','Bet our side of the spread when the model margin is 3-6 points off the Novig line. Pass at 6+.','29-17 (roster era 17-12)','0.5u'),
('CORE','C2 Road favorites under 8','Road favorite against the spread when the spread is under 8. Skip when the home team is on a B2B and the road team is rested (see T9).','16-12 roster era; vs home B2B 3-2','0.5u'),
('CORE','C3 ML favorites 60%+','Moneyline favorite when Novig no-vig price is 60-87%. Size to win 0.25u, but never risk more than 1u. Over 87% (about -700): pass (X7). Road favorites of 8+: take the ML, not the spread.','99-30, +6.3% ROI; with cap 89-29, +6.7%','to win 0.25u, max risk 1u'),
('CORE','C4 Fade model total 6+ off','When our game total is 6+ points off the line, bet the other side.','15-7 at adoption; live 2-0','0.25u (new pace drift)'),
('CRAFTED','K1 Favorites','Every CraftedNBA spread favorite (their projection 1+ off the line at the Novig number).','Follow rules live 20-16','0.5u'),
('CRAFTED','K2 Dogs we agree','CraftedNBA spread underdog only when our model also has the dog covering.','','0.5u'),
('CRAFTED','K3 Unders','CraftedNBA Unders (2+ off), ignore our totals.','','0.5u'),
('CRAFTED','K4 Skip Overs','Never play CraftedNBA Overs.','Skipped Overs 5-10','—'),
('TEST','T1 Juiced Over -> Under','Bet the Under when Novig prices the Over at 52%+.','12-4','0.25u'),
('TEST','T2 Turnover environment','Own TOV% + opponent forced TOV% (both teams): low third -> Under, high third -> Over.','Over 24-13, Under 22-14','0.25u'),
('TEST','T3 Fav TT Under + dog TT Over','Model has the favorite under its team total and the underdog over: bet the game Under.','31-20','0.25u'),
('TEST','T4 Rested home vs road B2B','Home spread when the away team is on the 2nd night of a back-to-back and home is rested.','Road B2B teams 9-9 ATS','0.25u'),
('TEST','T5 Top-10 vs bottom-10','Top-10 team (CraftedNBA points per game) against a bottom-10 opponent, against the spread.','15-10, +5.0 vs line','0.25u'),
('TEST','T6 Team missing its star','Back the team whose star (Tier A/B) is out, against the spread.','19-11','0.25u'),
('TEST','T7 Both TT Overs','Both team-total Overs when the team-total lines sum 1.5+ below the game total.','28-18','0.25u'),
('TEST','T8 Big totals Under','Under when the game total is 235+.','19-16','0.25u'),
('TEST','T9 Home B2B vs rested road (new 11/15)','Home spread when the home team is on the 2nd night of a back-to-back and the road team is rested. X2 still wins (home dogs 0.5-4.5 in this spot are 1-2).','15-9 ATS (home fav 9-6, home dog 5+ 5-1); all 5 covered 11/14','0.25u'),
('AVOID','X1','Our spread 6+ points off the line (missing information).','7-8',''),
('AVOID','X2','Home underdogs of 0.5 to 4.5.','12-21',''),
('AVOID','X3','Underdogs at +200 or longer.','6-32',''),
('AVOID','X4','Raw model edges of 8%+ (the model card).','card 12-19 on 11/11',''),
('AVOID','X5','Model Unders when our total is 3+ below the line.','actual +4.8 over the line',''),
('AVOID','X6','A core play that is the opposite side of a CraftedNBA tracked pick.','',''),
('AVOID','X7 (new 11/15)','ML favorites over 87% no-vig (about -700 or shorter). Risk too large for the edge.','87%+ 10-1, +1.9% ROI; one loss = 2u (MIN -809 on 11/14)',''),
('','','','',''),
('PROMOTION','','A TEST rule moves to CORE after about 30 live bets above break-even; a CORE rule drops to TEST if its last 30 run below break-even.','',''),
('TESTED, NOT ADOPTED','ML vs model conflict','Passing a C3 ML when the model is 3+ points the other way. Those MLs are 30-10, +5.9% ROI, same as the rest, so no rule.','',''),
('','','','',''),
('MODEL CHANGES 11/12','Back-to-back penalty','Assumptions C13 1.5 -> 2.5 (B2B teams: eFG -1.5, ORtg -2.4; opponents eFG +1.4). Model B2B error about 0 since (avg -0.5 pts).','',''),
('MODEL CHANGES 11/12','Recent league pace','Assumptions C51:C53. Matchup pace adds the last-14-day league pace change (TeamBoxAdvanced PACE). League pace by week 102.2, 99.3, 99.3, 97.2.','',''),
('MODEL CHANGES 11/12','Recent player minutes','Assumptions C49. PlayerRatings Exp MPG = minutes weighted by recency (6-day half-life) from BoxScores; season MPG if no box match.','',''),
('MODEL CHANGES 11/12','Injury impact scale','Assumptions C54 = 0.5 (set 11/13). Injured players count as half lost (set 1 for full).','',''),
('MODEL CHANGES 11/12','BoxScores duplicates','423 duplicated player rows from 11/1-11/2 cleared (they doubled those games in TeamShooting 3P luck).','',''),
('MODEL CHANGES 11/12','Not changed','Home court 2.0, pace weight 0.5, 3P luck adjustment, current-season trust 20 games.','',''),
]
def c(ref,txt,st): return f'<c r="{ref}" s="{st}" t="inlineStr"><is><t xml:space="preserve">{escape(txt)}</t></is></c>' if txt else ''
rows=[]
for i,row in enumerate(R,start=1):
    st='29' if i==1 else ('82' if i!=4 else '81')
    cells=''.join(c(f'{col}{i}',v,('80' if (col=='A' and i>4) else st)) for col,v in zip('ABCDE',row))
    rows.append(f'<row r="{i}">{cells}</row>')
xml=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
 f'<dimension ref="A1:E{len(R)}"/><sheetViews><sheetView workbookViewId="0" showGridLines="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
 '<cols><col min="1" max="1" width="22" customWidth="1"/><col min="2" max="2" width="36" customWidth="1"/><col min="3" max="3" width="95" customWidth="1"/><col min="4" max="4" width="44" customWidth="1"/><col min="5" max="5" width="22" customWidth="1"/></cols>'
 f'<sheetData>{"".join(rows)}</sheetData><pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')
open(os.path.join(d,'xl/worksheets/sheet23.xml'),'w').write(xml)
print('Rules sheet v3 written',len(R),'rows')

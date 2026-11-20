import pandas as pd, numpy as np, json, sys
sys.path.insert(0,'work')
G=pd.read_pickle('work/box_G2.pkl')
CODE={'Atlanta Hawks':'ATL','Boston Celtics':'BOS','Brooklyn Nets':'BKN','Charlotte Hornets':'CHA','Chicago Bulls':'CHI','Cleveland Cavaliers':'CLE','Dallas Mavericks':'DAL','Denver Nuggets':'DEN','Detroit Pistons':'DET','Golden State Warriors':'GSW','Houston Rockets':'HOU','Indiana Pacers':'IND','LA Clippers':'LAC','Los Angeles Lakers':'LAL','Memphis Grizzlies':'MEM','Miami Heat':'MIA','Milwaukee Bucks':'MIL','Minnesota Timberwolves':'MIN','New Orleans Pelicans':'NOP','New York Knicks':'NYK','Oklahoma City Thunder':'OKC','Orlando Magic':'ORL','Philadelphia 76ers':'PHI','Phoenix Suns':'PHX','Portland Trail Blazers':'POR','Sacramento Kings':'SAC','San Antonio Spurs':'SAS','Toronto Raptors':'TOR','Utah Jazz':'UTA','Washington Wizards':'WAS'}
T=pd.DataFrame(json.load(open('work/teamgames.json')))
T['team']=T.team.map(CODE); T['opp']=T.opp.map(CODE); T['date']=pd.to_datetime(T.date).dt.date
fix=(T.date==pd.Timestamp('2026-10-28').date())&(T.team.isin(['SAC','NOP','MEM','POR']))&(T.opp.isin(['SAC','NOP','MEM','POR']))
T.loc[fix,'date']=pd.Timestamp('2026-10-29').date()
M=G.merge(T[['date','team','mod','mkt','pts']],on=['date','team'],how='left')
print('merged',M['mod'].notna().sum(),'of',len(M),'pts match',(M.pts==M.PTS).mean())
# add roster-model projections
R=json.load(open('work/bt_recent.json'))  # not full season; use season_roster_legs games? recompute via season script data
M['e_mod']=M.PTS-M['mod']; M['e_mkt']=M.PTS-M['mkt']
for k in ['e_mod','e_mkt']:
    X=np.column_stack([np.ones(len(M)),M.luck3,M.luckFT,M.POSS-M.POSS.mean()])
    b,*_=np.linalg.lstsq(X,M[k],rcond=None); res=M[k]-X@b
    print(k,'SD',round(M[k].std(),2),'| after removing own 3P luck, FT luck, pace surprise: SD',round(res.std(),2),'R2',round(1-res.var()/M[k].var(),2),'coef 3P',round(b[1],2),'FT',round(b[2],2),'pace',round(b[3],2))
    r3=np.corrcoef(M[k],M.luck3)[0,1]**2; print('   share explained by own 3P% luck alone',round(r3,2))
# game total errors vs combined 3P luck
g=M[M.home==1].copy()
g['tot_err_mkt']=(g.PTS+g.oPTS)-(g['mkt']+M.set_index(['date','team']).loc[list(zip(g.date,g.opp)),'mkt'].values)
g['luck_tot']=g.luck3+g.oluck3
print('game total error vs market: SD',round(g.tot_err_mkt.std(),1),'| corr with both teams 3P luck',round(np.corrcoef(g.tot_err_mkt,g.luck_tot)[0,1],2),'R2',round(np.corrcoef(g.tot_err_mkt,g.luck_tot)[0,1]**2,2))
M.to_pickle('work/box_M.pkl')

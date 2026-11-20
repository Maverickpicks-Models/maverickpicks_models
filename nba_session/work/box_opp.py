import pandas as pd, numpy as np, sys, io, contextlib
sys.path.insert(0,'work')
from engine import Model
G=pd.read_pickle('work/box_G3.pkl'); P=pd.read_pickle('work/box_P2.pkl')
m=Model('in16/nba.xlsx')
FULL={'ATL':'Atlanta Hawks','BOS':'Boston Celtics','BKN':'Brooklyn Nets','CHA':'Charlotte Hornets','CHI':'Chicago Bulls','CLE':'Cleveland Cavaliers','DAL':'Dallas Mavericks','DEN':'Denver Nuggets','DET':'Detroit Pistons','GSW':'Golden State Warriors','HOU':'Houston Rockets','IND':'Indiana Pacers','LAC':'LA Clippers','LAL':'Los Angeles Lakers','MEM':'Memphis Grizzlies','MIA':'Miami Heat','MIL':'Milwaukee Bucks','MIN':'Minnesota Timberwolves','NOP':'New Orleans Pelicans','NYK':'New York Knicks','OKC':'Oklahoma City Thunder','ORL':'Orlando Magic','PHI':'Philadelphia 76ers','PHX':'Phoenix Suns','POR':'Portland Trail Blazers','SAC':'Sacramento Kings','SAS':'San Antonio Spurs','TOR':'Toronto Raptors','UTA':'Utah Jazz','WAS':'Washington Wizards'}
H=G[G.home==1].copy()
lp=m.pP
H['pa']=H.team.map(lambda t:m.R25[FULL[t]]['p']-lp); H['pb']=H.opp.map(lambda t:m.R25[FULL[t]]['p']-lp)
y=H.PACE-H.PACE.mean()
X=np.column_stack([np.ones(len(H)),H.pa+H.pb]); b,*_=np.linalg.lstsq(X,H.PACE,rcond=None); r=H.PACE-X@b
se=np.sqrt(r@r/(len(H)-2)/(((H.pa+H.pb)-(H.pa+H.pb).mean())**2).sum())
print(f"game pace vs (sum of both teams' 2025-26 pace deviations): slope {b[1]:.2f} se {se:.2f}  [model uses 0.5]; this-season league pace {H.PACE.mean():.1f} vs 2025-26 {lp:.1f}; model's blended league pace {m.LP:.1f}")
# leave-one-out current-season pace
lo=[]
for i,row in H.iterrows():
    def loo(t):
        d=G[(G.team==t)&~((G.date==row.date))]; return d.PACE.mean()
    lo.append((loo(row.team),loo(row.opp)))
H['ca']=[a for a,b_ in lo]; H['cb']=[b_ for a,b_ in lo]
X=np.column_stack([np.ones(len(H)),(H.ca-H.PACE.mean())+(H.cb-H.PACE.mean()),H.pa+H.pb]); b,*_=np.linalg.lstsq(X,H.PACE,rcond=None)
print(f"  adding this-season (leave-one-out) pace: coef this-season {b[1]:.2f}, last-season {b[2]:.2f}")
# four-factor additivity: game factor ~ team's LOO rate + opponent's LOO allowed rate
def rate(d,f):
    if f=='tov': return d.TOV.sum()/d.poss.sum()
    if f=='orb': return d.OREB.sum()/(d.OREB.sum()+d.oDREB.sum())
    if f=='ftr': return d.FTA.sum()/d.FGA.sum()
    if f=='3par': return d.TPA.sum()/d.FGA.sum()
    if f=='3p': return d.TPM.sum()/d.TPA.sum()
    if f=='efg': return (d.FGM.sum()+.5*d.TPM.sum())/d.FGA.sum()
def opp_rate(d,f):  # what opponents did vs this team
    o=G[(G.opp==d.team.iloc[0])&G.date.isin(d.date)]
    return rate(o,f)
gv={'tov':lambda r:r.TOV/r.poss,'orb':lambda r:r.OREB/(r.OREB+r.oDREB),'ftr':lambda r:r.FTA/r.FGA,'3par':lambda r:r.TPA/r.FGA,'3p':lambda r:r.TPM/r.TPA,'efg':lambda r:(r.FGM+.5*r.TPM)/r.FGA}
out=[]
for f in gv:
    xs=[];ys=[];zs=[]
    for i,row in G.iterrows():
        a=G[(G.team==row.team)&(G.date!=row.date)]; o=G[(G.team==row.opp)&(G.date!=row.date)]
        if len(a)<2 or len(o)<2: continue
        xs.append(rate(a,f)); zs.append(opp_rate(o,f)); ys.append(gv[f](row))
    xs,ys,zs=map(np.array,(xs,ys,zs))
    X=np.column_stack([np.ones(len(ys)),xs,zs]); b,*_=np.linalg.lstsq(X,ys,rcond=None); r=ys-X@b
    cov=np.linalg.pinv(X.T@X)*(r@r/(len(ys)-3)); se=np.sqrt(np.diag(cov))
    out.append((f,b[1],se[1],b[2],se[2]))
print('\nper-game factor ~ team own rate (other games) + opponent allowed rate (other games):')
for f,b1,s1,b2,s2 in out: print(f"  {f:5s} own {b1:+.2f} (se {s1:.2f})   opponent {b2:+.2f} (se {s2:.2f})")
# player scoring vs opponent defense and pace
A=pd.read_pickle('work/box_adj.pkl')
Q=P[(P.MIN>=20)].copy()
ppm=Q.groupby('PLAYER').apply(lambda d: d.PTS.sum()/d.MIN.sum())
gp=Q.groupby('PLAYER').size(); Q=Q[Q.PLAYER.map(gp)>=3]
Q['exp']=Q.apply(lambda r: (Q[(Q.PLAYER==r.PLAYER)&(Q.date!=r.date)].PTS.sum()/Q[(Q.PLAYER==r.PLAYER)&(Q.date!=r.date)].MIN.sum())*r.MIN,axis=1)
Q=Q.merge(G[['date','team','PACE']],on=['date','team'])
Q['oppD']=Q.opp.map(A.adjD); Q['ratio']=Q.PTS/Q.exp
X=np.column_stack([np.ones(len(Q)),Q.oppD,Q.PACE-Q.PACE.mean()]); b,*_=np.linalg.lstsq(X,Q.PTS-Q.exp,rcond=None); r=(Q.PTS-Q.exp)-X@b
cov=np.linalg.pinv(X.T@X)*(r@r/(len(Q)-3)); se=np.sqrt(np.diag(cov))
print(f"\nplayers 20+ min (n={len(Q)} player-games): points above own per-minute norm vs opponent defense {b[1]:+.2f}/pt of opp adjDRtg (se {se[1]:.2f}); vs game pace {b[2]:+.2f}/possession (se {se[2]:.2f})")
print('SD of player-game points vs own norm',round((Q.PTS-Q.exp).std(),1))

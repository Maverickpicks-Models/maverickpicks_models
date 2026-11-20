import pandas as pd, numpy as np, sys, unicodedata, re, io, contextlib
sys.path.insert(0,'work')
with contextlib.redirect_stdout(io.StringIO()):
    import bt_recent as BR
    import proster as PR
P=pd.read_pickle('work/box_P2.pkl'); G=pd.read_pickle('work/box_M.pkl'); A=pd.read_pickle('work/box_adj.pkl')
FULL={v:k for k,v in {'Atlanta Hawks':'ATL','Boston Celtics':'BOS','Brooklyn Nets':'BKN','Charlotte Hornets':'CHA','Chicago Bulls':'CHI','Cleveland Cavaliers':'CLE','Dallas Mavericks':'DAL','Denver Nuggets':'DEN','Detroit Pistons':'DET','Golden State Warriors':'GSW','Houston Rockets':'HOU','Indiana Pacers':'IND','LA Clippers':'LAC','Los Angeles Lakers':'LAL','Memphis Grizzlies':'MEM','Miami Heat':'MIA','Milwaukee Bucks':'MIL','Minnesota Timberwolves':'MIN','New Orleans Pelicans':'NOP','New York Knicks':'NYK','Oklahoma City Thunder':'OKC','Orlando Magic':'ORL','Philadelphia 76ers':'PHI','Phoenix Suns':'PHX','Portland Trail Blazers':'POR','Sacramento Kings':'SAC','San Antonio Spurs':'SAS','Toronto Raptors':'TOR','Utah Jazz':'UTA','Washington Wizards':'WAS'}.items()}
def nm(s):
    s=''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c)).lower()
    s=re.sub(r"[.'\-]",'',s); s=re.sub(r'\b(jr|sr|ii|iii|iv)\b','',s); return ' '.join(s.split())
BB={nm(n):n for n in PR.S['27']}
P['key']=P.PLAYER.map(nm)
miss=sorted(set(P[P.MIN>=15].key)-set(BB)); print('box players (15+ min games) not matched to BBRef:',len(miss),miss[:15])
# core players: mpg>=22 in games played, >=2 games
st=P[P.MIN>0].groupby(['team','PLAYER','key']).agg(g=('date','count'),mpg=('MIN','mean')).reset_index()
core=st[(st.mpg>=22)&(st.g>=2)]
# include players who played for team per BBRef but not in box? only box-based
teamdates=G[['team','date','opp','home']].copy()
def impact(team_code,keys):
    t=FULL[team_code]; outs={nm(BB[k]):1 for k in keys if k in BB}
    o0,d0=BR.team_rating(t,{}); o1,d1=BR.team_rating(t,{BR.nm(BB[k]):1 for k in keys if k in BB})
    return (o0+d0)-(o1+d1)
rows=[]
for _,r in teamdates.iterrows():
    played=set(P[(P.team==r.team)&(P.date==r.date)&(P.MIN>0)].key)
    c=core[core.team==r.team]
    missing=[k for k in c.key if k not in played]
    rows.append(dict(team=r.team,date=r.date,missing=missing,imp=impact(r.team,missing) if missing else 0.0))
M=pd.DataFrame(rows)
G=G.merge(M,on=['team','date'])
o=G[['date','team','imp','missing']].rename(columns={'team':'opp','imp':'oimp','missing':'omissing'})
G=G.merge(o,on=['date','opp'])
G['net']=100*(G.PTS-G.oPTS)/G.POSS
G['exp_net']=G.team.map(A.adjNet)-G.opp.map(A.adjNet)+(G.home-0.5)*2*1.65/2
G['res']=G.net-G.exp_net
G['dimp']=G.imp-G.oimp
H=G[G.home==1]
X=np.column_stack([np.ones(len(H)),H.dimp]); b,*_=np.linalg.lstsq(X,H.res,rcond=None)
res=H.res-X@b; se=np.sqrt(res@res/(len(H)-2)/((H.dimp-H.dimp.mean())**2).sum())
print(f"\nteam-games with a core player missing: {(G.imp>0).sum()} of {len(G)}")
print(f"actual net residual vs roster-model missing impact: slope {b[1]:.2f} (se {se:.2f})  [1 = roster model's size is right; expected sign negative: more missing -> worse]")
# vs market: margin residual vs spread
H=H.copy(); H['mres']=(H.PTS-H.oPTS)-(-(H['mkt']-H['mkt']))  # placeholder
mk=G.set_index(['date','team'])['mkt']
H['mkt_margin']=H['mkt']-mk.loc[list(zip(H.date,H.opp))].values
H['mres']=(H.PTS-H.oPTS)-H.mkt_margin
X=np.column_stack([np.ones(len(H)),H.dimp]); b2,*_=np.linalg.lstsq(X,H.mres,rcond=None); r2=H.mres-X@b2; se2=np.sqrt(r2@r2/(len(H)-2)/((H.dimp-H.dimp.mean())**2).sum())
print(f"margin vs market spread on the same missing impact: slope {b2[1]:.2f} (se {se2:.2f})  [0 = market prices absences right]")
big=G[G.imp>=2].sort_values('imp',ascending=False)[['date','team','opp','missing','imp','net','exp_net','res']]
big['missing']=big.missing.apply(lambda L:', '.join(x.title() for x in L))
print(big.round(1).to_string())
G.to_pickle('work/box_G3.pkl')

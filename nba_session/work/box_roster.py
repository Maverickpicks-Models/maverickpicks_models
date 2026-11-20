import pandas as pd, numpy as np, sys, unicodedata
sys.path.insert(0,'work')
P=pd.read_pickle('work/box_P.pkl'); G=pd.read_pickle('work/box_M.pkl')
P['MIN']=pd.to_numeric(P.MIN,errors='coerce').fillna(0)
P=P.merge(G[['date','team','PTS','oPTS','POSS']].rename(columns={'PTS':'tPTS'}),on=['date','team'])
P['margin']=P.tPTS-P.oPTS
# ---- rotation use ----
tg=P.groupby(['team','date'])
rot=tg.apply(lambda d: pd.Series({'n_played':(d.MIN>0).sum(),'n_12':(d.MIN>=12).sum(),'top5':d.MIN.nlargest(5).sum()/d.MIN.sum(),'top8':d.MIN.nlargest(8).sum()/d.MIN.sum(),'margin':d.margin.iloc[0]})).reset_index()
R=rot.groupby('team').agg(games=('date','count'),rot12=('n_12','mean'),top5=('top5','mean'),top8=('top8','mean'))
# top-8 stability (Jaccard between consecutive games)
def jac(d):
    d=d.sort_values('date'); sets=[set(x.nlargest(8,'MIN').PLAYER) for _,x in d.groupby('date')]
    return np.mean([len(a&b)/len(a|b) for a,b in zip(sets,sets[1:])]) if len(sets)>1 else np.nan
R['top8_stability']=P.groupby('team').apply(jac)
print('league avg: players >=12 min',round(rot.n_12.mean(),2),'| top-5 share',round(rot.top5.mean(),3),'| top-8 share',round(rot.top8.mean(),3))
print(R.sort_values('rot12').round(2).to_string())
# blowouts: starters' (top-5 by season avg) minutes by margin bucket
avgmin=P[P.MIN>0].groupby(['team','PLAYER']).MIN.mean()
top5=avgmin.groupby('team',group_keys=False).nlargest(5).reset_index()[['team','PLAYER']]; top5['core5']=1
P=P.merge(top5,on=['team','PLAYER'],how='left'); P['core5']=P.core5.fillna(0)
P['absm']=P.margin.abs(); P['bucket']=pd.cut(P.absm,[-1,9,19,100],labels=['0-9','10-19','20+'])
c5=P[(P.core5==1)&(P.MIN>0)].groupby('bucket').MIN.mean()
print('\ncore-5 minutes by final margin:',c5.round(1).to_dict(),'| games per bucket',(G[G.home==1].assign(a=lambda d:(d.PTS-d.oPTS).abs()).a.apply(lambda v:'0-9' if v<=9 else '10-19' if v<=19 else '20+').value_counts().to_dict()))
# total error vs market by margin bucket (garbage time)
g=G[G.home==1].copy(); g['tot_err']=(g.PTS+g.oPTS)-(g['mkt']+G.set_index(['date','team']).loc[list(zip(g.date,g.opp)),'mkt'].values)
g['absm']=(g.PTS-g.oPTS).abs(); g['b']=pd.cut(g.absm,[-1,9,19,100],labels=['0-9','10-19','20+'])
print('game total vs market line by final margin:',g.groupby('b').tot_err.agg(['mean','count']).round(1).to_dict())
P.to_pickle('work/box_P2.pkl'); rot.to_pickle('work/box_rot.pkl'); R.to_pickle('work/box_R.pkl')

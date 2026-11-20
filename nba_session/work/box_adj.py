import pandas as pd, numpy as np
G=pd.read_pickle('work/box_G2.pkl')
teams=sorted(G.team.unique()); ix={t:i for i,t in enumerate(teams)}; n=len(teams)
def ridge_ratings(D,col,lam=5.0,weight_col='POSS'):
    # col per 100: value = mu + off[team] + def[opp] + h*home
    X=np.zeros((len(D),2*n+1)); y=(D[col]).values; w=D[weight_col].values/100
    for k,(t,o,h) in enumerate(zip(D.team,D.opp,D.home)):
        X[k,ix[t]]=1; X[k,n+ix[o]]=1; X[k,2*n]=h-0.5
    mu=np.average(y,weights=w); yc=y-mu
    W=np.diag(w); A=X.T@W@X+lam*np.diag([1]*(2*n)+[0]); b=np.linalg.solve(A,X.T@W@yc)
    return mu,b[:n],b[n:2*n],b[2*n]
G['ortg']=100*G.PTS/G.POSS
G['xortg']=100*(G.PTS-G.luck3)/G.POSS     # 3P%-neutral
G['oxortg']=100*(G.oPTS-G.oluck3)/G.POSS
mu,off,de,h=ridge_ratings(G,'ortg')
mux,offx,dex,hx=ridge_ratings(G,'xortg')
print(f'home edge per 100 (raw) {h:.2f}  (3P-neutral) {hx:.2f}  league {mu:.1f}')
prof=pd.read_pickle('work/box_prof.pkl')
A=pd.DataFrame({'team':teams,'adjO':off,'adjD':de,'adjO_x':offx,'adjD_x':dex}).set_index('team')
A['adjNet']=A.adjO-A.adjD; A['adjNet_x']=A.adjO_x-A.adjD_x
A=A.join(prof[['NRtg','NRtg_luckadj','luck_net','GP']])
# schedule strength: avg opponent adjNet
sos=G.groupby('team').opp.apply(lambda s: A.loc[s,'adjNet'].mean()); A['SOS']=sos
print(A.sort_values('adjNet',ascending=False).round(2).to_string())
A.to_pickle('work/box_adj.pkl')
# ---- split-half predictive tests ----
G=G.sort_values('date')
rows=[]
for t,D in G.groupby('team'):
    k=int(np.ceil(len(D)/2)); a,b=D.iloc[:k],D.iloc[k:]
    def net(d,adj=False):
        p=d.POSS.sum()
        if adj: return 100*((d.PTS-d.luck3).sum()-(d.oPTS-d.oluck3).sum())/p
        return 100*(d.PTS.sum()-d.oPTS.sum())/p
    rows.append(dict(team=t,first=net(a),first_x=net(a,True),second=net(b),
        f3=a.TPM.sum()/a.TPA.sum(),s3=b.TPM.sum()/b.TPA.sum(),fo3=a.oTPM.sum()/a.oTPA.sum(),so3=b.oTPM.sum()/b.oTPA.sum(),
        fpace=a.PACE.mean(),space=b.PACE.mean(),ftov=a.TOV.sum()/a.poss.sum(),stov=b.TOV.sum()/b.poss.sum(),
        forb=(a.OREB.sum()/(a.OREB.sum()+a.oDREB.sum())),sorb=(b.OREB.sum()/(b.OREB.sum()+b.oDREB.sum())),
        fftr=a.FTA.sum()/a.FGA.sum(),sftr=b.FTA.sum()/b.FGA.sum(),f3par=a.TPA.sum()/a.FGA.sum(),s3par=b.TPA.sum()/b.FGA.sum(),
        fx=net(a,True)))
S=pd.DataFrame(rows)
c=lambda x,y: round(np.corrcoef(S[x],S[y])[0,1],2)
print('\nsplit-half (first ~3 games -> next ~3) correlations across 30 teams:')
print(' raw net -> later net',c('first','second'),'| 3P-neutral net -> later net',c('first_x','second'))
print(' 3P% persistence',c('f3','s3'),'| opp 3P% persistence',c('fo3','so3'),'| pace',c('fpace','space'),'| TOV%',c('ftov','stov'),'| ORB%',c('forb','sorb'),'| FTr',c('fftr','sftr'),'| 3PA rate',c('f3par','s3par'))
S.to_pickle('work/box_split.pkl')

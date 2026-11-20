import pandas as pd, numpy as np, math, openpyxl
from scipy.stats import norm
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
df=pd.read_pickle('work/legs9.pkl')
opp=lambda r: None
# drop markets with impossible pricing (typos): reconstruct hold from odds & novig
df['hold']=[imp(o)/nv-1 if nv>0 else 0 for o,nv in zip(df.odds,df.novig_p)]
bad=(df.hold>0.11)|(df.hold<-0.02); print('dropped legs',int(bad.sum()), df[bad][['game','market','odds']].values.tolist())
df=df[~bad].copy()
m=(df.date=='2026-10-24')&(df.market=='Total')&(df.edge>=.04)&(df.ev>0)&(df.model_p<=.70); df.loc[m,'carded']=True
df['fwd']=df.date>='2026-10-23'
def s(name,d,pr=True):
    n=len(d)
    if n==0: print(f'{name:38} none'); return
    w=int(d.win.sum()); l=n-w-int(d.push.sum()); u=d.profit.sum(); z=(u-d.mkt_ev.sum())/math.sqrt(d.mkt_var.sum())
    print(f'{name:38} {w:3}-{l:<3} {u:+7.2f}u ROI {u/n:+6.1%} z {z:+5.2f} p {1-norm.cdf(z):.2f} | expW mdl {d.model_p.sum():5.1f} mkt {d.novig_p.sum():5.1f}')
C=df[df.carded]
print('=== CARD'); s('All',C)
for d in sorted(df.date.unique()): s('  '+d,C[C.date==d])
for mk in ['ML','Spread','Total','TT']: s('  '+mk,C[C.market==mk])
for sd in ['Over','Under']: s('  '+sd,C[C.side==sd])
for fd in ['Fav','Dog']: s('  '+fd,C[C.fav_dog==fd])
s('  ML dogs +150 or longer',C[(C.market=='ML')&(C.odds>=150)]); s('  ML other',C[(C.market=='ML')&(C.odds<150)])
for lo,hi in [(.04,.08),(.08,.12),(.12,.20),(.20,1)]: s(f'  edge {lo:.0%}-{hi:.0%}',C[(C.edge>=lo)&(C.edge<hi)])
s('  card before cap change? model>70%',C[C.model_p>.70])
rules={'A Gap 3-6':(df.gap>=3)&(df.gap<6),'B Model>=60% @ -115..+115':(df.model_p>=.6)&(df.odds.abs()<=115),
 'C Under, model 55-65%':(df.side=='Under')&(df.model_p>=.55)&(df.model_p<.65),'D Card game-total Unders':(df.market=='Total')&(df.side=='Under')&df.carded,
 'all Unders':df.side=='Under','all Overs':df.side=='Over'}
print('\n=== FROZEN RULES forward 10/23-10/26 | by night')
for k,mm in rules.items():
    s(k,df[mm&df.fwd]); print('      nights:',' '.join(f"{d[5:]}:{df[mm&(df.date==d)].profit.sum():+.1f}" for d in sorted(df[df.fwd].date.unique())))
# SAFE ROUTE: card ∩ A, no ML >= +150, edge<=20%, one per game (max edge)
S=C[(C.gap>=3)&(C.gap<6)&~((C.market=='ML')&(C.odds>=150))&(C.edge<=.20)]
S1=S.sort_values('edge',ascending=False).drop_duplicates('game')
print('\n=== SAFE ROUTE (card + rule A, no long dogs, edge<=20%, 1 per game)')
s('All nights',S1); s('Forward 10/23+',S1[S1.fwd]); s('10/26 only',S1[S1.date=='2026-10-26'])
print(S1[S1.date=='2026-10-26'][['game','market','side','odds','edge','win','profit']].round(3).to_string(index=False))
s('Safe route without 1-per-game',S)
# projections
t=openpyxl.load_workbook('in9/nba.xlsx',data_only=True)['Tracking']; rows=[]
for r in range(13,313):
    a=t[f'A{r}'].value
    if a is None or t[f'AN{r}'].value is None: continue
    rows.append(dict(date=str(a.date()),aw=t[f'B{r}'].value,hm=t[f'C{r}'].value,ap=t[f'D{r}'].value,hp=t[f'E{r}'].value,A=t[f'AN{r}'].value,H=t[f'AO{r}'].value,U=t[f'U{r}'].value,P=t[f'P{r}'].value,Q=t[f'Q{r}'].value,AA=t[f'AA{r}'].value,AE=t[f'AE{r}'].value,
                     pml=t[f'I{r}'].value,J=t[f'J{r}'].value,K=t[f'K{r}'].value))
P=pd.DataFrame(rows); P['tot']=P.A+P.H
me=(P.H-P.A)-(P.hp-P.ap); mk=(P.H-P.A)-P.U; te=P.tot-P.Q; le=P.tot-P.P
print(f"\n=== PROJECTIONS ({len(P)} games)\nmargin RMSE model {np.sqrt((me**2).mean()):.1f} mkt {np.sqrt((mk**2).mean()):.1f} | MAE model {me.abs().mean():.1f} mkt {mk.abs().mean():.1f}")
print(f"total: mean err model {te.mean():+.1f} line {le.mean():+.1f} | RMSE model {np.sqrt((te**2).mean()):.1f} line {np.sqrt((le**2).mean()):.1f} | overs {int((P.tot>P.P).sum())}/{len(P)} | model below line {int((P.Q<P.P).sum())}/{len(P)}")
print('model side of total right', int(((P.tot>P.P)==(P.Q>P.P)).sum()),'/',len(P))
print('by night total err line:', P.groupby('date').apply(lambda g:(g.tot-g.P).mean()).round(1).to_dict())
ok=P.K.abs()<2000
nv=[imp(k)/(imp(j)+imp(k)) for j,k in zip(P.J,P.K)]; P['nv']=nv; hw=(P.H>P.A)
ll=lambda p,y: -np.mean(np.log(np.where(y,p,1-p)))
print(f"ML log loss model {ll(P.pml[ok].values,hw[ok].values):.3f} mkt {ll(P.nv[ok].values,hw[ok].values):.3f} | winners model {int(((P.hp>P.ap)==hw).sum())} mkt fav {int(((P.U>0)==hw).sum())} of {len(P)}")
# team scoring vs projection, home/away
ts=pd.concat([pd.DataFrame(dict(team=P.aw,date=P.date,proj=P.ap,act=P.A,tt=P.AA,home=False)),pd.DataFrame(dict(team=P.hm,date=P.date,proj=P.hp,act=P.H,tt=P.AE,home=True))])
ts['err']=ts.act-ts.proj
print('team pts: proj',round(ts.proj.mean(),1),'actual',round(ts.act.mean(),1),'| home err',round(ts[ts.home].err.mean(),1),'away err',round(ts[~ts.home].err.mean(),1),'| home margin actual',round((P.H-P.A).mean(),1),'model',round((P.hp-P.ap).mean(),1))
# b2b generic
dates=sorted(P.date.unique()); played={d:set(P[P.date==d].aw)|set(P[P.date==d].hm) for d in dates}
import datetime as dt
def prev(d): return str((dt.date.fromisoformat(d)-dt.timedelta(days=1)))
ts['b2b']=[ (prev(d) in played and tm in played[prev(d)]) for tm,d in zip(ts.team,ts.date)]
print('b2b team-games',int(ts.b2b.sum()),'| err b2b',round(ts[ts.b2b].err.mean(),1),'rested',round(ts[~ts.b2b].err.mean(),1),'| vs TT line b2b',round((ts[ts.b2b].act-ts[ts.b2b].tt).mean(),1),'rested',round((ts[~ts.b2b].act-ts[~ts.b2b].tt).mean(),1))
# calibration
df['pb']=pd.cut(df.model_p,[0,.35,.45,.55,.65,.70,1])
print('\nCalibration all legs'); print(df.groupby('pb',observed=True).agg(n=('win','size'),model=('model_p','mean'),mkt=('novig_p','mean'),actual=('win','mean')).round(3).to_string())
print('\nCalibration by market (model>=55% legs): ')
print(df[df.model_p>=.55].groupby('market').agg(n=('win','size'),model=('model_p','mean'),mkt=('novig_p','mean'),actual=('win','mean')).round(3).to_string())

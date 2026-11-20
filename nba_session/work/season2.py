import pandas as pd, numpy as np, math
from scipy.stats import norm
df=pd.read_pickle('work/legs5.pkl'); df['fwd']=df.date>='2026-10-23'
def s(name,d):
    n=len(d)
    if n==0: print(f'{name:38} none'); return
    w=int(d.win.sum()); l=n-w-int(d.push.sum()); u=d.profit.sum(); mev=d.mkt_ev.sum(); sd=math.sqrt(d.mkt_var.sum())
    z=(u-mev)/sd; print(f'{name:38} {w:3}-{l:<3} {u:+7.2f}u ROI {u/n:+6.1%} | z {z:+5.2f} p {1-norm.cdf(z):.3f} | expW model {d.model_p.sum():5.1f} mkt {d.novig_p.sum():5.1f} | games {d.game.nunique()}')
C=df[df.carded]
print('=== CARD PLAYS (paper, 1u flat)'); s('All card plays',C)
for d in sorted(df.date.unique()): s('  '+d,C[C.date==d])
for m in ['ML','Spread','Total','TT']: s('  '+m,C[C.market==m])
for sd in ['Over','Under','Fav','Dog']: s('  '+sd,C[C.side==sd])
for lo,hi in [(.04,.08),(.08,.12),(.12,.20),(.20,1)]: s(f'  edge {lo:.0%}-{hi:.0%}',C[(C.edge>=lo)&(C.edge<hi)])
rules={
 'CAND Gap 3-6':(df.gap>=3)&(df.gap<6),
 'CAND Model>=60% @ -115..+115':(df.model_p>=.6)&(df.odds.abs()<=115),
 'CAND Under, model 55-65%':(df.side=='Under')&(df.model_p>=.55)&(df.model_p<.65),
 'CAND Card game-total Unders':(df.market=='Total')&(df.side=='Under')&df.carded,
 'CAUT Card dogs':(df.side=='Dog')&df.carded,
 'CAUT Edge>=20%':df.edge>=.20,
 'CAUT Gap>=6':df.gap>=6,
 'CAUT Odds>=+130':df.odds>=130,
 'BASE every leg':df.market.notna(),
 'BASE all Unders':df.side=='Under',
 'BASE all Overs':df.side=='Over',
}
print('\n=== FROZEN RULES: FORWARD (10/23 only)')
for k,m in rules.items(): s(k,df[m&df.fwd])
print('\n=== FROZEN RULES: IN-SAMPLE (10/20-10/22)')
for k,m in rules.items(): s(k,df[m&~df.fwd])
# projections / market
G=df[(df.market=='ML')&(df.home_away=='Home')].copy()
import openpyxl
t=openpyxl.load_workbook('in5/nba.xlsx',data_only=True)['Tracking']
rows=[]
for r in range(13,313):
    a=t[f'A{r}'].value
    if a is None or t[f'AN{r}'].value is None: continue
    rows.append(dict(date=str(a.date()),ap=t[f'D{r}'].value,hp=t[f'E{r}'].value,A=t[f'AN{r}'].value,H=t[f'AO{r}'].value,U=t[f'U{r}'].value,P=t[f'P{r}'].value,Q=t[f'Q{r}'].value,
                     pml=t[f'I{r}'].value,J=t[f'J{r}'].value,K=t[f'K{r}'].value,R=t[f'R{r}'].value))
P=pd.DataFrame(rows)
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
P['mm']=P.hp-P.ap; P['am']=P.H-P.A; P['mkt']=P.U
P['nvml']=[imp(k)/(imp(j)+imp(k)) for j,k in zip(P.J,P.K)]; P['hw']=P.H>P.A
P['tot']=P.A+P.H
for lab,sub in [('10/20-22',P[P.date<'2026-10-23']),('10/23',P[P.date>='2026-10-23']),('ALL',P)]:
    me=sub.am-sub.mm; mk=sub.am-sub.mkt; te=sub.tot-sub.Q; le=sub.tot-sub.P
    ll=lambda p,y: -np.log(np.where(y,p,1-p)).mean()
    print(f"\n{lab} n={len(sub)} margin RMSE model {np.sqrt((me**2).mean()):.1f} mkt {np.sqrt((mk**2).mean()):.1f} | total err mean model {te.mean():+.1f} line {le.mean():+.1f} RMSE model {np.sqrt((te**2).mean()):.1f} line {np.sqrt((le**2).mean()):.1f} | overs {int((sub.tot>sub.P).sum())}/{len(sub)} | ML logloss model {ll(sub.pml.values,sub.hw.values):.3f} mkt {ll(sub.nvml.values,sub.hw.values):.3f} | model<line {int((sub.Q<sub.P).sum())}")
# calibration all legs: model p bins
df['pb']=pd.cut(df.model_p,[0,.35,.45,.55,.65,.75,1])
print('\nCalibration (all legs):'); print(df.groupby('pb',observed=True).agg(n=('win','size'),model=('model_p','mean'),mkt=('novig_p','mean'),actual=('win','mean')).round(3).to_string())
df.to_pickle('work/legs5f.pkl')

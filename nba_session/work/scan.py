import pandas as pd, numpy as np, itertools, math, sys
from scipy.stats import norm
df=pd.read_pickle('work/legs.pkl')
C={}  # family -> {label: mask}
C['Market']={f'{m}':df.market==m for m in ['ML','Spread','Total','TT']}
C['Side']={'Over':df.side=='Over','Under':df.side=='Under','Fav':df.fav_dog=='Fav','Dog':df.fav_dog=='Dog'}
C['Venue']={'Home team':df.home_away=='Home','Away team':df.home_away=='Away'}
C['Price']={'Plus money':df.odds>0,'Minus money':df.odds<0,'Odds -115 to +115':df.odds.abs().le(115)|(df.odds==100),
            'Odds >= +130':df.odds>=130,'Odds <= -130':df.odds<=-130}
C['Model %']={'Model <45%':df.model_p<.45,'Model 45-55%':df.model_p.between(.45,.55),'Model 55-65%':df.model_p.between(.55,.65,inclusive='left'),
              'Model >=60%':df.model_p>=.60,'Model >=65%':df.model_p>=.65}
C['Edge']={'Edge <0':df.edge<0,'Edge 0-4%':df.edge.between(0,.04,inclusive='left'),'Edge >=4% (card gate)':df.edge>=.04,
           'Edge 4-8%':df.edge.between(.04,.08,inclusive='left'),'Edge 8-12%':df.edge.between(.08,.12,inclusive='left'),
           'Edge >=8%':df.edge>=.08,'Edge 12-20%':df.edge.between(.12,.20,inclusive='left'),'Edge >=20%':df.edge>=.20}
C['EV']={'EV <0':df.ev<0,'EV 0-10%':df.ev.between(0,.10,inclusive='left'),'EV 10-20%':df.ev.between(.10,.20,inclusive='left'),'EV >=20%':df.ev>=.20}
C['Proj gap']={'Gap <0':df.gap<0,'Gap 0-3 pts':df.gap.between(0,3,inclusive='left'),'Gap 3-6 pts':df.gap.between(3,6,inclusive='left'),
               'Gap >=3 pts':df.gap>=3,'Gap >=6 pts':df.gap>=6}
C['Line']={'Spread <=3.5':(df.market=='Spread')&(df.line<=3.5),'Spread >=7.5':(df.market=='Spread')&(df.line>=7.5),
           'Total line >=235':(df.market=='Total')&(df.line>=235),'Total line <235':(df.market=='Total')&(df.line<235),
           'TT line >=118':(df.market=='TT')&(df.line>=118),'TT line <118':(df.market=='TT')&(df.line<118)}
C['Card']={'Card play':df.carded,'Not a card play':~df.carded}
split = df.date=='2026-10-21'
def stats(m):
    d=df[m]; n=len(d)
    if n==0: return None
    w=int(d.win.sum()); p=int(d.push.sum()); l=n-w-p
    prof=d.profit.sum(); mev=d.mkt_ev.sum(); sd=math.sqrt(d.mkt_var.sum())
    z=(prof-mev)/sd if sd>0 else 0
    a=df[m&split]; b=df[m&~split]
    return dict(legs=n,games=d.game.nunique(),W=w,L=l,P=p,win_pct=w/max(1,w+l),flat_units=prof,roi=prof/n,
        mkt_expected_units=mev,model_claimed_units=d.ev.sum(),z_vs_market=z,p_value=1-norm.cdf(z),
        avg_odds=d.odds.mean(),avg_model_p=d.model_p.mean(),avg_novig_p=d.novig_p.mean(),avg_edge=d.edge.mean(),
        wed_legs=len(a),wed_roi=a.profit.sum()/len(a) if len(a) else np.nan,
        tue_thu_legs=len(b),tue_thu_roi=b.profit.sum()/len(b) if len(b) else np.nan)
rows=[]
flat=[(f,k,v) for f,dd in C.items() for k,v in dd.items()]
for f,k,v in flat:
    s=stats(v); 
    if s: rows.append(dict(rule=k,family=f,depth=1,**s))
for (f1,k1,v1),(f2,k2,v2) in itertools.combinations(flat,2):
    if f1==f2: continue
    s=stats(v1&v2)
    if s and s['legs']>=8: rows.append(dict(rule=f'{k1} + {k2}',family=f'{f1} × {f2}',depth=2,**s))
R=pd.DataFrame(rows)
R=R[R.legs>=8].drop_duplicates(subset=['legs','W','L','flat_units','games']).copy()  # identical leg sets
# Benjamini-Hochberg
R=R.sort_values('p_value'); m=len(R); R['bh_q']=(R.p_value*m/np.arange(1,m+1))[::-1].cummin()[::-1].clip(upper=1)
R['stable']=(R.wed_roi>0)&(R.tue_thu_roi>0)&(R.wed_legs>=3)&(R.tue_thu_legs>=3)
R.to_pickle('work/rules.pkl')
print('rules tested',m,'| min p',R.p_value.min().round(4),'| min q',R.bh_q.min().round(3),'| q<0.10:',(R.bh_q<.10).sum())
pd.set_option('display.width',250); pd.set_option('display.max_colwidth',60)
cols=['rule','legs','games','W','L','flat_units','roi','mkt_expected_units','z_vs_market','p_value','bh_q','wed_roi','tue_thu_roi','stable']
print(R[R.depth==1].sort_values('flat_units',ascending=False)[cols].round(3).to_string(index=False))
print('\nTOP PAIRS by z, stable, games>=6')
print(R[(R.depth==2)&R.stable&(R.games>=6)].sort_values('z_vs_market',ascending=False)[cols].head(25).round(3).to_string(index=False))
print('\nWORST pairs')
print(R[(R.depth==2)&(R.games>=6)].sort_values('z_vs_market')[cols].head(10).round(3).to_string(index=False))

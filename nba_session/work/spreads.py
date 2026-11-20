import openpyxl, pandas as pd, numpy as np, math, itertools
from scipy.stats import norm
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
t=openpyxl.load_workbook('in9/nba.xlsx',data_only=True)['Tracking']
L=[]
for r in range(13,313):
    g={c:t[f'{c}{r}'].value for c in ['A','B','C','D','E','H','I','J','K','P','Q','R','S','T','U','V','W','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AN','AO']}
    if g['A'] is None or g['AN'] is None: continue
    U=g['U']; A,H=g['AN'],g['AO']; card=(g['AI'] or '')+' |'
    nvml_h=imp(g['K'])/(imp(g['J'])+imp(g['K'])); mlhold=imp(g['J'])+imp(g['K'])-1
    spr_hold=imp(g['W'])+imp(g['Z'])-1
    if spr_hold>.11 or spr_hold<-.02: continue
    for side in ('Away','Home'):
        a = side=='Away'
        line = U if a else -U
        p = g['V'] if a else 1-g['V']; o = g['W'] if a else g['Z']; oo = g['Z'] if a else g['W']
        nv = imp(o)/(imp(o)+imp(oo)); margin=(A-H) if a else (H-A)
        projm = (g['D']-g['E']) if a else (g['E']-g['D'])
        ml_ok = (-.02<=mlhold<=.11) and abs(g['K'])<2000
        tt_ok_own = True
        own_tt_over = g['AB'] if a else g['AF']; opp_tt_over = g['AF'] if a else g['AB']
        own_tt_line = g['AA'] if a else g['AE']; opp_tt_line = g['AE'] if a else g['AA']
        own_proj = g['D'] if a else g['E']; opp_proj = g['E'] if a else g['D']
        o1,o2 = (g['AC'],g['AD']) if a else (g['AG'],g['AH'])
        own_tt_nv = imp(o1)/(imp(o1)+imp(o2)) if -.02<=imp(o1)+imp(o2)-1<=.11 else np.nan
        q1,q2 = (g['AG'],g['AH']) if a else (g['AC'],g['AD'])
        opp_tt_nv = imp(q1)/(imp(q1)+imp(q2)) if -.02<=imp(q1)+imp(q2)-1<=.11 else np.nan
        L.append(dict(date=str(g['A'].date()), game=f"{g['B'].split()[-1]}@{g['C'].split()[-1]}", side=side, line=line,
            fav=line<0, odds=o, model_p=p, novig_p=nv, edge=p-nv, ev=p*dec(o)-(1-p), gap=projm+line,
            ml_model=(g['H'] if a else g['I']) if ml_ok else np.nan,
            ml_mkt=((1-nvml_h) if a else nvml_h) if ml_ok else np.nan,
            own_tt_edge=own_tt_over-own_tt_nv, opp_tt_under_edge=(1-opp_tt_over)-(1-opp_tt_nv),
            own_gap=own_proj-own_tt_line, opp_gap=opp_tt_line-opp_proj,  # +: model likes own over / opp under
            total_line=g['P'], total_gap=g['Q']-g['P'], carded=(f"Spread {g['B'] if a else g['C']} {line:+.1f} |") in card,
            win=margin+line>0, push=margin+line==0, profit=(dec(o) if margin+line>0 else 0 if margin+line==0 else -1.0),
            mkt_ev=nv*dec(o)-(1-nv), mkt_var=nv*(1-nv)*(dec(o)+1)**2))
df=pd.DataFrame(L); df['ml_edge']=df.ml_model-df.ml_mkt
df.to_pickle('work/spr.pkl')
print('spread legs',len(df),'games',df.game.nunique())
def st(d):
    n=len(d); w=int(d.win.sum()); l=n-w-int(d.push.sum()); u=d.profit.sum(); sd=math.sqrt(d.mkt_var.sum()); z=(u-d.mkt_ev.sum())/sd if sd else 0
    return n,w,l,u,u/n if n else 0,z,d.game.nunique(), d[d.date<'2026-10-23'].profit.sum(), d[d.date>='2026-10-23'].profit.sum(), len(d[d.date<'2026-10-23']), len(d[d.date>='2026-10-23'])
def pr(name,d):
    n,w,l,u,roi,z,gm,a,b,na,nb=st(d); print(f'{name:44} {w:3}-{l:<3} {u:+6.2f}u ROI {roi:+6.1%} z {z:+5.2f} p {1-norm.cdf(z):.3f} | early {a:+.1f} ({na}) late {b:+.1f} ({nb})')
print('\n--- baselines'); pr('all spread sides',df); pr('card spread plays',df[df.carded]); pr('favorites',df[df.fav]); pr('underdogs',df[~df.fav]); pr('home',df[df.side=='Home']); pr('away',df[df.side=='Away'])
C={
 'Model cover':{'cover<45%':df.model_p<.45,'cover 45-55%':df.model_p.between(.45,.55),'cover 55-65%':df.model_p.between(.55,.65,inclusive='left'),'cover>=60%':df.model_p>=.60,'cover 60-70%':df.model_p.between(.60,.70),'cover>70%':df.model_p>.70},
 'Edge':{'edge>=4%':df.edge>=.04,'edge 4-12%':df.edge.between(.04,.12),'edge 12-20%':df.edge.between(.12,.20),'edge>20%':df.edge>.20,'edge<0':df.edge<0},
 'Gap':{'gap 0-3':df.gap.between(0,3,inclusive='left'),'gap 3-6':df.gap.between(3,6,inclusive='left'),'gap>=6':df.gap>=6,'gap<0':df.gap<0},
 'Line':{'fav':df.fav,'dog':~df.fav,'line <=3.5 (abs)':df.line.abs()<=3.5,'line 4-7.5':df.line.abs().between(4,7.5),'line >=8':df.line.abs()>=8,'dog +8 or more':(df.line>=8),'fav -8 or more':(df.line<=-8)},
 'Venue':{'home':df.side=='Home','away':df.side=='Away'},
 'ML model win%':{'ML model <40%':df.ml_model<.40,'ML model 40-55%':df.ml_model.between(.40,.55),'ML model 55-70%':df.ml_model.between(.55,.70),'ML model >70%':df.ml_model>.70},
 'ML market win%':{'ML mkt <35%':df.ml_mkt<.35,'ML mkt 35-50%':df.ml_mkt.between(.35,.50),'ML mkt 50-65%':df.ml_mkt.between(.50,.65),'ML mkt >65%':df.ml_mkt>.65},
 'ML edge':{'ML edge >=4%':df.ml_edge>=.04,'ML edge <0':df.ml_edge<0,'ML edge 4-15%':df.ml_edge.between(.04,.15)},
 'Team totals':{'own TT edge>0 (model likes own over)':df.own_tt_edge>0,'own TT edge>=4%':df.own_tt_edge>=.04,'opp TT under edge>=4%':df.opp_tt_under_edge>=.04,
                'both TT agree (own over & opp under >0)':(df.own_tt_edge>0)&(df.opp_tt_under_edge>0),'TT disagree (own over<0)':df.own_tt_edge<0,
                'own proj beats own TT line by 2+':df.own_gap>=2,'opp proj under opp TT line by 2+':df.opp_gap>=2},
 'Total':{'total line <228':df.total_line<228,'total line >=232':df.total_line>=232,'model total under line':df.total_gap<0,'model total over line':df.total_gap>0},
 'Card':{'card play':df.carded},
}
rows=[]
flat=[(f,k,v) for f,d in C.items() for k,v in d.items()]
for f,k,v in flat:
    d=df[v.fillna(False)] if hasattr(v,'fillna') else df[v]
    if len(d)>=8: n,w,l,u,roi,z,gm,a,b,na,nb=st(d); rows.append(dict(rule=k,depth=1,n=n,w=w,l=l,u=u,roi=roi,z=z,games=gm,early=a,late=b,na=na,nb=nb))
for (f1,k1,v1),(f2,k2,v2) in itertools.combinations(flat,2):
    if f1==f2: continue
    m=(v1.fillna(False) if hasattr(v1,'fillna') else v1)&(v2.fillna(False) if hasattr(v2,'fillna') else v2)
    d=df[m]
    if len(d)>=10: n,w,l,u,roi,z,gm,a,b,na,nb=st(d); rows.append(dict(rule=f'{k1} + {k2}',depth=2,n=n,w=w,l=l,u=u,roi=roi,z=z,games=gm,early=a,late=b,na=na,nb=nb))
R=pd.DataFrame(rows).drop_duplicates(subset=['n','w','l','u']); R['p']=1-norm.cdf(R.z)
R=R.sort_values('p'); m=len(R); R['bh_q']=(R.p*m/np.arange(1,m+1))[::-1].cummin()[::-1].clip(upper=1)
R['both_halves']=(R.early>0)&(R.late>0)&(R.na>=4)&(R.nb>=4)
R.to_pickle('work/spr_rules.pkl')
pd.set_option('display.width',250)
print('\nrules tested',m,'| min q',round(R.bh_q.min(),3),'| p<.05:',int((R.p<.05).sum()),'expected by luck ~',round(.05*m))
print('\n--- single features (n>=8)')
print(R[R.depth==1].sort_values('u',ascending=False)[['rule','n','w','l','u','roi','z','p','early','late','both_halves']].round(3).to_string(index=False))
print('\n--- top pairs (n>=10, positive both halves)')
print(R[(R.depth==2)&R.both_halves].sort_values('z',ascending=False).head(20)[['rule','n','w','l','u','roi','z','p','bh_q','early','late']].round(3).to_string(index=False))

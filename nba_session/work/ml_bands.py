import openpyxl, math, pandas as pd, numpy as np
t=openpyxl.load_workbook('out_1101b/MaverickPicks_NBA_Simulations.xlsx',data_only=True)['Tracking']
rows=[]
for r in range(13,103):
    v=lambda c: t.cell(r,c).value
    if not v(2) or v(40) is None: continue
    rows.append(dict(row=r,date=str(v(1))[:10],aw=v(2),hm=v(3),pa=v(8),ph=v(9),oa=v(10),oh=v(11),A=v(40),H=v(41)))
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
L=[]; bad=[]
for x in rows:
    if not all(isinstance(x[k],(int,float)) for k in ('pa','ph','oa','oh')): bad.append((x['row'],'missing')); continue
    vig=imp(x['oa'])+imp(x['oh'])-1
    if vig>0.11 or vig<-0.02: bad.append((x['row'],x['aw'],x['oa'],x['oh'])); continue
    for side in ('away','home'):
        p=x['pa'] if side=='away' else x['ph']; o=x['oa'] if side=='away' else x['oh']; oo=x['oh'] if side=='away' else x['oa']
        won=(x['A']>x['H']) if side=='away' else (x['H']>x['A'])
        nv=imp(o)/(imp(o)+imp(oo))
        L.append(dict(side=side,date=x['date'],team=x['aw'] if side=='away' else x['hm'],p=p,odds=o,nv=nv,edge=p-nv,won=won,pl=dec(o) if won else -1))
D=pd.DataFrame(L)
print('games',len(rows),'excluded',bad)
def table(d,col,bins,labels):
    d=d.copy(); d['band']=pd.cut(d[col],bins=bins,labels=labels,right=False)
    g=d.groupby('band',observed=False).agg(n=('won','size'),wins=('won','sum'),model=('p','mean'),market=('nv','mean'),units=('pl','sum'),edge=('edge','mean'))
    g['win%']=g.wins/g.n; g['roi']=g.units/g.n
    # z vs market
    out=[]
    for b,s in d.groupby('band',observed=False):
        if len(s)==0: out.append(np.nan); continue
        var=(s.nv*(1-s.nv)).sum(); out.append((s.won.sum()-s.nv.sum())/math.sqrt(var) if var>0 else np.nan)
    g['z_vs_mkt']=out
    return g[['n','wins','win%','model','market','edge','units','roi','z_vs_mkt']]
pd.set_option('display.width',200)
for side in ('away','home'):
    d=D[D.side==side]
    print(f'\n===== ML {side.upper()} (n={len(d)}) record if bet every one: {int(d.won.sum())}-{int((~d.won).sum())} {d.pl.sum():+.2f}u')
    print('-- by model probability'); print(table(d,'p',[0,.3,.4,.5,.6,.7,1.01],['<30','30-40','40-50','50-60','60-70','70+']).round(3).to_string())
    print('-- by odds'); print(table(d,'odds',[-10000,-250,-150,-100,101,200,10000],['<=-250','-249..-150','-149..-101','-100..+100','+101..+199','>=+200']).round(3).to_string())
    print('-- by edge'); print(table(d,'edge',[-1,-.08,-.04,0,.04,.08,.12,1],['<-8','-8..-4','-4..0','0..4','4..8','8..12','12+']).round(3).to_string())
    pick=d[d.p>0.5]; print('model favorite (p>50%) won', int(pick.won.sum()),'of',len(pick), f"{pick.won.mean():.1%}", '| market favorite won', int(d[d.nv>0.5].won.sum()),'of',len(d[d.nv>0.5]))
# both sides combined, model pick accuracy & calibration
g=D[D.p>0.5]; print('\nALL games: model pick won',int(g.won.sum()),'of',len(g),f"{g.won.mean():.1%}",'market pick',f"{D[D.nv>0.5].won.mean():.1%}")
br=lambda c: ((D[c]-D.won)**2).mean(); print('Brier model %.4f market %.4f'%(br('p'),br('nv')))
D.to_pickle('work/ml_legs.pkl')

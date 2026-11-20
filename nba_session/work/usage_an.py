import json,collections,numpy as np,openpyxl
R=json.load(open('work/usage_raw.json')); rows=R['rows']; team=R['team']
wb=openpyxl.load_workbook('in1113/s.xlsx',read_only=True,data_only=True)
code={r[0]:r[1] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}
off={}
for r in wb['PlayerRatings'].iter_rows(min_row=6,max_row=805,values_only=True):
    if r[0] and r[2] and isinstance(r[23],(int,float)): off[(r[0],code.get(r[2]))]=r[23]
P=collections.defaultdict(list)
for x in rows:
    if isinstance(x['min'],(int,float)) and x['min']>0: P[(x['p'],x['t'])].append(x)
TG=collections.defaultdict(list)
for k,v in team.items():
    t,d=k.split('|'); TG[t].append(d)
for t in TG: TG[t].sort()
played={(x['p'],x['t'],x['d']) for x in rows}
prof={}
for (p,t),g in P.items():
    mins=[x['min'] for x in g]
    if len(g)>=3:
        prof[(p,t)]=dict(n=len(g),mpg=np.mean(mins),usg=np.average([x['usg'] for x in g],weights=mins),ts=np.average([x['ts'] for x in g if x['ts'] is not None],weights=[x['min'] for x in g if x['ts'] is not None]),first=min(x['d'] for x in g),last=max(x['d'] for x in g),off=off.get((p,t)))
reg={k:v for k,v in prof.items() if v['mpg']>=20}
byteam=collections.defaultdict(list)
for (p,t),v in reg.items(): byteam[t].append(p)
# team-game missing
TGM={}
for t,ds in TG.items():
    for d in ds:
        miss=[p for p in byteam[t] if (p,t,d) not in played and reg[(p,t)]['first']<d]
        M=sum(reg[(p,t)]['usg']/100*reg[(p,t)]['mpg']/48 for p in miss)
        V=sum(reg[(p,t)]['mpg']/240*5*((reg[(p,t)]['off'] or 0)+1.5)*0.92 for p in miss)
        TGM[(t,d)]=dict(miss=miss,M=M,V=V)
print('team-games',len(TGM),'with a regular missing',sum(1 for v in TGM.values() if v['miss']),'| avg missing usage share when missing %.3f'%np.mean([v['M'] for v in TGM.values() if v['miss']]))
# team offense deviation
lg=np.mean([v['ortg'] for v in team.values()])
full=collections.defaultdict(list); oppd=collections.defaultdict(list)
for k,v in team.items():
    t,d=k.split('|'); 
    if TGM[(t,d)]['M']<0.02: full[t].append(v['ortg'])
    oppd[t].append(v['drtg'])
oppavg={t:np.mean(v) for t,v in oppd.items()}
Y=[];M=[];V=[]
for k,v in team.items():
    t,d=k.split('|'); mu=v['mu']; o=mu.split('@')[1].strip() if '@' in mu else mu.split('vs.')[1].strip()
    if len(full[t])<3: continue
    y=v['ortg']-np.mean(full[t])-(oppavg[o]-lg)
    Y.append(y);M.append(TGM[(t,d)]['M']);V.append(TGM[(t,d)]['V'])
Y,M,V=map(np.array,(Y,M,V))
def ols(X,y):
    X=np.c_[X,np.ones(len(y))]; b=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@b; s2=e.var()*len(y)/(len(y)-X.shape[1]); se=np.sqrt(np.diag(s2*np.linalg.inv(X.T@X))); return b,se
b,se=ols(V[:,None],Y); print(f'\nTeam ORtg vs model-formula offensive loss V (full impact): slope {b[0]:+.2f} (se {se[0]:.2f}) -> model says -1.00 per point; n {len(Y)}')
b,se=ols(M[:,None]*100,Y); print(f'Team ORtg vs missing usage (pct of possessions): {b[0]:+.3f} per 1% (se {se[0]:.3f})')
for lo,hi in ((0,.001),(.001,.10),(.10,.20),(.20,1)):
    s=(M>=lo)&(M<hi); print(f'  missing usage {lo:.0%}-{hi:.0%}: n {s.sum():3d} ORtg vs full-strength {Y[s].mean():+5.1f}  (model formula says {-V[s].mean():+5.1f})')
# redistribution
D=[]
for t,ds in TG.items():
    for d in ds:
        Mi=TGM[(t,d)]['M']
        for p in [x for x in byteam[t]]+[]: pass
for x in rows:
    k=(x['p'],x['t'])
    if k not in prof or not isinstance(x['min'],(int,float)) or x['min']<12: continue
    tm=TGM.get((x['t'],x['d']))
    if tm is None: continue
    # baseline usage in full-strength games
    base=[y for y in P[k] if TGM.get((y['t'],y['d']),{}).get('M',1)<0.02]
    if len(base)<2: continue
    bu=np.average([y['usg'] for y in base],weights=[y['min'] for y in base]); bts=np.average([y['ts'] for y in base if y['ts'] is not None],weights=[y['min'] for y in base if y['ts'] is not None])
    D.append(dict(M=tm['M'],bu=bu,du=x['usg']-bu,dts=(x['ts']-bts) if x['ts'] is not None else None,dmin=x['min']-np.mean([y['min'] for y in base]),bmin=np.mean([y['min'] for y in base]),star=prof[k]['usg']>=25))
D=[d for d in D if d['dts'] is not None]
Mv=np.array([d['M'] for d in D]); bu=np.array([d['bu'] for d in D]); du=np.array([d['du'] for d in D]); dts=np.array([d['dts'] for d in D]); dmin=np.array([d['dmin'] for d in D]); bmin=np.array([d['bmin'] for d in D])
print(f'\nTeammate redistribution (player-games, 12+ min, n {len(D)}; baseline = his full-strength games):')
for lo,hi in ((0,.001),(.001,.10),(.10,.20),(.20,1)):
    s=(Mv>=lo)&(Mv<hi)
    print(f'  team missing {lo:.0%}-{hi:.0%} usage: n {s.sum():4d} | teammate USG change {du[s].mean():+5.2f} pts | minutes {dmin[s].mean():+5.2f} | TS% change {dts[s].mean():+5.2f}')
s=Mv>=0.05
b,se=ols(np.c_[bu[s]*Mv[s],Mv[s]*100],du[s]); print(f'  USG change ~ {b[0]:.2f} x (own USG x missing share) + {b[1]:.3f} x missing% ; se {se[0]:.2f}/{se[1]:.3f}  (pure proportional would be about 1.1 x and 0)')
for lab,sel in (('high-usage teammates (base USG 25%+)',bu>=25),('mid (18-25%)',(bu>=18)&(bu<25)),('low (<18%)',bu<18)):
    s2=s&sel; print(f'    {lab:36s} n {s2.sum():3d} USG {du[s2].mean():+5.2f}  TS% {dts[s2].mean():+5.2f}  min {dmin[s2].mean():+5.2f}')
b,se=ols(du[:,None],dts); print(f'  efficiency tradeoff: TS% change per +1 USG pt {b[0]:+.3f} (se {se[0]:.3f})')
json.dump(dict(prof={f'{p}|{t}':v for (p,t),v in prof.items()}),open('work/usage_prof.json','w'),default=float)

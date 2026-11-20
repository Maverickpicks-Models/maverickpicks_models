import openpyxl,collections,datetime,numpy as np,pickle
wb=openpyxl.load_workbook('in1104/src.xlsx',read_only=True,data_only=True)
def dd(d): return (datetime.date(1899,12,30)+datetime.timedelta(days=int(d))) if isinstance(d,(int,float)) else d.date()
P=collections.defaultdict(list)
for r in wb['BoxScores'].iter_rows(min_row=2,values_only=True):
    if not r[0] or r[3] is None: continue
    P[(r[0],r[1])].append((dd(r[3]),float(r[10] or 0),float(r[11] or 0),float(r[5] or 0)))
for k in P: P[k].sort()
M=sum(x[1] for v in P.values() for x in v); A=sum(x[2] for v in P.values() for x in v); lg=M/A
print('league 3P%',round(lg,4),'players',len(P),'3PA',int(A))
# 1) spread of player 3P% vs pure chance
for mn in (20,30,40):
    rows=[(sum(x[1] for x in v),sum(x[2] for x in v)) for v in P.values() if sum(x[2] for x in v)>=mn]
    m=np.array([a for a,b in rows]); a=np.array([b for a,b in rows]); p=m/a
    obs=np.var(p); chance=np.mean(lg*(1-lg)/a)
    print(f'3PA>={mn}: players {len(rows)}, SD of 3P% {np.sqrt(obs)*100:.1f} pts, SD expected from chance alone {np.sqrt(chance)*100:.1f} -> share of spread that is chance {min(1,chance/obs)*100:.0f}%  (true-talent SD {np.sqrt(max(0,obs-chance))*100:.1f})')
# 2) split-half reliability: odd vs even games
x=[];y=[];w=[]
for v in P.values():
    o=[g for i,g in enumerate(v) if i%2==0]; e=[g for i,g in enumerate(v) if i%2==1]
    ao=sum(g[2] for g in o); ae=sum(g[2] for g in e)
    if ao>=12 and ae>=12: x.append(sum(g[1] for g in o)/ao); y.append(sum(g[1] for g in e)/ae); w.append(min(ao,ae))
r=np.corrcoef(x,y)[0,1]; print(f'odd vs even games 3P%: players {len(x)}, correlation {r:+.2f}, median attempts per half {np.median(w):.0f}')
# 3) first-half vs second-half of each player's games (does hot early shooting carry on?)
x=[];y=[];ya=[]
for v in P.values():
    h=len(v)//2; f,s=v[:h],v[h:]
    af=sum(g[2] for g in f); as_=sum(g[2] for g in s)
    if af>=12 and as_>=12: x.append(sum(g[1] for g in f)/af-lg); y.append(sum(g[1] for g in s)/as_-lg); ya.append(as_)
x=np.array(x);y=np.array(y); b=np.polyfit(x,y,1)[0]
print(f'early vs late games: players {len(x)}, slope {b:+.2f} (1 = all skill carries over, 0 = all luck), corr {np.corrcoef(x,y)[0,1]:+.2f}')
for lab,m in [('hot early (+8 pts or more above lg)',x>=.08),('cold early (-8 pts or more below)',x<=-.08),('in between',abs(x)<.08)]:
    print(f'   {lab}: n{m.sum()}  early {x[m].mean()*100:+.1f}  later {y[m].mean()*100:+.1f}')
# 4) team level: 3P% first half vs second half of team games
T=collections.defaultdict(lambda: collections.defaultdict(lambda:[0,0]))
for (n,t),v in P.items():
    for d,m,a,mi in v: T[t][d][0]+=m; T[t][d][1]+=a
x=[];y=[]
for t,g in T.items():
    ds=sorted(g); h=len(ds)//2
    f=[g[d] for d in ds[:h]]; s=[g[d] for d in ds[h:]]
    x.append(sum(a for a,b in f)/sum(b for a,b in f)-lg); y.append(sum(a for a,b in s)/sum(b for a,b in s)-lg)
x=np.array(x);y=np.array(y)
print(f'teams first vs second half of games: corr {np.corrcoef(x,y)[0,1]:+.2f}, slope {np.polyfit(x,y,1)[0]:+.2f}')
# 5) hot hand: player made 3s in last game above his to-date -> next game?
x=[];y=[]
for v in P.values():
    for i in range(3,len(v)):
        prevm=sum(g[1] for g in v[:i-1]); preva=sum(g[2] for g in v[:i-1])
        if preva<10 or v[i-1][2]<4 or v[i][2]<3: continue
        base=prevm/preva
        x.append(v[i-1][1]/v[i-1][2]-base); y.append(v[i][1]/v[i][2]-base)
x=np.array(x);y=np.array(y)
print(f'hot hand (last game vs own to-date, next game): n{len(x)} corr {np.corrcoef(x,y)[0,1]:+.2f}; after hot game (+15 pts) next game {y[x>=.15].mean()*100:+.1f} vs own avg (n{(x>=.15).sum()}), after cold (-15) {y[x<=-.15].mean()*100:+.1f} (n{(x<=-.15).sum()})')
# biggest current over/under-performers vs league (for listing)
rows=[]
for (n,t),v in P.items():
    m=sum(g[1] for g in v); a=sum(g[2] for g in v)
    if a>=30: rows.append((m/a,a,m,n,t))
rows.sort()
pickle.dump(dict(rows=rows,lg=lg),open('work/p3luck.pkl','wb'))
print('hottest:',[(n,t,f"{int(m)}/{int(a)}",round(p*100,1)) for p,a,m,n,t in rows[-8:]])
print('coldest:',[(n,t,f"{int(m)}/{int(a)}",round(p*100,1)) for p,a,m,n,t in rows[:8]])

import random
def hh(PP):
    x=[];y=[]
    for v in PP.values():
        for i in range(3,len(v)):
            prevm=sum(g[1] for g in v[:i-1]); preva=sum(g[2] for g in v[:i-1])
            if preva<10 or v[i-1][2]<4 or v[i][2]<3: continue
            base=prevm/preva; x.append(v[i-1][1]/v[i-1][2]-base); y.append(v[i][1]/v[i][2]-base)
    return np.corrcoef(x,y)[0,1]
real=hh(P); random.seed(1); sims=[]
for _ in range(200):
    Q={k:random.sample(v,len(v)) for k,v in P.items()}
    sims.append(hh(Q))
print(f'hot hand check: real corr {real:+.3f}; with game order shuffled {np.mean(sims):+.3f} (95% range {np.percentile(sims,2.5):+.3f} to {np.percentile(sims,97.5):+.3f})')

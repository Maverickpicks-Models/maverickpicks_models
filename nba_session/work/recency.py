import openpyxl,numpy as np,collections,datetime as dt
wb=openpyxl.load_workbook('in1111c/s.xlsx',read_only=True,data_only=True)
trad={};adv={}
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True):
    if r[0] and r[2]: trad[(r[0],r[2].date())]=r[:24]
    if r[26] and r[28]: adv[(r[26],r[28].date())]=r[26:45]
def opp(mu):
    mu=mu.replace('\xa0',' '); return mu.split('@')[1].strip() if '@' in mu else mu.split('vs.')[1].strip()
TG=collections.defaultdict(list); played=collections.defaultdict(set)
for (t,d),a in adv.items():
    tr=trad.get((t,d)); 
    if not tr: continue
    o=opp(a[1]); played[t].add(d)
    TG[t].append(dict(d=d,o=o,home='vs.' in a[1],pace=a[17],ortg=a[5],drtg=a[6],efg=a[15],tov=a[14],orb=a[11],p3a=tr[10],p3m=tr[9],fga=tr[7],fta=tr[13],pts=tr[5]))
for t in TG: TG[t].sort(key=lambda x:x['d'])
# attach opponent shooting allowed
idx={(t,g['d']):g for t in TG for g in TG[t]}
for t in TG:
    for g in TG[t]:
        og=idx.get((g['o'],g['d']))
        g['op3m'],g['op3a'],g['ofga'],g['oefg']=(og['p3m'],og['p3a'],og['fga'],og['efg']) if og else (None,)*4
        g['p3pct']=g['p3m']/g['p3a']; g['p3r']=g['p3a']/g['fga']; g['op3pct']=g['op3m']/g['op3a'] if og else None; g['op3r']=g['op3a']/g['ofga'] if og else None
        g['b2b']=(g['d']-dt.timedelta(days=1)) in played[t]
stats=['ortg','drtg','pace','efg','p3pct','p3r','op3pct','op3r','tov','orb']
L={s:np.mean([g[s] for t in TG for g in TG[t] if g[s] is not None]) for s in stats}
print('league:',{k:round(v,3) for k,v in L.items()})
print('\nPredicting a team\'s NEXT game from its prior games (team-games with 5+ prior games). RMSE (lower better):')
print(f"{'stat':8s} {'league':>7s} {'season':>7s} {'last5':>7s} {'last3':>7s} {'EW hl4':>7s} {'shrunk':>7s}  n")
for s in stats:
    err=collections.defaultdict(list)
    for t in TG:
        G=TG[t]
        for i in range(5,len(G)):
            y=G[i][s]
            if y is None: continue
            prev=[g[s] for g in G[:i] if g[s] is not None]
            w=np.array([0.5**((len(prev)-1-k)/4) for k in range(len(prev))])
            seas=np.mean(prev); n=len(prev)
            preds=dict(league=L[s],season=seas,last5=np.mean(prev[-5:]),last3=np.mean(prev[-3:]),ew=np.sum(w*prev)/w.sum(),shrunk=L[s]+(seas-L[s])*n/(n+8))
            for k,v in preds.items(): err[k].append((v-y)**2)
    print(f"{s:8s} "+' '.join(f"{np.sqrt(np.mean(err[k])):7.3f}" for k in ('league','season','last5','last3','ew','shrunk'))+f"  {len(err['league'])}")
# split-half persistence
print('\nSplit-half persistence (corr of first-half vs second-half team averages):')
for s in stats:
    a=[];b=[]
    for t in TG:
        G=[g for g in TG[t] if g[s] is not None]; h=len(G)//2
        if h<3: continue
        a.append(np.mean([g[s] for g in G[:h]])); b.append(np.mean([g[s] for g in G[h:]]))
    print(f"  {s:8s} {np.corrcoef(a,b)[0,1]:+.2f}")
# defense and 3P: does a team's prior opp 3PA rate / opp 3P% predict the opponent's 3P outcome, beyond the shooter's own?
X=[];Y=[];Z=[]
for t in TG:
    G=TG[t]
    for i in range(4,len(G)):
        g=G[i]; og=idx.get((g['o'],g['d']))
        if og is None: continue
        oprev=[x for x in TG[g['o']] if x['d']<g['d']]
        if len(oprev)<4: continue
        dprev=G[:i]
        X.append([np.mean([x['op3pct'] for x in dprev if x['op3pct']]),np.mean([x['op3r'] for x in dprev if x['op3r']]),np.mean([x['p3pct'] for x in oprev]),np.mean([x['p3r'] for x in oprev])])
        Y.append([og['p3pct'],og['p3r']])
X=np.array(X);Y=np.array(Y)
def reg(cols,yi):
    A=np.c_[X[:,cols],np.ones(len(X))]; b=np.linalg.lstsq(A,Y[:,yi],rcond=None)[0]; e=Y[:,yi]-A@b
    s2=e.var()*len(e)/(len(e)-A.shape[1]); se=np.sqrt(np.diag(s2*np.linalg.inv(A.T@A)))
    return b,se
print(f"\nDefense vs 3s (n {len(X)} team-games): opponent's 3P% / 3PA rate in this game ~ defense's prior allowed + shooter's prior")
b,se=reg([0,2],0); print(f"  3P%: defense prior opp 3P% coef {b[0]:+.2f} (se {se[0]:.2f}) | shooter prior 3P% coef {b[1]:+.2f} (se {se[1]:.2f})")
b,se=reg([1,3],1); print(f"  3PA rate: defense prior allowed rate coef {b[0]:+.2f} (se {se[0]:.2f}) | shooter prior rate coef {b[1]:+.2f} (se {se[1]:.2f})")
# situational factors on shooting: eFG and 3P% residual vs own prior average
print('\nSituational effects on shooting (team-game value minus its own prior average, 3+ prior games):')
res=collections.defaultdict(list)
for t in TG:
    G=TG[t]
    for i in range(3,len(G)):
        g=G[i]; pe=np.mean([x['efg'] for x in G[:i]]); p3=np.mean([x['p3pct'] for x in G[:i]]); po=np.mean([x['ortg'] for x in G[:i]]); pp=np.mean([x['pace'] for x in G[:i]])
        og=idx.get((g['o'],g['d']))
        od=np.mean([x['drtg'] for x in TG[g['o']] if x['d']<g['d']]) if og else None
        keys=['all','home' if g['home'] else 'road','B2B' if g['b2b'] else 'rested']
        if od is not None: keys.append('vs good D (prior DRtg<110)' if od<110 else ('vs bad D (prior DRtg>115)' if od>115 else 'vs avg D'))
        if og: keys.append('opp on B2B' if og['b2b'] else None)
        for k in keys:
            if k: res[k].append((g['efg']-pe,(g['p3pct']-p3)*100,g['ortg']-po,g['pace']-pp))
for k,v in res.items():
    v=np.array(v); print(f"  {k:28s} n {len(v):3d} eFG {v[:,0].mean():+5.1f}  3P% {v[:,1].mean():+5.1f}  ORtg {v[:,2].mean():+5.1f}  pace {v[:,3].mean():+5.1f}")

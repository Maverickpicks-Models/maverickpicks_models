import json,numpy as np,collections,datetime
G=json.load(open('work/deep_games.json'))
G.sort(key=lambda g:g['d'])
# team-level residuals: points scored vs model, vs market implied TT; split by date halves
dates=sorted(set(g['d'] for g in G)); mid=dates[len(dates)//2]
def team_rows(g):
    if g['U'] is None or g['P'] is None: return []
    ia=g['P']/2-g['U']/2; ih=g['P']/2+g['U']/2   # U = away spread: away implied = P/2 - U/2
    return [(g['ab'],'off',g['an']-g['ap'],g['an']-ia),(g['hb'],'off',g['hn']-g['hp'],g['hn']-ih),
            (g['hb'],'def',g['an']-g['ap'],g['an']-ia),(g['ab'],'def',g['hn']-g['hp'],g['hn']-ih)]
for kind in ('off','def'):
    E=collections.defaultdict(list);L=collections.defaultdict(list)
    for g in G:
        for t,k,rmod,rmk in team_rows(g):
            if k!=kind: continue
            (E if g['d']<mid else L)[t].append((rmod,rmk))
    ts=[t for t in E if len(E[t])>=3 and len(L[t])>=3]
    for j,lab in ((0,'vs model'),(1,'vs market')):
        x=np.array([np.mean([v[j] for v in E[t]]) for t in ts]); y=np.array([np.mean([v[j] for v in L[t]]) for t in ts])
        print(f"{kind} residual {lab}: early->late team correlation {np.corrcoef(x,y)[0,1]:+.2f}, slope {np.polyfit(x,y,1)[0]:+.2f} (n teams {len(ts)})")
# rolling: does team's prior average residual vs MARKET predict next game residual vs market? (margin)
hist=collections.defaultdict(list); X=[];Y=[]; Xm=[];Ym=[]
for g in G:
    if g['U'] is None: continue
    am=g['an']-g['hn']; rk=am+g['U']; rmod=am-(g['ap']-g['hp'])
    ha,hh=hist[g['ab']],hist[g['hb']]
    if len(ha)>=3 and len(hh)>=3:
        X.append(np.mean([v[0] for v in ha[-6:]])-np.mean([v[0] for v in hh[-6:]])); Y.append(rk)
        Xm.append(np.mean([v[1] for v in ha[-6:]])-np.mean([v[1] for v in hh[-6:]])); Ym.append(rmod)
    hist[g['ab']].append((rk,rmod)); hist[g['hb']].append((-rk,-rmod))
X,Y,Xm,Ym=map(np.array,(X,Y,Xm,Ym))
print(f"\nrecent ATS form (last<=6 games, cover margin vs line) -> next game cover margin: corr {np.corrcoef(X,Y)[0,1]:+.2f}, slope {np.polyfit(X,Y,1)[0]:+.2f}, n {len(X)}")
print(f"recent residual vs model -> next residual vs model: corr {np.corrcoef(Xm,Ym)[0,1]:+.2f}, slope {np.polyfit(Xm,Ym,1)[0]:+.2f}")
# cover rate when betting team with better recent ATS form by 8+
for thr in (5,8,12):
    m=np.abs(X)>=thr; s=np.sign(X[m])*Y[m]
    print(f"  back better-ATS-form team when gap>={thr}: {np.sum(s>0)}-{np.sum(s<0)}")
    print(f"  fade (bet worse-form team) gap>={thr}: {np.sum(s<0)}-{np.sum(s>0)}")

import json,math,numpy as np,collections
G=json.load(open('work/deep_games.json'))
def rm(x): x=np.array(x); return math.sqrt((x**2).mean())
def ols(X,y):
    X=np.column_stack([np.ones(len(y))]+X); b,*_=np.linalg.lstsq(X,y,rcond=None); e=y-X@b
    se=np.sqrt(np.diag(e@e/(len(y)-X.shape[1])*np.linalg.inv(X.T@X))); return b,se
for era in ('all','old','roster'):
    xs=[g for g in G if (era=='all' or g['era']==era) and g['U'] is not None]
    am=np.array([g['an']-g['hn'] for g in xs]); mm=np.array([g['ap']-g['hp'] for g in xs]); km=np.array([-g['U'] for g in xs])
    at=np.array([g['an']+g['hn'] for g in xs]); mt=np.array([g['ap']+g['hp'] for g in xs]); kt=np.array([g['P'] for g in xs])
    b,se=ols([mm-km],am-km); bt,st=ols([mt-kt],at-kt)
    print(f"[{era}] n={len(xs)} margin RMSE model {rm(am-mm):.2f} market {rm(am-km):.2f} | model bias (actual-model, away pov) {np.mean(am-mm):+.2f} market {np.mean(am-km):+.2f}")
    print(f"     totals RMSE model {rm(at-mt):.2f} market {rm(at-kt):.2f} | bias model {np.mean(at-mt):+.2f} market {np.mean(at-kt):+.2f}")
    print(f"     weight on (model-market): margin {b[1]:+.2f} (se {se[1]:.2f}), total {bt[1]:+.2f} (se {st[1]:.2f})")
    for k in (0,0.25,0.5,1):
        print(f"       blend k={k}: margin RMSE {rm(am-(km+k*(mm-km))):.2f}  total RMSE {rm(at-(kt+k*(mt-kt))):.2f}")
# home court
for era in ('old','roster'):
    xs=[g for g in G if g['era']==era and g['U'] is not None]
    print(f"[{era}] home margin actual {np.mean([g['hn']-g['an'] for g in xs]):+.2f} model {np.mean([g['hp']-g['ap'] for g in xs]):+.2f} market {np.mean([g['U'] for g in xs]):+.2f}")
# B2B
print()
for era in ('all','roster'):
    for lab,f in [('away on B2B only',lambda g:g['a_b2b'] and not g['h_b2b']),('home on B2B only',lambda g:g['h_b2b'] and not g['a_b2b']),('neither',lambda g:not g['a_b2b'] and not g['h_b2b'])]:
        xs=[g for g in G if (era=='all' or g['era']==era) and g['U'] is not None and f(g)]
        if not xs: continue
        res_m=np.mean([(g['an']-g['hn'])-(g['ap']-g['hp']) for g in xs]); res_k=np.mean([(g['an']-g['hn'])+g['U'] for g in xs])
        print(f"[{era}] {lab:18s} n={len(xs):3d}  away-margin resid vs model {res_m:+.2f}  vs market {res_k:+.2f}")

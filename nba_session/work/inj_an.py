import json,numpy as np,collections,datetime as dt
R=[r for r in json.load(open('work/pace_rows.json')) if 'mt' in r]
# league pace by week
A=json.load(open('work/pace_rows.json'))
wk=collections.defaultdict(list)
for r in A:
    d=dt.date.fromisoformat(r['d']); wk[(d-dt.date(2026,10,20)).days//7].append(r['act_pace'])
print('league pace by week:',{k:round(np.mean(v),1) for k,v in sorted(wk.items())})
adj_m=np.array([r['mm']-r['mm0'] for r in R]); adj_t=np.array([r['mt']-r['mt0'] for r in R])
act_m=np.array([r['margin'] for r in R]); mkt_m=np.array([-r['U'] if r['U'] is not None else np.nan for r in R])
act_t=np.array([r['tot'] for r in R]); line=np.array([r['P'] for r in R])
mm=np.array([r['mm'] for r in R]); mm0=np.array([r['mm0'] for r in R]); mt=np.array([r['mt'] for r in R]); mt0=np.array([r['mt0'] for r in R])
ok=~np.isnan(mkt_m)
print(f"\nroster-era games {len(R)}; injury adjustment to margin: mean |adj| {np.abs(adj_m).mean():.1f}, games with |adj|>=2: {(np.abs(adj_m)>=2).sum()}")
rm=lambda x,y:np.sqrt(np.mean((x-y)**2))
print(f"Margin RMSE: with injuries {rm(mm[ok],act_m[ok]):.2f} | without {rm(mm0[ok],act_m[ok]):.2f} | market {rm(mkt_m[ok],act_m[ok]):.2f}")
print(f"Total  RMSE: with injuries {rm(mt,act_t):.2f} | without {rm(mt0,act_t):.2f} | line {rm(line,act_t):.2f}")
# slope: actual - no-injury projection vs injury adjustment (1.0 = sized right)
def slope(x,y):
    X=np.c_[x,np.ones(len(x))]; b,res,_,_=np.linalg.lstsq(X,y,rcond=None); e=y-X@b; se=np.sqrt(e.var()*len(x)/(len(x)-2)/((x-x.mean())**2).sum()); return b[0],se
for lab,s in (('all',ok),('|adj|>=2',ok&(np.abs(adj_m)>=2))):
    b,se=slope(adj_m[s],(act_m-mm0)[s]); b2,se2=slope(adj_m[s],(act_m-mkt_m)[s])
    print(f"  margin [{lab}, n {s.sum()}]: actual-vs-healthy slope on injury adj {b:.2f} (se {se:.2f}) | vs market residual {b2:+.2f} (se {se2:.2f})")
b,se=slope(adj_t,act_t-mt0); b2,se2=slope(adj_t,act_t-line)
print(f"  total: actual-vs-healthy slope {b:.2f} (se {se:.2f}) | vs line residual {b2:+.2f} (se {se2:.2f})")
# big injury games: who was right
big=ok&(np.abs(adj_m)>=3)
print(f"\nGames where injuries moved our margin 3+ pts: n {big.sum()}")
for r,a in zip([r for r,s in zip(R,big) if s],adj_m[big]):
    print(f"  {r['d']} {r['g']:8s} inj adj {a:+5.1f} | healthy {r['mm0']:+5.1f} model {r['mm']:+5.1f} market {-r['U']:+5.1f} actual {r['margin']:+4.0f}")
# which side: when model with injuries disagrees with market by 3+, does injury explain the disagreement?
gap=mm-mkt_m; gap0=mm0-mkt_m
print(f"\nModel-vs-market gap: mean |gap| with injuries {np.nanmean(np.abs(gap)):.1f}, healthy {np.nanmean(np.abs(gap0)):.1f}")

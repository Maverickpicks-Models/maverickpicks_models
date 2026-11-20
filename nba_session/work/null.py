import pandas as pd, numpy as np, math, itertools
exec(open('work/scan.py').read().split("split = df.date")[0])   # reuse condition families
R=pd.read_pickle('work/rules.pkl')
print('rules p<0.05:',(R.p_value<.05).sum(),'of',len(R),'(expected by chance ~',round(.05*len(R)),')')
# Monte Carlo null: re-draw every GAME's outcome from the market so mirrored legs stay complementary.
rng=np.random.default_rng(7)
flat=[v.values for dd in C.values() for v in dd.values()]
fam=[f for f,dd in C.items() for _ in dd]
masks=flat+[a&b for (i,a),(j,b) in itertools.combinations(enumerate(flat),2) if fam[i]!=fam[j] and (a&b).sum()>=8]
M=np.array(masks,dtype=float)
dec=np.where(df.odds<0,100/df.odds.abs(),df.odds/100)
nv=df.novig_p.values; mev=nv*dec-(1-nv); var=nv*(1-nv)*(dec+1)**2
pair=np.arange(len(df))^1      # legs come in complementary pairs (away/home, over/under)
sd=np.sqrt(M@var); base=M@mev
mx=[]
for _ in range(2000):
    u=rng.random(len(df)//2)
    first=np.repeat(u,2)
    win=np.where(np.arange(len(df))%2==0, first<nv, first>=nv[pair])
    prof=np.where(win,dec,-1.0)
    z=(M@prof-base)/sd
    mx.append(z.max())
mx=np.array(mx); obs=R.z_vs_market.max()
print('observed best z',round(obs,2),'| luck-only best z median',round(np.median(mx),2),'90th',round(np.quantile(mx,.9),2),
      '| share of luck-only runs beating observed:',round((mx>=obs).mean(),3))
# overlap among candidates
cand={'A Gap 3-6':C['Proj gap']['Gap 3-6 pts'],'B Model>=60% @ -115..+115':C['Model %']['Model >=60%']&C['Price']['Odds -115 to +115'],
      'C Under + Model 55-65%':C['Side']['Under']&C['Model %']['Model 55-65%']}
for a,b in itertools.combinations(cand,2): print(a,'&',b,'shared legs',int((cand[a]&cand[b]).sum()),'of',int(cand[a].sum()),int(cand[b].sum()))
u=cand['A Gap 3-6']|cand['B Model>=60% @ -115..+115']|cand['C Under + Model 55-65%']; d=df[u]
print('union',len(d),int(d.win.sum()),round(d.profit.sum(),2))
for k,m in cand.items():
    d=df[m]; print(k, d.groupby('market').agg(n=('win','size'),w=('win','sum'),u=('profit','sum')).round(2).to_dict('index'))

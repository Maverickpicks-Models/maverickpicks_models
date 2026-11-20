import json, math, itertools
from statistics import NormalDist
Z=NormalDist()
L=json.load(open('work/season_roster_legs.json'))
L=[x for x in L if x['edge']>0 and not x['push']]
def dec(o): return 100/-o if o<0 else o/100
for x in L:
    nv=x['model']-x['edge']; d=dec(x['odds']); x['mev']=nv*d-(1-nv); x['mvar']=nv*(1-nv)*(d+1)**2
    x['fav']=x['odds']<0
    x['ou']= None if x['market'] in ('ML','Spread') else ('U' if (x['lab'].startswith('Under') or ' TT u' in x['lab']) else 'O')
print('legs with positive edge',len(L))
F={
 'mkt':lambda x:x['market'],
 'side':lambda x:x['side'] or 'game',
 'ou':lambda x:x['ou'] or 'na',
 'fav':lambda x:'fav' if x['fav'] else 'dog',
 'odds':lambda x:'<=-150' if x['odds']<=-150 else '-149..-111' if x['odds']<=-111 else '-110..+110' if x['odds']<=110 else '+111..+149' if x['odds']<150 else '>=+150',
 'model':lambda x:'<45' if x['model']<.45 else '45-55' if x['model']<.55 else '55-60' if x['model']<.6 else '60-65' if x['model']<.65 else '65-70' if x['model']<.7 else '70+',
 'edge':lambda x:'0-4' if x['edge']<.04 else '4-8' if x['edge']<.08 else '8-12' if x['edge']<.12 else '12-20' if x['edge']<.2 else '20+',
 'gap':lambda x:'na' if x['gap'] is None else '<1' if x['gap']<1 else '1-3' if x['gap']<3 else '3-6' if x['gap']<6 else '6+',
 'disM':lambda x:'<2' if x['disagree_m']<2 else '2-4' if x['disagree_m']<4 else '4+',
 'disT':lambda x:'<3' if x['disagree_t']<3 else '3-6' if x['disagree_t']<6 else '6+',
 'b2b':lambda x:'b2b' if x['b2b'] else 'rest',
}
for x in L: x['f']={k:f(x) for k,f in F.items()}
EARLY=lambda x:x['date']<='2026-10-25'
def stats(S):
    n=len(S); w=sum(x['won'] for x in S); u=sum(x['pl'] for x in S); e=sum(x['mev'] for x in S); v=sum(x['mvar'] for x in S)
    z=(u-e)/math.sqrt(v) if v>0 else 0
    return n,w,u,z
rows=[]
keys=list(F)
for k in (1,2,3):
    for combo in itertools.combinations(keys,k):
        groups={}
        for x in L:
            groups.setdefault(tuple(x['f'][c] for c in combo),[]).append(x)
        for val,S in groups.items():
            if len(S)<15: continue
            n,w,u,z=stats(S); E=[x for x in S if EARLY(x)]; Lt=[x for x in S if not EARLY(x)]
            if len(E)<6 or len(Lt)<6: continue
            ne,we,ue,ze=stats(E); nl,wl,ul,zl=stats(Lt)
            p=2*(1-Z.cdf(abs(z)))
            rows.append(dict(rule=' & '.join(f"{c}={v}" for c,v in zip(combo,val)),n=n,w=w,u=u,z=z,p=p,ze=ze,zl=zl,ue=ue,ul=ul,ne=ne,nl=nl))
# BH
rows.sort(key=lambda r:r['p']); m=len(rows)
qmin=1
for i in range(m-1,-1,-1):
    qmin=min(qmin,rows[i]['p']*m/(i+1)); rows[i]['q']=qmin
print('combos tested',m)
print('best by full-sample p:')
for r in rows[:15]:
    print(f"  {r['rule']:55s} n{r['n']:3d} {r['w']}-{r['n']-r['w']} {r['u']:+6.1f}u z{r['z']:+.2f} q{r['q']:.2f} | early z{r['ze']:+.2f} ({r['ue']:+.1f}u n{r['ne']}) late z{r['zl']:+.2f} ({r['ul']:+.1f}u n{r['nl']})")
# replication: discovered early (z>=2) and positive late
rep=[r for r in rows if r['ze']>=2]
print('\nrules with early z>=2:',len(rep),' of which late z>0:',sum(r['zl']>0 for r in rep),' late z>=1.64:',sum(r['zl']>=1.64 for r in rep))
for r in sorted(rep,key=lambda r:-r['zl'])[:12]:
    print(f"  {r['rule']:55s} early {r['ue']:+5.1f}u z{r['ze']:+.2f} n{r['ne']} -> late {r['ul']:+5.1f}u z{r['zl']:+.2f} n{r['nl']}")
# null expectation of early z>=2 count
print('expected false hits at early z>=2 by chance ~', round(m*0.023))
base=stats(L); print('all positive-edge legs',base[0],base[1],'-',base[0]-base[1],round(base[2],1),'u z',round(base[3],2))
json.dump(rows,open('work/mine_roster_rows.json','w'))

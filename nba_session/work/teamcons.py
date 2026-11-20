import json, math, random, statistics as st
from collections import defaultdict
raw=json.load(open('work/teamgames_raw.json'))
G=[]
for x in raw:
    if x['A'] is None: continue
    G.append(dict(date=x['date'],aw=x['aw'],hm=x['hm'],ap=x['ap'],hp=x['hp'],A=x['A'],H=x['Hs'],tl=x['tl'],asp=x['asp']))
r=json.load(open('work/run1030b.json')); S=json.load(open('work/scores1030.json'))
for g in r['games']:
    A,H=S[g['game']]
    G.append(dict(date='2026-10-30',aw=g['aw'],hm=g['hm'],ap=g['ap'],hp=g['hp'],A=A,H=H,tl=g['mkt_total'],asp=-g['mkt_margin']))
# market implied points: home favored by asp when asp>0 (away +asp)
T=[]  # team-game rows
bad=0
for g in G:
    if not isinstance(g['tl'],(int,float)) or not isinstance(g['asp'],(int,float)) or g['tl']<150: bad+=1; continue
    ma=(g['tl']-g['asp'])/2; mh=(g['tl']+g['asp'])/2
    T.append(dict(team=g['aw'],opp=g['hm'],date=g['date'],home=0,pts=g['A'],allow=g['H'],mod=g['ap'],moda=g['hp'],mkt=ma,mkta=mh))
    T.append(dict(team=g['hm'],opp=g['aw'],date=g['date'],home=1,pts=g['H'],allow=g['A'],mod=g['hp'],moda=g['ap'],mkt=mh,mkta=ma))
print('games',len(G),'bad lines',bad,'team-games',len(T))
for x in T:
    x['e_mod']=x['pts']-x['mod']; x['e_mkt']=x['pts']-x['mkt']; x['d_mod']=x['allow']-x['moda']; x['d_mkt']=x['allow']-x['mkta']
json.dump(T,open('work/teamgames.json','w'))
by=defaultdict(list)
for x in T: by[x['team']].append(x)
rmse=lambda L: math.sqrt(sum(v*v for v in L)/len(L))
print('overall team-pts RMSE model',round(rmse([x['e_mod'] for x in T]),2),'market',round(rmse([x['e_mkt'] for x in T]),2),
      'bias model',round(st.mean(x['e_mod'] for x in T),2),'market',round(st.mean(x['e_mkt'] for x in T),2))
rows=[]
for tm,L in by.items():
    n=len(L)
    rows.append(dict(team=tm,n=n,ppg=st.mean(x['pts'] for x in L),opp=st.mean(x['allow'] for x in L),
      sd_pts=st.stdev(x['e_mkt'] for x in L) if n>1 else 0, sd_all=st.stdev(x['d_mkt'] for x in L) if n>1 else 0,
      off_mod=st.mean(x['e_mod'] for x in L), off_mkt=st.mean(x['e_mkt'] for x in L),
      def_mod=st.mean(x['d_mod'] for x in L), def_mkt=st.mean(x['d_mkt'] for x in L),
      mkt_minus_mod_off=st.mean(x['mkt']-x['mod'] for x in L), mkt_minus_mod_def=st.mean(x['mkta']-x['moda'] for x in L)))
rows.sort(key=lambda x:-x['sd_pts'])
print(f"{'team':24s} n  ppg  opp | SD scored SD allowed (vs market) | scored vs model / vs mkt | allowed vs model / vs mkt | mkt-model off/def")
for x in rows:
    print(f"{x['team']:24s} {x['n']} {x['ppg']:5.1f} {x['opp']:5.1f} | {x['sd_pts']:5.1f} {x['sd_all']:5.1f} | {x['off_mod']:+5.1f} {x['off_mkt']:+5.1f} | {x['def_mod']:+5.1f} {x['def_mkt']:+5.1f} | {x['mkt_minus_mod_off']:+5.1f} {x['mkt_minus_mod_def']:+5.1f}")
json.dump(rows,open('work/teamcons_rows.json','w'))
# heterogeneity permutation test: is spread of per-team SDs bigger than random?
def stat(T,key):
    b=defaultdict(list)
    for x in T: b[x['team']].append(x[key])
    sds=[st.stdev(v) for v in b.values() if len(v)>2]
    return st.pstdev(sds), b
random.seed(1)
for key in ['e_mkt','d_mkt']:
    obs,_=stat(T,key); vals=[x[key] for x in T]; cnt=0; N=2000
    teams=[x['team'] for x in T]
    for _ in range(N):
        random.shuffle(vals)
        TT=[dict(team=t,**{key:v}) for t,v in zip(teams,vals)]
        if stat(TT,key)[0]>=obs: cnt+=1
    print(key,'spread of team SDs',round(obs,2),'perm p',cnt/N)
# team mean-error heterogeneity (bias) for model vs market: variance of team means vs expected noise
for key in ['e_mod','e_mkt','d_mod','d_mkt']:
    b=defaultdict(list)
    for x in T: b[x['team']].append(x[key])
    resid_var=st.mean([st.pvariance(v)*len(v)/(len(v)-1) for v in b.values()])
    means=[st.mean(v) for v in b.values()]; ns=[len(v) for v in b.values()]
    exp_var=st.mean([resid_var/n for n in ns]); obs_var=st.pvariance(means)
    # permutation
    vals=[x[key] for x in T]; teams=[x['team'] for x in T]; cnt=0
    for _ in range(2000):
        random.shuffle(vals); bb=defaultdict(list)
        for t_,v in zip(teams,vals): bb[t_].append(v)
        if st.pvariance([st.mean(v) for v in bb.values()])>=obs_var: cnt+=1
    print(key,'team-mean variance',round(obs_var,1),'expected from noise',round(exp_var,1),'perm p',cnt/2000)

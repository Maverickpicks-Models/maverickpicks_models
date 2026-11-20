import json,math,numpy as np
from statistics import NormalDist
N=NormalDist()
# Crafted published away win prob + Crafted projected home margin
C={('Milwaukee Bucks','New York Knicks'):(11.9,14.3),('Boston Celtics','Philadelphia 76ers'):(57.5,-2.2),('LA Clippers','Phoenix Suns'):(45.8,1.2),
 ('Miami Heat','Utah Jazz'):(66.0,-4.7),('Orlando Magic','Sacramento Kings'):(62.3,-3.6),('Oklahoma City Thunder','Portland Trail Blazers'):(48.5,0.4),
 ('Boston Celtics','Toronto Raptors'):(68.1,-5.4),('Cleveland Cavaliers','New York Knicks'):(34.7,4.5),('Washington Wizards','Indiana Pacers'):(32.8,5.1),
 ('Brooklyn Nets','New Orleans Pelicans'):(40.2,2.8),('Denver Nuggets','Memphis Grizzlies'):(64.1,-4.1),('Los Angeles Lakers','Milwaukee Bucks'):(91.2,-16.7),
 ('San Antonio Spurs','Chicago Bulls'):(92.0,-17.5),('Orlando Magic','Utah Jazz'):(53.8,-1.1),('Golden State Warriors','Houston Rockets'):(30.9,5.8),
 ('Oklahoma City Thunder','Portland Trail Blazers#2'):(36.5,4.0)}
S={'11/10':[(85,117),(123,101),(110,133),(115,109),(107,100),(103,123)],'11/11':[(98,93),(115,107),(101,114),(145,111),(123,118),(123,112),(124,119),(123,106),(108,115),(108,118)]}
R=[]
for f,day in (('run1110c.json','11/10'),('run1111.json','11/11')):
    for g,(a,h) in zip(json.load(open('work/'+f)),S[day]):
        key=(g['aw'],g['hm']) if not (day=='11/11' and g['aw']=='Oklahoma City Thunder') else (g['aw'],g['hm']+'#2')
        cp,cm=C[key]
        L={x['lab']:x for x in g['legs']}
        R.append(dict(day=day,g=f"{g['aw'].split()[-1]}@{g['hm'].split()[-1]}",crafted=cp/100,model=L[f"{g['aw']} ML"]['model'],market=L[f"{g['aw']} ML"]['nv'],won=int(a>h),cm=cm))
# implied sigma of crafted
sig=[abs(r['cm'])/abs(N.inv_cdf(r['crafted'])) for r in R if abs(r['crafted']-.5)>.05]
print('Crafted implied margin SD: median %.1f'%np.median(sig))
def score(k):
    p=np.array([r[k] for r in R]); y=np.array([r['won'] for r in R])
    brier=np.mean((p-y)**2); ll=-np.mean(y*np.log(p)+(1-y)*np.log(1-p)); acc=np.mean((p>.5)==y)
    return brier,ll,acc,p
print(f"{'':8s} Brier  LogLoss  Picked winner")
for k in ('crafted','model','market'):
    b,l,a,_=score(k); print(f"{k:8s} {b:.3f}  {l:.3f}   {int(round(a*len(R)))}/{len(R)}")
print('coin flip 0.250  0.693')
for r in R: print(f"{r['day']} {r['g']:22s} crafted {r['crafted']*100:5.1f} model {r['model']*100:5.1f} market {r['market']*100:5.1f}  away won {r['won']}")
json.dump(R,open('work/wp_cmp.json','w'))

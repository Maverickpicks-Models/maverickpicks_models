import json,numpy as np,math
G=json.load(open('work/deep_games.json'))
def dec(o): return 100/-o if o<0 else o/100
sgn=lambda x:(x>0)-(x<0)
def z(rows):  # rows (win,nv)
    w=sum(r[0] for r in rows); e=sum(r[1] for r in rows); v=sum(r[1]*(1-r[1]) for r in rows); return (w-e)/math.sqrt(v) if v else 0
print("ML favorites by Novig no-vig probability (favorite side of every game):")
bands=[(0.5,0.6),(0.6,0.7),(0.7,0.8),(0.8,0.9),(0.9,1.01)]
for lo,hi in bands:
    for era in ('old','roster'):
        rows=[]
        for g in G:
            p=g['nv_ml_away']
            if p is None or g['J'] is None: continue
            fav_a=p>=0.5; pf=p if fav_a else 1-p
            if not(lo<=pf<hi): continue
            win=sgn(g['an']-g['hn'])*(1 if fav_a else -1)>0
            o=g['J'] if fav_a else g['K']; u=dec(o) if win else -1
            rows.append((win,pf,u))
        if rows: print(f"  fav {lo:.0%}-{min(hi,1):.0%} {era:6s}: {sum(r[0] for r in rows)}-{sum(1-r[0] for r in rows)}  won {np.mean([r[0] for r in rows])*100:4.1f}% vs priced {np.mean([r[1] for r in rows])*100:4.1f}%  {sum(r[2] for r in rows):+.2f}u  z {z(rows):+.1f}")
print("\nTotals: juiced side (Novig 52%+), split by Over/Under juiced:")
for side in ('over','under'):
    for era in ('old','roster'):
        w=l=0
        for g in G:
            p=g['nv_over']
            if p is None: continue
            if side=='over' and p<0.52: continue
            if side=='under' and p>0.48: continue
            ov=sgn(g['an']+g['hn']-g['P'])
            r= ov if side=='over' else -ov
            w+=r>0; l+=r<0
        print(f"  juiced {side:5s} {era:6s}: juiced side {w}-{l}")
print("\nUnder by week:")
import datetime,collections
wk=collections.defaultdict(lambda:[0,0,[]])
for g in G:
    if g['P'] is None: continue
    d=datetime.date.fromisoformat(g['d']); k=(d-datetime.date(2026,10,20)).days//7
    r=sgn(g['P']-(g['an']+g['hn'])); wk[k][0]+=r>0; wk[k][1]+=r<0; wk[k][2].append(g['an']+g['hn']-g['P'])
for k in sorted(wk): print(f"  week {k+1}: unders {wk[k][0]}-{wk[k][1]}, avg total vs line {np.mean(wk[k][2]):+.1f}")
print("\nModel spread disagreement bands (follow model side), by era:")
for lo,hi in ((0,1),(1,2),(2,3),(3,4),(4,6),(6,9),(9,99)):
    for era in ('old','roster'):
        w=l=0
        for g in G:
            if g['U'] is None or g['era']!=era: continue
            dm=(g['ap']-g['hp'])+g['U']
            if not(lo<=abs(dm)<hi): continue
            c=sgn((g['an']-g['hn'])+g['U'])*(1 if dm>0 else -1); w+=c>0; l+=c<0
        print(f"  {lo}-{hi} pts {era:6s}: {w}-{l}",end='   ')
    print()
print("\nModel total disagreement bands (follow model side):")
for lo,hi in ((0,2),(2,4),(4,6),(6,9),(9,99)):
    for era in ('old','roster'):
        w=l=0
        for g in G:
            if g['P'] is None or g['era']!=era: continue
            dt=(g['ap']+g['hp'])-g['P']
            if not(lo<=abs(dt)<hi): continue
            c=sgn((g['an']+g['hn'])-g['P'])*(1 if dt>0 else -1); w+=c>0; l+=c<0
        print(f"  {lo}-{hi} {era:6s}: {w}-{l}",end='   ')
    print()

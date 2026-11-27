"""11/25 paper card: v5.2 plays sized like the season replay ($20 unit, $20 bet, $30 game, $120 night, scaled in proportion)."""
import json
R=json.load(open('work/run1125_recs.json')); G=json.load(open('work/run1125.json'))
def units(s):
    s=str(s)
    if s.startswith('risk'): return float(s.split()[1].rstrip('u'))
    return float(s.split('u')[0])
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
CFG=json.load(open('work/cfg_1125.json')); QH=CFG.get('q_half',{})
games=[]
for o,g in zip(R,G):
    st=[[min(20.0,units(p['units'])*20),p] for p in o['plays']]
    for x in st:      # questionable 30+ mpg starter on the team we back -> half stake
        tm=g['aw'] if x[1]['side']=='away' else g['hm'] if x[1]['side']=='home' else None
        if tm in QH and x[1]['mk'] in ('spread','ml'):
            x[0]/=2; x[1]['codes']=x[1]['codes']+[f"half: {QH[tm]}"]
    t=sum(x[0] for x in st)
    if t>30:
        for x in st: x[0]*=30/t
    games.append((g,st))
tot=sum(x[0] for _,st in games for x in st); k=min(1,120/tot)
out=[]
MK={'spread':'Spread','total':'Total','ml':'ML'}
for g,st in games:
    for usd,p in st:
        side={'away':'Away','home':'Home','over':'Over','under':'Under'}[p['side']]
        out.append(dict(date='2026-11-25',aw=g['aw'],hm=g['hm'],market=MK[p['mk']],side=side,lab=p['lab'],sec=p['sec'],
                        price_pct=round(imp(p['odds']),3),odds=p['odds'],stake=round(usd*k*2)/2,units=round(usd*k/20,3),rules='+'.join(c for c in p['codes'] if not c.startswith('half'))+''.join(f' ({c})' for c in p['codes'] if c.startswith('half'))))
json.dump(out,open('work/bets_1125.json','w'),indent=1)
for x in out: print(f"{x['aw'][:12]:12s} @ {x['hm'][:12]:12s} {x['sec']:5s} {x['lab']:18s} {x['odds']:+5d}  ${x['stake']:5.1f}  {x['rules']}")
print('total $',sum(x['stake'] for x in out), 'scale',round(k,3))

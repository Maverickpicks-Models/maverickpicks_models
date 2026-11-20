import sys, json, openpyxl, datetime
sys.path.insert(0,'work')
import bt_recent as BR
from collections import defaultdict
wb=openpyxl.load_workbook('in16/nba.xlsx',data_only=True); t=wb['Tracking']
H={t.cell(12,c).value:c for c in range(1,50) if t.cell(12,c).value}
games=[]
for r in range(13,84):
    g=lambda h: t.cell(r,H[h]).value
    if not g('Away') or g('Away pts') is None: continue
    d=str(g('Game date'))[:10]
    if r in (82,83): d='2026-10-29'
    games.append(dict(row=r,date=d,aw=g('Away'),hm=g('Home'),A=g('Away pts'),H=g('Home pts'),old=(g('Away proj'),g('Home proj')),
      mlo=(g('ML away odds'),g('ML home odds')),tl=g('Total line'),to=(g('Over odds'),g('Under odds')),asp=g('Away spread'),so=(g('Away spr odds'),g('Home spr odds')),
      atl=g('Away TT line'),ato=(g('Away TT Over'),g('Away TT Under')),htl=g('Home TT line'),hto=(g('Home TT Over'),g('Home TT Under'))))
games+= [g for g in BR.games if g['date']=='2026-10-30']
# B2B from schedule
played=defaultdict(set)
for g in games: played[g['date']]|={g['aw'],g['hm']}
def prevday(d): return (datetime.date.fromisoformat(d)-datetime.timedelta(days=1)).isoformat()
legs=[]
for g in games:
    ab=g['aw'] in played[prevday(g['date'])]; hb=g['hm'] in played[prevday(g['date'])]
    outs=BR.OUT.get(g['date'],{})
    ap,hp=BR.proj(g['aw'],g['hm'],outs,ab,hb)
    g['new']=(ap,hp); g['b2b']=(ab,hb)
    for x in BR.legs(g,ap,hp):
        side='away' if x['lab'].startswith('away') else 'home' if x['lab'].startswith('home') else None
        x.update(market=x['mk'], side=side, over=('o' in x['lab'].split()[-1][:1] or x['lab'].startswith('Over')) if x['mk'] in('Total','TT') else None,
                 b2b=(ab if side=='away' else hb) if side else (ab or hb), opp_b2b=(hb if side=='away' else ab) if side else None,
                 mkt_margin=-g['asp'], model_margin=ap-hp, disagree_m=abs((ap-hp)-(-g['asp'])), disagree_t=abs(ap+hp-g['tl']))
        legs.append(x)
print('games',len(games),'legs',len(legs),'dates',sorted({g['date'] for g in games}))
json.dump(legs,open('work/season_roster_legs.json','w'),default=str)
c=[x for x in legs if x['card']]
print('roster card season',sum(x['won'] for x in c),'-',sum(not x['won'] and not x['push'] for x in c),round(sum(x['pl'] for x in c),2))
for d in sorted({x['date'] for x in legs}):
    cc=[x for x in c if x['date']==d]; print(d,sum(x['won'] for x in cc),'-',sum(not x['won'] and not x['push'] for x in cc),round(sum(x['pl'] for x in cc),2))

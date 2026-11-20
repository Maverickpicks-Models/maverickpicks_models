src=open('audit/luck_style.py').read().split("os.environ['WB']")[0]
exec(src)
import datetime as dt
day=dt.date(2026,11,17)
games=[('NYK','TOR',-2.5,111,102),('DET','SAS',9.5,105,93),('POR','MIN',3.5,105,106),('UTA','LAC',6.5,132,107),('CHA','LAL',7.5,114,118)]
# terciles from historical G json
import json
H=json.load(open('audit/luck_style_games.json'))
def terc(f):
    xs=sorted(f(g['pa'],g['ph']) for g in H); return xs[len(xs)//3],xs[2*len(xs)//3]
FTR=lambda a,h:(a['ftr']-a['oftr'])-(h['ftr']-h['oftr'])
FORM=lambda a,h:a['form']-h['form']
PY=lambda a,h:a['pyth']-h['pyth']
for name,f,sgn in [('FT-rate edge (bet the side with the edge)',FTR,+1),('Form fade (bet against the hotter team)',FORM,-1),('Pythagorean fade (bet against the luckier record)',PY,-1)]:
    lo,hi=terc(f); print('--',name)
    for a,h,U,an,hn in games:
        pa,ph=prof(a,day),prof(h,day); x=f(pa,ph)
        if x>=hi: want_away = sgn>0
        elif x<=lo: want_away = sgn<0
        else: print(f'   {a}@{h}: no signal ({x:+.3f})'); continue
        acov=(an-hn)+U; res='W' if (acov>0)==want_away else 'L'
        print(f"   {a}@{h}: bet {'away '+a if want_away else 'home '+h} -> {res}")

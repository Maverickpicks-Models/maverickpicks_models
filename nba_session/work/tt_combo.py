import json,numpy as np
G=json.load(open('work/deep_games11.json'))
S=[(98,93),(115,107),(101,114),(145,111),(123,118),(123,112),(124,119),(123,106),(108,115),(108,118)]
for g,(a,h) in zip(json.load(open('work/run1111.json')),S):
    L={x['lab']:x for x in g['legs']}; P=g['tot'][0]
    d=dict(d='2026-11-11',era='roster',an=a,hn=h,P=P,R=L[f'Over {P}']['model'],S=L[f'Over {P}']['odds'],T=L[f'Under {P}']['odds'],U=g['sp'][0],ap=g['ap'],hp=g['hp'],AA=None,AE=None)
    if g['att']:
        d.update(AA=g['att'][0],AB=L[f"{g['aw']} TT Over {g['att'][0]}"]['model'],AE=g['htt'][0],AF=L[f"{g['hm']} TT Over {g['htt'][0]}"]['model'])
    G.append(d)
def dec(o): return 100/-o if o<0 else o/100
rows=[]
for g in G:
    if not g.get('AA') or not g.get('AE') or g['P'] is None or g.get('AB') is None or g.get('AF') is None: continue
    tot=g['an']+g['hn']
    if tot==g['P']: continue
    fav_away = (g['U'] is not None and g['U']<0) if g['U'] is not None else g['ap']>g['hp']
    rows.append(dict(era=g['era'],aU=g['AB']<.5,hU=g['AF']<.5,favU=(g['AB']<.5) if fav_away else (g['AF']<.5),dogU=(g['AF']<.5) if fav_away else (g['AB']<.5),
      gU=g['R']<.5,under=tot<g['P'],So=g['S'],To=g['T'],
      aUact=g['an']<g['AA'],hUact=g['hn']<g['AE'],ttsum=g['AA']+g['AE']-g['P']))
print('games with both TT lines + model',len(rows))
def rep(lab,sel,side):
    for e in ('all','old','roster'):
        s=[r for r in rows if sel(r) and (e=='all' or r['era']==e)]
        if not s: continue
        win=[(r['under'] if side=='U' else not r['under']) for r in s]
        u=sum((dec(r['To'] if side=='U' else r['So']) if w else -1) for r,w in zip(s,win) if (r['To'] if side=='U' else r['So']))
        print(f"  {lab:34s} {e:6s} game {'Under' if side=='U' else 'Over '} {sum(win)}-{len(win)-sum(win)} ({sum(win)/len(win)*100:4.0f}%) {u:+5.1f}u")
print('MODEL LEANS (pre-game) vs GAME TOTAL result')
rep('Model: both TT Under',lambda r:r['aU'] and r['hU'],'U')
rep('Model: both TT Over',lambda r:not r['aU'] and not r['hU'],'O')
rep('Model: split TT (bet game Under)',lambda r:r['aU']!=r['hU'],'U')
rep('Model: favorite TT Under',lambda r:r['favU'],'U')
rep('Model: favorite TT Over',lambda r:not r['favU'],'O')
rep('Model: underdog TT Under',lambda r:r['dogU'],'U')
rep('Model: underdog TT Over',lambda r:not r['dogU'],'O')
rep('Model: away TT Under',lambda r:r['aU'],'U')
rep('Model: away TT Over',lambda r:not r['aU'],'O')
rep('Model: home TT Under',lambda r:r['hU'],'U')
rep('Model: home TT Over',lambda r:not r['hU'],'O')
rep('Model: game total Under (reference)',lambda r:r['gU'],'U')
rep('Model: game total Over (reference)',lambda r:not r['gU'],'O')
rep('Both TT Under AND game Under lean',lambda r:r['aU'] and r['hU'] and r['gU'],'U')
rep('Both TT Over AND game Over lean',lambda r:not r['aU'] and not r['hU'] and not r['gU'],'O')
print('\nACTUAL RESULTS (how often team totals and game total land together)')
import itertools
both_u=[r for r in rows if r['aUact'] and r['hUact']]; both_o=[r for r in rows if not r['aUact'] and not r['hUact']]; split=[r for r in rows if r['aUact']!=r['hUact']]
print(f"  both TT went Under: {len(both_u)} games, game total Under {sum(r['under'] for r in both_u)}")
print(f"  both TT went Over : {len(both_o)} games, game total Over {sum(not r['under'] for r in both_o)}")
print(f"  split             : {len(split)} games, game total Under {sum(r['under'] for r in split)}")
print(f"  TT lines sum vs game total: mean {np.mean([r['ttsum'] for r in rows]):+.2f}")
print()
rep('BASELINE every game',lambda r:True,'U')
rep('Fav TT Under + Dog TT Over',lambda r:r['favU'] and not r['dogU'],'U')
rep('Fav TT Over + Dog TT Under',lambda r:not r['favU'] and r['dogU'],'U')

exec(open('audit/angles34_b.py').read().split("print('| angle 3 strategy")[0])
import math
day=dt.date(2026,11,17)
print('--- angle 3: ML vs spread residual (follow ML side on spread when |resid|>=0.03)')
for r in rows:
    g=r['g']
    if g['d']!=day: continue
    acov=(g['an']-g['hn'])+g['U']; side='away' if r['res']>0 else 'home'
    print(f"  resid {r['res']:+.3f} -> {'BET '+side if abs(r['res'])>=0.03 else 'no signal'}; away covered {acov>0}")
SIGT=10.0
print('--- angle 4: TT vs total / spread')
for g in G:
    if g['d']!=day or None in (g['AA'],g['AE'],g['AC'],g['AD'],g['AG'],g['AH']): 
        if g['d']==day: print('  no full TT data'); 
        continue
    ta=g['AA']+SIGT*N.inv_cdf(nv(g['AC'],g['AD'])); th=g['AE']+SIGT*N.inv_cdf(nv(g['AG'],g['AH']))
    tot=g['P']+17*N.inv_cdf(nv(g['S'],g['T'])); hm=g['U']+SIG*N.inv_cdf(nv(g['Z'],g['W']))
    sg=(ta+th)-tot; mg=(th-ta)-hm
    print(f"  TT sum gap {sg:+.1f} (signal >=+1.5 -> TT Unders) | margin gap {mg:+.1f} (signal |>=1| -> spread side TTs favor: {'home' if mg>0 else 'away'}) | final {g['an']}-{g['hn']}, TTs {g['AA']}/{g['AE']}")

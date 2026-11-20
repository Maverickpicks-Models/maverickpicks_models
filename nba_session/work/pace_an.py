import json,numpy as np
R=[r for r in json.load(open('work/pace_rows.json'))]
P=[r for r in R if r['exp_pace'] is not None]
LGE=np.mean([r['eff'] for r in R])
print(f"games with pre-game pace: {len(P)} | league pace {np.mean([r['act_pace'] for r in R]):.1f}, league ORtg {LGE:.1f}")
def summ(lab,s):
    dp=np.array([r['act_pace']-r['exp_pace'] for r in s]); de=np.array([r['eff']-LGE for r in s]); res=np.array([r['tot']-r['P'] for r in s])
    l3=np.array([r['luck3'] for r in s]); ot=sum(r['ot'] for r in s)
    print(f"{lab:16s} n {len(s):3d} | vs line {res.mean():+6.1f} | pace vs expected {dp.mean():+5.1f} (median {np.median(dp):+.1f}) | ORtg vs league {de.mean():+5.1f} | 3P luck {l3.mean():+5.1f} pts | OT {ot}")
ov=[r for r in P if r['tot']>r['P']]; un=[r for r in P if r['tot']<r['P']]
summ('OVERS',ov); summ('UNDERS',un)
for lo,hi,lab in ((10,99,'Over by 10+'),(0,10,'Over by 0-10'),(-10,0,'Under by 0-10'),(-99,-10,'Under by 10+')):
    summ(lab,[r for r in P if lo<=r['tot']-r['P']<hi])
# distribution of pace deviation in overs/unders
dp_o=np.array([r['act_pace']-r['exp_pace'] for r in ov]); dp_u=np.array([r['act_pace']-r['exp_pace'] for r in un])
print(f"Overs: pace above expected in {np.mean(dp_o>0)*100:.0f}% (3+ above {np.mean(dp_o>=3)*100:.0f}%) | Unders: pace below expected in {np.mean(dp_u<0)*100:.0f}% (3+ below {np.mean(dp_u<=-3)*100:.0f}%)")
# decomposition of total miss vs line: points = 2*poss*eff/100 ; d(total) ~ 2*eff/100*dPace + 2*pace/100*dEff
res=np.array([r['tot']-r['P'] for r in P]); dp=np.array([r['act_pace']-r['exp_pace'] for r in P]); de=np.array([r['eff']-LGE for r in P])
l3=np.array([r['luck3'] for r in P]); tov=np.array([r['tov'] for r in P]); fta=np.array([r['fta'] for r in P]); orb=np.array([r['orb'] for r in P])
def r2(X,y):
    X=np.c_[X,np.ones(len(y))]; b=np.linalg.lstsq(X,y,rcond=None)[0]; return 1-np.var(y-X@b)/np.var(y),b
print('\nWhat explains total minus the line (same-game stats, R2):')
for lab,X in (('pace vs expected',dp[:,None]),('efficiency (ORtg)',de[:,None]),('pace + efficiency',np.c_[dp,de]),('3P luck only',l3[:,None]),('FTA',fta[:,None]),('turnovers',tov[:,None]),('off rebounds',orb[:,None]),('3P luck+FTA+TOV+ORB',np.c_[l3,fta,tov,orb])):
    print(f"  {lab:22s} R2 {r2(X,res)[0]:.2f}")
b=r2(np.c_[dp,de],res)[1]; print(f"  points per +1 pace: {b[0]:.1f}; per +1 ORtg: {b[1]:.1f}")
# pre-game: did expected pace predict total vs line?
ep=np.array([r['exp_pace'] for r in P]); print(f"\nPre-game expected pace vs (total - line): corr {np.corrcoef(ep,res)[0,1]:+.2f}; expected pace vs actual pace corr {np.corrcoef(ep,[r['act_pace'] for r in P])[0,1]:+.2f}")
for lo,hi in ((0,99),(99,100.5),(100.5,200)):
    s=[r for r in P if lo<=r['exp_pace']<hi]
    print(f"  expected pace {lo}-{hi}: n {len(s)} under {sum(r['tot']<r['P'] for r in s)}-{sum(r['tot']>r['P'] for r in s)} mean vs line {np.mean([r['tot']-r['P'] for r in s]):+.1f}, actual-expected pace {np.mean([r['act_pace']-r['exp_pace'] for r in s]):+.1f}")
# model miss in roster era
M=[r for r in R if 'mt' in r]
mres=np.array([r['tot']-r['mt'] for r in M]); lres=np.array([r['tot']-r['P'] for r in M])
print(f"\nRoster era n {len(M)}: model total minus line {np.mean([r['mt']-r['P'] for r in M]):+.1f}; actual minus model {mres.mean():+.1f}; actual minus line {lres.mean():+.1f}")
dpm=np.array([r['act_pace']-100.1 for r in M]); dem=np.array([r['eff']-LGE for r in M]); l3m=np.array([r['luck3'] for r in M])
print('  model miss R2: pace %.2f, efficiency %.2f, 3P luck %.2f, pace+eff %.2f'%(r2(dpm[:,None],mres)[0],r2(dem[:,None],mres)[0],r2(l3m[:,None],mres)[0],r2(np.c_[dpm,dem],mres)[0]))
# where model disagrees with line: which way was it wrong?
gap=np.array([r['mt']-r['P'] for r in M])
for lo,hi in ((-99,-3),(-3,3),(3,99)):
    s=(gap>=lo)&(gap<hi)
    print(f"  model total {lo:+}..{hi:+} vs line: n {s.sum()} actual-line {lres[s].mean():+.1f} actual-model {mres[s].mean():+.1f}")

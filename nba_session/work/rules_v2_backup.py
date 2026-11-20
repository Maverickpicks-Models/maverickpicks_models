"""Rules engine. usage: python3 work/rules.py RUN.json CONFIG.json  -> prints sections, writes RUN_recs.json
CONFIG: {"date":"2026-11-12","crafted":{"AW|HM":{"home_margin":x,"total":y,"picks":["spread","under",...]}}, "stars_out":["Team",...], "b2b":["Team",...]}"""
import json,sys,runpy,io,contextlib,datetime as dt,numpy as np
RUN,CFG=sys.argv[1],sys.argv[2]
D=json.load(open(RUN)); C=json.load(open(CFG)); day=dt.date.fromisoformat(C['date'])
with contextlib.redirect_stdout(io.StringIO()):
    X=runpy.run_path('work/xposs.py'); B=runpy.run_path('work/crafted_bt.py',run_name='x')
prof,Xh,n2c=X['prof'],X['X'],X['n2c']
q=np.quantile([x['tov'] for x in Xh],[1/3,2/3])
rating,code=B['rating'],B['code']
rk=sorted(code,key=lambda c:-(rating(c,day)[0] or -99)); rank={c:i+1 for i,c in enumerate(rk)}
def dec(o): return 100/-o if o<0 else o/100
def am(p): return round(-100*p/(1-p)) if p>0.5 else round(100*(1-p)/p)
out=[]
for g in D:
    aw,hm=g['aw'],g['hm']; a,h=n2c[aw],n2c[hm]; L={x['lab']:x for x in g['legs']}
    U=g['sp'][0]; P=g['tot'][0]; mg=g['ap']-g['hp']; mkt=-U; mt=g['ap']+g['hp']
    spA,spH=L[f'{aw} {U:+g}'],L[f'{hm} {-U:+g}']; ov,un=L[f'Over {P}'],L[f'Under {P}']; mlA,mlH=L[f'{aw} ML'],L[f'{hm} ML']
    awb,hb=aw in C.get('b2b',[]),hm in C.get('b2b',[])
    R=[]  # (section, code, market, side, label, odds, size)
    def add(sec,code_,mk,side,lab,odds,size): R.append(dict(sec=sec,code=code_,mk=mk,side=side,lab=lab,odds=odds,size=size))
    lab_sp=lambda side:(f"{aw.split()[-1]} {U:+g}" if side=='away' else f"{hm.split()[-1]} {-U:+g}")
    # CORE
    gap=mg-mkt
    if 3<=abs(gap)<6:
        side='away' if gap>0 else 'home'; leg=spA if side=='away' else spH
        add('CORE','C1 model 3-6 off','spread',side,lab_sp(side),leg['odds'],'0.5u')
    if U<0 and -U<8: add('CORE','C2 road fav <8','spread','away',lab_sp('away'),spA['odds'],'0.5u')
    nvA=mlA['nv']
    if max(nvA,1-nvA)>=0.60:
        side='away' if nvA>=.5 else 'home'; leg=mlA if side=='away' else mlH
        risk=round(0.25/dec(leg['odds']),2)
        add('CORE','C3 ML fav 60%+','ml',side,f"{(aw if side=='away' else hm).split()[-1]} ML",leg['odds'],f'risk {risk}u to win 0.25u')
    if abs(mt-P)>=6:
        side='under' if mt>P else 'over'; add('CORE','C4 fade model total 6+','total',side,f"{side.title()} {P:g}",(un if side=='under' else ov)['odds'],'0.5u')
    # CRAFTED
    cf=C.get('crafted',{}).get(f'{aw}|{hm}')
    if cf:
        ch=cf['home_margin']  # crafted home margin
        e_home=ch-(U)  # home covers -U? home spread = -U ... home margin needed > U
        # crafted edge on home side = ch - U (home spread line is -U => home covers if margin > U)
        if abs(ch-U)>=1:
            side='home' if ch>U else 'away'
            fav=(side=='away' and U<0) or (side=='home' and U>0)
            agree=(mg<-U) if side=='home' else (mg>-U)   # our model: away margin vs line
            if fav or agree:
                add('CRAFTED','K1 fav' if fav else 'K2 dog we agree','spread',side,lab_sp(side),(spA if side=='away' else spH)['odds'],'0.5u')
            else: add('SKIP','K2 dog we disagree','spread',side,lab_sp(side),None,'')
        if cf.get('total') is not None and cf['total']<=P-2:
            add('CRAFTED','K3 Under','total','under',f'Under {P:g}',un['odds'],'0.5u')
    # TEST
    if ov['price']>=0.52: add('TEST','T1 juiced Over','total','under',f'Under {P:g}',un['odds'],'0.25u')
    pa,ph=prof(a,day),prof(h,day)
    if pa and ph:
        t=pa['tov']+ph['ftov']+ph['tov']+pa['ftov']
        if t<q[0]: add('TEST','T2 low turnovers','total','under',f'Under {P:g}',un['odds'],'0.25u')
        elif t>=q[1]: add('TEST','T2 high turnovers','total','over',f'Over {P:g}',ov['odds'],'0.25u')
    if g['att'] and g['htt']:
        aU=L[f"{aw} TT Over {g['att'][0]}"]['model']<.5; hU=L[f"{hm} TT Over {g['htt'][0]}"]['model']<.5
        favU,dogU=(aU,hU) if U<0 else (hU,aU)
        if favU and not dogU: add('TEST','T3 fav TT U + dog TT O','total','under',f'Under {P:g}',un['odds'],'0.25u')
        if g['att'][0]+g['htt'][0]<=P-1.5: add('TEST','T7 both TT Overs','tt','over',f"Both TT Overs ({g['att'][0]}/{g['htt'][0]})",None,'0.25u each')
    if awb and not hb: add('TEST','T4 rested home vs road B2B','spread','home',lab_sp('home'),spH['odds'],'0.25u')
    ta=lambda c:'top' if rank[c]<=10 else ('bot' if rank[c]>20 else 'mid')
    if ta(a)=='top' and ta(h)=='bot': add('TEST','T5 top-10 vs bottom-10','spread','away',lab_sp('away'),spA['odds'],'0.25u')
    if ta(h)=='top' and ta(a)=='bot': add('TEST','T5 top-10 vs bottom-10','spread','home',lab_sp('home'),spH['odds'],'0.25u')
    for tm,side in ((aw,'away'),(hm,'home')):
        if tm in C.get('stars_out',[]): add('TEST','T6 team missing star','spread',side,lab_sp(side),(spA if side=='away' else spH)['odds'],'0.25u')
    if P>=235: add('TEST','T8 total 235+','total','under',f'Under {P:g}',un['odds'],'0.25u')
    # AVOID filters
    notes=[]
    keep=[]
    for r in R:
        if r['mk']=='spread':
            o=r['odds']
            dog=(r['side']=='away' and U>0) or (r['side']=='home' and U<0)
            if r['side']=='home' and dog and 0.5<=abs(U)<=4.5: notes.append(f"X2 home dog {r['lab']} removed ({r['code']})"); continue
            if r['code'].startswith('C2') and r['sec']=='CORE' and False: pass
        if r['mk']=='ml' and r['odds'] and r['odds']>=200: notes.append('X3'); continue
        if r['mk']=='total' and r['side']=='under' and r['sec']=='CORE' and mt<=P-3: notes.append('X5'); continue
        keep.append(r)
    if abs(gap)>=6: notes.append(f'X1 model {gap:+.1f} off the spread: no model spread play')
    # conflicts: same market opposite sides -> pass all on that market (except SKIP rows)
    final=[]
    for mk in ('spread','total','ml','tt'):
        rows=[r for r in keep if r['mk']==mk and r['sec']!='SKIP']
        main=[r for r in rows if r['sec'] in ('CORE','CRAFTED')]
        if len({r['side'] for r in main})>1:
            notes.append(f"conflict on {mk}: "+', '.join(f"{r['code']}->{r['lab']}" for r in main)+' -> pass'); continue
        if main:
            ms=main[0]['side']; drop=[r for r in rows if r['sec']=='TEST' and r['side']!=ms]
            for r in drop: notes.append(f"test {r['code']} ({r['lab']}) dropped: opposite a core/CraftedNBA play")
            rows=[r for r in rows if r not in drop]
        elif len({r['side'] for r in rows})>1:
            notes.append(f"conflict on {mk}: "+', '.join(f"{r['code']}->{r['lab']}" for r in rows)+' -> pass'); continue
        final+=rows
    # crafted tracked pick opposite core already covered by conflict pass
    tier=f"{a} #{rank[a]} vs {h} #{rank[h]}"
    out.append(dict(game=f'{aw}|{hm}',tier=tier,recs=final,notes=notes,skips=[r for r in keep if r['sec']=='SKIP']))
json.dump(out,open(RUN.replace('.json','_recs.json'),'w'),indent=1)
for o in out:
    print(f"\n{o['game']}  [{o['tier']}]")
    for r in o['recs']: print(f"   {r['sec']:7s} {r['code']:26s} {r['lab']:28s} {('' if r['odds'] is None else ('%+d'%r['odds'])):>6s} {r['size']}")
    for n in o['notes']: print('   note:',n)
    for r in o['skips']: print('   skip:',r['code'],r['lab'])

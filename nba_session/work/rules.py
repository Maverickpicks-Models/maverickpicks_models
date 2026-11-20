"""Rules engine (Rulebook v5.1 + P1/P2 from 11/20). usage: python3 work/rules.py RUN.json CONFIG.json  -> prints sections, writes RUN_recs.json
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
# fatigue (T12): team game dates from TeamBoxAdvanced
import openpyxl as _ox, os as _os, collections as _co
_TD=_co.defaultdict(set)
for _r in _ox.load_workbook(_os.environ['WB'],read_only=True,data_only=True)['TeamBoxAdvanced'].iter_rows(min_row=2,max_col=3,values_only=True):
    if _r[0] and _r[2] is not None:
        _d=_r[2].date() if hasattr(_r[2],'date') else dt.date(1899,12,30)+dt.timedelta(days=int(_r[2]))
        _TD[_r[0]].add(_d)
for _tm,_ds in C.get('extra_games',{}).items():
    for _d in _ds: _TD[_tm].add(dt.date.fromisoformat(_d))
def fatigue(tm):
    L=_TD.get(tm,set()); b2b=(day-dt.timedelta(1)) in L
    g4=1+sum(1 for x in L if day-dt.timedelta(3)<=x<day); g6=1+sum(1 for x in L if day-dt.timedelta(5)<=x<day)
    return int(b2b)+int(g4>=3)+int(g6>=4), dict(b2b=b2b,g4=g4,g6=g6)
# P1/P2 (11/20, from mpm.mine): season-only, shooting-luck-adjusted ratings, as in the 2025-26 / 2026-27 test
_PM=runpy.run_path('work/prod.py')['Prod'](_os.environ['WB'])
_NETLUCK={r[0]:r[14] for r in _PM.wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True) if r[0]}
def season_team(t):
    c=_PM.R27.get(t); lo,ld=_PM.luck.get(t,(0,0))
    return None if not c or c['gp']<8 else dict(o=c['o']-(lo or 0),d=c['d']-(ld or 0),p=c['p'],gp=c['gp'])
def season_margin(aw,hm,ab,hb):
    """away margin from season-to-date ratings only (current-season weight 1), no roster prior"""
    A=_PM.A; a,h=season_team(aw),season_team(hm)
    if not a or not h: return None
    pace=_PM.LP+A[11]*((a['p']-_PM.LP)+(h['p']-_PM.LP))
    ra=pace/100*(a['o']+h['d']-_PM.LB); rh=pace/100*(h['o']+a['d']-_PM.LB)
    ta=-(A[13] if ab else 0); th=-(A[13] if hb else 0)
    return (ra+(ta-th)/2-A[12]/2)-(rh+(th-ta)/2+A[12]/2), (a['o']-a['d'])-(h['o']-h['d'])
P_GAP,P_LUCK,P_NET=1.8,0.47,3.63
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
        my_sp=U if side=='away' else -U
        pre_notes=[]
        if my_sp<=-10:   # v5.1 (11/19): C1 on 10+ point favorites -> paper (0-3; 10+ favs ATS 19-22)
            pre_notes.append(f'C1 paper only: {lab_sp(side)} is a 10+ point favorite')
        else:
            add('CORE','C1 model 3-6 off','spread',side,lab_sp(side),leg['odds'],'0.5u')
    else:
        pre_notes=[]
    if U<0 and -U<=4.5:
        if hb and not awb: pre_notes.append('C2 road fav skipped: home team on B2B vs rested road team (T9)')
        else: add('CORE','C2 road fav <=4.5','spread','away',lab_sp('away'),spA['odds'],'0.75u')
    elif U<0 and -U<8: pre_notes.append(f'C2 v5: road fav {U:+g} not played (favorites 5-9.5 ATS 28-39, -17%)')
    nvA=mlA['nv']
    if max(nvA,1-nvA)>=0.60:
        side='away' if nvA>=.5 else 'home'; leg=mlA if side=='away' else mlH
        fv=max(nvA,1-nvA)
        if 0.65<=fv<0.75: pre_notes.append(f"C3 v5: ML favorite at {100*fv:.0f}% no-vig not played (65-75% leak, -6.7%)")
        elif 5<=abs(U)<=9.5: pre_notes.append(f"C3 v5: ML favorite with a {abs(U):g}-pt spread not played (5-9.5 favorites leak)")
        elif max(nvA,1-nvA)>0.87: pre_notes.append(f"X7 ML favorite {(aw if side=='away' else hm).split()[-1]} {leg['odds']:+d} is over 87% no-vig: pass")
        else:
            risk=round(0.25/dec(leg['odds']),2)
            if risk>1: add('CORE','C3 ML fav 60%+','ml',side,f"{(aw if side=='away' else hm).split()[-1]} ML",leg['odds'],f"risk 1u (capped) to win {dec(leg['odds']):.2f}u")
            else: add('CORE','C3 ML fav 60%+','ml',side,f"{(aw if side=='away' else hm).split()[-1]} ML",leg['odds'],f'risk {risk}u to win 0.25u')
    if 0<U<=4.5: add('TEST','T11 home fav <=4.5','spread','home',lab_sp('home'),spH['odds'],'0.5u')
    if abs(U)<=4.5 and 0.5<=max(nvA,1-nvA)<0.60:
        side='away' if nvA>=.5 else 'home'; leg=mlA if side=='away' else mlH
        add('TEST','T10 ML fav spread <=4.5','ml',side,f"{(aw if side=='away' else hm).split()[-1]} ML",leg['odds'],'0.5u')
    if abs(mt-P)>=6:
        side='under' if mt>P else 'over'; add('CORE','C4 fade model total 6+','total',side,f"{side.title()} {P:g}",(un if side=='under' else ov)['odds'],'0.25u')
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
    fa,fa_d=fatigue(a); fh,fh_d=fatigue(h)
    if awb and not hb: pre_notes.append('T4 (paper since 11/17): rested home vs road B2B -> would be home spread')
    if abs(fa-fh)>=1:
        side='away' if fa>fh else 'home'
        add('TEST',f'T12 more tired team (fatigue {fa} vs {fh})','spread',side,lab_sp(side),(spA if side=='away' else spH)['odds'],'0.25u')
    if hb and not awb: add('TEST','T9 home B2B vs rested road','spread','home',lab_sp('home'),spH['odds'],'0.25u')
    ta=lambda c:'top' if rank[c]<=10 else ('bot' if rank[c]>20 else 'mid')
    if ta(a)=='top' and ta(h)=='bot': add('TEST','T5 top-10 vs bottom-10','spread','away',lab_sp('away'),spA['odds'],'0.25u')
    if ta(h)=='top' and ta(a)=='bot': add('TEST','T5 top-10 vs bottom-10','spread','home',lab_sp('home'),spH['odds'],'0.25u')
    for tm,side in ((aw,'away'),(hm,'home')):
        if tm in C.get('stars_out',[]) and not (aw in C.get('stars_out',[]) and hm in C.get('stars_out',[])): add('TEST','T6 team missing star','spread',side,lab_sp(side),(spA if side=='away' else spH)['odds'],'0.25u')
    if P>=235: add('TEST','T8 total 235+','total','under',f'Under {P:g}',un['odds'],'0.25u')
    # P1 / P2 (11/20): $5 each (0.25u at $20)
    sm=season_margin(aw,hm,awb,hb)
    if sm:
        smg,snet=sm
        for side,my_gap,my_net,opp in (('away',smg+U,snet,hm),('home',-smg-U,-snet,aw)):
            if my_gap>=P_GAP and (_NETLUCK.get(opp) or 0)>=P_LUCK:
                add('TEST',f'P1 fade 3P-lucky {opp.split()[-1]} (luck {_NETLUCK[opp]:+.1f}, gap {my_gap:+.1f})','spread',side,lab_sp(side),(spA if side=='away' else spH)['odds'],'0.25u')
            if my_gap>=P_GAP and my_net>=P_NET:
                leg=mlA if side=='away' else mlH
                if leg['nv']>0.87: pre_notes.append(f"P2 {(aw if side=='away' else hm).split()[-1]} ML over 87% no-vig: pass (X7)")
                else: add('TEST',f'P2 better team ML (net {my_net:+.1f}, gap {my_gap:+.1f})','ml',side,f"{(aw if side=='away' else hm).split()[-1]} ML",leg['odds'],'0.25u')
    # AVOID filters
    notes=list(pre_notes)
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
    # X6: a core/test spread or ML opposite CraftedNBA's spread pick (incl. dogs we disagree with) -> pass that side
    cside={r['side'] for r in R if r['code'].startswith('K2 dog we disagree') or r['code'].startswith('K1') or r['code'].startswith('K2 dog we agree')}
    if len(cside)==1:
        cs=next(iter(cside)); bad=[r for r in keep if r['mk'] in ('spread','ml') and r['side']!=cs and r['sec'] in ('CORE','TEST')]
        for r in bad: notes.append(f"X6 {r['code']} ({r['lab']}) passed: opposite CraftedNBA's pick"); keep.remove(r)
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
    # T7 both TT Overs vs a game-total Under -> contradictory, pass both
    if any(r['mk']=='tt' for r in final) and any(r['mk']=='total' and r['side']=='under' for r in final):
        notes.append('T7 TT Overs vs total Under conflict -> pass both')
        final=[r for r in final if not (r['mk']=='tt' or (r['mk']=='total' and r['side']=='under'))]
    # X8 (test filter, 11/16): C3 ML favorite when a spread rule backs the other team -> pass the ML, keep the spread
    sp_sides={r['side'] for r in final if r['mk']=='spread'}
    for r in [r for r in final if r['mk']=='ml']:
        if sp_sides and r['side'] not in sp_sides:
            final.remove(r); notes.append(f"X8 {r['lab']} passed: a spread rule backs the other team (ML 16-8, -10% ROI in that spot)")
    # PRICING v4 (11/16): units from shrunk backtest ROI (ROI x n/(n+40)); see Rules tab
    UN={'C1':0.75,'C2':0.75,'C4':0.75,'K1':0.5,'K2':0.25,'K3':0.25,'T1':0.5,'T2h':0.5,'T2l':0.5,'T3':0.5,'T4':0.25,'T5':0.5,'T6':0.25,'T7':0.25,'T8':0.25,'T9':0.5,'T10':0.5,'T11':0.5,'T12':0.25}
    CAP={'CORE':1.0,'CRAFTED':0.75,'TEST':0.5}; TIERS=[0.25,0.5,0.75,1.0]
    def rc(r):
        c=r['code'].split()[0]
        return ('T2h' if 'high' in r['code'] else 'T2l') if c=='T2' else c
    plays=[]
    for key in dict.fromkeys((r['mk'],r['side']) for r in final):
        rows=[r for r in final if (r['mk'],r['side'])==key]; mk,side=key
        codes=[rc(r) for r in rows]; secs={r['sec'] for r in rows}
        why=[]
        if mk=='ml':
            p2=0.25 if 'P2' in codes else 0
            if 'C3' in codes and p2: plays.append(dict(mk=mk,side=side,lab=rows[0]['lab'],odds=rows[0]['odds'],codes=codes,units=[r for r in rows if rc(r)=='C3'][0]['size']+' + risk 0.25u (P2)',sec='CORE',why='C3 sizing plus $5 for P2'))
            elif 'P2' in codes and not ({'C3','T10'}&set(codes)): plays.append(dict(mk=mk,side=side,lab=rows[0]['lab'],odds=rows[0]['odds'],codes=codes,units='risk 0.25u',sec='TEST',why='P2 $5'))
            elif 'T10' in codes and p2: plays.append(dict(mk=mk,side=side,lab=rows[0]['lab'],odds=rows[0]['odds'],codes=codes,units='0.75u',sec='TEST',why='T10 0.5u + P2 0.25u'))
            elif 'C3' in codes: plays.append(dict(mk=mk,side=side,lab=rows[0]['lab'],odds=rows[0]['odds'],codes=codes,units=[r for r in rows if rc(r)=='C3'][0]['size'],sec='CORE',why='C3 sizing (to win 0.25u, max risk 1u)'))
            else: plays.append(dict(mk=mk,side=side,lab=rows[0]['lab'],odds=rows[0]['odds'],codes=codes,units='0.5u',sec='TEST',why='T10 ML favorite <=4.5 (36-23, +9.9%)'))
            continue
        pc=[c for c in codes if c in ('P1','P2')]; base=[c for c in codes if c not in ('P1','P2')]
        u=max(UN.get(c,0.25) for c in base) if base else 0
        if mk=='spread' and 'CORE' in secs and ({'T5','T6','T9'}&set(codes)): u=1.0; why.append('core+test spread combo 17-5, +55%')
        if mk=='total' and 'T8' in codes and ({'T2l','T3'}&set(codes)): u=0.25; why.append('T8 stacked with T2/T3 Unders 2-7')
        if mk=='total' and len(codes)>1 and not why: why.append('stacked totals: no extra size')
        if mk=='total' and side=='under' and mt<=P-3: u=TIERS[max(0,TIERS.index(u)-1)] if u in TIERS else 0.25; why.append('X5 flag: model 3+ below the line, one tier down')
        if mk=='spread' and abs(gap)>=6 and side==('away' if gap>0 else 'home') and u in TIERS: u=TIERS[max(0,TIERS.index(u)-1)]; why.append('X1 flag, one tier down')
        cap=max(CAP[x] for x in secs if x in CAP); u=min(u,cap)
        if mk=='tt': u=0.25; why.append('0.25u each leg')
        if pc: u+=0.25; why.append(('P1 $5' if not base else 'plus $5 for P1'))
        plays.append(dict(mk=mk,side=side,lab=rows[0]['lab'],odds=rows[0]['odds'],codes=codes,units=f'{u:g}u',sec=('CORE' if 'CORE' in secs else 'CRAFTED' if 'CRAFTED' in secs else 'TEST'),why='; '.join(why)))
    tier=f"{a} #{rank[a]} vs {h} #{rank[h]}"
    out.append(dict(game=f'{aw}|{hm}',tier=tier,recs=final,plays=plays,notes=notes,skips=[r for r in keep if r['sec']=='SKIP']))
json.dump(out,open(RUN.replace('.json','_recs.json'),'w'),indent=1)
for o in out:
    print(f"\n{o['game']}  [{o['tier']}]")
    for r in o['recs']: print(f"   {r['sec']:7s} {r['code']:26s} {r['lab']:28s} {('' if r['odds'] is None else ('%+d'%r['odds'])):>6s}")
    for pl in o['plays']: print(f"   >> PLAY {pl.get('sec','CORE'):7s} {pl['lab']:28s} {('' if pl['odds'] is None else ('%+d'%pl['odds'])):>6s} {pl['units']:>8s}  [{'+'.join(pl['codes'])}] {pl['why']}")
    for n in o['notes']: print('   note:',n)
    for r in o['skips']: print('   skip:',r['code'],r['lab'])

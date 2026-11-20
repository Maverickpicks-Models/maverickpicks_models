import openpyxl,datetime as dt,collections,json,io,contextlib,runpy,os,numpy as np
os.environ['WB']='in1116u/s.xlsx'
with contextlib.redirect_stdout(io.StringIO()):
    X=runpy.run_path('work/xposs.py'); B=runpy.run_path('work/crafted_bt.py',run_name='x')
prof,Xh,n2c=X['prof'],X['X'],X['n2c']; q=np.quantile([x['tov'] for x in Xh],[1/3,2/3])
rating,code=B['rating'],B['code']
wb=openpyxl.load_workbook('in1117/s2.xlsx',data_only=True); t=wb['Tracking']
def dd(x):
    if hasattr(x,'date'): return x.date()
    if isinstance(x,(int,float)): return dt.date(1899,12,30)+dt.timedelta(days=int(x))
def imp(o): return -o/(100-o) if o<0 else 100/(100+o)
def dec(o): return 100/-o if o<0 else o/100
# team game dates for B2B
ta=wb['TeamBoxAdvanced']; TD=collections.defaultdict(set)
for r in ta.iter_rows(min_row=2,max_col=3,values_only=True):
    if r[0] and r[2] is not None: TD[r[0]].add(dd(r[2]))
G=[]
for r in range(13,230):
    v=lambda c: t.cell(r,c).value
    d=dd(v(1)); an,hn=v(40),v(41)
    if d is None or not isinstance(an,(int,float)) or not isinstance(hn,(int,float)): continue
    g=dict(d=d,aw=v(2),hm=v(3),ap=v(4),hp=v(5),J=v(10),K=v(11),P=v(16),Q=v(17),S=v(19),T=v(20),U=v(21),W=v(23),Z=v(26),
           AA=v(27),AB=v(28),AE=v(31),AF=v(32),an=an,hn=hn)
    if None in (g['U'],g['P'],g['J'],g['K'],g['W'],g['Z'],g['S'],g['T']) or not isinstance(g['ap'],(int,float)): continue
    G.append(g)
R=collections.defaultdict(list)   # rule -> list of (profit, stake)
HITS=[]; CUR={}
def bet(rule,won,odds,stake=1.0,push=False,mk=None,side=None):
    if push: return
    R[rule].append((stake*dec(odds) if won else -stake, stake))
    if mk: HITS.append(dict(gid=CUR['gid'],aw=CUR['aw'],hm=CUR['hm'],d=str(CUR['d']),mk=mk,side=side,rule=rule.split()[0],won=won,odds=odds))
for gi,g in enumerate(G):
    CUR['gid']=gi; CUR['d']=g['d']; CUR['aw']=g['aw']; CUR['hm']=g['hm']
    a,h=n2c.get(g['aw']),n2c.get(g['hm']); d=g['d']
    U,P=g['U'],g['P']; mg=g['ap']-g['hp']; mkt=-U; mt=g['Q'] if isinstance(g['Q'],(int,float)) else g['ap']+g['hp']
    am=g['an']-g['hn']; tot=g['an']+g['hn']
    acov=am+U; hcov=-acov; push_sp=acov==0
    ovw=tot>P; push_t=tot==P
    pa,ph=imp(g['J']),imp(g['K']); nvA=pa/(pa+ph)
    po,pu=imp(g['S']),imp(g['T'])
    awb=a and (d-dt.timedelta(days=1)) in TD.get(a,()); hb=h and (d-dt.timedelta(days=1)) in TD.get(h,())
    def spread(rule,side,stake=1.0):
        bet(rule,(acov>0) if side=='away' else (hcov>0),g['W'] if side=='away' else g['Z'],stake,push_sp,'spread',side)
    gap=mg-mkt
    if 3<=abs(gap)<6: spread('C1 Model spread 3-6 off','away' if gap>0 else 'home')
    if U<0 and -U<8 and not (hb and not awb): spread('C2 Road favorite under 8','away')
    fav=max(nvA,1-nvA)
    if fav>=0.60 and fav<=0.87:
        side='away' if nvA>=.5 else 'home'; o=g['J'] if side=='away' else g['K']
        won=(am>0) if side=='away' else (am<0)
        HITS.append(dict(gid=gi,aw=g['aw'],hm=g['hm'],d=str(d),mk='ml',side=side,rule='C3',won=won,odds=o)); R['C3 ML favorite 60-87%'].append(((0.25 if won else -min(1,0.25/dec(o))) if min(1,0.25/dec(o))==0.25/dec(o) else (dec(o) if won else -1), min(1,0.25/dec(o))))
    if fav>0.87:
        side='away' if nvA>=.5 else 'home'; o=g['J'] if side=='away' else g['K']; won=(am>0) if side=='away' else (am<0)
        R['X7 ML favorite over 87%'].append((0.25 if won else -0.25/dec(o),0.25/dec(o)))
    if abs(mt-P)>=6:
        side='under' if mt>P else 'over'; bet('C4 Fade model total 6+',(not ovw) if side=='under' else ovw,g['T'] if side=='under' else g['S'],1,push_t,'total',side)
    if po/(po+pu)>=0.52 or po>=0.52: bet('T1 Juiced Over -> Under',not ovw,g['T'],1,push_t,'total','under')
    if a and h:
        fa,fh=prof(a,d),prof(h,d)
        if fa and fh:
            tv=fa['tov']+fh['ftov']+fh['tov']+fa['ftov']
            if tv<q[0]: bet('T2 Turnovers low -> Under',not ovw,g['T'],1,push_t,'total','under')
            elif tv>=q[1]: bet('T2 Turnovers high -> Over',ovw,g['S'],1,push_t,'total','over')
    if isinstance(g['AA'],(int,float)) and isinstance(g['AE'],(int,float)) and isinstance(g['AB'],(int,float)):
        aU,hU=g['AB']<.5,g['AF']<.5; favU,dogU=(aU,hU) if U<0 else (hU,aU)
        if favU and not dogU: bet('T3 Fav TT Under + dog TT Over -> Under',not ovw,g['T'],1,push_t,'total','under')
        if g['AA']+g['AE']<=P-1.5:
            for side,line,pts in (('a',g['AA'],g['an']),('h',g['AE'],g['hn'])): 
                if pts!=line: bet('T7 Both TT Overs (each)',pts>line,-110)
    if awb and not hb: spread('T4 Rested home vs road B2B','home')
    if hb and not awb: spread('T9 Home B2B vs rested road','home')
    if a and h:
        rk=sorted(code,key=lambda c:-(rating(c,d)[0] or -99)); rank={c:i+1 for i,c in enumerate(rk)}
        tt=lambda c:'top' if rank[c]<=10 else ('bot' if rank[c]>20 else 'mid')
        if tt(a)=='top' and tt(h)=='bot': spread('T5 Top-10 vs bottom-10','away')
        if tt(h)=='top' and tt(a)=='bot': spread('T5 Top-10 vs bottom-10','home')
    if P>=235: bet('T8 Total 235+ -> Under',not ovw,g['T'],1,push_t,'total','under')
    # avoid: what the avoided bet did
    if abs(gap)>=6: spread('X1 Model spread 6+ off (model side)','away' if gap>0 else 'home')
    if -4.5<=U<=-0.5: spread('X2 Home dog 0.5-4.5','home')
    for side,o,won in (('a',g['J'],am>0),('h',g['K'],am<0)):
        if o>=200: bet('X3 Dogs +200 or longer (ML)',won,o)
    if mt<=P-3: bet('X5 Model Under 3+ below line',not ovw,g['T'],1,push_t,'total','under')
out={}
for k in sorted(R):
    L=R[k]; w=sum(1 for p,s in L if p>0); l=sum(1 for p,s in L if p<0); pl=sum(p for p,s in L); st=sum(s for p,s in L)
    out[k]=(w,l,pl,st); print('%-42s %3d-%-3d  units %+6.2f  ROI %+6.1f%%'%(k,w,l,pl,100*pl/st))
print('games',len(G),min(g['d'] for g in G),max(g['d'] for g in G))
json.dump(HITS,open('work/rule_hits2.json','w'))

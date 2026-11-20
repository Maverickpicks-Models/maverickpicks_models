import openpyxl,datetime as dt,math,random,collections
from statistics import NormalDist
N=NormalDist(); random.seed(5)
def dd(x):
    if hasattr(x,'date'): return x.date()
    if isinstance(x,(int,float)) and x>40000: return dt.date(1899,12,30)+dt.timedelta(days=int(x))
def imp(o): return -o/(100-o) if o<0 else 100/(100+o)
def dec(o): return 100/-o if o<0 else o/100
t=openpyxl.load_workbook('in1117/s2.xlsx',data_only=True)['Tracking']
G={};
for r in t.iter_rows(min_row=13,max_row=t.max_row,values_only=True):
    d=dd(r[0])
    if not d or not isinstance(r[39],(int,float)): continue
    k=(d,r[1],r[2])
    if k in G: continue
    G[k]=dict(d=d,J=r[9],K=r[10],P=r[15],S=r[18],T=r[19],U=r[20],W=r[22],Z=r[25],AA=r[26],AC=r[28],AD=r[29],AE=r[30],AG=r[32],AH=r[33],an=r[39],hn=r[40])
G=list(G.values()); print('games',len(G))
def nv(o1,o2): a,b=imp(o1),imp(o2); return a/(a+b)
def boot(pl,B=3000):
    n=len(pl)
    if n<5: return (float('nan'),)*2
    xs=sorted(sum(random.choice(pl) for _ in range(n))/n for _ in range(B)); return xs[int(.025*B)],xs[int(.975*B)]
def rep(name,L,per=None):
    n=len(L)
    if not n: print(f'| {name} | 0 |'); return
    w=sum(1 for x in L if x>0); l=sum(1 for x in L if x<0); lo,hi=boot(L)
    fl='VERY LOW' if n<15 else ('LOW' if n<30 else '')
    print(f'| {name} | {n} | {w}-{l} | {sum(L):+.2f} | {100*sum(L)/n:+.1f}% | [{100*lo:+.0f}%, {100*hi:+.0f}%] | {fl} |')
SIG=14.0   # margin sd (market RMSE 14.5 in audit)
# ---------- ANGLE 3: ML vs spread
rows=[]
for g in G:
    if None in (g['J'],g['K'],g['U'],g['W'],g['Z']): continue
    qa=nv(g['W'],g['Z'])                      # no-vig prob away covers U
    mu_a=-g['U']+SIG*N.inv_cdf(qa)            # implied away mean margin
    p_spr=N.cdf(mu_a/SIG)                     # spread-implied away win prob
    p_ml=nv(g['J'],g['K'])
    rows.append(dict(g=g,p_spr=p_spr,p_ml=p_ml,d=p_ml-p_spr))
# fit systematic relation: logit(p_ml) = a + b*logit(p_spr)
lg=lambda p: math.log(p/(1-p))
X=[lg(r['p_spr']) for r in rows]; Y=[lg(r['p_ml']) for r in rows]
mx,my=sum(X)/len(X),sum(Y)/len(Y); b=sum((x-mx)*(y-my) for x,y in zip(X,Y))/sum((x-mx)**2 for x in X); a=my-b*mx
print(f'ML vs spread fit: logit(ML) = {a:+.3f} + {b:.3f}*logit(spread-implied)  (b>1 means ML prices favorites stronger than the spread implies)')
for r in rows:
    pf=1/(1+math.exp(-(a+b*lg(r['p_spr'])))); r['res']=r['p_ml']-pf
# which is better calibrated vs outcomes?
y=[1 if r['g']['an']>r['g']['hn'] else 0 for r in rows]
br=lambda ps: sum((p-o)**2 for p,o in zip(ps,y))/len(y)
print(f'Brier ML no-vig {br([r["p_ml"] for r in rows]):.4f} | spread-implied (sd {SIG}) {br([r["p_spr"] for r in rows]):.4f}')
# by favorite size: avg gap ML - spread-implied for favorite
bk=collections.defaultdict(list)
for r,o in zip(rows,y):
    fav_away=r['p_ml']>=.5; pm=r['p_ml'] if fav_away else 1-r['p_ml']; ps=r['p_spr'] if fav_away else 1-r['p_spr']; won=o==1 if fav_away else o==0
    s=abs(r['g']['U']); b_='<=4.5' if s<=4.5 else '5-9.5' if s<10 else '10+'
    bk[b_].append((pm,ps,won))
print('| fav size | n | ML says | spread implies | fav actually won |')
for b_ in ['<=4.5','5-9.5','10+']:
    L=bk[b_]; n=len(L); print(f'| {b_} | {n} | {100*sum(x[0] for x in L)/n:.1f}% | {100*sum(x[1] for x in L)/n:.1f}% | {100*sum(x[2] for x in L)/n:.1f}% |')
# strategies by residual size: when ML is "expensive" for a side relative to spread (res>0 for away), bet the other side's ML, or bet that side's spread
print('| angle 3 strategy | n | W-L | units (1u risk) | ROI | 95% CI | sample |')
for thr in (0.01,0.02,0.03):
    cheapML=[];cheapSpr=[]
    for r in rows:
        g=r['g']; 
        if abs(r['res'])<thr: continue
        away_exp=r['res']>0   # away ML priced richer than spread implies
        # bet the cheap ML (the other side)
        side_home=away_exp; won=(g['hn']>g['an']) if side_home else (g['an']>g['hn']); o=g['K'] if side_home else g['J']
        cheapML.append(dec(o) if won else -1)
        # bet the spread of the side whose ML is rich (spread cheaper)
        acov=(g['an']-g['hn'])+g['U']
        if acov!=0:
            wa=(acov>0)==away_exp; o2=g['W'] if away_exp else g['Z']; cheapSpr.append(dec(o2) if wa else -1)
    rep(f'|resid|>={thr:.2f}: bet the cheap ML',cheapML); rep(f'|resid|>={thr:.2f}: bet spread of the side with rich ML',cheapSpr)
# ---------- ANGLE 4: team totals vs total vs spread
SIGT=10.0  # team total sd approx
rows4=[]
for g in G:
    if None in (g['AA'],g['AE'],g['AC'],g['AD'],g['AG'],g['AH'],g['P'],g['S'],g['T'],g['U']): continue
    ta=g['AA']+SIGT*N.inv_cdf(nv(g['AC'],g['AD']))   # median-adjusted
    th=g['AE']+SIGT*N.inv_cdf(nv(g['AG'],g['AH']))
    tot=g['P']+17*N.inv_cdf(nv(g['S'],g['T']))
    hm_spr=g['U']+SIG*N.inv_cdf(nv(g['Z'],g['W']))   # home mean margin from spread  (home covers -U... home line = -U)
    rows4.append(dict(g=g,sum_gap=(ta+th)-tot,mar_gap=(th-ta)-hm_spr,ta=ta,th=th,tot=tot,hm=hm_spr))
print('games with full TT data',len(rows4))
act_tot=[r['g']['an']+r['g']['hn'] for r in rows4]; act_hm=[r['g']['hn']-r['g']['an'] for r in rows4]
mae=lambda xs,ys: sum(abs(a-b) for a,b in zip(xs,ys))/len(xs)
print(f'total MAE: game-total line {mae([r["tot"] for r in rows4],act_tot):.2f} | TT sum {mae([r["ta"]+r["th"] for r in rows4],act_tot):.2f}')
print(f'margin MAE: spread {mae([r["hm"] for r in rows4],act_hm):.2f} | TT difference {mae([r["th"]-r["ta"] for r in rows4],act_hm):.2f}')
print('avg sum gap %+.2f, sd %.2f; avg margin gap %+.2f sd %.2f'%(sum(r['sum_gap'] for r in rows4)/len(rows4),(sum(r['sum_gap']**2 for r in rows4)/len(rows4))**.5,sum(r['mar_gap'] for r in rows4)/len(rows4),(sum(r['mar_gap']**2 for r in rows4)/len(rows4))**.5))
print('| angle 4 strategy | n | W-L | units | ROI | 95% CI | sample |')
for thr in (1.0,1.5,2.5):
    gOver=[];gUnder=[];ttO=[];ttU=[]
    for r in rows4:
        g=r['g']; T=g['an']+g['hn']
        if r['sum_gap']<=-thr:   # TTs imply fewer points than the total -> total too high OR TTs too low
            if T!=g['P']: gUnder.append(dec(g['T']) if T<g['P'] else -1)
            for line,pts,o in ((g['AA'],g['an'],g['AC']),(g['AE'],g['hn'],g['AG'])):
                if pts!=line: ttO.append(dec(o) if pts>line else -1)
        if r['sum_gap']>=thr:
            if T!=g['P']: gOver.append(dec(g['S']) if T>g['P'] else -1)
            for line,pts,o in ((g['AA'],g['an'],g['AD']),(g['AE'],g['hn'],g['AH'])):
                if pts!=line: ttU.append(dec(o) if pts<line else -1)
    rep(f'TT sum {thr}+ below total: game Under',gUnder); rep(f'TT sum {thr}+ below total: both TT Overs (legs)',ttO)
    rep(f'TT sum {thr}+ above total: game Over',gOver); rep(f'TT sum {thr}+ above total: both TT Unders (legs)',ttU)
for thr in (1.0,2.0,3.0):
    spr=[];tt=[]
    for r in rows4:
        g=r['g']
        if abs(r['mar_gap'])<thr: continue
        home_more=r['mar_gap']>0   # TTs say home better than spread says
        acov=(g['an']-g['hn'])+g['U']
        if acov!=0: spr.append(dec(g['Z'] if home_more else g['W']) if ((acov<0)==home_more) else -1)
        # TT side: the team the spread likes more -> its TT over? test: home TT over if spread likes home more (home_more False -> spread likes home more relative)
        line,pts,o=(g['AE'],g['hn'],g['AG']) if not home_more else (g['AA'],g['an'],g['AC'])
        if pts!=line: tt.append(dec(o) if pts>line else -1)
    rep(f'margin gap {thr}+: bet spread side the TTs favor',spr); rep(f'margin gap {thr}+: TT Over of the side the spread favors',tt)
print('| ML favorite by spread size (1u risk) | n | W-L | units | ROI | CI | sample |')
for lo,hi,name in [(0,4.5,'<=4.5'),(5,9.5,'5-9.5'),(10,99,'10+')]:
  for P,c in [('all',lambda d:True),('10/31+',lambda d:d>=dt.date(2026,10,31))]:
    L=[]
    for r in rows:
        g=r['g']
        if not (lo<=abs(g['U'])<=hi) or not c(g['d']): continue
        fav_away=r['p_ml']>=.5; o=g['J'] if fav_away else g['K']; won=(g['an']>g['hn'])==fav_away
        L.append(dec(o) if won else -1)
    rep(f'ML fav, spread {name} ({P})',L)
# stability of ML-vs-spread follow-ML rule by period
for thr in (0.02,0.03):
  for P,c in [('10/20-10/30',lambda d:d<dt.date(2026,10,31)),('10/31-11/16',lambda d:d>=dt.date(2026,10,31))]:
    L=[]
    for r in rows:
        g=r['g']
        if abs(r['res'])<thr or not c(g['d']): continue
        away_exp=r['res']>0; acov=(g['an']-g['hn'])+g['U']
        if acov!=0: L.append(dec(g['W'] if away_exp else g['Z']) if ((acov>0)==away_exp) else -1)
    rep(f'follow-ML spread, resid>={thr} ({P})',L)
for thr in (1.0,1.5):
  for P,c in [('10/20-10/30',lambda d:d<dt.date(2026,10,31)),('10/31-11/16',lambda d:d>=dt.date(2026,10,31))]:
    L=[];M=[]
    for r in rows4:
        g=r['g']
        if not c(g['d']): continue
        if abs(r['mar_gap'])>=thr:
            home_more=r['mar_gap']>0; acov=(g['an']-g['hn'])+g['U']
            if acov!=0: L.append(dec(g['Z'] if home_more else g['W']) if ((acov<0)==home_more) else -1)
        if r['sum_gap']>=thr:
            for line,pts,o in ((g['AA'],g['an'],g['AD']),(g['AE'],g['hn'],g['AH'])):
                if pts!=line: M.append(dec(o) if pts<line else -1)
    rep(f'TT-margin follow spread, gap>={thr} ({P})',L); rep(f'TT sum above total -> TT Unders, gap>={thr} ({P})',M)

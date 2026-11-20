import openpyxl,datetime as dt,math,collections,json,random,runpy,io,contextlib,os
random.seed(3)
# arena lat, lon, utc offset (standard), altitude ft
AR={'ATL':(33.757,-84.396,-5,1050),'BOS':(42.366,-71.062,-5,20),'BKN':(40.683,-73.975,-5,30),'CHA':(35.225,-80.839,-5,750),
'CHI':(41.881,-87.674,-6,600),'CLE':(41.497,-81.688,-5,650),'DAL':(32.790,-96.810,-6,430),'DEN':(39.749,-105.008,-7,5280),
'DET':(42.341,-83.055,-5,600),'GSW':(37.768,-122.388,-8,10),'HOU':(29.751,-95.362,-6,50),'IND':(39.764,-86.155,-5,715),
'LAC':(33.945,-118.341,-8,100),'LAL':(34.043,-118.267,-8,300),'MEM':(35.138,-90.051,-6,280),'MIA':(25.781,-80.188,-5,10),
'MIL':(43.045,-87.917,-6,620),'MIN':(44.980,-93.276,-6,830),'NOP':(29.949,-90.082,-6,10),'NYK':(40.751,-73.993,-5,30),
'OKC':(35.463,-97.515,-6,1200),'ORL':(28.539,-81.384,-5,100),'PHI':(39.901,-75.172,-5,40),'PHX':(33.446,-112.071,-7,1100),
'POR':(45.532,-122.667,-8,50),'SAC':(38.580,-121.500,-8,30),'SAS':(29.427,-98.438,-6,650),'TOR':(43.643,-79.379,-5,250),
'UTA':(40.768,-111.901,-7,4300),'WAS':(38.898,-77.021,-5,50)}
def miles(a,b):
    la1,lo1=map(math.radians,a[:2]); la2,lo2=map(math.radians,b[:2])
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2; return 3959*2*math.asin(math.sqrt(h))
def dd(x):
    if hasattr(x,'date'): return x.date()
    if isinstance(x,(int,float)) and x>40000: return dt.date(1899,12,30)+dt.timedelta(days=int(x))
def imp(o): return -o/(100-o) if o<0 else 100/(100+o)
def dec(o): return 100/-o if o<0 else o/100
wb=openpyxl.load_workbook('in1117/s3.xlsx',read_only=True,data_only=True)
S=collections.defaultdict(list)
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,max_col=3,values_only=True):
    if not r[0] or not r[1]: continue
    tm=r[0]; mu=r[1]; d=dd(r[2])
    if ' @ ' in mu: opp=mu.split(' @ ')[1]; loc=opp; home=False
    else: opp=mu.split(' vs. ')[1]; loc=tm; home=True
    S[tm].append((d,loc,home,opp))
F={}
for tm,L in S.items():
    L=sorted(set(L)); prev=None; trip=0
    for i,(d,loc,home,opp) in enumerate(L):
        past=[x for x in L if x[0]<d]
        rest=(d-past[-1][0]).days-1 if past else None
        g4=sum(1 for x in L if d-dt.timedelta(3)<=x[0]<=d)
        g6=sum(1 for x in L if d-dt.timedelta(5)<=x[0]<=d)
        prev_loc=past[-1][1] if past else tm
        tr=miles(AR[prev_loc],AR[loc])
        miles7=0; locs=[x[1] for x in L if d-dt.timedelta(6)<=x[0]<=d]
        seq=[x[1] for x in L if x[0]<=d][-len(locs)-1:] if past else locs
        for a,b in zip(seq,seq[1:]): miles7+=miles(AR[a],AR[b])
        tz=AR[loc][2]-AR[prev_loc][2]   # + = moved east
        trip=(trip+1) if not home else 0
        home_after_trip=home and past and not past[-1][2] and sum(1 for x in reversed(past) if not x[2]) >=0
        # length of road trip just ended (consecutive away games before this home game)
        k=0
        for x in reversed(past):
            if x[2]: break
            k+=1
        F[(tm,d)]=dict(rest=rest,b2b=rest==0,g4=g4,g6=g6,travel=tr,miles7=miles7,tz=tz,trip=trip if not home else 0,ret_home=(home and k>=3),trip_len_before=k if home else None,alt=AR[loc][3],home=home)
# join Tracking
os.environ['WB']='in1116u/s.xlsx'
with contextlib.redirect_stdout(io.StringIO()): n2c=runpy.run_path('work/xposs.py')['n2c']
t=wb['Tracking']; G={}
for r in t.iter_rows(min_row=13,max_row=t.max_row,values_only=True):
    d=dd(r[0])
    if not d or not isinstance(r[39],(int,float)) or r[20] is None: continue
    k=(d,r[1],r[2])
    if k in G: continue
    a,h=n2c.get(r[1]),n2c.get(r[2])
    if (a,d) not in F or (h,d) not in F: continue
    G[k]=dict(d=d,a=a,h=h,U=r[20],W=r[22],Z=r[25],P=r[15],S=r[18],T=r[19],an=r[39],hn=r[40],fa=F[(a,d)],fh=F[(h,d)],ap=r[3],hp=r[4])
G=list(G.values()); print('games joined',len(G))
def boot(L,B=3000):
    n=len(L)
    if n<5: return (float('nan'),)*2
    xs=sorted(sum(random.choice(L) for _ in range(n))/n for _ in range(B)); return xs[int(.025*B)],xs[int(.975*B)]
def rep(name,L):
    n=len(L)
    if not n: print(f'| {name} | 0 | | | | |'); return
    w=sum(1 for x in L if x>0); lo,hi=boot(L); fl='VERY LOW' if n<15 else ('LOW' if n<30 else '')
    print(f'| {name} | {n} | {w}-{n-w} | {100*sum(L)/n:+.1f}% | [{100*lo:+.0f}%, {100*hi:+.0f}%] | {fl} |')
def bet(g,home):
    acov=(g['an']-g['hn'])+g['U']
    if acov==0: return None
    won=(acov<0)==home; o=g['Z'] if home else g['W']; return dec(o) if won else -1
def bet_tot(g,over):
    T=g['an']+g['hn']
    if T==g['P'] or g['S'] is None: return None
    won=(T>g['P'])==over; return dec(g['S'] if over else g['T']) if won else -1
def seg(name,cond):  # cond(f_team,f_opp) -> bet that team
    L=[];L2=[]
    for g in G:
        for home in (True,False):
            fm,fo=(g['fh'],g['fa']) if home else (g['fa'],g['fh'])
            if cond(fm,fo):
                x=bet(g,home)
                if x is not None: (L2 if g['d']>=dt.date(2026,10,31) else L).append(x)
    rep(name+' (all)',L+L2); rep(name+' (10/31+)',L2)
print('| segment: bet the named team ATS | n | W-L | ROI | 95% CI | sample |')
seg('rest advantage 2+ days',lambda m,o: m['rest'] is not None and o['rest'] is not None and m['rest']-o['rest']>=2)
seg('rest disadvantage 2+ days',lambda m,o: m['rest'] is not None and o['rest'] is not None and o['rest']-m['rest']>=2)
seg('team on 3rd game in 4 nights, opp not',lambda m,o: m['g4']>=3 and o['g4']<3)
seg('team on 4th game in 6 nights, opp not',lambda m,o: m['g6']>=4 and o['g6']<4)
seg('team traveled 1000+ mi since last game, opp <300',lambda m,o: m['travel']>=1000 and o['travel']<300)
seg('team 2500+ mi in last 7 days, opp <1000',lambda m,o: m['miles7']>=2500 and o['miles7']<1000)
seg('road team flew west 2+ time zones (since last game)',lambda m,o: not m['home'] and m['tz']<=-2)
seg('road team flew east 2+ time zones',lambda m,o: not m['home'] and m['tz']>=2)
seg('road team at altitude (DEN/UTA)',lambda m,o: not m['home'] and m['alt']>=4000)
seg('home team at altitude (DEN/UTA)',lambda m,o: m['home'] and m['alt']>=4000)
seg('road team game 4+ of a road trip',lambda m,o: not m['home'] and m['trip']>=4)
seg('road team game 1 of a road trip',lambda m,o: not m['home'] and m['trip']==1)
seg('home team first game back after 3+ game trip',lambda m,o: m['home'] and m['ret_home'])
seg('B2B team that traveled vs rested opp',lambda m,o: m['b2b'] and m['travel']>=300 and not o['b2b'])
seg('B2B team no travel (same city) vs rested opp',lambda m,o: m['b2b'] and m['travel']<300 and not o['b2b'])
seg('both teams B2B: home',lambda m,o: m['home'] and m['b2b'] and o['b2b'])
seg('rested 2+ days vs B2B opp',lambda m,o: m['rest'] is not None and m['rest']>=2 and o['b2b'])
# totals
print('| totals segment | n | W-L | ROI | 95% CI | sample |')
for name,cond,over in [('either team B2B -> Under',lambda g:g['fa']['b2b'] or g['fh']['b2b'],False),('both teams 2+ rest -> Over',lambda g:(g['fa']['rest'] or 0)>=2 and (g['fh']['rest'] or 0)>=2,True),
                       ('game at altitude -> Over',lambda g:g['fh']['alt']>=4000,True),('road team 3-in-4 -> Under',lambda g:g['fa']['g4']>=3,False),
                       ('road team flew west 2+ tz -> Over',lambda g:g['fa']['tz']<=-2,True)]:
    L=[x for g in G if cond(g) for x in [bet_tot(g,over)] if x is not None]; rep(name,L)
# does the model already capture B2B? model margin error for B2B team
E=[]
for g in G:
    for home in (True,False):
        fm,fo=(g['fh'],g['fa']) if home else (g['fa'],g['fh'])
        if fm['b2b'] and not fo['b2b']:
            act=(g['hn']-g['an']) if home else (g['an']-g['hn']); mod=(g['hp']-g['ap']) if home else (g['ap']-g['hp']); mkt=(g['U']) if home else -g['U']
            E.append((act-mod,act-mkt))
print('B2B team: actual minus model %+.1f, actual minus market %+.1f, n=%d'%(sum(e[0] for e in E)/len(E),sum(e[1] for e in E)/len(E),len(E)))
json.dump({f'{k[0]}|{k[1]}':v for k,v in F.items()},open('audit/fatigue_table.json','w'),default=str)
print('team-games in fatigue table',len(F))
def fat(f): return (1 if f['b2b'] else 0)+(1 if f['g4']>=3 else 0)+(1 if f['g6']>=4 else 0)
print('| composite (fatigue score = B2B + 3-in-4 + 4-in-6) | n | W-L | ROI | 95% CI | sample |')
for thr in (1,2):
    seg(f'more tired team (score diff >= {thr})',lambda m,o,thr=thr: fat(m)-fat(o)>=thr)
for P,lo,hi in [('10/20-10/30',dt.date(2026,10,1),dt.date(2026,10,30)),('10/31-11/11',dt.date(2026,10,31),dt.date(2026,11,11)),('11/12-11/16',dt.date(2026,11,12),dt.date(2026,11,30))]:
    L=[]
    for g in G:
        if not lo<=g['d']<=hi: continue
        for home in (True,False):
            fm,fo=(g['fh'],g['fa']) if home else (g['fa'],g['fh'])
            if fat(fm)-fat(fo)>=1:
                x=bet(g,home)
                if x is not None: L.append(x)
    rep(f'more tired team, diff>=1, {P}',L)
for side in ('home','away'):
    L=[]
    for g in G:
        for home in (True,False):
            if (side=='home')!=home: continue
            fm,fo=(g['fh'],g['fa']) if home else (g['fa'],g['fh'])
            if fat(fm)-fat(fo)>=1:
                x=bet(g,home)
                if x is not None: L.append(x)
    rep(f'more tired team is {side}',L)
# outliers: margin of cover distribution

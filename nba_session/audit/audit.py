import openpyxl,datetime as dt,collections,random,math,json,runpy,io,contextlib,os
random.seed(7)
wb=openpyxl.load_workbook('/tmp/f.xlsx',data_only=True,read_only=True)
def dd(x):
    if hasattr(x,'date'): return x.date()
    if isinstance(x,(int,float)) and x>40000: return dt.date(1899,12,30)+dt.timedelta(days=int(x))
def imp(o): return -o/(100-o) if o<0 else 100/(100+o)
def dec(o): return 100/-o if o<0 else o/100
os.environ['WB']='in1116u/s.xlsx'
with contextlib.redirect_stdout(io.StringIO()): n2c=runpy.run_path('work/xposs.py')['n2c']
# ---- box scores: team dates, player minutes
P=collections.defaultdict(list)   # (player,team)-> [(date,min)]
TG=collections.defaultdict(set)
for r in wb['BoxScores'].iter_rows(min_row=2,max_col=6,values_only=True):
    if not r[0]: continue
    d=dd(r[3]); TG[r[1]].add(d); P[(r[0],r[1])].append((d,r[5] or 0))
TDATES={}
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,max_col=3,values_only=True):
    if r[0] and r[2] is not None: TDATES.setdefault(r[0],set()).add(dd(r[2]))
def key_out(team,d):
    # players averaging >=30 min over >=4 prior team games who did not play on d (team played on d)
    if d not in TG.get(team,()): return None
    out=[]
    for (pl,tm),L in P.items():
        if tm!=team: continue
        prior=[m for x,m in L if x<d]
        if len(prior)>=4 and sum(prior)/len(prior)>=30 and d not in {x for x,_ in L}: out.append(pl)
    return out
G=[]
for r in wb['Tracking'].iter_rows(min_row=13,max_row=213,values_only=True):
    d=dd(r[0])
    if not d or not isinstance(r[39],(int,float)): continue
    g=dict(d=d,aw=r[1],hm=r[2],ap=r[3],hp=r[4],mlpa=r[7],J=r[9],K=r[10],P=r[15],Q=r[16],po=r[17],S=r[18],T=r[19],U=r[20],pac=r[21],W=r[22],Z=r[25],
           mk=r[35],side=r[36],odds=r[37],u=r[38],an=r[39],hn=r[40],grade=r[44],prof=r[45],close=r[46])
    a,h=n2c.get(g['aw']),n2c.get(g['hm']); g['a'],g['h']=a,h
    g['ab2b']=bool(a and d-dt.timedelta(1) in TDATES.get(a,())); g['hb2b']=bool(h and d-dt.timedelta(1) in TDATES.get(h,()))
    g['aout']=key_out(a,d) if a else None; g['hout']=key_out(h,d) if h else None
    g['period']='A 10/20-10/30' if d<dt.date(2026,10,31) else ('B 10/31-11/11' if d<dt.date(2026,11,12) else 'C 11/12-11/16')
    G.append(g)
json.dump([{k:(str(v) if isinstance(v,dt.date) else v) for k,v in g.items()} for g in G],open('audit/games.json','w'))
print('games',len(G))

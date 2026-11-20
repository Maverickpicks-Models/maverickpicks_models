import openpyxl,json,datetime as dt,collections,numpy as np,sys
wb=openpyxl.load_workbook(__import__('os').environ.get('WB','in1112/s.xlsx'),read_only=True,data_only=True)
code={r[1]:r[0] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}  # code->name
name2code={v:k for k,v in code.items()}
games={}
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True):
    if not r[0] or r[2] is None: continue
    t,mu,d,pm=r[0],r[1],r[2],r[23]
    d=d.date() if hasattr(d,'date') else d
    if '@' in mu: aw,hm=t,mu.split('@')[1].strip()
    else: hm,aw=t,mu.split('vs.')[1].strip()
    key=(d,aw,hm)
    m=pm if t==hm else -pm      # home margin
    games[key]=m
G=json.load(open('work/deep_games11.json'))
for g in G:  # add tracking games not in box log (11/10)
    d=dt.date.fromisoformat(g['d']); key=(d,name2code[g['aw']],name2code[g['hm']])
    if key not in games: games[key]=g['hn']-g['an']
GL=sorted(games.items())
print('games in log',len(GL),GL[0][0][0],GL[-1][0][0])
played=collections.defaultdict(set)
for (d,a,h),m in GL: played[a].add(d); played[h].add(d)
SHR=4
def netm(team,before,excl):   # team's mean margin before date, excluding games vs excl, shrunk
    v=[ (m if h==team else -m) for (d,a,h),m in GL if d<before and team in (a,h) and excl not in (a,h)]
    return sum(v)/(len(v)+SHR) if v else 0.0
perf=collections.defaultdict(list)   # team -> list of (date, pts)
for (d,a,h),m in GL:
    for t,o,mm,road in ((h,a,m,False),(a,h,-m,True)):
        res=3 if mm>=4 else (1 if mm>-4 else 0)
        pts=res+max(-20,min(20,mm))+netm(o,d,t)+(1.7 if road else -1.7)+(1.75 if (d-dt.timedelta(days=1)) in played[t] else 0)
        perf[t].append((d,pts))
def rating(t,before):
    v=[p for d,p in perf[t] if d<before]; return (sum(v)/len(v) if v else None, len(v))
# validate vs today's Crafted Pts/G
try:
    C={r[1]:r[11]/r[2] for r in wb['Ratings_2026_27'].iter_rows(min_row=2,max_row=31,values_only=True)}
    x=[C[code[c]] for c in code]; y=[rating(c,dt.date(2026,11,11))[0] for c in code]
    print('replica corr %.3f'%np.corrcoef(x,y)[0,1])
except Exception as e: pass
out=[]
for g in G:
    if g['U'] is None or g['nv_away_sp'] is None: continue
    d=dt.date.fromisoformat(g['d']); a,h=name2code[g['aw']],name2code[g['hm']]
    ra,na=rating(a,d); rh,nh=rating(h,d)
    if ra is None or rh is None or min(na,nh)<3: continue
    g2=dict(g); g2['cr']=(rh-ra); g2['n']=min(na,nh); out.append(g2)
json.dump(out,open('work/crafted_bt.json','w')); print('backtest games',len(out))

import openpyxl,collections,datetime,numpy as np,pickle,sys
sys.path.insert(0,'work'); from prod import nm
ps=openpyxl.load_workbook('ps/ps.xlsx',read_only=True,data_only=True)
def season(n):
    d={}
    for r in ps[n].iter_rows(min_row=2,values_only=True):
        if not r[1] or r[0] is None: continue
        k=nm(r[1])
        if k in d: continue   # first row = TOT for traded players
        d[k]=dict(m=float(r[11] or 0),a=float(r[12] or 0),name=r[1],ftm=float(r[18] or 0),fta=float(r[19] or 0))
    return d
S26,S25=season('25-26 Player'),season('24-25 Player')
lg26=sum(v['m'] for v in S26.values())/sum(v['a'] for v in S26.values()); lg25=sum(v['m'] for v in S25.values())/sum(v['a'] for v in S25.values())
print('league 3P% 24-25',round(lg25,4),'25-26',round(lg26,4))
# fit shrinkage K: predict 25-26 from 24-25
best=None
for K in range(100,2001,50):
    err=0;w=0
    for k,v in S25.items():
        if k in S26 and v['a']>=50 and S26[k]['a']>=100:
            pred=(v['m']+K*lg25)/(v['a']+K); act=S26[k]['m']/S26[k]['a']; wt=S26[k]['a']
            err+=wt*(act-pred)**2; w+=wt
    if best is None or err/w<best[0]: best=(err/w,K)
K=best[1]; print('best shrink K (pseudo-attempts) predicting next season',K)
# current season box
wb=openpyxl.load_workbook('in1104/src.xlsx',read_only=True,data_only=True)
def dd(d): return (datetime.date(1899,12,30)+datetime.timedelta(days=int(d))) if isinstance(d,(int,float)) else d.date()
P=collections.defaultdict(lambda: dict(m=0.,a=0.,g=0,team=None,name=None,games=[]))
for r in wb['BoxScores'].iter_rows(min_row=2,values_only=True):
    if not r[0] or r[3] is None: continue
    p=P[nm(r[0])]; p['m']+=float(r[10] or 0); p['a']+=float(r[11] or 0); p['g']+=1; p['team']=r[1]; p['name']=r[0]; p['games'].append((dd(r[3]),r[1],float(r[10] or 0),float(r[11] or 0)))
LGc=sum(p['m'] for p in P.values())/sum(p['a'] for p in P.values())
ROOK=0.335
rows=[]
for k,p in P.items():
    if p['a']==0: continue
    m=a=0.
    if k in S26: m+=2*S26[k]['m']; a+=2*S26[k]['a']
    if k in S25: m+=S25[k]['m']; a+=S25[k]['a']
    base = lg26*0.67+lg25*0.33
    prior=(m+K*(base if a>0 else ROOK))/(a+K) if a>0 else ROOK
    rows.append(dict(k=k,name=p['name'],team=p['team'],m=p['m'],a=p['a'],prior=prior,hist_a=a/ (2 if k in S26 else 1) if a else 0,
        raw_hist=(m/a if a else None),has=a>0,games=p['games']))
pickle.dump(dict(rows=rows,K=K,lg26=lg26,lg25=lg25,LGc=LGc),open('work/p3exp.pkl','wb'))
print('players this season',len(rows),'with prior-season 3PA',sum(r['has'] for r in rows),'current league',round(LGc,4))
A=np.array([r['a'] for r in rows]); M=np.array([r['m'] for r in rows]); PR=np.array([r['prior'] for r in rows])
print('expected makes from own history',round((A*PR).sum()),'actual',int(M.sum()),'attempts',int(A.sum()),
      '-> expected 3P%',round((A*PR).sum()/A.sum()*100,1),'actual',round(M.sum()/A.sum()*100,1))
# does own history predict this season? weighted regression, players 30+ attempts
m=A>=25
act=M[m]/A[m]; w=A[m]
def wcorr(x,y,w):
    mx=np.average(x,weights=w); my=np.average(y,weights=w)
    return np.average((x-mx)*(y-my),weights=w)/np.sqrt(np.average((x-mx)**2,weights=w)*np.average((y-my)**2,weights=w))
print('players 25+ 3PA:',m.sum(),'corr(prior-based expected, actual 3P%)',round(wcorr(PR[m],act,w),3))
# z-scores vs own expectation
z=(M-A*PR)/np.sqrt(A*PR*(1-PR))
zz=z[A>=20]; print('z vs own expected (3PA>=20): SD',round(zz.std(),2),'(1.0 = pure chance)', ' share |z|>2:',round((abs(zz)>2).mean()*100,1),'% (chance ~4.6%)')
# league-wide shift adjustment
shift=M.sum()/ (A*PR).sum()
print('league-wide: this season shooting at',round(shift*100,1),'% of history-based expectation')

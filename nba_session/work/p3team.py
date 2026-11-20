import pickle,collections,numpy as np,openpyxl,datetime
D=pickle.load(open('work/p3exp.pkl','rb')); rows=D['rows']; LGc=D['LGc']
shift=sum(r['m'] for r in rows)/sum(r['a']*r['prior'] for r in rows)
# team-game aggregates
TG=collections.defaultdict(lambda: dict(m=0.,a=0.,e=0.))
for r in rows:
    for d,t,m,a in r['games']:
        g=TG[(d,t)]; g['m']+=m; g['a']+=a; g['e']+=a*r['prior']*shift
wb=openpyxl.load_workbook('in1104/src.xlsx',read_only=True,data_only=True)
def dd(d): return (datetime.date(1899,12,30)+datetime.timedelta(days=int(d))) if isinstance(d,(int,float)) else d.date()
opp={};poss={}
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True):
    if r[0] and r[2] is not None:
        k=(dd(r[2]),r[0]); opp[k]=r[1].split()[-1]; poss[k]=r[17]*r[4]/48
code={r[1]:r[0] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}
cur={r[1]:(r[12],r[13]) for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}
T=collections.defaultdict(lambda: dict(m=0.,a=0.,e=0.,om=0.,oa=0.,oe=0.,poss=0.,g=0))
for (d,t),g in TG.items():
    if (d,t) not in opp: continue
    o=TG.get((d,opp[(d,t)]))
    x=T[t]; x['m']+=g['m']; x['a']+=g['a']; x['e']+=g['e']; x['poss']+=poss[(d,t)]; x['g']+=1
    if o: x['om']+=o['m']; x['oa']+=o['a']; x['oe']+=o['e']
out=[]
for t,x in T.items():
    off_lg=(x['m']-LGc*x['a'])*3/x['g']; off_pl=(x['m']-x['e'])*3/x['g']
    def_lg=(x['om']-LGc*x['oa'])*3/x['g']; def_pl=(x['om']-x['oe'])*3/x['g']
    out.append((t,x['g'],x['m']/x['a'],x['e']/x['a'],x['om']/x['oa'],x['oe']/x['oa'],off_lg,off_pl,def_lg,def_pl,cur[t]))
out.sort(key=lambda r:-(r[7]-r[9]))
print(f"{'tm':4s} {'G':>2} {'3P%':>5} {'exp':>5} | {'opp':>5} {'exp':>5} | off luck pts/g lg-rate vs player-based | def luck lg vs player | net player-based | workbook off/def per100")
for r in out:
    print(f"{r[0]:4s} {r[1]:2d} {r[2]*100:5.1f} {r[3]*100:5.1f} | {r[4]*100:5.1f} {r[5]*100:5.1f} | {r[6]:+5.1f} {r[7]:+5.1f} | {r[8]:+5.1f} {r[9]:+5.1f} | {r[7]-r[9]:+5.1f} | {r[10][0]:+5.1f} {r[10][1]:+5.1f}")
a=np.array([r[3] for r in out]); print('spread of team expected 3P% (player-based): SD',round(a.std()*100,2),'pts; range',round(a.min()*100,1),round(a.max()*100,1))
b=np.array([r[5] for r in out]); print('opp expected 3P% spread SD',round(b.std()*100,2))
d1=np.array([r[6]-r[7] for r in out]); print('difference between methods, offense pts/g: SD',round(d1.std(),2),'max',round(abs(d1).max(),1))
# predictive test: per team, split games by date; predict 2nd-half 3P% from (a) league, (b) player-based expected (2nd half attempts), (c) first-half actual
errs=collections.defaultdict(float); W=0
for t in T:
    gs=sorted(k for k in TG if k[1]==t and k in opp); h=len(gs)//2
    f=[TG[k] for k in gs[:h]]; s=[TG[k] for k in gs[h:]]
    sa=sum(g['a'] for g in s); sm=sum(g['m'] for g in s); se=sum(g['e'] for g in s)
    fp=sum(g['m'] for g in f)/sum(g['a'] for g in f)
    act=sm/sa
    for lab,pred in [('league avg',LGc),('player-history expected',se/sa),('team first-half actual',fp),('50/50 hist+first half',.5*se/sa+.5*fp)]:
        errs[lab]+=sa*(act-pred)**2
    W+=sa
print('\nPredicting each team\'s 3P% in its later games (RMSE, pct pts):')
for k,v in errs.items(): print(f'  {k:26s} {np.sqrt(v/W)*100:.2f}')
pickle.dump(out,open('work/p3team.pkl','wb'))

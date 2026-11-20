import sys, json, math, statistics as st
sys.path.insert(0,'work')
import proster as PR
from engine import Model
m=Model('in16/nba.xlsx')
PARAMS=(800,-1.5,-0.5,1,-2,-0.5); SO,SD=0.92,0.95
def roster_team(team):
    O=D=MP=0
    for n,p in PR.S['27'].items():
        if team in p['teams']:
            mp=p['teams'][team][2]; o,d,_=PR.prior(n,'27',*PARAMS); O+=mp*o; D+=mp*d; MP+=mp
    return O/MP*5*SO, D/MP*5*SD
RT={t:roster_team(t) for t in m.R26}
def proj(aw,hm,mode):
    A,H=m.team(aw),m.team(hm)
    # pure prior versions (cw=0)
    reg=m.A[10]
    def old(t):
        p=m.R25[t]; return dict(o=m.pO+(1-reg)*(p['o']-m.pO), d=m.pD+(1-reg)*(p['d']-m.pD), p=p['p'])
    def ros(t):
        o,d=RT[t]; return dict(o=m.LO+o, d=m.LD-d, p=m.R25[t]['p'])
    f=old if mode=='old' else ros
    a,h=f(aw),f(hm)
    pace=m.LP+m.A[11]*((a['p']-m.LP)+(h['p']-m.LP))
    ap=pace/100*(a['o']+h['d']-m.LB)-m.A[12]/2; hp=pace/100*(h['o']+a['d']-m.LB)+m.A[12]/2
    return ap,hp
T=json.load(open('work/teamgames.json'))
games={}
for t in T:
    if t['home']==0: games[(t['date'],t['team'],t['opp'])]=t
res=[]
for (d,aw,hm),t in games.items():
    oa,oh=proj(aw,hm,'old'); ra,rh=proj(aw,hm,'ros')
    res.append(dict(date=d,aw=aw,hm=hm,A=t['pts'],H=t['allow'],mod=(t['mod'],t['moda']),mkt=(t['mkt'],t['mkta']),old=(oa,oh),ros=(ra,rh)))
rm=lambda L: math.sqrt(sum(v*v for v in L)/len(L))
print('games',len(res))
for k in ['old','ros','mod','mkt']:
    em=[(x[k][0]-x[k][1])-(x['A']-x['H']) for x in res]; et=[(x[k][0]+x[k][1])-(x['A']+x['H']) for x in res]
    tp=[x[k][0]-x['A'] for x in res]+[x[k][1]-x['H'] for x in res]
    print(f"{k:4s} margin RMSE {rm(em):5.2f} | total RMSE {rm(et):5.2f} bias {st.mean(et):+5.1f} | team pts RMSE {rm(tp):5.2f}")
# who is right when roster disagrees with market
def reg(x,y):
    mx,my=st.mean(x),st.mean(y); sxx=sum((a-mx)**2 for a in x); b=sum((a-mx)*(c-my) for a,c in zip(x,y))/sxx
    r_=[c-my-b*(a-mx) for a,c in zip(x,y)]; return round(b,2), round(math.sqrt(sum(v*v for v in r_)/(len(x)-2)/sxx),2)
for k in ['old','ros','mod']:
    x=[(r['mkt'][0]-r['mkt'][1])-(r[k][0]-r[k][1]) for r in res]; y=[(r['A']-r['H'])-(r[k][0]-r[k][1]) for r in res]
    print(k,'margin: actual-proj on mkt-proj slope',reg(x,y),'sd gap',round(st.pstdev(x),2))
# blends with market? correlation of roster margin with market margin
print('corr margin with market: old',round(st.correlation([r['old'][0]-r['old'][1] for r in res],[r['mkt'][0]-r['mkt'][1] for r in res]),3),
      'ros',round(st.correlation([r['ros'][0]-r['ros'][1] for r in res],[r['mkt'][0]-r['mkt'][1] for r in res]),3),
      'mod',round(st.correlation([r['mod'][0]-r['mod'][1] for r in res],[r['mkt'][0]-r['mkt'][1] for r in res]),3))
json.dump(res,open('work/bt_roster.json','w'))
print(sorted([(t,round(v[0],1),round(v[1],1)) for t,v in RT.items()],key=lambda z:-(z[1]+z[2]))[:30])

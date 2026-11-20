import sys, statistics; sys.path.insert(0,'work')
from pd import load, norm
D=load()
# league PM centre (minute-weighted, 40-400 MP, PM present)
pool=[d for d in D.values() if isinstance(d['pm'],(int,float)) and isinstance(d['mp'],(int,float)) and 40<=d['mp']<=400]
PMC=sum(d['pm']*d['mp'] for d in pool)/sum(d['mp'] for d in pool)
K_PRIOR,K_NOPRIOR,K_PM=600,250,1500
REP=(-1.5,-0.5)
W={'Out':1,'Doubtful':0.75,'Questionable':0.5}
# name: (G, MP, OBPM, DBPM or None if unknown, s1 2025-26 (MP,O,D,G), s2 2024-25 (MP,O,D))
P={
 'Dennis Schroder':(5,162,-4.0,-2.3,(1697,-0.9,-1.3,70),(2105,-1.3,-0.9)),
 'Justin Champagnie':(3,73,None,None,(1377,0.6,-1.0,69),(1340,-0.3,-0.2)),
 'Tre Johnson':(4,91,-1.2,-2.3,(1443,-2.1,-2.9,60),None),
 'Jalen Smith':(5,117,2.7,-2.2,None,None),
 'Jalen Duren':(2,38,4.6,1.9,(1976,4.4,0.5,70),(2034,1.6,1.5)),
 'Isaiah Joe':(3,42,-3.0,-2.6,(1507,2.0,0.5,71),(1604,1.4,-0.1)),
 'Egor Demin':(4,87,None,None,(1308,-0.9,-0.7,52),None),
 'Jaylen Brown':(5,182,-0.8,-0.6,(2443,3.5,-0.1,71),(2158,0.4,-0.4)),
 'Paolo Banchero':(2,68,6.1,1.2,(2502,1.4,0.0,72),(1582,3.4,0.2)),
 'Jalen Suggs':(3,100,-5.0,0.0,(1574,0.7,1.8,57),None),
 'Kawhi Leonard':(2,52,None,None,(2085,7.4,0.6,65),(1180,2.5,0.6)),
 'Alperen Sengun':(4,136,6.0,1.7,(2398,2.7,1.5,72),(2395,2.6,1.8)),
 'Reed Sheppard':(4,93,-0.7,0.2,(2147,1.2,1.5,82),None),
 'Marcus Smart':(2,48,None,None,(1769,-2.9,0.6,62),None),
 'Sergio de Larrea':(3,46,None,None,None,None),
 'Naji Marshall':(3,83,-0.1,-0.6,(2184,-0.7,0.1,74),(1919,-0.3,-0.5)),
 'Tyrese Haliburton':(4,132,7.0,-0.1,None,(2451,5.7,0.2)),
 'Ivica Zubac':(3,64,None,None,(1446,0.7,-0.9,48),(2624,2.3,0.8)),
 'Rui Hachimura':(3,94,-8.5,-2.3,(1927,-0.8,-1.5,68),(1869,-0.1,-0.6)),
 'Anthony Edwards':(4,135,5.5,1.5,(2137,4.7,-0.1,61),(2871,4.4,0.0)),
 'Ziaire Williams':(4,114,2.6,-0.6,(1281,-2.0,0.4,56),(1541,-2.2,-0.1)),
 'Gui Santos':(4,96,0.6,-1.8,(1395,-0.9,0.3,68),None),
}
def rating(n):
    g,mp,o,d,s1,s2=P[n]
    ss=[(s1,2)] if s1 else []; ss+= [(s2,1)] if s2 else []
    if ss:
        w=sum(s[0]*k for s,k in ss); po=sum(s[0]*k*s[1] for s,k in ss)/w; pdd=sum(s[0]*k*s[2] for s,k in ss)/w; K=K_PRIOR
    else: po,pdd,K=REP[0],REP[1],K_NOPRIOR
    if o is None: o,d,mpc=po,pdd,0
    else: mpc=mp
    bo=(o*mpc+po*K)/(mpc+K); bd=(d*mpc+pdd*K)/(mpc+K)
    # PM layer: defensive on-court evidence (negative PM = good), heavy shrink
    pdrow=D.get(norm(n)); pm=pdrow['pm'] if pdrow else None
    if isinstance(pm,(int,float)):
        ev=-(pm-PMC); wpm=pdrow['mp']/(pdrow['mp']+K_PM); bd2=bd+(ev-bd)*wpm
    else: ev,wpm,bd2=None,0,bd
    mpg = mp/g if g>=3 or not s1 else s1[0]/s1[3]
    return dict(bo=bo,bd_bpm=bd,bd=bd2,pm=pm,pm_w=wpm,mpg=mpg)
def val(n,w):
    r=rating(n); sh=r['mpg']/48
    o=(r['bo']-REP[0])*sh; d=(r['bd']-REP[1])*sh
    return dict(name=n,w=w,O=o,D=d,full=o+d,**r)
INJ={ # team: [(player, status)]
 'Charlotte Hornets':[('Dennis Schroder','Questionable')],
 'Washington Wizards':[('Justin Champagnie','Out'),('Tre Johnson','Questionable')],
 'Chicago Bulls':[('Jalen Smith','Questionable')],
 'Boston Celtics':[],
 'Detroit Pistons':[('Jalen Duren','Out'),('Isaiah Joe','Questionable')],
 'Brooklyn Nets':[('Egor Demin','Out')],
 'New York Knicks':[],
 'Philadelphia 76ers':[('Jaylen Brown','Questionable')],
 'Orlando Magic':[('Paolo Banchero','Out'),('Jalen Suggs','Out')],
 'Toronto Raptors':[('Kawhi Leonard','Out')],
 'Houston Rockets':[('Alperen Sengun','Questionable'),('Reed Sheppard','Out'),('Marcus Smart','Questionable')],
 'Dallas Mavericks':[('Naji Marshall','Questionable'),('Sergio de Larrea','Out')],
 'Indiana Pacers':[('Tyrese Haliburton','Out'),('Ivica Zubac','Out')],
 'Miami Heat':[],
 'LA Clippers':[('Rui Hachimura','Questionable')],
 'Minnesota Timberwolves':[('Anthony Edwards','Out')],
 'Denver Nuggets':[],
 'Phoenix Suns':[],
 'Los Angeles Lakers':[('Ziaire Williams','Questionable')],
 'Golden State Warriors':[('Gui Santos','Doubtful')],
}
GAMES=[('Charlotte Hornets','Washington Wizards'),('Chicago Bulls','Boston Celtics'),('Detroit Pistons','Brooklyn Nets'),
 ('New York Knicks','Philadelphia 76ers'),('Orlando Magic','Toronto Raptors'),('Houston Rockets','Dallas Mavericks'),
 ('Indiana Pacers','Miami Heat'),('LA Clippers','Minnesota Timberwolves'),('Denver Nuggets','Phoenix Suns'),('Los Angeles Lakers','Golden State Warriors')]
def team(t):
    rows=[]
    for n,s in INJ[t]:
        v=val(n,W[s]); v['status']=s
        if v['full']<=0: v['O']=v['D']=0  # not better than replacement
        rows.append(v)
    neff=sum(r['w'] for r in rows if r['full']>=1.0)
    m=min(1.30,1+0.15*max(0,neff-1))
    O=sum(r['O']*r['w'] for r in rows)*m; Dd=sum(r['D']*r['w'] for r in rows)*m
    return O,Dd,m,rows
if __name__=='__main__':
    print('PM centre',round(PMC,2))
    for a,h in GAMES:
        print(f"\n{a} @ {h}")
        for t in (a,h):
            O,Dd,m,rows=team(t)
            print(f"  {t:24s} lineup adj {-(O+Dd):+.1f}  (own pts -{O:.1f}, opp pts +{Dd:.1f}) mult {m:.2f}")
            for r in rows:
                pm = 'n/a' if r['pm'] is None else f"{r['pm']:+.1f}"
                print(f"     {r['name']:20s} {r['status']:12s} mpg {r['mpg']:4.1f} O {r['bo']:+.2f} D(bpm) {r['bd_bpm']:+.2f} PM {pm} w{r['pm_w']:.2f} -> D {r['bd']:+.2f} | full O {r['O']:.2f} D {r['D']:.2f} = {r['full']:.2f}")

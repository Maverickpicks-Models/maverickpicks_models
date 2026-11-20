import sys, json; sys.path.insert(0,'work')
import inj1030 as I
from engine import Model
m=Model('in14/nba.xlsx')
# add prior-only players (not played this season): (G,MP,O,D,s1,s2)
I.P.update({
 'Kon Knueppel':(0,0,None,None,(2551,3.1,-0.4,81),None),
 'Coby White':(0,0,None,None,(1249,0.6,-1.9,50),None),
 'Jimmy Butler III':(0,0,None,None,(1182,5.0,0.5,38),None),
 'Mark Williams':(0,0,None,None,(1416,1.5,0.5,60),None),
 'Cameron Johnson':(1,11,None,None,(1647,0.3,-0.9,54),None),
 'Donte DiVincenzo':(0,0,None,None,(2494,0.0,0.7,82),None),
})
# games with THIS team last season (for prior inclusion)
PRIOR_G={'Justin Champagnie':69,'Tre Johnson':60,'Jalen Smith':0,'Jalen Duren':70,'Isaiah Joe':0,'Egor Demin':52,'Jaylen Brown':0,
 'Paolo Banchero':72,'Jalen Suggs':57,'Kawhi Leonard':0,'Alperen Sengun':72,'Reed Sheppard':82,'Marcus Smart':0,'Sergio de Larrea':0,
 'Naji Marshall':74,'Tyrese Haliburton':0,'Ivica Zubac':5,'Rui Hachimura':0,'Anthony Edwards':61,'Ziaire Williams':0,'Gui Santos':68,
 'Kon Knueppel':81,'Coby White':21,'Jimmy Butler III':38,'Mark Williams':60,'Cameron Johnson':54,'Donte DiVincenzo':82,'Dennis Schroder':0}
TEAM_OF={}
for t,l in I.INJ.items():
    for n,s in l: TEAM_OF[n]=t
# user's OUT list adds/upgrades
I.INJ['Charlotte Hornets']+= [('Kon Knueppel','Out'),('Coby White','Out')]
I.INJ['Golden State Warriors']+= [('Jimmy Butler III','Out')]
I.INJ['Phoenix Suns']+= [('Mark Williams','Out')]
I.INJ['Denver Nuggets']+= [('Cameron Johnson','Out')]
I.INJ['Minnesota Timberwolves']+= [('Donte DiVincenzo','Out')]
def team(t):
    tm=m.team(t); cw=tm['cw']; gp=m.R26[t]['gp']
    rows=[]
    for n,s in I.INJ[t]:
        v=I.val(n,I.W[s]); g=I.P[n][0]
        if v['full']<=0: v['O']=v['D']=0
        inc=cw*min(1,g/gp)+(1-cw)*(1-m.A[10])*PRIOR_G.get(n,0)/82
        v.update(status=s,inc=inc,g=g,gp=gp); rows.append(v)
    neff=sum(r['w'] for r in rows if r['full']*r['inc']>=0.75)
    mult=min(1.30,1+0.15*max(0,neff-1))
    O=sum(r['O']*r['w']*r['inc'] for r in rows)*mult; D=sum(r['D']*r['w']*r['inc'] for r in rows)*mult
    return O,D,mult,rows,cw
res={}
for a,h in I.GAMES:
    print(f"\n{a} @ {h}")
    for t in (a,h):
        O,D,mult,rows,cw=team(t); old=I.team(t); res[t]=-(O+D)
        print(f"  {t:24s} NEW {-(O+D):+.1f} (old {-(old[0]+old[1]):+.1f}) cw {cw:.2f}")
        for r in rows:
            print(f"     {r['name']:20s} {r['status']:12s} full {r['full']:+.2f} inc {r['inc']:.2f} (G {r['g']}/{r['gp']}, prior G {PRIOR_G.get(r['name'],0)}) -> {r['full']*r['w']*r['inc'] if r['full']>0 else 0:.2f}")
json.dump(res,open('work/adj1030b.json','w'))

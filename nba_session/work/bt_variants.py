import sys, json, math, statistics as st
sys.path.insert(0,'work')
import backtest_roster as B
import proster as PR
rm=lambda L: math.sqrt(sum(v*v for v in L)/len(L))
def run(params,so,sd,mixold=0.0):
    RT={}
    for t in B.m.R26:
        O=D=MP=0
        for n,p in PR.S['27'].items():
            if t in p['teams']:
                mp=p['teams'][t][2]; o,d,_=PR.prior(n,'27',*params); O+=mp*o; D+=mp*d; MP+=mp
        RT[t]=(O/MP*5*so,D/MP*5*sd)
    B.RT=RT
    em=[];tp=[]
    for x in B.res:
        ra,rh=B.proj(x['aw'],x['hm'],'ros'); oa,oh=x['old']
        a=(1-mixold)*ra+mixold*oa; h=(1-mixold)*rh+mixold*oh
        em.append((a-h)-(x['A']-x['H'])); tp+= [a-x['A'],h-x['H']]
    return rm(em),rm(tp)
for params,so,sd,mix in [((800,-1.5,-0.5,1,-2,-0.5),0.92,0.95,0),((1500,-1.5,-0.5,1,-2,-0.5),1.06,1.13,0),((800,-1.5,-0.5,1,-2,-0.5),1.1,1.1,0),
                          ((800,-1.5,-0.5,0,-2,-0.5),0.92,0.95,0),((300,-1.5,-0.5,1,-2,-0.5),0.85,0.85,0),((800,-1.5,-0.5,1,-2,-0.5),0.92,0.95,0.3),((800,-1.5,-0.5,1,-2,-0.5),0.92,0.95,0.5)]:
    print(params,so,sd,'mix old',mix,'-> margin %.2f team pts %.2f'%run(params,so,sd,mix))

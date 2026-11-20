import sys, json; sys.path.insert(0,'work')
from engine import Model, N
m=Model('in14/nba.xlsx'); A=m.A
NV=json.load(open('work/novig1030.json'))
FULL={'CHA':'Charlotte Hornets','WAS':'Washington Wizards','CHI':'Chicago Bulls','BOS':'Boston Celtics','ORL':'Orlando Magic','TOR':'Toronto Raptors',
 'NYK':'New York Knicks','PHI':'Philadelphia 76ers','DET':'Detroit Pistons','BKN':'Brooklyn Nets','IND':'Indiana Pacers','MIA':'Miami Heat',
 'LAC':'LA Clippers','MIN':'Minnesota Timberwolves','HOU':'Houston Rockets','DAL':'Dallas Mavericks','LAL':'Los Angeles Lakers','GS':'Golden State Warriors','GSW':'Golden State Warriors',
 'DEN':'Denver Nuggets','PHX':'Phoenix Suns'}
ADJ={'Washington Wizards':-1.6,'Chicago Bulls':-0.7,'Detroit Pistons':-4.9,'Philadelphia 76ers':-1.5,'Orlando Magic':-6.4,'Toronto Raptors':-5.7,
 'Houston Rockets':-5.3,'Dallas Mavericks':-0.5,'Indiana Pacers':-7.5,'Minnesota Timberwolves':-4.4,'Golden State Warriors':-0.6}
def am(p): return round(-100*p/(1-p)) if p>0.5 else (round(100*(1-p)/p) if p<0.5 else 100)
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
ms,ts=A[14],A[15]; import math; tsd=math.sqrt((ms**2+ts**2)/4)
def wlp(mean,sd,cut):
    if abs(cut-round(cut))<1e-6:
        w=1-N((cut+0.5-mean)/sd); l=N((cut-0.5-mean)/sd); return w,l
    w=1-N((cut-mean)/sd); return w,1-w
legs=[]; games=[]
for g in NV:
    aw,hm=FULL[g['away']],FULL[g['home']]
    aa,ha=ADJ.get(aw,0),ADJ.get(hm,0)
    ap,hp,acw,hcw=m.project(aw,hm,aa,ha)
    ap0,hp0,_,_=m.project(aw,hm,0,0)
    mg,tot=ap-hp,ap+hp
    tt=list(g['tt'].items())
    def main(lad): return min(lad,key=lambda x:abs(x['over_p']-x['under_p']))
    atl,htl=main(tt[0][1]),main(tt[1][1])
    sa,sh=g['away'],g['home']; s=g['spread']; t=g['total']; ml=g['ml']
    games.append(dict(game=f"{sa} @ {sh}",aw=aw,hm=hm,ap=ap,hp=hp,ap0=ap0,hp0=hp0,aa=aa,ha=ha,mkt_margin=-s['away_line'],mkt_total=t['line'],atl=atl['line'],htl=htl['line']))
    L=[('ML',sa,f"{sa} ML",(mg,ms,0.0),ml['away_p'],ml['home_p'],None,'away'),
       ('ML',sh,f"{sh} ML",(-mg,ms,0.0),ml['home_p'],ml['away_p'],None,'home'),
       ('Spread',sa,f"{sa} {s['away_line']:+g}",(mg,ms,-s['away_line']),s['away_p'],s['home_p'],mg+s['away_line'],'away'),
       ('Spread',sh,f"{sh} {s['home_line']:+g}",(-mg,ms,-s['home_line']),s['home_p'],s['away_p'],-mg+s['home_line'],'home'),
       ('Total','O',f"Over {t['line']}",(tot,ts,t['line']),t['over_p'],t['under_p'],tot-t['line'],None),
       ('Total','U',f"Under {t['line']}",(-tot,ts,-t['line']),t['under_p'],t['over_p'],t['line']-tot,None),
       ('TT',sa+'O',f"{sa} TT o{atl['line']}",(ap,tsd,atl['line']),atl['over_p'],atl['under_p'],ap-atl['line'],'away'),
       ('TT',sa+'U',f"{sa} TT u{atl['line']}",(-ap,tsd,-atl['line']),atl['under_p'],atl['over_p'],atl['line']-ap,'away'),
       ('TT',sh+'O',f"{sh} TT o{htl['line']}",(hp,tsd,htl['line']),htl['over_p'],htl['under_p'],hp-htl['line'],'home'),
       ('TT',sh+'U',f"{sh} TT u{htl['line']}",(-hp,tsd,-htl['line']),htl['under_p'],htl['over_p'],htl['line']-hp,'home')]
    for mk,key,lab,(mean,sd,cut),p,pp,gap,side in L:
        w,l=wlp(mean,sd,cut) if mk!='ML' else (1-N(-mean/sd),N(-mean/sd))
        model=w/(w+l); o,oo=am(p),am(pp)
        nv=imp(o)/(imp(o)+imp(oo)); edge=model-nv; ev=w*dec(o)-l
        kelly=max(0,ev/dec(o)); units=kelly*A[18]*A[19]
        card= edge>=A[16] and ev>0 and model<=A[17]
        legs.append(dict(game=f"{sa} @ {sh}",mk=mk,key=key,lab=lab,price=p,odds=o,model=model,nv=nv,edge=edge,ev=ev,units=units,card=card,gap=gap,side=side,team=(sa if side=='away' else sh) if side else None,
                         ruleA= gap is not None and 3<=gap<=6, ruleB= model>=0.60 and -115<=o<=115, ruleC= lab.startswith('Under') or ' TT u' in lab and 0.55<=model<=0.65))
# Rule C fix: Under with model 55-65
for x in legs:
    x['ruleC']= (x['lab'].startswith('Under') or ' TT u' in x['lab']) and 0.55<=x['model']<=0.65
    x['ruleD']= x['card'] and x['lab'].startswith('Under')
# Rule E: card spread + own TT over positive edge
for x in legs:
    x['ruleE']=False
    if x['mk']=='Spread' and x['card']:
        own=[y for y in legs if y['game']==x['game'] and y['mk']=='TT' and y['key']==x['team']+'O']
        x['ruleE']= bool(own) and own[0]['edge']>0
json.dump(dict(games=games,legs=legs),open('work/run1030.json','w'),indent=1,default=float)
for gm in games:
    print(f"\n{gm['game']}: proj {gm['ap']:.1f}-{gm['hp']:.1f} (no inj {gm['ap0']:.1f}-{gm['hp0']:.1f}) adj {gm['aa']}/{gm['ha']} | model margin(away) {gm['ap']-gm['hp']:+.1f} mkt {gm['mkt_margin']:+.1f} | total {gm['ap']+gm['hp']:.1f} line {gm['mkt_total']} | TT lines {gm['atl']}/{gm['htl']}")
    for x in [y for y in legs if y['game']==gm['game']]:
        tags=''.join(t for t,f in [('CARD ',x['card']),('A',x['ruleA']),('B',x['ruleB']),('C',x['ruleC']),('D',x['ruleD']),('E',x['ruleE'])] if f)
        gs='' if x['gap'] is None else f"{x['gap']:+5.1f}"
        print(f"   {x['lab']:20s} {x['odds']:+5d} model {x['model']*100:5.1f} nv {x['nv']*100:5.1f} edge {x['edge']*100:+5.1f} EV {x['ev']*100:+5.1f} u {x['units']:4.1f} gap {gs:6s} {tags}")

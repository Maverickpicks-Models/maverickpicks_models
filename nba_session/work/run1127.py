import sys, json, math
sys.path.insert(0,'work')
from prod import Prod, nm, N
m=Prod('in1125/s3.xlsx'); A=m.A
exec(open('work/outs_1127.py').read())
OK={nm(k):v for k,v in OUTS.items() if v>0}
keys={p['key']:p for p in m.players}
print('outs in PlayerRatings:',sorted(p['name']+'('+p['team'][:3]+f",{p['mpg']:.0f}mpg)" for k,p in keys.items() if k in OK))
print('not on any roster (no 2026-27 minutes):',[k for k in OK if k not in keys])
B2B=set()   # no games on Thanksgiving 11/26
# Novig 6:24-6:34 PM (user screenshots); team totals = middle line shown
G=[('Miami Heat','New York Knicks',(2.5,.475,.535),(221.5,.53,.48),(.43,.575),(111.5,.47,.585),(114.5,.445,.60)),
('Philadelphia 76ers','Indiana Pacers',(-3.5,.495,.51),(228.5,.475,.53),(.61,.395),(119.5,.435,.67),(115.5,.415,.625)),
('Milwaukee Bucks','Detroit Pistons',(9.5,.48,.525),(219.5,.50,.51),(.22,.785),(103.5,.56,.48),(116.5,.46,.585)),
('Brooklyn Nets','Toronto Raptors',(9.5,.515,.49),(218.5,.495,.515),(.24,.765),(105.5,.48,.56),(116.5,.43,.62)),
('Atlanta Hawks','Boston Celtics',(8.5,.475,.53),(225.5,.50,.51),(.24,.77),(105.5,.60,.455),(117.5,.52,.53)),
('Memphis Grizzlies','Minnesota Timberwolves',(2.5,.49,.515),(219.5,.53,.475),(.42,.585),(109.5,.485,.535),(113.5,.46,.60)),
('Dallas Mavericks','Phoenix Suns',(3.5,.52,.485),(225.5,.515,.49),(.425,.58),(111.5,.535,.495),(114.5,.57,.575)),
('Denver Nuggets','Utah Jazz',(-9.5,.505,.505),(232.5,.505,.505),(.78,.225),(119.5,.575,.445),(108.5,.625,.425)),
('Golden State Warriors','Portland Trail Blazers',(7.5,.485,.52),(216.5,.495,.51),(.275,.73),(106.5,.455,.60),(116.5,.39,.675)),
('New Orleans Pelicans','LA Clippers',(2.5,.515,.49),(230.5,.495,.515),(.455,.555),(112.5,.59,.465),(116.5,.485,.54)),
('Los Angeles Lakers','San Antonio Spurs',(6.5,.535,.475),(225.5,.525,.49),(.35,.655),(110.5,.50,.515),(115.5,.525,.505))]
def am(p): return round(-100*p/(1-p)) if p>0.5 else (round(100*(1-p)/p) if p<0.5 else 100)
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
ms,ts=A[14],A[15]; tsd=math.sqrt((ms**2+ts**2)/4)
def wl(mean,sd,cut):
    if abs(cut-round(cut))<1e-6: return 1-N((cut+.5-mean)/sd), N((cut-.5-mean)/sd)
    w=1-N((cut-mean)/sd); return w,1-w
out=[]
for aw,hm,sp,tot,ml,att,htt in G:
    ap,hp,acw,hcw=m.project(aw,hm,OK,aw in B2B,hm in B2B)
    ap0,hp0,_,_=m.project(aw,hm,{},aw in B2B,hm in B2B)
    mg=ap-hp; mkt_m=-sp[0]
    legs=[]
    spec=[('ML',f'{aw} ML',(mg,ms,None),ml[0],ml[1],'away'),('ML',f'{hm} ML',(-mg,ms,None),ml[1],ml[0],'home'),
      ('Spread',f'{aw} {sp[0]:+g}',(mg,ms,-sp[0]),sp[1],sp[2],'away'),('Spread',f'{hm} {-sp[0]:+g}',(-mg,ms,sp[0]),sp[2],sp[1],'home'),
      ('Total',f'Over {tot[0]}',(ap+hp,ts,tot[0]),tot[1],tot[2],None),('Total',f'Under {tot[0]}',(-(ap+hp),ts,-tot[0]),tot[2],tot[1],None),
      ]+([] if att is None else [('TT',f'{aw} TT Over {att[0]}',(ap,tsd,att[0]),att[1],att[2],'away'),('TT',f'{aw} TT Under {att[0]}',(-ap,tsd,-att[0]),att[2],att[1],'away'),
      ('TT',f'{hm} TT Over {htt[0]}',(hp,tsd,htt[0]),htt[1],htt[2],'home'),('TT',f'{hm} TT Under {htt[0]}',(-hp,tsd,-htt[0]),htt[2],htt[1],'home')])
    for mk,lab,(mean,sd,cut),p,pp,side in spec:
        o,oo=am(p),am(pp)
        if mk=='ML': w,l=1-N(-mean/sd),N(-mean/sd)
        else: w,l=wl(mean,sd,cut)
        model=w/(w+l); nv=imp(o)/(imp(o)+imp(oo)); ev=w*dec(o)-l; vig=imp(o)+imp(oo)-1
        card= model-nv>=A[16] and ev>0 and model<=A[17] and vig<=0.11
        kelly=max(0,ev/dec(o)); units=kelly*A[18]*A[19]
        legs.append(dict(mk=mk,lab=lab,price=p,odds=o,model=model,nv=nv,edge=model-nv,ev=ev,units=units,card=card,vig=vig,side=side,fav=o<0))
    disT=abs(ap+hp-tot[0]); disM=abs(mg-mkt_m)
    out.append(dict(aw=aw,hm=hm,ap=ap,hp=hp,ap0=ap0,hp0=hp0,acw=acw,hcw=hcw,sp=sp,tot=tot,ml=ml,att=att,htt=htt,legs=legs,disT=disT,disM=disM,b2b=(aw in B2B,hm in B2B)))
    print(f"\n{aw} @ {hm}: proj {ap:.1f}-{hp:.1f} (no inj {ap0:.1f}-{hp0:.1f}) margin {mg:+.1f} vs mkt {mkt_m:+.1f} (diff {disM:.1f}) | total {ap+hp:.1f} vs {tot[0]} (diff {disT:.1f}) | B2B {aw in B2B}/{hm in B2B}")
    for x in legs:
        flag=('CARD ' if x['card'] else '     ')
        print(f"   {flag}{x['lab']:38s} {x['price']*100:5.1f}c {x['odds']:+5d} model {x['model']*100:5.1f} nv {x['nv']*100:5.1f} edge {x['edge']*100:+5.1f} vig {x['vig']*100:4.1f}")
json.dump(out,open('work/run1127.json','w'),indent=1)

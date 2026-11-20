import sys, json, math
sys.path.insert(0,'work')
from prod import Prod, nm, N
m=Prod('in1111c/s.xlsx'); A=m.A
OUTS={'Paul George':1,'Devin Carter':1,'Amari Williams':1,
 'Scottie Barnes':1,'Nate Bittle':1,'Trayce Jackson-Davis':1,'Kawhi Leonard':1,
 'Sam Merrill':1,"Nae'Qwan Tomlin":1,'Khalifa Diop':1,'Jaylon Tyson':.5,'Josh Hart':.5,
 'Tyrese Haliburton':1,'Ben Sheppard':1,'Johnny Furphy':1,'T.J. McConnell':.5,
 'Reece Beekman':1,'Justin Champagnie':1,'Tristan Vukcevic':1,'Jamir Watkins':1,
 'Nolan Traore':.5,'Trendon Watford':1,'Yves Missi':1,
 'Julian Strawther':1,'Quinten Post':1,'Richie Saunders':1,'Scotty Pippen Jr.':1,'Isaiah Stewart':.5,
 'Quentin Grimes':.5,'Tyler Herro':.5,
 'Tobias Harris':1,'Jayden Quaintance':1,'Devin Vassell':.5,'Tobe Awaka':.5,'Zach Collins':.5,'Norman Powell':.5,
 'Tristan da Silva':.5,'Jonathan Isaac':1,'Jalen Suggs':1,'Paolo Banchero':1,'Noah Penda':1,'Izaiyah Nelson':1,
 'Keyonte George':.75,'Lauri Markkanen':.75,'Jusuf Nurkic':1,'Jaren Jackson Jr.':1,
 'Gary Payton II':1,'Brandon Williams':1,'Kristaps Porzingis':1,'Moses Moody':1,'Jimmy Butler III':1,'Will Richard':.5,
 'Clint Capela':1,'Steven Adams':1,
 'Chet Holmgren':1,'Jalen Williams':1,'Cason Wallace':1,'Jaylin Williams':.75,'Nikola Topic':1,'Thomas Sorber':1,
 'Vit Krejci':1,'Ja Morant':1,'Shaedon Sharpe':1,'Caleb Youngblood':.5}
OK={nm(k):v for k,v in OUTS.items() if v>0}
keys={p['key']:p for p in m.players}
print('outs in PlayerRatings:',sorted(p['name']+'('+p['team'][:3]+f",{p['mpg']:.0f}mpg)" for k,p in keys.items() if k in OK))
print('not on any roster (no 2026-27 minutes):',[k for k in OK if k not in keys])
B2B={'Boston Celtics','New York Knicks','Milwaukee Bucks','Orlando Magic','Utah Jazz','Oklahoma City Thunder','Portland Trail Blazers'}
G=[('Boston Celtics','Toronto Raptors',(-5.5,.49,.525),(216.5,.495,.51),(.66,.345),(110.5,.545,.53),(105.5,.545,.53)),
('Cleveland Cavaliers','New York Knicks',(4.5,.475,.535),(222.5,.50,.51),(.35,.655),(109.5,.515,.55),(112.5,.57,.495)),
('Washington Wizards','Indiana Pacers',(3.5,.52,.49),(227.5,.505,.50),(.42,.585),(112.5,.525,.515),(115.5,.50,.535)),
('Brooklyn Nets','New Orleans Pelicans',(3.5,.52,.49),(228.5,.49,.515),(.41,.595),(112.5,.545,.51),(116.5,.48,.55)),
('Denver Nuggets','Memphis Grizzlies',(-3.5,.52,.49),(230.5,.505,.505),(.61,.40),(116.5,.54,.505),(112.5,.565,.495)),
('Los Angeles Lakers','Milwaukee Bucks',(-14.5,.51,.495),(229.5,.495,.52),(.885,.12),(122.5,.505,.54),(108.5,.465,.58)),
('San Antonio Spurs','Chicago Bulls',(-15.5,.49,.515),(238.5,.48,.53),(.91,.10),(126.5,.54,.515),(111.5,.51,.535)),
('Orlando Magic','Utah Jazz',(-3.5,.535,.47),(214.5,.505,.505),(.63,.375),(109.5,.525,.535),(105.5,.525,.53)),
('Golden State Warriors','Houston Rockets',(6.5,.50,.51),(220.5,.485,.52),(.305,.705),(108.5,.45,.60),(113.5,.525,.535)),
('Oklahoma City Thunder','Portland Trail Blazers',(2.5,.495,.515),(224.5,.505,.505),(.435,.57),(113.5,.465,.625),(112.5,.56,.53))]
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
json.dump(out,open('work/run1111.json','w'),indent=1)

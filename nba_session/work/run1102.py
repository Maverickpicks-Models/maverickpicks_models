import sys, json, math
sys.path.insert(0,'work')
from prod import Prod, nm, N
m=Prod('lo4/s.xlsx'); A=m.A
OUTS={'Jock Landale':1,'Jalen Johnson':.5,'Mouhamed Gueye':1,'Henri Veesaar':1,
 'Mitchell Robinson':1,'Devin Carter':1,'Moses Brown':1,'Egor Demin':1,
 'Grant Williams':1,'Kon Knueppel':1,'Coby White':1,'Nicolas Claxton':.75,
 'Payton Watson':.5,'Jaylon Tyson':1,"Nae'Qwan Tomlin":1,
 'Kyrie Irving':.5,'Santi Aldama':.75,'Tyler Biberovic':1,'Dereck Lively II':1,'Sergio De Larrea':1,
 'Hamidou Diallo':.5,'Spencer Jones':.5,'Julian Strawther':1,'Isaiah Joe':.5,'Jalen Duren':1,
 'Stephen Curry':1,'Draymond Green':1,'Kristaps Porzingis':1,'Moses Moody':1,'Jimmy Butler III':1,
 'Clint Capela':.5,'Reed Sheppard':.5,'Steven Adams':1,
 'Obi Toppin':1,'Ivica Zubac':1,'T.J. McConnell':1,'Tyrese Haliburton':1,'Ben Sheppard':1,'Johnny Furphy':1,
 'Brandon Ingram':1,'Yanic Konan Niederhauser':1,'Bradley Beal':1,'Max Strus':1,'Jordan Miller':1,
 'Adou Thiero':1,'Ziaire Williams':1,'Scotty Pippen Jr.':.75,'Quinten Post':.5,
 'Anthony Edwards':1,'Donte DiVincenzo':1,'Jordan Poole':1,'Yves Missi':1,'Jose Alvarado':.5,
 'Nikola Topic':1,'Thomas Sorber':1,'Chet Holmgren':1,'Alex Caruso':1,'Cason Wallace':1,'Jalen Williams':1,
 'Anthony Gill':.5,'Tristan Vukcevic':1,'Alex Sarr':.5,'Justin Champagnie':1,'Jamir Watkins':1,
 'Jonathan Isaac':1,'Jalen Suggs':1,'Paolo Banchero':1,'Izaiyah Nelson':1,'Noah Penda':1,
 'Joel Embiid':.5,'Dominick Barlow':1,'Ariel Hukporti':1,
 'Dylan Cardwell':.5,'Zach LaVine':.5,'Maxime Raynaud':1,'Keegan Murray':1,'Ben Simmons':1,
 'Jaren Jackson Jr.':1,'Trey Alexander':1,'Jusuf Nurkic':1,'Tobias Harris':1,'Jayden Quaintance':1,
 'Ja Morant':1,'Shaedon Sharpe':1,'Mark Williams':1,
 'Jakob Poeltl':.5,'Kawhi Leonard':1,'Nate Bittle':1,'Tim Hardaway Jr.':.5}
OK={nm(k):v for k,v in OUTS.items() if v>0}
keys={p['key']:p for p in m.players}
print('outs in PlayerRatings:',sorted(p['name']+'('+p['team'][:3]+f",{p['mpg']:.0f}mpg)" for k,p in keys.items() if k in OK))
print('not on any roster (no 2026-27 minutes):',[k for k in OK if k not in keys])
B2B={'Boston Celtics','Orlando Magic','Brooklyn Nets','Indiana Pacers','LA Clippers','Golden State Warriors','Toronto Raptors','Los Angeles Lakers'}
G=[('Oklahoma City Thunder','Cleveland Cavaliers',(4.5,.51,.495),(229.5,.495,.51),(.39,.62),(112.5,.54,.52),(116.5,.53,.51)),
('Washington Wizards','Orlando Magic',(3.5,.53,.48),(225.5,.495,.51),(.425,.58),(112.5,.49,.575),(113.5,.55,.51)),
('Detroit Pistons','Charlotte Hornets',(-5.5,.535,.475),(210.5,.485,.52),(.68,.33),(107.5,.53,.505),(101.5,.545,.51)),
('Brooklyn Nets','New York Knicks',(14.5,.50,.505),(218.5,.52,.485),(.12,.885),(102.5,.505,.535),(117.5,.52,.535)),
('Chicago Bulls','Philadelphia 76ers',(9.5,.50,.51),(238.5,.52,.485),(.185,.82),None,None),
('Atlanta Hawks','Indiana Pacers',(-9.5,.495,.515),(227.5,.51,.505),(.77,.235),(119.5,.495,.55),(109.5,.50,.53)),
('Sacramento Kings','Dallas Mavericks',(8.5,.515,.495),(231.5,.495,.51),(.25,.755),(111.5,.53,.505),(120.5,.51,.545)),
('Milwaukee Bucks','Minnesota Timberwolves',(10.5,.515,.495),(229.5,.535,.47),(.22,.785),(110.5,.51,.54),(122.5,.455,.61)),
('New Orleans Pelicans','Memphis Grizzlies',(5.5,.49,.515),(231.5,.49,.515),(.35,.655),(114.5,.47,.585),(118.5,.545,.515)),
('Boston Celtics','Houston Rockets',(4.5,.50,.51),(215.5,.505,.50),(.375,.63),(106.5,.505,.555),(110.5,.52,.545)),
('Utah Jazz','San Antonio Spurs',(16.5,.52,.485),(229.5,.49,.52),(.115,.89),(106.5,.52,.53),(122.5,.535,.50)),
('Portland Trail Blazers','Denver Nuggets',(4.5,.51,.495),(230.5,.535,.47),(.385,.62),(113.5,.54,.515),(117.5,.54,.53)),
('Miami Heat','Los Angeles Lakers',(2.5,.52,.485),(237.5,.47,.535),(.44,.565),(118.5,.50,.55),(119.5,.51,.53)),
('Phoenix Suns','Golden State Warriors',(3.5,.535,.47),(226.5,.51,.495),(.44,.57),(112.5,.525,.52),(114.5,.545,.505)),
('Toronto Raptors','LA Clippers',(-3.5,.535,.475),(219.5,.515,.50),(.625,.38),(111.5,.54,.51),(107.5,.53,.52))]
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
json.dump(out,open('work/run1102.json','w'),indent=1)

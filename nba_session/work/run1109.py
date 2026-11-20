import sys, json, math
sys.path.insert(0,'work')
from prod import Prod, nm, N
m=Prod('in1108/s.xlsx'); A=m.A
OUTS={'Jarrett Allen':.5,'Sam Merrill':1,"Nae'Qwan Tomlin":1,'Jaylon Tyson':1,
 'Moussa Diabate':.5,'Kon Knueppel':1,'Brandon Miller':1,'Dennis Schroder':1,'Grant Williams':1,
 'Luka Doncic':.5,'Keshon Gilbert':1,'Mouhamed Gueye':1,'Jock Landale':.5,'Asa Newell':1,'Henri Veesaar':1,
 'Reece Beekman':1,'Justin Champagnie':1,'Tristan Vukcevic':1,'Jamir Watkins':1,'Anthony Davis':.5,'Jalen Duren':1,'Isaiah Joe':1,
 'Scotty Pippen Jr.':1,'Isaiah Stewart':1,'Scottie Barnes':.5,'Nate Bittle':1,'Kawhi Leonard':1,'Immanuel Quickley':.5,
 'Tarik Biberovic':1,'Sergio de Larrea':1,'Dereck Lively II':1,'Tyrese Haliburton':1,'T.J. McConnell':1,'Johnny Furphy':1,'Ben Sheppard':1,
 'Julian Strawther':1,'Spencer Jones':1,'Steven Adams':1,'Clint Capela':1,'Tobias Harris':1,'Jayden Quaintance':1,
 'Mark Williams':1,'Rasheer Fleming':.5,'Jordan Goodwin':.5,'Yves Missi':1,
 'Jimmy Butler III':1,'Moses Moody':1,'Kristaps Porzingis':1,'Gary Payton II':.5,'Gui Santos':.5}
OK={nm(k):v for k,v in OUTS.items() if v>0}
keys={p['key']:p for p in m.players}
print('outs in PlayerRatings:',sorted(p['name']+'('+p['team'][:3]+f",{p['mpg']:.0f}mpg)" for k,p in keys.items() if k in OK))
print('not on any roster (no 2026-27 minutes):',[k for k in OK if k not in keys])
B2B={'Los Angeles Lakers','Detroit Pistons','Dallas Mavericks','New Orleans Pelicans'}
G=[('Los Angeles Lakers','Atlanta Hawks',(2.5,.5,.5),(233.5,.5,.5),(.45,.55),None,None),
('Cleveland Cavaliers','Charlotte Hornets',(-8.5,.5,.5),(215.0,.5,.5),(.78,.22),None,None),
('Washington Wizards','Detroit Pistons',(9.5,.5,.5),(218.5,.5,.5),(.2,.8),None,None),
('Memphis Grizzlies','Toronto Raptors',(-2.0,.5,.5),(225.5,.5,.5),(.55,.45),None,None),
('Indiana Pacers','Dallas Mavericks',(4.5,.5,.5),(226.5,.5,.5),(.35,.65),None,None),
('Denver Nuggets','Houston Rockets',(4.0,.5,.5),(223.5,.5,.5),(.37,.63),None,None),
('San Antonio Spurs','Phoenix Suns',(-9.0,.5,.5),(226.5,.5,.5),(.78,.22),None,None),
('New Orleans Pelicans','Golden State Warriors',(11.5,.5,.5),(229.5,.5,.5),(.17,.83),None,None)]
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
json.dump(out,open('work/run1109.json','w'),indent=1)

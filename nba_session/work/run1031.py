import sys, json, math
sys.path.insert(0,'work')
from prod import Prod, nm, N
m=Prod('lo4/s.xlsx'); A=m.A
OUTS={'Shaedon Sharpe':1,'Ja Morant':1,'Chris Youngblood':1,'Robert Williams III':.5,
 'Jaren Jackson Jr.':1,'Jusuf Nurkic':1,'Trey Alexander':1,'Lauri Markkanen':.5,
 'LeBron James':1,'Joel Embiid':1,'Dominick Barlow':1,'Jabari Walker':1,'Tacko Fall':1,'Ariel Hukporti':1,'Jaylen Brown':.5,
 'Kon Knueppel':1,'Coby White':1,'Grant Williams':1,'Kylan Boswell':1,'Jordan Poole':1,'Yves Missi':1,
 'Ben Simmons':1,'Dylan Cardwell':1,'Keegan Murray':1,'Maxime Raynaud':1,'Quinten Post':.75,'Scotty Pippen Jr.':.5,'Ty Jerome':.5,
 'Jaylon Tyson':1,'Meleek Thomas':.5,"Nae'Qwan Tomlin":1,'Anthony Edwards':1,'Donte DiVincenzo':1,'Jayden Quaintance':1,'Tobias Harris':1,
 'Alperen Sengun':.5,'Reed Sheppard':.5,'Steven Adams':1,'Alex Caruso':1,'Chet Holmgren':1,'Jalen Williams':1,'Cason Wallace':1,'Nikola Topic':1,'Thomas Sorber':1}
OUTS.update({'Robert Williams III':0,'Lauri Markkanen':0,'Meleek Thomas':0,'Rudy Gobert':.5,'Stephon Castle':.5,'Reed Sheppard':1,'Alperen Sengun':0,'Fred VanVleet':1,'Jabari Walker':.5,'Tacko Fall':.5})
OK={nm(k):v for k,v in OUTS.items() if v>0}
keys={p['key']:p for p in m.players}
print('outs in PlayerRatings:',sorted(p['name']+'('+p['team'][:3]+f",{p['mpg']:.0f}mpg)" for k,p in keys.items() if k in OK))
print('not on any roster (no 2026-27 minutes):',[k for k in OK if k not in keys])
B2B={'Philadelphia 76ers','Charlotte Hornets','Minnesota Timberwolves','Houston Rockets'}
G=[ # away, home, (away spread, p_away, p_home), (total, p_over, p_under), (ml_away, ml_home), away TT (line,o,u), home TT
 ('Portland Trail Blazers','Utah Jazz',(-7.5,.475,.53),(232.5,.535,.47),(.705,.30),(120.5,.51,.51),(113.5,.51,.525)),
 ('Philadelphia 76ers','Charlotte Hornets',(1.5,.54,.47),(213.5,.49,.53),(.51,.495),(106.5,.545,.51),(107.5,.495,.57)),
 ('Atlanta Hawks','New Orleans Pelicans',(-4.5,.505,.505),(240.5,.51,.505),(.63,.38),(122.5,.525,.535),(118.5,.51,.51)),
 ('Sacramento Kings','Memphis Grizzlies',(9.5,.535,.475),(230.5,.495,.525),(.245,.765),(111.5,.50,.545),(123.5,.475,.65)),
 ('Cleveland Cavaliers','Milwaukee Bucks',(-9.5,.495,.51),(235.5,.50,.51),(.77,.235),(122.5,.535,.515),(112.5,.54,.51)),
 ('Minnesota Timberwolves','San Antonio Spurs',(12.5,.505,.50),(227.5,.515,.50),(.17,.835),(107.5,.525,.53),(120.5,.515,.54)),
 ('Oklahoma City Thunder','Houston Rockets',(2.5,.51,.50),(218.5,.525,.48),(.445,.565),(108.5,.515,.53),(111.5,.50,.555)),
]
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
      ('TT',f'{aw} TT Over {att[0]}',(ap,tsd,att[0]),att[1],att[2],'away'),('TT',f'{aw} TT Under {att[0]}',(-ap,tsd,-att[0]),att[2],att[1],'away'),
      ('TT',f'{hm} TT Over {htt[0]}',(hp,tsd,htt[0]),htt[1],htt[2],'home'),('TT',f'{hm} TT Under {htt[0]}',(-hp,tsd,-htt[0]),htt[2],htt[1],'home')]
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
json.dump(out,open('work/run1031.json','w'),indent=1)

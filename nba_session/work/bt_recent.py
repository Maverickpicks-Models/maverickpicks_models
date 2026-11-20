import sys, json, math, statistics as st, unicodedata, openpyxl
sys.path.insert(0,'work')
import proster as PR
from engine import Model, N
m=Model('in16/nba.xlsx'); A=m.A
PARAMS=(800,-1.5,-0.5,1,-2,-0.5); SO,SD=0.92,0.95; REP=(-1.5,-0.5)
def nm(s): return ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c)).lower().replace('.','')
RAT={}
for n,p in PR.S['27'].items():
    RAT[n]=PR.prior(n,'27',*PARAMS)[:2]
def team_rating(team,outs):
    O=D=B=ACT=0
    for n,p in PR.S['27'].items():
        if team not in p['teams']: continue
        G,GS,mp,_,_=p['teams'][team]
        if not G: continue
        mpg=mp/G; o,d=RAT[n]; w=1-outs.get(nm(n),0)
        O+=mpg*w*o; D+=mpg*w*d; B+=mpg; ACT+=mpg*w
    lost=B-ACT
    return (O+lost*REP[0])/B*5*SO, (D+lost*REP[1])/B*5*SD
def proj(aw,hm,outs,ab2b,hb2b):
    def t(x):
        o,d=team_rating(x,outs); return dict(o=m.LO+o,d=m.LD-d,p=m.R25[x]['p'])
    a,h=t(aw),t(hm)
    pace=m.LP+A[11]*((a['p']-m.LP)+(h['p']-m.LP))
    ra=pace/100*(a['o']+h['d']-m.LB); rh=pace/100*(h['o']+a['d']-m.LB)
    ta=-(A[13] if ab2b else 0); th=-(A[13] if hb2b else 0)
    return ra+(ta-th)/2-A[12]/2, rh+(th-ta)/2+A[12]/2
OUT={'2026-10-28':{'Pelle Larsson':.5,'Justin Champagnie':.5,'Tyrese Haliburton':.5,'Andrew Nembhard':.5,'Paolo Banchero':1,'Jalen Suggs':1,'Alperen Sengun':1,
  'Yaxel Lendeborg':.5,'Anthony Edwards':1,'Lauri Markkanen':.5,'Jaren Jackson Jr':1,'Alex Caruso':1,'Chet Holmgren':1,'Jalen Williams':1,'Ajay Mitchell':.5,'Kyrie Irving':.5,'Naji Marshall':.5},
 '2026-10-29':{'Dejounte Murray':1,'Jordan Poole':.5},
 '2026-10-30':{'Dennis Schroder':.5,'Justin Champagnie':1,'Tre Johnson':.5,'Jalen Smith':.5,'Jalen Duren':1,'Isaiah Joe':.5,'Egor Demin':1,'Jose Alvarado':1,'Jaylen Brown':.5,'Jabari Walker':1,
  'Paolo Banchero':1,'Jalen Suggs':1,'Kawhi Leonard':1,'Alperen Sengun':.5,'Reed Sheppard':1,'Marcus Smart':.5,'Steven Adams':1,'Naji Marshall':.5,'Sergio de Larrea':1,
  'Tyrese Haliburton':1,'Ivica Zubac':1,'Ben Sheppard':1,'Simone Fontecchio':.5,'Rui Hachimura':.5,'Anthony Edwards':1,'Cameron Johnson':1,'Oso Ighodaro':.5,'Ziaire Williams':.5,'Gui Santos':.75}}
OUT={d:{nm(k):v for k,v in o.items()} for d,o in OUT.items()}
# check names exist
allnames={nm(n) for n in PR.S['27']}
for d,o in OUT.items():
    miss=[k for k in o if k not in allnames]
    if miss: print('not in 26-27 data (no effect):',d,miss)
B2B={'2026-10-28':{'Detroit Pistons','New York Knicks','San Antonio Spurs','Los Angeles Lakers'},'2026-10-29':{'Cleveland Cavaliers','Atlanta Hawks','New Orleans Pelicans'},'2026-10-30':set()}
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
ms,ts=A[14],A[15]; tsd=math.sqrt((ms**2+ts**2)/4)
def wl(mean,sd,cut):
    if abs(cut-round(cut))<1e-6: return 1-N((cut+.5-mean)/sd), N((cut-.5-mean)/sd)
    w=1-N((cut-mean)/sd); return w,1-w
# games with prices: Tracking rows dated 10/28 (rows 69-80), 81-83 (10/29), 10/30 from run1030b
wb=openpyxl.load_workbook('in16/nba.xlsx',data_only=True); t=wb['Tracking']
H={t.cell(12,c).value:c for c in range(1,50) if t.cell(12,c).value}
games=[]
for r in range(69,84):
    g=lambda h: t.cell(r,H[h]).value
    d='2026-10-28' if r<=80 else '2026-10-29'
    games.append(dict(date=d,aw=g('Away'),hm=g('Home'),A=g('Away pts'),H=g('Home pts'),old=(g('Away proj'),g('Home proj')),card_old=g('Card') or '',
      mlo=(g('ML away odds'),g('ML home odds')),tl=g('Total line'),to=(g('Over odds'),g('Under odds')),asp=g('Away spread'),so=(g('Away spr odds'),g('Home spr odds')),
      atl=g('Away TT line'),ato=(g('Away TT Over'),g('Away TT Under')),htl=g('Home TT line'),hto=(g('Home TT Over'),g('Home TT Under'))))
r30=json.load(open('work/graded1030.json'))['run1030b']; S30=json.load(open('work/scores1030.json'))
for gm in r30['games']:
    L=[x for x in r30['legs'] if x['game']==gm['game']]; od={x['lab']:x['odds'] for x in L}
    A_,H_=S30[gm['game']]; asp=-gm['mkt_margin']; sa,sh=gm['game'].split(' @ ')
    fl=lambda v: f"{v:+g}"
    games.append(dict(date='2026-10-30',aw=gm['aw'],hm=gm['hm'],A=A_,H=H_,old=(gm['ap'],gm['hp']),card_old=None,
      mlo=(L[0]['odds'],L[1]['odds']),tl=gm['mkt_total'],to=(L[4]['odds'],L[5]['odds']),asp=asp,so=(L[2]['odds'],L[3]['odds']),
      atl=gm['atl'],ato=(L[6]['odds'],L[7]['odds']),htl=gm['htl'],hto=(L[8]['odds'],L[9]['odds']),legs_old=L))
def legs(g,ap,hp):
    mg=ap-hp; out=[]; A_,H_=g['A'],g['H']; T=A_+H_
    spec=[('ML','away ML',(mg,ms,None),g['mlo'][0],g['mlo'][1],A_>H_,None),('ML','home ML',(-mg,ms,None),g['mlo'][1],g['mlo'][0],H_>A_,None),
     ('Spread',f"away {g['asp']:+g}",(mg,ms,-g['asp']),g['so'][0],g['so'][1],A_-H_+g['asp'],mg+g['asp']),
     ('Spread',f"home {-g['asp']:+g}",(-mg,ms,g['asp']),g['so'][1],g['so'][0],H_-A_-g['asp'],-mg-g['asp']),
     ('Total',f"Over {g['tl']}",(ap+hp,ts,g['tl']),g['to'][0],g['to'][1],T-g['tl'],ap+hp-g['tl']),
     ('Total',f"Under {g['tl']}",(-(ap+hp),ts,-g['tl']),g['to'][1],g['to'][0],g['tl']-T,g['tl']-ap-hp),
     ('TT',f"away TT o{g['atl']}",(ap,tsd,g['atl']),g['ato'][0],g['ato'][1],A_-g['atl'],ap-g['atl']),
     ('TT',f"away TT u{g['atl']}",(-ap,tsd,-g['atl']),g['ato'][1],g['ato'][0],g['atl']-A_,g['atl']-ap),
     ('TT',f"home TT o{g['htl']}",(hp,tsd,g['htl']),g['hto'][0],g['hto'][1],H_-g['htl'],hp-g['htl']),
     ('TT',f"home TT u{g['htl']}",(-hp,tsd,-g['htl']),g['hto'][1],g['hto'][0],g['htl']-H_,g['htl']-hp)]
    for mk,lab,(mean,sd,cut),o,oo,res,gap in spec:
        if not isinstance(o,(int,float)) or not isinstance(oo,(int,float)) or not isinstance(cut if cut is not None else 0,(int,float)): continue
        vig=imp(o)+imp(oo)-1
        if vig>0.11 or vig<-0.02: continue
        if mk=='ML': w,l=1-N(-mean/sd),N(-mean/sd); won=res; push=False
        else: w,l=wl(mean,sd,cut); won=res>0; push=res==0
        model=w/(w+l); nv=imp(o)/(imp(o)+imp(oo)); ev=w*dec(o)-l
        card=model-nv>=A[16] and ev>0 and model<=A[17]
        out.append(dict(game=f"{g['aw']} @ {g['hm']}",date=g['date'],mk=mk,lab=lab,odds=o,model=model,edge=model-nv,card=card,gap=gap,won=won,push=push,
                        pl=0 if push else (dec(o) if won else -1)))
    return out
res=[]
for g in games:
    ap,hp=proj(g['aw'],g['hm'],OUT[g['date']],g['aw'] in B2B[g['date']],g['hm'] in B2B[g['date']])
    g['new']=(ap,hp); g['newlegs']=legs(g,ap,hp); g['oldlegs']=legs(g,*g['old'])
def summ(L,name):
    w=sum(x['won'] and not x['push'] for x in L); l=sum((not x['won']) and not x['push'] for x in L)
    return f"{name}: {w}-{l}, {sum(x['pl'] for x in L):+.2f}u"
def safe(legsall):
    out=[]
    for gname in dict.fromkeys(x['game'] for x in legsall):
        c=[x for x in legsall if x['game']==gname and x['card'] and x['gap'] is not None and 3<=x['gap']<=6 and x['edge']<=0.20]
        if c: out.append(max(c,key=lambda x:x['edge']))
    return out
for d in ['2026-10-28','2026-10-29','2026-10-30','ALL']:
    G=[g for g in games if d=='ALL' or g['date']==d]
    for ver in ['old','new']:
        L=[x for g in G for x in g[ver+'legs']]
        card=[x for x in L if x['card']]; sf=safe(L)
        mg=[(g[ver][0]-g[ver][1])-(g['A']-g['H']) for g in G]; tt=[(g[ver][0]+g[ver][1])-(g['A']+g['H']) for g in G]
        print(d,ver,summ(card,'card'),'|',summ(sf,'safe'),f"| margin RMSE {math.sqrt(sum(v*v for v in mg)/len(mg)):.2f} total RMSE {math.sqrt(sum(v*v for v in tt)/len(tt)):.2f}")
    mk=[(-g['asp'])-(g['A']-g['H']) for g in G]; mt=[g['tl']-(g['A']+g['H']) for g in G]
    print(d,'market margin RMSE %.2f total RMSE %.2f'%(math.sqrt(sum(v*v for v in mk)/len(mk)),math.sqrt(sum(v*v for v in mt)/len(mt))))
print()
for g in games:
    sf=safe(g['newlegs'])
    print(f"{g['date'][5:]} {g['aw'][:14]:14s}@{g['hm'][:14]:14s} act {g['A']-g['H']:+4d} T{g['A']+g['H']} | mkt {-g['asp']:+5.1f} {g['tl']} | old {g['old'][0]-g['old'][1]:+5.1f} {sum(g['old']):.0f} | new {g['new'][0]-g['new'][1]:+5.1f} {sum(g['new']):.0f} | new safe: {[(x['lab'],x['odds'],round(x['edge']*100,1),'W' if x['won'] else ('P' if x['push'] else 'L')) for x in sf]}")
json.dump(games,open('work/bt_recent.json','w'),default=str)

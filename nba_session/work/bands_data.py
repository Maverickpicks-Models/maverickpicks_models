import openpyxl,datetime,json,math
ws=openpyxl.load_workbook('out_1110/chk.xlsx',data_only=True)['Tracking']
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
def num(v): return float(v) if isinstance(v,(int,float)) else None
legs=[];skipped=[]
for r in range(13,164):
    c=lambda col: ws.cell(r,col).value
    d=c(1); an,hn=num(c(40)),num(c(41))
    if not isinstance(d,datetime.datetime) or an is None or hn is None: continue
    d=d.date(); aw,hm=c(2),c(3)
    ap,hp,acw,hcw=num(c(4)),num(c(5)),num(c(6)),num(c(7))
    era='Old team model (10/20-10/29)' if d<=datetime.date(2026,10,29) else ('Injury v2 (10/30)' if d==datetime.date(2026,10,30) else 'Roster model (10/31+)')
    card=str(c(35) or '')
    P,Q,R,S,T=num(c(16)),num(c(17)),num(c(18)),num(c(19)),num(c(20))
    U,V,W,X,Y,Z=num(c(21)),num(c(22)),num(c(23)),num(c(24)),num(c(25)),num(c(26))
    AA,AB,AC,AD,AE,AF,AG,AH=[num(c(i)) for i in range(27,35)]
    H,I,J,K=num(c(8)),num(c(9)),num(c(10)),num(c(11))
    mkt_margin=-U if U is not None else None  # away margin implied
    mg=ap-hp if ap is not None else None
    base=dict(row=r,date=str(d),aw=aw,hm=hm,era=era,ap=ap,hp=hp,cw=((acw or 0)+(hcw or 0))/2,
              disM=(mg-mkt_margin) if (mg is not None and mkt_margin is not None) else None,
              disT=(Q-P) if (Q is not None and P is not None) else None)
    def add(prop,side,model,odds,opp,line,gap,res,cardkey):
        if None in (model,odds,opp): return
        if odds==0 or opp==0: return
        vig=imp(odds)+imp(opp)-1
        if vig>0.11 or vig<-0.02: skipped.append((r,prop,odds,opp)); return
        nv=imp(odds)/(imp(odds)+imp(opp))
        ev=model*dec(odds)-(1-model)
        units=1*dec(odds) if res>0 else (-1 if res<0 else 0)
        legs.append(dict(base,prop=prop,side=side,model=model,odds=odds,nv=nv,edge=model-nv,ev=ev,
            kelly=max(0,ev/dec(odds)),line=line,gap=gap,res=res,units=units,vig=vig,fav=odds<0,
            card=(cardkey in card)))
    sgn=lambda v:(v>0)-(v<0)
    # ML
    if H is not None and J is not None and K is not None:
        add('ML Away','away',H,J,K,None,mg,sgn(an-hn),f'ML {aw}')
        add('ML Home','home',I,K,J,None,-mg,sgn(hn-an),f'ML {hm}')
    # spread (skip rows where home spread isn't the mirror of away spread)
    if U is not None and X is not None and abs(U+X)<0.01 and abs(U)<30:
        add('Spread Away','away',V,W,Z,U,mg+U,sgn(an-hn+U),f'Spread {aw}')
        add('Spread Home','home',Y,Z,W,X,-mg+X,sgn(hn-an+X),f'Spread {hm}')
    elif U is not None: skipped.append((r,'spread',U,X))
    if P is not None and R is not None:
        add('Total Over','over',R,S,T,P,Q-P,sgn(an+hn-P),'Total Over')
        add('Total Under','under',1-R,T,S,P,P-Q,sgn(P-an-hn),'Total Under')
    if AA is not None and AB is not None:
        add('Away TT Over','over',AB,AC,AD,AA,ap-AA,sgn(an-AA),f'TT {aw} Over')
        add('Away TT Under','under',1-AB,AD,AC,AA,AA-ap,sgn(AA-an),f'TT {aw} Under')
    if AE is not None and AF is not None:
        add('Home TT Over','over',AF,AG,AH,AE,hp-AE,sgn(hn-AE),f'TT {hm} Over')
        add('Home TT Under','under',1-AF,AH,AG,AE,AE-hp,sgn(AE-hn),f'TT {hm} Under')
json.dump(legs,open('work/bands_legs.json','w'))
import collections
print('legs',len(legs),'games',len(set(l['row'] for l in legs)),'skipped',len(skipped))
print(collections.Counter(l['prop'] for l in legs))
print(skipped[:12])

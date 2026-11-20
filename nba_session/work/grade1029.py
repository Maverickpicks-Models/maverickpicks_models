import openpyxl, json
wb=openpyxl.load_workbook('in13/nba.xlsx',data_only=True); t=wb['Tracking']
hdr={t.cell(12,c).value:c for c in range(1,36)}
S={81:(111,114),82:(120,132),83:(124,103)}
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
legs=[]
for r,(A,H) in S.items():
    g=lambda h: t.cell(r,hdr[h]).value
    aw,hm=g('Away'),g('Home'); sa,sh=aw.split()[-1],hm.split()[-1]
    ap,hp=g('Away proj'),g('Home proj'); card=g('Card') or ''
    T=A+H; tl=g('Total line'); asp=g('Away spread'); hsp=g('Home spread')
    print(f"{sa}@{sh} final {A}-{H} proj {ap:.1f}-{hp:.1f} margin act {A-H:+} proj {ap-hp:+.1f} mkt {-asp:+.1f} | total act {T} proj {ap+hp:.1f} line {tl}")
    print('  card:',card)
    L=[('ML',f'{sa} ML',g('ML away'),g('ML away odds'),g('ML home odds'),A>H,None,None),
       ('ML',f'{sh} ML',g('ML home'),g('ML home odds'),g('ML away odds'),H>A,None,None),
       ('Spread',f'{sa} {asp:+g}',g('Away cover %'),g('Away spr odds'),g('Home spr odds'),A-H+asp>0,(ap-hp)+asp,f'Spread {aw} {asp:+g}'),
       ('Spread',f'{sh} {hsp:+g}',g('Home cover %'),g('Home spr odds'),g('Away spr odds'),H-A+hsp>0,(hp-ap)+hsp,f'Spread {hm} {hsp:+g}'),
       ('Total',f'Over {tl}',g('Over %'),g('Over odds'),g('Under odds'),T>tl,ap+hp-tl,f'Total Over {tl}'),
       ('Total',f'Under {tl}',1-g('Over %'),g('Under odds'),g('Over odds'),T<tl,tl-ap-hp,f'Total Under {tl}'),
       ('TT',f'{sa} TT o{g("Away TT line")}',g('Away TT over %'),g('Away TT Over'),g('Away TT Under'),A>g('Away TT line'),ap-g('Away TT line'),f'TT {aw} Over {g("Away TT line")}'),
       ('TT',f'{sa} TT u{g("Away TT line")}',1-g('Away TT over %'),g('Away TT Under'),g('Away TT Over'),A<g('Away TT line'),g('Away TT line')-ap,f'TT {aw} Under {g("Away TT line")}'),
       ('TT',f'{sh} TT o{g("Home TT line")}',g('Home TT over %'),g('Home TT Over'),g('Home TT Under'),H>g('Home TT line'),hp-g('Home TT line'),f'TT {hm} Over {g("Home TT line")}'),
       ('TT',f'{sh} TT u{g("Home TT line")}',1-g('Home TT over %'),g('Home TT Under'),g('Home TT Over'),H<g('Home TT line'),g('Home TT line')-hp,f'TT {hm} Under {g("Home TT line")}')]
    for m,lab,p,o,oo,won,gap,cardlab in L:
        if not isinstance(o,(int,float)) or not isinstance(oo,(int,float)): continue
        nv=imp(o)/(imp(o)+imp(oo)); vig=imp(o)+imp(oo)-1
        carded = (cardlab and cardlab in card) or (m=='ML' and f'ML {aw if lab.startswith(sa) else hm}' in card)
        prof=dec(o) if won else -1
        legs.append(dict(r=r,m=m,lab=lab,p=p,o=o,nv=nv,edge=p-nv,ev=p*dec(o)-(1-p),gap=gap,won=won,prof=prof,card=bool(carded),vig=vig))
for x in legs:
    flag=('CARD ' if x['card'] else '     ')+('A ' if x['gap'] is not None and 3<=x['gap']<=6 else '  ')
    print(f"{flag}{x['lab']:26s} {x['o']:+5.0f} model {x['p']*100:5.1f} nv {x['nv']*100:5.1f} edge {x['edge']*100:+5.1f} gap {'' if x['gap'] is None else f'{x[chr(103)+chr(97)+chr(112)]:+.1f}':6s} vig {x['vig']*100:4.1f} {'W' if x['won'] else 'L'} {x['prof']:+.2f}")
c=[x for x in legs if x['card']]
print('CARD', sum(x['won'] for x in c),'-',sum(not x['won'] for x in c), round(sum(x['prof'] for x in c),2))
a=[x for x in legs if x['gap'] is not None and 3<=x['gap']<=6]
print('RuleA', sum(x['won'] for x in a),'-',sum(not x['won'] for x in a), round(sum(x['prof'] for x in a),2))
json.dump(legs,open('work/legs1029.json','w'),default=float)

import csv, json
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
f=lambda x: float(x.replace('%','').replace('+',''))
plays=[]; excl=[]
for r in csv.DictReader(open('work/slate_1024b.tsv'),delimiter='\t'):
    aw,hm=r['Away'],r['Home']; a,h=aw.split()[-1],hm.split()[-1]
    D,E=f(r['Away proj']),f(r['Home proj']); pm=E-D; U=f(r['Away spread']); V=f(r['Away cover %'])/100
    P,Q,R=f(r['Total line']),f(r['Total proj']),f(r['Over %'])/100
    AA,AB,AE,AF=f(r['Away TT line']),f(r['Away TT over %'])/100,f(r['Home TT line']),f(r['Home TT over %'])/100
    card=r['Card']+' |'
    o=lambda k: f(r[k])
    S=[('ML',f'{a} ML','',f(r['ML away'])/100,o('ML away odds'),o('ML home odds'),-pm,f'ML {aw}'),
       ('ML',f'{h} ML','',f(r['ML home'])/100,o('ML home odds'),o('ML away odds'),pm,f'ML {hm}'),
       ('Spread',a,f'{U:+g}',V,o('Away spr odds'),o('Home spr odds'),-pm+U,f'Spread {aw} {U:+.1f}'),
       ('Spread',h,f'{-U:+g}',1-V,o('Home spr odds'),o('Away spr odds'),pm-U,f'Spread {hm} {-U:+.1f}'),
       ('Total','Over',f'{P:g}',R,o('Over odds'),o('Under odds'),Q-P,'TOTO'),
       ('Total','Under',f'{P:g}',1-R,o('Under odds'),o('Over odds'),P-Q,'TOTU'),
       ('TT',f'{a} TT Over',f'{AA:g}',AB,o('Away TT Over'),o('Away TT Under'),D-AA,f'TT {aw} Over {AA:.1f}'),
       ('TT',f'{a} TT Under',f'{AA:g}',1-AB,o('Away TT Under'),o('Away TT Over'),AA-D,f'TT {aw} Under {AA:.1f}'),
       ('TT',f'{h} TT Over',f'{AE:g}',AF,o('Home TT Over'),o('Home TT Under'),E-AE,f'TT {hm} Over {AE:.1f}'),
       ('TT',f'{h} TT Under',f'{AE:g}',1-AF,o('Home TT Under'),o('Home TT Over'),AE-E,f'TT {hm} Under {AE:.1f}')]
    for m,lab,line,p,od,oo,gap,key in S:
        nv=imp(od)/(imp(od)+imp(oo)); e=p-nv; ev=p*dec(od)-(1-p); hold=imp(od)+imp(oo)-1
        under = lab.endswith('Under')
        cardplay = (key in card) if key not in ('TOTO','TOTU') else (e>=.04 and ev>0 and p<=.70)
        rules=[x for x,c in [('A',3<=gap<6),('B',p>=.6 and abs(od)<=115),('C',under and .55<=p<.65),('D',m=='Total' and under and cardplay)] if c]
        if not rules: continue
        rec=dict(game=f'{a} @ {h}',away=aw,home=hm,market=m,play=lab,line=line,odds=od,model=p,edge=e,ev=ev,gap=gap,rules=rules,card=cardplay)
        why=[]
        if e<=0: why.append('negative edge')
        if p>.70: why.append('model above your 70% cap')
        if hold>.08: why.append(f'suspect price ({hold:.0%} vig)')
        (excl if why else plays).append({**rec,'why':why})
plays.sort(key=lambda x:(-len(x['rules']),-x['edge']))
json.dump(dict(plays=plays,excl=excl),open('work/ruleplays.json','w'),indent=1)
for x in plays: print(f"{x['game']:22}{x['play']:22}{x['line']:7}{x['odds']:+5.0f} {x['model']:.1%} {x['edge']:+.1%} gap {x['gap']:+.1f} {''.join(x['rules'])} card={x['card']}")
print('EXCLUDED'); [print(' ',x['game'],x['play'],x['line'],x['odds'],x['why']) for x in excl]

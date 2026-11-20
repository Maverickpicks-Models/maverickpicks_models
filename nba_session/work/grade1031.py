import json, math
S=[(112,90),(109,104),(99,121),(105,136),(136,111),(111,121),(98,119)]
D=json.load(open('work/run1031.json'))
def dec(o): return 100/-o if o<0 else o/100
allp=[]
for g,(A,H) in zip(D,S):
    T=A+H; asp=g['sp'][0]
    res={'ML':None}
    for x in g['legs']:
        lab=x['lab']
        if x['mk']=='ML': won=(A>H) if lab.startswith(g['aw']) else (H>A)
        elif x['mk']=='Spread': won=(A-H+asp>0) if lab.startswith(g['aw']) else (H-A-asp>0)
        elif x['mk']=='Total': won=(T>g['tot'][0]) if lab.startswith('Over') else (T<g['tot'][0])
        else:
            pts=A if lab.startswith(g['aw']) else H; line=float(lab.split()[-1])
            won=pts>line if ' Over ' in lab else pts<line
        x['won']=won; x['pl']=dec(x['odds']) if won else -1
    g['A'],g['H']=A,H
    c=[x for x in g['legs'] if x['card']]
    print(f"{g['aw'][:12]:12s}@{g['hm'][:12]:12s} {A}-{H} act margin {A-H:+d} T{T} | model {g['ap']-g['hp']:+.1f} {g['ap']+g['hp']:.1f} | mkt {-asp:+.1f} {g['tot'][0]} | model pts {g['ap']:.1f}/{g['hp']:.1f} | card {sum(x['won'] for x in c)}-{sum(not x['won'] for x in c)} {sum(x['pl'] for x in c):+.2f}")
    for x in c: print('     ',x['lab'],x['odds'],round(x['edge']*100,1),'W' if x['won'] else 'L')
    allp+=c
print('CARD',sum(x['won'] for x in allp),'-',sum(not x['won'] for x in allp),round(sum(x['pl'] for x in allp),2))
mg=[(g['ap']-g['hp'])-(g['A']-g['H']) for g in D]; mk=[-g['sp'][0]-(g['A']-g['H']) for g in D]
tt=[(g['ap']+g['hp'])-(g['A']+g['H']) for g in D]; mt=[g['tot'][0]-(g['A']+g['H']) for g in D]
r=lambda L: math.sqrt(sum(v*v for v in L)/len(L))
print('margin RMSE model %.1f market %.1f | total RMSE model %.1f market %.1f | mean total err model %+.1f market %+.1f'%(r(mg),r(mk),r(tt),r(mt),sum(tt)/7,sum(mt)/7))
# no-injury version margins
mg0=[(g['ap0']-g['hp0'])-(g['A']-g['H']) for g in D]; print('margin RMSE no-injury %.1f'%r(mg0))
json.dump(D,open('work/graded1031.json','w'))

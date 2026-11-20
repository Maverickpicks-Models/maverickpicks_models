import openpyxl, sys, math, json, statistics as st
wb=openpyxl.load_workbook(sys.argv[1],data_only=True); t=wb['Tracking']
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
def ab(n): return n.split()[-1]
bets=[]; games=[]; real=[]
for r in range(13,t.max_row+1):
    g={c:t[f'{c}{r}'].value for c in ['A','B','C','D','E','H','I','J','K','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN','AO','AS','AT']}
    if g['AN'] is None or g['AO'] is None: continue
    aw,hm=g['B'],g['C']; A,H=g['AN'],g['AO']; T=A+H; U=g['U']; V=g['V']
    fixed = abs(g['X']+U)>0.01
    plays=set(p.strip() for p in (g['AI'] or '').split('|'))
    sides=[
     ('ML',f"ML {aw}",g['H'],g['J'],g['K'],A>H),('ML',f"ML {hm}",g['I'],g['K'],g['J'],H>A),
     ('Spread',f"Spread {aw} {U:+g}",V,g['W'],g['Z'],A-H+U>0),('Spread',f"Spread {hm} {-U:+g}",1-V,g['Z'],g['W'],H-A-U>0),
     ('Total',f"Total Over {g['P']:g}",g['R'],g['S'],g['T'],T>g['P']),('Total',f"Total Under {g['P']:g}",1-g['R'],g['T'],g['S'],T<g['P']),
     ('TT',f"TT {aw} Over {g['AA']:g}",g['AB'],g['AC'],g['AD'],A>g['AA']),('TT',f"TT {aw} Under {g['AA']:g}",1-g['AB'],g['AD'],g['AC'],A<g['AA']),
     ('TT',f"TT {hm} Over {g['AE']:g}",g['AF'],g['AG'],g['AH'],H>g['AE']),('TT',f"TT {hm} Under {g['AE']:g}",1-g['AF'],g['AH'],g['AG'],H<g['AE']),
    ]
    for m,key,p,o,oo,won in sides:
        nv=imp(o)/(imp(o)+imp(oo)); ev=p*dec(o)-(1-p); u=max(0,ev/dec(o))*25
        rule=(p-nv)>=0.04 and ev>0 and p<=0.78
        if key in plays or rule:
            bets.append(dict(date=str(g['A'].date()),game=f"{ab(aw)}@{ab(hm)}",m=m,key=key,side=('Under' if 'Under' in key else 'Over' if 'Over' in key else 'Dog' if o>0 else 'Fav'),
              odds=o,p=p,edge=p-nv,ev=ev,u=u,won=won,carded=key in plays,
              flat=dec(o) if won else -1.0,kelly=u*dec(o) if won else -u))
    # market vs model
    mlnv=imp(g['J'])/(imp(g['J'])+imp(g['K']))
    ovnv=imp(g['S'])/(imp(g['S'])+imp(g['T']))
    games.append(dict(date=str(g['A'].date()),game=f"{ab(aw)}@{ab(hm)}",ap=g['D'],hp=g['E'],A=A,H=H,
        mm=g['E']-g['D'],am=H-A,mkt_m=-U if True else None,tp=g['Q'],at=T,line=g['P'],
        pml=g['I'],nvml=1-mlnv,homewin=H>A,pov=g['R'],nvov=ovnv,over=T>g['P']))
    if g['AJ']: real.append(dict(game=f"{ab(aw)}@{ab(hm)}",mk=g['AJ'],side=g['AK'],odds=g['AL'],u=g['AM'],grade=g['AS'],profit=g['AT']))
json.dump(dict(bets=bets,games=games,real=real),open(sys.argv[2],'w'),indent=1)
print('games',len(games),'bets',len(bets),'carded',sum(b['carded'] for b in bets)); print('real',real)

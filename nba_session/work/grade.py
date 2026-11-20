import openpyxl, json, sys
wb=openpyxl.load_workbook(sys.argv[1],data_only=True); t=wb['Tracking']
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
rows=[]
for r in (13,14,15):
    g={c:t[f'{c}{r}'].value for c in ['B','C','D','E','H','I','J','K','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AN','AO','AP']}
    aw,hm=g['B'],g['C']; A,H=g['AN'],g['AO']; T=A+H
    def short(n): return n.split()[-1]
    mk=[
     ('ML',f"{short(aw)} ML",g['H'],g['J'],g['I'],g['K'],A>H),
     ('ML',f"{short(hm)} ML",g['I'],g['K'],g['H'],g['J'],H>A),
     ('Spread',f"{short(aw)} {g['U']:+}",g['V'],g['W'],g['Y'],g['Z'],A-H+g['U']>0),
     ('Spread',f"{short(hm)} {g['X']:+}",g['Y'],g['Z'],g['V'],g['W'],H-A+g['X']>0),
     ('Total',f"Over {g['P']}",g['R'],g['S'],1-g['R'],g['T'],T>g['P']),
     ('Total',f"Under {g['P']}",1-g['R'],g['T'],g['R'],g['S'],T<g['P']),
     ('TT Away',f"{short(aw)} TT o{g['AA']}",g['AB'],g['AC'],1-g['AB'],g['AD'],A>g['AA']),
     ('TT Away',f"{short(aw)} TT u{g['AA']}",1-g['AB'],g['AD'],g['AB'],g['AC'],A<g['AA']),
     ('TT Home',f"{short(hm)} TT o{g['AE']}",g['AF'],g['AG'],1-g['AF'],g['AH'],H>g['AE']),
     ('TT Home',f"{short(hm)} TT u{g['AE']}",1-g['AF'],g['AH'],g['AF'],g['AG'],H<g['AE']),
    ]
    for m,label,p,o,_,oo,won in mk:
        nv=imp(o)/(imp(o)+imp(oo)); edge=p-nv; ev=p*dec(o)-(1-p)
        kelly=max(0,ev/dec(o)); units=kelly*0.25*100
        play= edge>=0.04 and ev>0 and p<=0.78
        profit=(units*dec(o) if won else -units)
        rows.append(dict(game=f"{short(aw)} @ {short(hm)}",final=f"{A}-{H}",market=m,bet=label,odds=o,model=p,novig=nv,edge=edge,ev=ev,units=units,play=play,won=won,profit=profit,flat=(dec(o) if won else -1)))
    rows.append(dict(game=f"{short(aw)} @ {short(hm)}",info=dict(ap=g['D'],hp=g['E'],tp=g['Q'],A=A,H=H)))
json.dump(rows,open(sys.argv[2],'w'),indent=1)
for x in rows:
    if 'info' in x: print(x); continue
    print(f"{x['game']:16}{x['bet']:22}{x['odds']:>5} m{x['model']:.3f} nv{x['novig']:.3f} e{x['edge']:+.3f} ev{x['ev']:+.3f} u{x['units']:5.2f} {'PLAY' if x['play'] else '    '} {'W' if x['won'] else 'L'} {x['profit']:+.2f}")

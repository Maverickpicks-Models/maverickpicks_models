import openpyxl, sys, pandas as pd
wb=openpyxl.load_workbook(sys.argv[1],data_only=True); t=wb['Tracking']
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def dec(o): return 100/-o if o<0 else o/100
L=[]
for r in range(13,313):
    g={c:t[f'{c}{r}'].value for c in ['A','B','C','D','E','H','I','J','K','P','Q','R','S','T','U','V','W','Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AN','AO']}
    if g['A'] is None or g['AN'] is None or g['AO'] is None: continue
    A,H=g['AN'],g['AO']; U=g['U']; V=g['V']; card=(g['AI'] or '')+' |'
    aw,hm=g['B'],g['C']; pm=g['E']-g['D']  # proj home margin
    gid=f"{g['A'].date()} {aw.split()[-1]}@{hm.split()[-1]}"
    def leg(market,side,ha,fd,p,o,oo,margin,gap,line,key):
        if not all(isinstance(x,(int,float)) for x in (p,o,oo)): return
        nv=imp(o)/(imp(o)+imp(oo))
        L.append(dict(game=gid,date=str(g['A'].date()),market=market,side=side,home_away=ha,fav_dog=fd,
            odds=o,model_p=p,novig_p=nv,edge=p-nv,ev=p*dec(o)-(1-p),gap=gap,line=line,
            carded=(key+' |') in card,win=margin>0,push=margin==0,
            profit=(dec(o) if margin>0 else 0 if margin==0 else -1.0),
            mkt_ev=nv*dec(o)-(1-nv),mkt_var=nv*(1-nv)*(dec(o)+1)**2))
    fav_home = U>0  # away getting points => home favorite
    # ML
    leg('ML','Away','Away','Dog' if g['J']>g['K'] else 'Fav',g['H'],g['J'],g['K'],A-H,-pm,None,f"ML {aw}")
    leg('ML','Home','Home','Fav' if g['K']<g['J'] else 'Dog',g['I'],g['K'],g['J'],H-A,pm,None,f"ML {hm}")
    # Spread (home line = -U)
    leg('Spread','Away','Away','Dog' if U>0 else 'Fav',V,g['W'],g['Z'],A-H+U,-pm+U,abs(U),f"Spread {aw} {U:+.1f}")
    leg('Spread','Home','Home','Fav' if U>0 else 'Dog',1-V,g['Z'],g['W'],H-A-U,pm-U,abs(U),f"Spread {hm} {-U:+.1f}")
    # Totals
    leg('Total','Over','—','—',g['R'],g['S'],g['T'],A+H-g['P'],g['Q']-g['P'],g['P'],f"Total Over {g['P']:.1f}")
    leg('Total','Under','—','—',1-g['R'],g['T'],g['S'],g['P']-A-H,g['P']-g['Q'],g['P'],f"Total Under {g['P']:.1f}")
    # Team totals
    leg('TT','Over','Away','—',g['AB'],g['AC'],g['AD'],A-g['AA'],g['D']-g['AA'],g['AA'],f"TT {aw} Over {g['AA']:.1f}")
    leg('TT','Under','Away','—',1-g['AB'],g['AD'],g['AC'],g['AA']-A,g['AA']-g['D'],g['AA'],f"TT {aw} Under {g['AA']:.1f}")
    leg('TT','Over','Home','—',g['AF'],g['AG'],g['AH'],H-g['AE'],g['E']-g['AE'],g['AE'],f"TT {hm} Over {g['AE']:.1f}")
    leg('TT','Under','Home','—',1-g['AF'],g['AH'],g['AG'],g['AE']-H,g['AE']-g['E'],g['AE'],f"TT {hm} Under {g['AE']:.1f}")
df=pd.DataFrame(L); df.to_pickle(sys.argv[2])
print(df.shape, df.game.nunique(), 'carded',df.carded.sum(), 'carded W',df[df.carded].win.sum(),'flat',round(df[df.carded].profit.sum(),2))
print(df.groupby('market').size())

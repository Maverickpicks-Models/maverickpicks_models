import openpyxl, json, sys, re
ws=openpyxl.load_workbook(sys.argv[1],data_only=True).active
def am(p):
    return round(-100*p/(1-p)) if p>0.5 else round(100*(1-p)/p) if p<0.5 else 100
games=[]
for c in range(1,ws.max_column+1):
    col=[ws.cell(r,c).value for r in range(1,ws.max_row+1)]
    col=[v for v in col if v is not None]
    away,home=col[0],col[4]
    i=7
    g=dict(away=away,home=home)
    g['spread']=dict(away_line=col[i],away_p=col[i+1],home_line=col[i+2],home_p=col[i+3]); i+=4
    g['total']=dict(line=float(col[i].split()[1]),over_p=col[i+1],under_p=col[i+3]); i+=4
    g['ml']=dict(away_p=col[i],home_p=col[i+1]); i+=2
    # team totals
    tts={}; cur=None; j=i
    while j<len(col):
        v=col[j]
        if isinstance(v,str) and v.endswith(': Team Total'):
            cur=v.split(':')[0]; tts[cur]=[]; j+=1; continue
        if isinstance(v,str) and re.match(r'^O \d',v):
            line=float(v.split()[1]); op=col[j+1]; up=col[j+3]
            assert col[j+2]==f'U {v.split()[1]}', (c,v,col[j+2])
            tts[cur].append(dict(line=line,over_p=op,under_p=up)); j+=4; continue
        j+=1
    g['tt']=tts; games.append(g)
json.dump(games,open(sys.argv[2],'w'),indent=1)
for g in games:
    s,t,m=g['spread'],g['total'],g['ml']
    print(f"\n{g['away']} @ {g['home']}")
    print(f"  ML      {g['away']} {m['away_p']:.3f} ({am(m['away_p']):+d})  {g['home']} {m['home_p']:.3f} ({am(m['home_p']):+d})  sum {m['away_p']+m['home_p']:.3f}")
    print(f"  Spread  {g['away']} {s['away_line']:+g} {s['away_p']:.3f} ({am(s['away_p']):+d})  {g['home']} {s['home_line']:+g} {s['home_p']:.3f} ({am(s['home_p']):+d})  sum {s['away_p']+s['home_p']:.3f}")
    print(f"  Total   {t['line']}  O {t['over_p']:.3f} ({am(t['over_p']):+d})  U {t['under_p']:.3f} ({am(t['under_p']):+d})  sum {t['over_p']+t['under_p']:.3f}")
    for team,lad in g['tt'].items():
        main=min(lad,key=lambda x:abs(x['over_p']-x['under_p']))
        print(f"  TT {team:3s} ladder "+'  '.join(f"{x['line']}:{x['over_p']:.3f}/{x['under_p']:.3f}" for x in lad))
        print(f"         main {main['line']}  O {main['over_p']:.3f} ({am(main['over_p']):+d})  U {main['under_p']:.3f} ({am(main['under_p']):+d})")

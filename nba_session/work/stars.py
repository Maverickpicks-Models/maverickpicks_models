import openpyxl,json,datetime as dt,numpy as np,collections,unicodedata
def nm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().strip()
TIER_A=['Luka Doncic','Victor Wembanyama','Nikola Jokic','Shai Gilgeous-Alexander','Stephen Curry','Giannis Antetokounmpo']
TIER_B=['Cade Cunningham','Kevin Durant','Jayson Tatum','Anthony Edwards','Jalen Brunson','Donovan Mitchell','Kawhi Leonard','Joel Embiid','LeBron James','Tyrese Maxey','Devin Booker','Ja Morant','Jaylen Brown']
wb=openpyxl.load_workbook('in1111c/s.xlsx',read_only=True,data_only=True)
team_of={}; played=set(); seen=collections.Counter()
for r in wb['BoxScores'].iter_rows(min_row=2,values_only=True):
    if not r[0] or not r[3]: continue
    n=nm(r[0]); d=r[3].date() if hasattr(r[3],'date') else r[3]
    if n in [nm(x) for x in TIER_A+TIER_B]:
        seen[n]+=1; team_of[n]=r[1]
        if isinstance(r[5],(int,float)) and r[5]>0: played.add((n,d))
print('found in box scores:',dict(seen)); print('missing:',[x for x in TIER_A+TIER_B if nm(x) not in seen])
code={r[1]:r[0] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}; n2c={v:k for k,v in code.items()}
starA=collections.defaultdict(list); starB=collections.defaultdict(list)
for x in TIER_A:
    if nm(x) in team_of: starA[team_of[nm(x)]].append(nm(x))
for x in TIER_B:
    if nm(x) in team_of: starB[team_of[nm(x)]].append(nm(x))
# team box dates to know game played
G=json.load(open('work/deep_games11.json'))
S=[(98,93),(115,107),(101,114),(145,111),(123,118),(123,112),(124,119),(123,106),(108,115),(108,118)]
for g,(a,h) in zip(json.load(open('work/run1111.json')),S):
    L={x['lab']:x for x in g['legs']}
    G.append(dict(d='2026-11-11',era='roster',aw=g['aw'],hm=g['hm'],an=a,hn=h,U=g['sp'][0],P=g['tot'][0],ap=g['ap'],hp=g['hp'],
      W=L[f"{g['aw']} {g['sp'][0]:+g}"]['odds'],Z=L[f"{g['hm']} {-g['sp'][0]:+g}"]['odds']))
maxbox=max(d for _,d in played)
def dec(o): return 100/-o if o<0 else o/100
rows=[]
for g in G:
    if g['U'] is None: continue
    d=dt.date.fromisoformat(g['d'])
    if d>maxbox: continue   # need box score to know who played
    for side in ('away','home'):
        t=n2c[g['aw'] if side=='away' else g['hm']]; o=n2c[g['hm'] if side=='away' else g['aw']]
        mg=(g['an']-g['hn'])*(1 if side=='away' else -1); mkt=-g['U'] if side=='away' else g['U']; mod=(g['ap']-g['hp'])*(1 if side=='away' else -1)
        hasA=bool(starA.get(t)); A_on=any((s,d) in played for s in starA.get(t,[])); A_off=hasA and not A_on
        hasB=bool(starB.get(t)); B_on=any((s,d) in played for s in starB.get(t,[]))
        oA_on=any((s,d) in played for s in starA.get(o,[]))
        rows.append(dict(era=g['era'],t=t,hasA=hasA,A_on=A_on,A_off=A_off,hasB=hasB,B_on=B_on,star_on=A_on or B_on,oA_on=oA_on,
            mg=mg,mkt=mkt,mod=mod,odds=g['W'] if side=='away' else g['Z']))
print('team-games',len(rows),'through',maxbox)
def rep(lab,s):
    if not s: return
    cov=np.array([r['mg']-r['mkt'] for r in s]); w=sum(cov>0); l=sum(cov<0)
    u=sum((dec(r['odds']) if r['mg']-r['mkt']>0 else -1) for r in s if r['mg']!=r['mkt'] and r['odds'])
    em=np.mean([abs(r['mg']-r['mod']) for r in s]); ek=np.mean([abs(r['mg']-r['mkt']) for r in s])
    print(f"  {lab:42s} n {len(s):3d} ATS {w}-{l} ({w/max(1,w+l)*100:3.0f}%) {u:+5.1f}u | vs line {cov.mean():+5.1f} | vs model {np.mean([r['mg']-r['mod'] for r in s]):+5.1f} | avg miss model {em:4.1f} market {ek:4.1f}")
print('\nTier A superstar (Doncic, Wemby, Jokic, SGA, Curry, Giannis):')
rep('team with Tier A star PLAYING',[r for r in rows if r['A_on']])
rep('team with Tier A star OUT',[r for r in rows if r['A_off']])
rep('opponent of a Tier A star playing',[r for r in rows if r['oA_on'] and not r['A_on']])
rep('star vs star (both Tier A playing)',[r for r in rows if r['A_on'] and r['oA_on']])
print('\nAny star (Tier A or B) playing:')
rep('team with any star playing',[r for r in rows if r['star_on']])
rep('team with no star playing',[r for r in rows if not r['star_on']])
rep('star team as favorite',[r for r in rows if r['star_on'] and r['mkt']>0])
rep('star team as underdog',[r for r in rows if r['star_on'] and r['mkt']<0])
for e in ('old','roster'):
    rep(f'Tier A playing ({e} era)',[r for r in rows if r['A_on'] and r['era']==e])
print('\nBy star:')
for x in TIER_A:
    t=team_of.get(nm(x))
    rep(f'{x} ({t}) playing',[r for r in rows if r['t']==t and r['A_on']])
print()
rep('team with Tier A or B star OUT (has one, none played)',[r for r in rows if (r['hasA'] or r['hasB']) and not r['star_on']])
rep('team with a Tier B star OUT (any)',[r for r in rows if r['hasB'] and not r['B_on']])

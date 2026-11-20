import runpy,io,contextlib,json,datetime as dt,numpy as np,collections
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path('work/crafted_bt.py',run_name='x')
rating,code,n2c=ns['rating'],ns['code'],ns['name2code']
G=json.load(open('work/deep_games11.json'))
S=[(98,93),(115,107),(101,114),(145,111),(123,118),(123,112),(124,119),(123,106),(108,115),(108,118)]
for g,(a,h) in zip(json.load(open('work/run1111.json')),S):
    L={x['lab']:x for x in g['legs']}
    G.append(dict(d='2026-11-11',era='roster',aw=g['aw'],hm=g['hm'],an=a,hn=h,U=g['sp'][0],P=g['tot'][0],ap=g['ap'],hp=g['hp'],
      W=L[f"{g['aw']} {g['sp'][0]:+g}"]['odds'],Z=L[f"{g['hm']} {-g['sp'][0]:+g}"]['odds'],J=L[f"{g['aw']} ML"]['odds'],K=L[f"{g['hm']} ML"]['odds']))
def dec(o): return 100/-o if o<0 else o/100
rows=[]
for g in G:
    if g['U'] is None: continue
    d=dt.date.fromisoformat(g['d'])
    teams=list(code)
    rs={c:rating(c,d) for c in teams}
    if min(n for _,n in rs.values())<3: continue
    order=sorted(teams,key=lambda c:-rs[c][0]); rank={c:i+1 for i,c in enumerate(order)}
    a,h=n2c[g['aw']],n2c[g['hm']]
    tier=lambda r:'top10' if r<=10 else ('bottom10' if r>20 else 'mid10')
    for t,o,side in ((a,h,'away'),(h,a,'home')):
        mg=(g['an']-g['hn']) if side=='away' else (g['hn']-g['an'])
        mkt=(-g['U']) if side=='away' else g['U']
        mod=(g['ap']-g['hp']) if side=='away' else (g['hp']-g['ap'])
        odds=g['W'] if side=='away' else g['Z']
        rows.append(dict(d=g['d'],t=t,o=o,tt=tier(rank[t]),ot=tier(rank[o]),mg=mg,mkt=mkt,mod=mod,cov=mg-mkt,odds=odds,fav=mkt>0,tot=g['an']+g['hn'],P=g['P']))
print('team-games',len(rows),'(games',len(rows)//2,') from',rows[0]['d'])
def rep(lab,s):
    if not s: return
    cov=np.array([r['cov'] for r in s]); w=sum(c>0 for c in cov); l=sum(c<0 for c in cov)
    u=sum((dec(r['odds']) if r['cov']>0 else -1) for r in s if r['cov']!=0 and r['odds'])
    print(f"  {lab:40s} n {len(s):3d} ATS {w}-{l} ({w/max(1,w+l)*100:3.0f}%) {u:+5.1f}u | vs market {cov.mean():+5.1f} | vs model {np.mean([r['mg']-r['mod'] for r in s]):+5.1f} | totals vs line {np.mean([r['tot']-r['P'] for r in s if r['P']]):+5.1f}")
print('\nTeam result by its OWN tier vs OPPONENT tier (positive = beat the line):')
for tt in ('top10','mid10','bottom10'):
    for ot in ('top10','mid10','bottom10'):
        rep(f'{tt} team vs {ot} opponent',[r for r in rows if r['tt']==tt and r['ot']==ot])
print('\nAny team vs a top-10 opponent (non-top-10 teams only):')
rep('non-top10 vs top10',[r for r in rows if r['ot']=='top10' and r['tt']!='top10'])
rep('  ...as home team?',[r for r in rows if r['ot']=='top10' and r['tt']!='top10' and not r['fav']])
rep('non-top10 vs bottom10',[r for r in rows if r['ot']=='bottom10' and r['tt']!='bottom10'])
print('\nTop-10 teams:')
rep('top10 vs bottom10 (play down?)',[r for r in rows if r['tt']=='top10' and r['ot']=='bottom10'])
rep('top10 vs top10',[r for r in rows if r['tt']=='top10' and r['ot']=='top10'])
rep('top10 favored by 8+',[r for r in rows if r['tt']=='top10' and r['mkt']>=8])
rep('bottom10 dog vs top10',[r for r in rows if r['tt']=='bottom10' and r['ot']=='top10'])

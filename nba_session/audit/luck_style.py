import openpyxl,datetime as dt,collections,random,math,json,runpy,io,contextlib,os
random.seed(9)
def dd(x):
    if hasattr(x,'date'): return x.date()
    if isinstance(x,(int,float)) and x>40000: return dt.date(1899,12,30)+dt.timedelta(days=int(x))
def dec(o): return 100/-o if o<0 else o/100
wb=openpyxl.load_workbook('in1117/s3.xlsx',read_only=True,data_only=True)
H=['TEAM','MU','D','WL','MIN','PTS','FGM','FGA','FGP','3PM','3PA','3PP','FTM','FTA','FTP','OREB','DREB','REB','AST','TOV','STL','BLK','PF','PM']
rows=[]
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,max_col=24,values_only=True):
    if not r[0] or not r[1] or r[2] is None: continue
    x=dict(zip(H,r)); x['D']=dd(x['D']); x['opp']=x['MU'].split(' @ ')[1] if ' @ ' in x['MU'] else x['MU'].split(' vs. ')[1]
    rows.append(x)
by={(x['TEAM'],x['D']):x for x in rows}
TG=[]  # team-game with opponent stats
for x in rows:
    o=by.get((x['opp'],x['D']))
    if not o: continue
    poss=x['FGA']-x['OREB']+x['TOV']+0.44*x['FTA']; oposs=o['FGA']-o['OREB']+o['TOV']+0.44*o['FTA']; P=(poss+oposs)/2
    TG.append(dict(t=x['TEAM'],d=x['D'],pts=x['PTS'],opts=o['PTS'],poss=P,
        tpm=x['3PM'],tpa=x['3PA'],otpm=o['3PM'],otpa=o['3PA'],fta=x['FTA'],ftm=x['FTM'],ofta=o['FTA'],oftm=o['FTM'],
        fga=x['FGA'],ofga=o['FGA'],oreb=x['OREB'],dreb=x['DREB'],ooreb=o['OREB'],odreb=o['DREB'],tov=x['TOV'],otov=o['TOV'],win=x['PTS']>o['PTS']))
print('team-games',len(TG))
TT=collections.defaultdict(list)
for g in TG: TT[g['t']].append(g)
def lg_before(d):
    L=[g for g in TG if g['d']<d]
    s=lambda k: sum(g[k] for g in L)
    return dict(tp=s('tpm')/s('tpa'), ft=s('ftm')/s('fta'))
LG={}
def prof(t,d,minG=5):
    L=sorted([g for g in TT[t] if g['d']<d],key=lambda g:g['d'])
    if len(L)<minG: return None
    if d not in LG: LG[d]=lg_before(d)
    lg=LG[d]; s=lambda k,LL=L: sum(g[k] for g in LL); n=len(L)
    poss=s('poss')
    ortg=100*s('pts')/poss; drtg=100*s('opts')/poss
    l5=L[-5:]; p5=s('poss',l5)
    net5=100*(s('pts',l5)-s('opts',l5))/p5
    tp=s('tpm')/s('tpa'); otp=s('otpm')/s('otpa')
    luck_off=3*(tp-lg['tp'])*s('tpa')/n            # pts/game from own 3P% above league
    luck_def=3*(otp-lg['tp'])*s('otpa')/n          # pts/game opp 3P% above league (bad luck for team if +)
    ftluck_def=(s('oftm')/s('ofta')-lg['ft'])*s('ofta')/n
    pyth=s('pts')**14/(s('pts')**14+s('opts')**14); wp=sum(g['win'] for g in L)/n
    return dict(ortg=ortg,drtg=drtg,net=ortg-drtg,net5=net5,form=net5-(ortg-drtg),pace=poss/n,
        tpr=s('tpa')/s('fga'),otpr=s('otpa')/s('ofga'),orb=s('oreb')/(s('oreb')+s('odreb')),drb=s('dreb')/(s('dreb')+s('ooreb')),
        tovp=100*s('tov')/poss,ftov=100*s('otov')/poss,ftr=s('fta')/s('fga'),oftr=s('ofta')/s('ofga'),
        luck3=luck_off-luck_def,luck_off=luck_off,luck_def=luck_def,ftluck=-ftluck_def,pyth=wp-pyth,n=n)
os.environ['WB']='in1116u/s.xlsx'
with contextlib.redirect_stdout(io.StringIO()): n2c=runpy.run_path('work/xposs.py')['n2c']
t=wb['Tracking']; G={}
for r in t.iter_rows(min_row=13,max_row=t.max_row,values_only=True):
    d=dd(r[0])
    if not d or not isinstance(r[39],(int,float)) or r[20] is None: continue
    k=(d,r[1],r[2])
    if k in G: continue
    a,h=n2c.get(r[1]),n2c.get(r[2]); pa,ph=prof(a,d),prof(h,d)
    if not pa or not ph: continue
    G[k]=dict(d=d,U=r[20],W=r[22],Z=r[25],P=r[15],S=r[18],T=r[19],an=r[39],hn=r[40],pa=pa,ph=ph)
G=list(G.values()); print('games with 5+ prior games for both teams',len(G),min(g['d'] for g in G))
json.dump([{**{k:v for k,v in g.items() if k not in('d',)},'d':str(g['d'])} for g in G],open('audit/luck_style_games.json','w'))

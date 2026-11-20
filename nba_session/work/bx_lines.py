import openpyxl,collections,datetime,json,math,pickle
import numpy as np
wb=openpyxl.load_workbook('in1104/src.xlsx',data_only=True)
def dd(d): return (datetime.date(1899,12,30)+datetime.timedelta(days=int(d))) if isinstance(d,(int,float)) else d.date()
code={r[0]:r[1] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}
full={v:k for k,v in code.items()}
# team-game box from players
G=collections.defaultdict(lambda: collections.defaultdict(float))
for r in wb['BoxScores'].iter_rows(min_row=2,values_only=True):
    if not r[0] or r[3] is None: continue
    k=(dd(r[3]),r[1]); g=G[k]; g['mu']=r[2]
    for i,n in [(6,'pts'),(7,'fgm'),(8,'fga'),(10,'p3m'),(11,'p3a'),(13,'ftm'),(14,'fta'),(16,'orb'),(17,'drb'),(22,'tov'),(23,'pf'),(19,'ast')]:
        g[n]+=float(r[i] or 0)
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True):
    if not r[0] or r[2] is None: continue
    k=(dd(r[2]),r[0])
    if k in G: G[k]['pace']=r[17]; G[k]['min']=r[4]; G[k]['ortg']=r[5]; G[k]['drtg']=r[6]
# opponent link
for (d,t),g in G.items():
    mu=g['mu']; opp=mu.split()[-1]; g['opp']=opp; g['home']=('vs.' in mu)
    o=G.get((d,opp))
    if o:
        for n in ('pts','fga','p3m','p3a','fta','ftm','orb','drb','tov','fgm'): g['o_'+n]=o[n]
for g in G.values(): g['poss']=g.get('pace',100)*g.get('min',48)/48
LG3=sum(g['p3m'] for g in G.values())/sum(g['p3a'] for g in G.values())
print('league 3P%',round(LG3,4),'team-games',len(G))
# tracking games
T=openpyxl.load_workbook('out_1104/MaverickPicks_NBA_Simulations.xlsx',data_only=True)['Tracking']; games=[]
for r in range(13,118):
    a,h,an,hn=T.cell(r,2).value,T.cell(r,3).value,T.cell(r,40).value,T.cell(r,41).value
    if an is None or hn is None or not isinstance(T.cell(r,16).value,(int,float)): continue
    d=T.cell(r,1).value.date()
    games.append(dict(row=r,d=d,a=code[a],h=code[h],ap=T.cell(r,4).value,hp=T.cell(r,5).value,tot=T.cell(r,16).value,
        hs=T.cell(r,24).value,att=T.cell(r,27).value,htt=T.cell(r,31).value,an=an,hn=hn))
print('graded games with lines',len(games))
def prior(t,d):
    P=[g for (dd_,tt),g in G.items() if tt==t and dd_<d and 'o_pts' in g]
    if not P: return None
    s=lambda n: sum(g[n] for g in P)
    poss=s('poss')
    f=dict(n=len(P),
      ortg=s('pts')/poss*100, drtg=s('o_pts')/poss*100, pace=sum(g['pace'] for g in P)/len(P),
      ppg=s('pts')/len(P), oppg=s('o_pts')/len(P),
      r3=s('p3a')/s('fga'), p3=s('p3m')/s('p3a'), op3=s('o_p3m')/s('o_p3a'), or3=s('o_p3a')/s('o_fga'),
      ftr=s('fta')/s('fga'), oftr=s('o_fta')/s('o_fga'), tov=s('tov')/poss*100, otov=s('o_tov')/poss*100,
      orb=s('orb')/(s('orb')+s('o_drb')), oorb=s('o_orb')/(s('o_orb')+s('drb')),
      efg=(s('fgm')+.5*s('p3m'))/s('fga'), oefg=(s('o_fgm')+.5*s('o_p3m'))/s('o_fga'),
      luck=(s('p3m')-LG3*s('p3a'))*3/poss*100, oluck=(s('o_p3m')-LG3*s('o_p3a'))*3/poss*100,
      ft=s('ftm')/max(1,s('fta')),
      sd=np.std([g['pts'] for g in P]) if len(P)>2 else None,
      last2=np.mean([g['pts'] for g in sorted(P,key=lambda g:g['pts']*0)[-2:]]) )
    Ps=sorted([(dd_,g) for (dd_,tt),g in G.items() if tt==t and dd_<d and 'o_pts' in g])
    f['form']=np.mean([g['pts'] for _,g in Ps[-2:]])-f['ppg']
    f['oform']=np.mean([g['o_pts'] for _,g in Ps[-2:]])-f['oppg']
    return f
rows=[]
for g in games:
    for side in ('a','h'):
        t=g[side]; o=g['h' if side=='a' else 'a']
        pt=prior(t,g['d']); po=prior(o,g['d'])
        if not pt or not po: continue
        hs=g['hs']; implied = g['tot']/2 - hs/2 if side=='h' else g['tot']/2 + hs/2
        actual=g['an'] if side=='a' else g['hn']; proj=g['ap'] if side=='a' else g['hp']
        ttl=g['att'] if side=='a' else g['htt']
        box=G.get((g['d'],t))
        rows.append(dict(g=g,side=side,t=t,o=o,pt=pt,po=po,implied=implied,actual=actual,proj=proj,ttl=ttl,box=box))
print('team-games with priors',len(rows))
pickle.dump(dict(rows=rows,games=games,LG3=LG3,G=dict((k,dict(v)) for k,v in G.items())),open('work/bx_lines.pkl','wb'))

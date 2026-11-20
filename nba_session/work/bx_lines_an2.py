import pickle,numpy as np
D=pickle.load(open('work/bx_lines.pkl','rb')); R=D['rows']; G=D['G']; LG3=D['LG3']
A=pickle.load(open('work/bx_lines_an.pkl','rb')); X=A['X']; rm=A['rm']; rp=A['rp']
GM=pickle.load(open('work/bx_lines_game.pkl','rb')); gi=GM['gi']; gres=GM['gres']; gpr=GM['gpr']
tov=np.array(X['Turnovers (own + opp forced)']); orb=np.array(X['Off rebound % (own + opp allowed)'])
print('corr TOV vs ORB feature (team level)',np.corrcoef(tov,orb)[0,1].round(2))
gt=np.array([tov[a]+tov[b] for a,b in gi]); go=np.array([orb[a]+orb[b] for a,b in gi])
gz=(gt-gt.mean())/gt.std()+(go-go.mean())/go.std()
Xm=np.column_stack([np.ones(len(gt)),(gt-gt.mean())/gt.std(),(go-go.mean())/go.std()])
b,res,_,_=np.linalg.lstsq(Xm,gres,rcond=None); e=gres-Xm@b; s2=e@e/(len(e)-3); se=np.sqrt(np.diag(s2*np.linalg.inv(Xm.T@Xm)))
print('joint game-total regression: TOV',b[1].round(2),'t',(b[1]/se[1]).round(1),' ORB',b[2].round(2),'t',(b[2]/se[2]).round(1))
r=np.corrcoef(gz,gres)[0,1]; print('combined "extra possessions" index r',r.round(2),'t',(r*np.sqrt((len(gz)-2)/(1-r*r))).round(1))
q=np.percentile(gz,[33.3,66.7])
for lo,hi,lab in [(-99,q[0],'low'),(q[0],q[1],'mid'),(q[1],99,'high')]:
    m=(gz>=lo)&(gz<hi); print(f'  {lab}: n{m.sum()} actual-line {gres[m].mean():+5.1f}  overs {(gres[m]>0).sum()}-{(gres[m]<0).sum()}  vs model {gpr[m].mean():+5.1f}')
# leave one team out
teams=sorted(set(r['t'] for r in R)); rs=[]
for T in teams:
    m=np.array([not(R[a]['t']==T or R[b]['t']==T) for a,b in gi])
    rs.append((np.corrcoef(gz[m],gres[m])[0,1],T))
print('leave-one-team-out r range',round(min(rs)[0],2),min(rs)[1],round(max(rs)[0],2),max(rs)[1])
# what do the teams look like (season-to-date as of latest)
import collections
lat={}
for r in R:
    for key,f in ((r['t'],r['pt']),(r['o'],r['po'])):
        if key not in lat or f['n']>lat[key]['n']: lat[key]=f
L=sorted(lat.items(),key=lambda kv:kv[1]['tov']+kv[1]['otov'])
print('most turnover-heavy games (own TOV + forced):',[(k,round(v['tov']+v['otov'],1)) for k,v in L[-5:]],' least:',[(k,round(v['tov']+v['otov'],1)) for k,v in L[:5]])
L=sorted(lat.items(),key=lambda kv:kv[1]['orb']+kv[1]['oorb'])
print('most off-rebound games:',[(k,round((v['orb']+v['oorb'])*50,1)) for k,v in L[-5:]],' least:',[(k,round((v['orb']+v['oorb'])*50,1)) for k,v in L[:5]])
# Does the market already price TOV/ORB? correlation with line
imp=np.array([R[a]['implied']+R[b]['implied'] for a,b in gi])
print('corr index vs game line',np.corrcoef(gz,imp)[0,1].round(2))
# same-game descriptive: what explained game-total misses vs line
rows=[]
for gk,(a,b) in enumerate(gi):
    ra,rb=R[a],R[b]; ga,gb=ra['box'],rb['box']
    if not ga or not gb or 'pace' not in ga: continue
    poss=(ga['poss']+gb['poss'])/2
    exp_pace=(ra['pt']['pace']+ra['po']['pace'])/2
    luck3=((ga['p3m']-LG3*ga['p3a'])+(gb['p3m']-LG3*gb['p3a']))*3
    ftl=(ga['ftm']+gb['ftm'])-0.78*(ga['fta']+gb['fta'])
    rows.append((gres[gk],luck3,ftl,(ga['pace']+gb['pace'])/2-exp_pace,ga['tov']+gb['tov']-(ra['pt']['tov']+rb['pt']['tov'])*poss/100,
                 ga['orb']+gb['orb'],ga['fta']+gb['fta'],ga['p3a']+gb['p3a']))
Z=np.array(rows); y=Z[:,0]
names=['3P luck (pts)','FT luck (pts)','pace vs expected','turnovers vs usual','off rebounds','FTA','3PA']
print('\nSame-game drivers of game-total miss vs line, n',len(y))
for i,nm in enumerate(names):
    r=np.corrcoef(Z[:,i+1],y)[0,1]; print(f'  {nm:20s} r {r:+.2f}  R2 {r*r:.2f}')
Xm=np.column_stack([np.ones(len(y)),Z[:,1],Z[:,2],Z[:,3]]); b=np.linalg.lstsq(Xm,y,rcond=None)[0]; e=y-Xm@b
print('  3P luck + FT luck + pace together R2',round(1-e.var()/y.var(),2),'coefs',b.round(2))
pickle.dump(dict(gz=gz,q=q),open('work/bx_lines_idx.pkl','wb'))

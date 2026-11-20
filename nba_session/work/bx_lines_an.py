import pickle,numpy as np,datetime
D=pickle.load(open('work/bx_lines.pkl','rb')); R=D['rows']; LG3=D['LG3']
LGR=np.mean([r['pt']['ortg'] for r in R])
def feats(r):
    t,o=r['pt'],r['po']
    raw=(t['pace']+o['pace'])/2/100*(t['ortg']+o['drtg']-LGR)
    return {'Box-only projection minus line':raw-r['implied'],
            'Box-only projection minus model':raw-r['proj'],
            'Model minus line':r['proj']-r['implied'],
            '3P luck (own off + opp def)':t['luck']+o['oluck'],
            '3PA rate (own + opp allowed)':t['r3']+o['or3'],
            'Pace (both teams)':t['pace']+o['pace'],
            'FT rate (own + opp allowed)':t['ftr']+o['oftr'],
            'Turnovers (own + opp forced)':t['tov']+o['otov'],
            'Off rebound % (own + opp allowed)':t['orb']+o['oorb'],
            'eFG% (own + opp allowed)':t['efg']+o['oefg'],
            'Last-2 form (own pts + opp allowed)':t['form']+o['oform'],
            'Scoring SD (own)':t['sd'] if t['sd'] is not None else np.nan,
            'Games of data (min of two)':min(t['n'],o['n']),
            'Home':1.0 if r['side']=='h' else 0.0}
X={};rm=[];rp=[];dates=[];ttres=[]
for r in R:
    f=feats(r)
    for k,v in f.items(): X.setdefault(k,[]).append(v)
    rm.append(r['actual']-r['implied']); rp.append(r['actual']-r['proj']); dates.append(r['g']['d'])
    ttres.append(r['actual']-r['ttl'] if isinstance(r['ttl'],(int,float)) else np.nan)
rm,rp,ttres=map(np.array,(rm,rp,ttres)); dates=np.array(dates)
mid=sorted(dates)[len(dates)//2]; early=dates<mid
print('n team-games',len(rm),'split date',mid, 'mean resid vs line',rm.mean().round(2),'sd',rm.std().round(1),'vs model mean',rp.mean().round(2),'sd',rp.std().round(1))
print('TT line available',np.isfinite(ttres).sum(),'mean actual-TT line',np.nanmean(ttres).round(2))
def stat(x,y):
    m=np.isfinite(x)&np.isfinite(y); x,y=x[m],y[m]
    xs=(x-x.mean())/x.std(); b=np.polyfit(xs,y,1)[0]; r=np.corrcoef(x,y)[0,1]; n=len(x); t=r*np.sqrt((n-2)/(1-r*r))
    return r,b,t,n
out={}
print(f"\n{'feature':40s} {'vs LINE r':>9} {'pts/SD':>7} {'t':>5} | {'early':>6} {'late':>6} | {'vs MODEL r':>10} {'t':>5}")
for k,v in X.items():
    x=np.array(v,float)
    r1,b1,t1,n=stat(x,rm); re_,_,_,_=stat(x[early],rm[early]); rl,_,_,_=stat(x[~early],rm[~early]); r2,b2,t2,_=stat(x,rp)
    out[k]=dict(r=r1,b=b1,t=t1,re=re_,rl=rl,r2=r2,b2=b2,t2=t2,n=n)
    print(f"{k:40s} {r1:+9.2f} {b1:+7.2f} {t1:+5.1f} | {re_:+6.2f} {rl:+6.2f} | {r2:+10.2f} {t2:+5.1f}")
# terciles for key features vs line, over rate vs implied
print('\nTerciles (mean actual - implied team total, over rate):')
for k in ['3P luck (own off + opp def)','Box-only projection minus line','Last-2 form (own pts + opp allowed)','Pace (both teams)','3PA rate (own + opp allowed)','Model minus line','FT rate (own + opp allowed)']:
    x=np.array(X[k],float); q=np.nanpercentile(x,[33.3,66.7]); s=[]
    for lo,hi,lab in [(-1e9,q[0],'low'),(q[0],q[1],'mid'),(q[1],1e9,'high')]:
        m=(x>=lo)&(x<hi); s.append(f"{lab} {rm[m].mean():+5.1f} ({(rm[m]>0).mean()*100:3.0f}% over, n{m.sum()})")
    print(f"  {k:38s} "+' | '.join(s))
pickle.dump(dict(X=X,rm=rm,rp=rp,dates=dates,out=out),open('work/bx_lines_an.pkl','wb'))
# game level totals
GG={}
for r,x in zip(R,range(len(R))):
    key=(r['g']['row']); GG.setdefault(key,[]).append(x)
gi=[v for v in GG.values() if len(v)==2]
gres=np.array([rm[a]+rm[b] for a,b in gi]); gpr=np.array([rp[a]+rp[b] for a,b in gi])
print('\nGAME TOTALS n',len(gi),'mean actual-line',gres.mean().round(2),'sd',gres.std().round(1),'over rate',(gres>0).mean().round(3))
print(f"{'feature':40s} {'r':>6} {'pts/SD':>7} {'t':>5} {'early':>6} {'late':>6} | vs model r")
gd=np.array([dates[a] for a,b in gi]); ge=gd<sorted(gd)[len(gd)//2]
gout={}
for k in ['Box-only projection minus line','Model minus line','3P luck (own off + opp def)','3PA rate (own + opp allowed)','Pace (both teams)','FT rate (own + opp allowed)','Turnovers (own + opp forced)','Off rebound % (own + opp allowed)','Last-2 form (own pts + opp allowed)','eFG% (own + opp allowed)']:
    x=np.array([X[k][a]+X[k][b] if k!='Pace (both teams)' else X[k][a] for a,b in gi],float)
    r1,b1,t1,n=stat(x,gres); re_,_,_,_=stat(x[ge],gres[ge]); rl,_,_,_=stat(x[~ge],gres[~ge]); r2,_,t2,_=stat(x,gpr)
    gout[k]=dict(r=r1,b=b1,t=t1,re=re_,rl=rl,r2=r2,t2=t2,n=n)
    print(f"{k:40s} {r1:+6.2f} {b1:+7.2f} {t1:+5.1f} {re_:+6.2f} {rl:+6.2f} | {r2:+6.2f} t {t2:+4.1f}")
pickle.dump(dict(gi=gi,gres=gres,gpr=gpr,gout=gout),open('work/bx_lines_game.pkl','wb'))

import sys, statistics as st, math, itertools
sys.path.insert(0,'work')
from pdata import load
wb,S,R26,R27=load('in16/nba.xlsx')
def age_adj(age,scale):
    if age is None: return 0
    a=age
    d= 1.0 if a<=21 else 0.6 if a<=23 else 0.25 if a<=25 else 0 if a<=28 else -0.4 if a<=31 else -0.9
    return d*scale
def prior(name,target,K,m0o,m0d,agescale,rk_o,rk_d):
    prev={'26':['25'],'27':['26','25']}[target]
    num_o=num_d=den=0
    for i,s in enumerate(prev):
        p=S[s].get(name)
        if not p or not p['tot']: continue
        G,GS,mp,o,d=p['tot']; w=(2 if i==0 else 1)*mp
        num_o+=w*o; num_d+=w*d; den+=w
    tgt=S[target].get(name); age=tgt['age'] if tgt else None
    if den==0: return rk_o, rk_d, 0
    bo=(num_o+K*m0o)/(den+K); bd=(num_d+K*m0d)/(den+K)
    aa=age_adj(age,agescale)
    return bo+aa*0.7, bd+aa*0.3, den
def team_vals(target,team,params):
    O=D=MP=0
    for n,p in S[target].items():
        if team in p['teams']:
            mp=p['teams'][team][2]; o,d,_=prior(n,target,*params)
            O+=mp*o; D+=mp*d; MP+=mp
    return O/MP*5, D/MP*5
lgO=st.mean(v['o'] for v in R26.values()); lgD=st.mean(v['d'] for v in R26.values())
def evaluate(params):
    po=[];pd=[];ao=[];ad=[]
    for t,v in R26.items():
        o,d=team_vals('26',t,params); po.append(o); pd.append(d); ao.append(v['o']-lgO); ad.append(lgD-v['d'])
    def fit(x,y):
        mx,my=st.mean(x),st.mean(y); b=sum((a-mx)*(c-my) for a,c in zip(x,y))/sum((a-mx)**2 for a in x)
        res=[c-my-b*(a-mx) for a,c in zip(x,y)]; return b, math.sqrt(sum(r*r for r in res)/len(res)), st.correlation(x,y)
    return fit(po,ao),fit(pd,ad),fit([a+b for a,b in zip(po,pd)],[a+b for a,b in zip(ao,ad)])
if __name__=='__main__':
    best=[]
    for K,m0o,m0d,ags,rko,rkd in itertools.product([0,300,800,1500],[-1.5,-0.5],[-0.5,0],[0,1],[-3,-2,-1],[-1,-0.5]):
        fo,fd,fn=evaluate((K,m0o,m0d,ags,rko,rkd))
        best.append((fn[1],K,m0o,m0d,ags,rko,rkd,fo,fd,fn))
    best.sort(key=lambda x:x[0])
    for b in best[:8]: print(f"net rmse {b[0]:.2f} r {b[9][2]:.3f} slope {b[9][0]:.2f} | K {b[1]} m0 {b[2]}/{b[3]} age {b[4]} rookie {b[5]}/{b[6]} | O r {b[7][2]:.2f} slope {b[7][0]:.2f} | D r {b[8][2]:.2f} slope {b[8][0]:.2f}")
    print('sd actual net', st.pstdev([v['n'] for v in R26.values()]))

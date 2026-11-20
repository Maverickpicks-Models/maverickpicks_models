import openpyxl, math
from statistics import NormalDist
N=NormalDist().cdf
class Model:
    def __init__(s,path):
        wb=openpyxl.load_workbook(path,data_only=True); s.wb=wb
        A=wb['Assumptions']; s.A={k:A[f'C{k}'].value for k in range(5,21)}
        def rat(name):
            ws=wb[name]; d={}
            for r in ws.iter_rows(min_row=2,values_only=True):
                if r[1]: d[r[1]]=dict(gp=r[2],o=r[7],d=r[8],n=r[9],p=r[10])
            return d
        s.R25=rat('Ratings_2025_26'); s.R26=rat('Ratings_2026_27')
        def avg(d,k):
            v=[x[k] for x in d.values() if isinstance(x[k],(int,float))]; return sum(v)/len(v)
        s.pO,s.pD,s.pP=avg(s.R25,'o'),avg(s.R25,'d'),avg(s.R25,'p')
        s.cO,s.cD,s.cP=avg(s.R26,'o'),avg(s.R26,'d'),avg(s.R26,'p')
        lw=min(1,avg(s.R26,'gp')/s.A[9])
        s.LO=lw*s.cO+(1-lw)*s.pO; s.LD=lw*s.cD+(1-lw)*s.pD; s.LB=(s.LO+s.LD)/2; s.LP=lw*s.cP+(1-lw)*s.pP
    def team(s,t):
        p=s.R25.get(t,dict(gp=0,o=0,d=0,p=0)); c=s.R26.get(t,dict(gp=0,o=0,d=0,p=0))
        reg=s.A[10]
        cw=0 if (c['gp'] or 0)<=0 else (1 if (p['gp'] or 0)<=0 else min(1,c['gp']/s.A[9]))
        po=s.LO if (p['gp'] or 0)<=0 else s.pO+(1-reg)*(p['o']-s.pO)
        pdd=s.LD if (p['gp'] or 0)<=0 else s.pD+(1-reg)*(p['d']-s.pD)
        pp=s.LP if (p['gp'] or 0)<=0 else p['p']
        return dict(o=cw*(c['o'] or 0)+(1-cw)*po, d=cw*(c['d'] or 0)+(1-cw)*pdd, p=cw*(c['p'] or 0)+(1-cw)*pp, cw=cw)
    def project(s,away,home,a_adj=0,h_adj=0,a_b2b=False,h_b2b=False):
        A,H=s.team(away),s.team(home)
        pace=s.LP+s.A[11]*((A['p']-s.LP)+(H['p']-s.LP))
        ra=pace/100*(A['o']+H['d']-s.LB); rh=pace/100*(H['o']+A['d']-s.LB)
        ta=a_adj-(s.A[13] if a_b2b else 0); th=h_adj-(s.A[13] if h_b2b else 0)
        ap=max(80,ra+(ta-th)/2-s.A[12]/2); hp=max(80,rh+(th-ta)/2+s.A[12]/2)
        return ap,hp,A['cw'],H['cw']
    def price(s,ap,hp):
        ms,ts=s.A[14],s.A[15]; tsd=math.sqrt((ms**2+ts**2)/4)
        def p(mean,sd,cut):
            if cut is None: w=1-N((0-mean)/sd); return w,1-w,0
            if abs(cut-round(cut))<1e-6:
                w=1-N((cut+0.5-mean)/sd); l=N((cut-0.5-mean)/sd); return w,l,1-w-l
            w=1-N((cut-mean)/sd); return w,1-w,0
        return dict(ms=ms,ts=ts,tsd=tsd,p=p)

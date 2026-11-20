"""Python replica of the production workbook (roster prior + shooting-adjusted current), from LO-recalculated values."""
import openpyxl, math, unicodedata, re
from statistics import NormalDist
N=NormalDist().cdf
def nm(s):
    s=''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c)).lower()
    s=re.sub(r"[.'\-]",'',s); s=re.sub(r'\b(jr|sr|ii|iii|iv)\b','',s); return ' '.join(s.split())
class Prod:
    def __init__(s,path):
        wb=openpyxl.load_workbook(path,data_only=True); s.wb=wb
        A=wb['Assumptions']; s.A={r:A[f'C{r}'].value for r in range(5,47)}
        C=wb['Calculations']; s.LO,s.LD,s.LB,s.LP=C['B28'].value,C['B29'].value,C['B30'].value,C['B31'].value
        s.players=[]
        for r in wb['PlayerRatings'].iter_rows(min_row=6,max_row=805,values_only=True):
            if r[0] and r[2]: s.players.append(dict(name=r[0],key=nm(r[0]),team=r[2],mpg=r[7] or 0,off=r[23],deff=r[27]))
        def rat(n):
            d={}
            new=wb[n]['C1'].value=='W'   # CraftedNBA new layout: # Team W L Pct GB L10 NRtg ORtg DRtg Pace Pts
            for r in wb[n].iter_rows(min_row=2,values_only=True):
                if r[1] and isinstance(r[2],(int,float)):
                    d[r[1]]=dict(gp=r[2]+r[3],o=r[8],d=r[9],p=r[10]) if new else dict(gp=r[2],o=r[7],d=r[8],p=r[10])
            return d
        s.R25=rat('Ratings_2025_26'); s.R27=rat('Ratings_2026_27')
        s.luck={}
        for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True): s.luck[r[0]]=(r[12],r[13])
    def roster(s,team,outs):
        B=ACT=O=D=0
        for p in s.players:
            if p['team']!=team: continue
            w=1-outs.get(p['key'],0); B+=p['mpg']; ACT+=p['mpg']*w; O+=p['mpg']*w*p['off']; D+=p['mpg']*w*p['deff']
        lost=B-ACT; A=s.A
        o=(O+lost*A[37])/B*5; d=(D+lost*A[38])/B*5
        return s.LO+A[39]*o, s.LD-A[40]*d
    def team(s,t,outs):
        A=s.A; c=s.R27.get(t,dict(gp=0,o=0,d=0,p=0)); p=s.R25[t]
        cw=0 if c['gp']<=0 else min(1,c['gp']/A[9])
        po,pdd=s.roster(t,outs) if A[30]=='Roster' else (None,None)
        co,cd=c['o'],c['d']
        if A[44]=='Yes' and c['gp']>0:
            lo,ld=s.luck[t]; co-=lo; cd-=ld
        return dict(o=cw*co+(1-cw)*po,d=cw*cd+(1-cw)*pdd,p=cw*c['p']+(1-cw)*p['p'],cw=cw)
    def project(s,aw,hm,outs={},ab=False,hb=False):
        A=s.A; a,h=s.team(aw,outs),s.team(hm,outs)
        pace=s.LP+A[11]*((a['p']-s.LP)+(h['p']-s.LP))
        ra=pace/100*(a['o']+h['d']-s.LB); rh=pace/100*(h['o']+a['d']-s.LB)
        ta=-(A[13] if ab else 0); th=-(A[13] if hb else 0)
        return max(80,ra+(ta-th)/2-A[12]/2), max(80,rh+(th-ta)/2+A[12]/2), a['cw'], h['cw']

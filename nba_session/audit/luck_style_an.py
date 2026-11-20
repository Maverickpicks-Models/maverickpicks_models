import json,math,random,statistics as st
random.seed(4)
G=json.load(open('audit/luck_style_games.json'))
def dec(o): return 100/-o if o<0 else o/100
def pearson(x,y):
    mx,my=st.mean(x),st.mean(y); sx=math.sqrt(sum((a-mx)**2 for a in x)); sy=math.sqrt(sum((b-my)**2 for b in y))
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/(sx*sy)
def pval(r,n):
    t=r*math.sqrt((n-2)/(1-r*r)); # two-sided normal approx
    return 2*(1-0.5*(1+math.erf(abs(t)/math.sqrt(2))))
def boot(L,B=3000):
    n=len(L)
    if n<5: return (float('nan'),)*2
    xs=sorted(sum(random.choice(L) for _ in range(n))/n for _ in range(B)); return xs[int(.025*B)],xs[int(.975*B)]
SPREAD={  # name: (diff function away-minus-home, expected sign of corr with away cover)
 '3P shooting luck (own+def)':(lambda a,h:a['luck3']-h['luck3'],-1),
 'Offensive 3P luck':(lambda a,h:a['luck_off']-h['luck_off'],-1),
 'Defensive 3P luck (opp 3P% low)':(lambda a,h:(-a['luck_def'])-(-h['luck_def']),-1),
 'Opp FT% luck':(lambda a,h:a['ftluck']-h['ftluck'],-1),
 'Record vs Pythagorean (luck)':(lambda a,h:a['pyth']-h['pyth'],-1),
 'Recent form (last 5 net - season net)':(lambda a,h:a['form']-h['form'],-1),
 'Season net rating':(lambda a,h:a['net']-h['net'],+1),
 'Offensive rebounding edge':(lambda a,h:(a['orb']-(1-h['drb']))-(h['orb']-(1-a['drb'])),+1),
 'Turnover edge (forced - own)':(lambda a,h:(a['ftov']-a['tovp'])-(h['ftov']-h['tovp']),+1),
 'Free-throw rate edge':(lambda a,h:(a['ftr']-a['oftr'])-(h['ftr']-h['oftr']),+1),
 '3PA rate edge (own - allowed)':(lambda a,h:(a['tpr']-a['otpr'])-(h['tpr']-h['otpr']),+1),
}
TOT={
 'Pace sum (fast teams)':(lambda a,h:a['pace']+h['pace'],+1),
 'Offensive 3P luck sum (both hot)':(lambda a,h:a['luck_off']+h['luck_off'],-1),
 'Defensive 3P luck sum (opps cold)':(lambda a,h:-(a['luck_def']+h['luck_def']),+1),
 '3PA rate sum':(lambda a,h:a['tpr']+h['tpr']+a['otpr']+h['otpr'],+1),
 'FT rate sum':(lambda a,h:a['ftr']+h['ftr']+a['oftr']+h['oftr'],+1),
 'Turnover % sum':(lambda a,h:a['tovp']+h['tovp'],-1),
 'ORtg sum (season)':(lambda a,h:a['ortg']+h['ortg'],+1),
 'Pace mismatch (abs diff)':(lambda a,h:abs(a['pace']-h['pace']),-1),
}
res=[]
def run(name,f,sgn,kind):
    xs=[];ys=[];bets=[];ds=[]
    for g in G:
        x=f(g['pa'],g['ph'])
        if kind=='spread': y=(g['an']-g['hn'])+g['U']
        else: y=(g['an']+g['hn'])-g['P']
        xs.append(x); ys.append(y); ds.append(g['d'])
    r=pearson(xs,ys); p=pval(r,len(xs))
    srt=sorted(xs); lo,hi=srt[len(srt)//3],srt[2*len(srt)//3]
    B=[];Bp={'pre':[],'post':[]}
    for x,y,g in zip(xs,ys,G):
        if y==0: continue
        if x>=hi: want=sgn>0      # high tercile: expect y>0 if sgn>0
        elif x<=lo: want=sgn<0
        else: continue
        if kind=='spread': o=g['W'] if want else g['Z']   # want True = away cover
        else: o=g['S'] if want else g['T']
        if o is None: continue
        pl=dec(o) if ((y>0)==want) else -1
        B.append(pl); Bp['post' if g['d']>='2026-11-12' else 'pre'].append(pl)
    w=sum(1 for z in B if z>0); l1,h1=boot(B)
    res.append((p,name,kind,r,sgn,len(xs),w,len(B)-w,sum(B)/len(B),l1,h1,Bp))
for k,(f,s) in SPREAD.items(): run(k,f,s,'spread')
for k,(f,s) in TOT.items(): run(k,f,s,'total')
# Benjamini-Hochberg
m=len(res); srt=sorted(res,key=lambda z:z[0])
bh={}
for i,z in enumerate(srt,1): bh[z[1]]=min(1,z[0]*m/i)
print('| market | feature | corr with miss (expected sign) | p | BH-adj p | tercile bets W-L | ROI | 95% CI | pre-11/12 | 11/12+ |')
for z in res:
    p,name,kind,r,sgn,n,w,l,roi,lo,hi,Bp=z
    f=lambda L: f"{sum(1 for x in L if x>0)}-{sum(1 for x in L if x<0)} {100*sum(L)/len(L):+.0f}%" if L else '—'
    print(f"| {kind} | {name} | {r:+.2f} ({'+' if sgn>0 else '-'}) | {p:.2f} | {bh[name]:.2f} | {w}-{l} | {100*roi:+.1f}% | [{100*lo:+.0f}%, {100*hi:+.0f}%] | {f(Bp['pre'])} | {f(Bp['post'])} |")
print('n games',len(G))

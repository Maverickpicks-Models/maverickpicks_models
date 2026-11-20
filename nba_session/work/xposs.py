import openpyxl,json,datetime as dt,numpy as np,collections
wb=openpyxl.load_workbook(''+__import__('os').environ.get('WB','in1112/s.xlsx')+'',read_only=True,data_only=True)
code={r[1]:r[0] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}; n2c={v:k for k,v in code.items()}
rows=[r[26:45] for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True) if r[26]]
# per team-game: date, opp, tov%, oreb%, dreb%
TG=collections.defaultdict(list); byg={}
for r in rows:
    t,mu,d=r[0],r[1].replace('\xa0',' '),r[2].date()
    opp=mu.split('@')[1].strip() if '@' in mu else mu.split('vs.')[1].strip()
    byg[(t,d)]=dict(opp=opp,tov=r[14],orb=r[11],drb=r[12],pace=r[17])
for (t,d),v in byg.items(): TG[t].append((d,v))
def prof(t,before):
    g=[(d,v) for d,v in TG[t] if d<before]
    if len(g)<3: return None
    tov=np.mean([v['tov'] for d,v in g]); orb=np.mean([v['orb'] for d,v in g])
    ftov=np.mean([byg[(v['opp'],d)]['tov'] for d,v in g if (v['opp'],d) in byg])
    orba=np.mean([100-v['drb'] for d,v in g])
    pace=np.mean([v['pace'] for d,v in g])
    return dict(tov=tov,ftov=ftov,orb=orb,orba=orba,pace=pace)
G=json.load(open('work/deep_games11.json'))
X=[]
for g in G:
    if g['P'] is None: continue
    d=dt.date.fromisoformat(g['d']); a,h=n2c[g['aw']],n2c[g['hm']]
    pa,ph=prof(a,d),prof(h,d)
    if not pa or not ph: continue
    X.append(dict(d=g['d'],tov=pa['tov']+ph['ftov']+ph['tov']+pa['ftov'],orb=pa['orb']+ph['orba']+ph['orb']+pa['orba'],
       pace=pa['pace']+ph['pace'],res=(g['an']+g['hn'])-g['P'],mres=(g['an']+g['hn'])-(g['ap']+g['hp']),S=g['S'],T=g['T'],tot=g['an']+g['hn'],P=g['P']))
def dec(o): return 100/-o if o<0 else o/100
for lab,sub in (('<=11/2 (original sample)',[x for x in X if x['d']<='2026-11-02']),('11/4-11/10 (out of sample)',[x for x in X if x['d']>'2026-11-02']),('all',X)):
    tov=np.array([x['tov'] for x in sub]); orb=np.array([x['orb'] for x in sub]); res=np.array([x['res'] for x in sub])
    z=(tov-tov.mean())/tov.std()+(orb-orb.mean())/orb.std()
    q=np.quantile(z,[1/3,2/3])
    out=[]
    for lo,hi,side in ((-9,q[0],'U'),(q[0],q[1],None),(q[1],9,'O')):
        m=(z>=lo)&(z<hi); out.append(f"{res[m].mean():+.1f}")
    # bets: under low third, over high third
    w=l=0;u=0
    for x,zz in zip(sub,z):
        side='U' if zz<q[0] else ('O' if zz>=q[1] else None)
        if not side or x['tot']==x['P']: continue
        win=(x['tot']<x['P']) if side=='U' else (x['tot']>x['P']); o=x['T'] if side=='U' else x['S']
        w+=win;l+=not win;u+=dec(o) if win else -1
    print(f"{lab}: n {len(sub)} corr(index,total-line) {np.corrcoef(z,res)[0,1]:+.2f} (TOV {np.corrcoef(tov,res)[0,1]:+.2f}, ORB {np.corrcoef(orb,res)[0,1]:+.2f}) | thirds low/mid/high vs line {out} | bets {w}-{l} {u:+.1f}u")
print('--- turnover environment only (high third Over, low third Under), thirds set on each sample')
for lab,sub in (('<=11/2',[x for x in X if x['d']<='2026-11-02']),('11/4-11/10',[x for x in X if x['d']>'2026-11-02']),('all',X)):
    tov=np.array([x['tov'] for x in sub]); q=np.quantile(tov,[1/3,2/3])
    for side_lab,mask_side in (('Over high',1),('Under low',-1)):
        w=l=0;u=0
        for x,t in zip(sub,tov):
            if mask_side==1 and t<q[1]: continue
            if mask_side==-1 and t>=q[0]: continue
            if x['tot']==x['P']: continue
            win=(x['tot']>x['P']) if mask_side==1 else (x['tot']<x['P']); o=x['S'] if mask_side==1 else x['T']
            w+=win;l+=not win;u+=dec(o) if win else -1
        print(lab,side_lab,f"{w}-{l} {u:+.1f}u")

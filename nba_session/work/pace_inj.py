import openpyxl,json,glob,datetime as dt,numpy as np,collections,re
wb=openpyxl.load_workbook('in1111c/s.xlsx',read_only=True,data_only=True)
code={r[1]:r[0] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}; n2c={v:k for k,v in code.items()}
trad={};adv={}
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True):
    if r[0] and r[2]: trad[(r[0],r[2].date())]=r[:24]
    if r[26] and r[28]: adv[(r[26],r[28].date())]=r[26:45]
def opp(mu):
    mu=mu.replace('\xa0',' '); return mu.split('@')[1].strip() if '@' in mu else mu.split('vs.')[1].strip()
# team-game records
TG=collections.defaultdict(list)
for (t,d),a in adv.items():
    tr=trad.get((t,d))
    if not tr: continue
    TG[t].append(dict(d=d,opp=opp(a[1]),pace=a[17],ortg=a[5],drtg=a[6],pts=tr[5],fga=tr[7],fgm=tr[6],p3m=tr[9],p3a=tr[10],ftm=tr[12],fta=tr[13],orb=tr[15],tov=tr[19],min=tr[4]))
LG_PACE=np.mean([g['pace'] for t in TG for g in TG[t]])
def pre(t,d):
    g=[x for x in TG[t] if x['d']<d]
    if len(g)<2: return None
    return dict(pace=np.mean([x['pace'] for x in g]),n=len(g))
# games: final projection per (date,aw,hm)
proj={}
for f in sorted(glob.glob('work/run1[01]*.json')):
    m=re.match(r'work/run(\d{4})',f); md=m.group(1)
    if md<'1031': continue
    d=dt.date(2026,int(md[:2]),int(md[2:]))
    try: D=json.load(open(f))
    except: continue
    for g in D:
        if 'ap0' in g: proj[(d,g['aw'],g['hm'])]=g
G=json.load(open('work/deep_games11.json'))
SC={(dt.date.fromisoformat(g['d']),g['aw'],g['hm']):(g['an'],g['hn'],g['P'],g['U']) for g in G}
for g,(a,h) in zip(json.load(open('work/run1111.json')),[(98,93),(115,107),(101,114),(145,111),(123,118),(123,112),(124,119),(123,106),(108,115),(108,118)]):
    SC[(dt.date(2026,11,11),g['aw'],g['hm'])]=(a,h,g['tot'][0],g['sp'][0])
rows=[]
for (d,aw,hm),(an,hn,P,U) in SC.items():
    a,h=n2c[aw],n2c[hm]
    ra,rh=adv.get((a,d)),adv.get((h,d)); ta,th=trad.get((a,d)),trad.get((h,d))
    if not (ra and rh and ta and th) or P is None: continue
    pa,ph=pre(a,d),pre(h,d)
    exp_pace=LG_PACE+0.5*((pa['pace']-LG_PACE)+(ph['pace']-LG_PACE)) if pa and ph else None
    act_pace=(ra[17]+rh[17])/2
    tot=an+hn
    ot=ta[4]>240
    poss=tot/((ra[5]+rh[5])/100)   # actual possessions per team
    # 3P luck: threes made above league rate on attempts
    lg3=0.355
    luck3=3*((ta[9]+th[9])-lg3*(ta[10]+th[10]))
    r=dict(d=d,g=f'{a}@{h}',tot=tot,P=P,U=U,margin=an-hn,ot=ot,act_pace=act_pace,exp_pace=exp_pace,poss=poss,eff=(ra[5]+rh[5])/2,luck3=luck3,
           tov=ta[21]+th[21],orb=ta[15]+th[15],fta=ta[13]+th[13],p3a=ta[10]+th[10],era='roster' if d>=dt.date(2026,10,31) else 'old')
    pj=proj.get((d,aw,hm))
    if pj:
        r.update(mt=pj['ap']+pj['hp'],mm=pj['ap']-pj['hp'],mt0=pj['ap0']+pj['hp0'],mm0=pj['ap0']-pj['hp0'])
    rows.append(r)
json.dump(rows,open('work/pace_rows.json','w'),default=str)
print('games',len(rows),'with pre-game pace',sum(r['exp_pace'] is not None for r in rows),'with model+no-inj proj',sum('mt' in r for r in rows),'league pace %.1f'%LG_PACE)

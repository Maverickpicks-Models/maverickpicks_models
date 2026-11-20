import json,math,random,collections,statistics as st
random.seed(11)
G=json.load(open('audit/games.json'))
def imp(o): return -o/(100-o) if o<0 else 100/(100+o)
def dec(o): return 100/-o if o<0 else o/100
def flag(n): return 'VERY LOW' if n<15 else ('LOW' if n<30 else '')
def boot(pl,st_,B=4000):
    n=len(pl); 
    if n<5: return (float('nan'),float('nan'))
    xs=[]
    for _ in range(B):
        idx=[random.randrange(n) for _ in range(n)]
        s=sum(st_[i] for i in idx); xs.append(sum(pl[i] for i in idx)/s if s else 0)
    xs.sort(); return xs[int(.025*B)],xs[int(.975*B)]
def line(name,items):  # items: list of (profit, stake, won)
    n=len(items)
    if n==0: print(f'| {name} | 0 | | | | | |'); return
    w=sum(1 for p,s,x in items if p>0); l=sum(1 for p,s,x in items if p<0)
    pl=sum(p for p,s,x in items); stake=sum(s for p,s,x in items)
    lo,hi=boot([p for p,s,x in items],[s for p,s,x in items])
    print(f'| {name} | {n} | {w}-{l} | {pl:+.2f} | {100*pl/stake:+.1f}% | [{100*lo:+.0f}%, {100*hi:+.0f}%] | {flag(n)} |')
print('## T3 logged bets')
B=[g for g in G if g['mk'] and g['grade'] in ('W','L','P')]
it=lambda L:[(g['prof'],g['u'],g['grade']) for g in L]
line('ALL logged',it(B))
for m in ['Spread','Total','ML','TT Away','TT Home']: line('mkt '+m,it([g for g in B if g['mk']==m]))
def ob(o): return '<=-200' if o<=-200 else ('-199..-121' if o<=-121 else ('-120..+100' if o<=100 else ('+101..+199' if o<200 else '>=+200')))
for b in ['<=-200','-199..-121','-120..+100','+101..+199','>=+200']: line('odds '+b,it([g for g in B if ob(g['odds'])==b]))
for p in sorted({g['period'] for g in B}): line('period '+p,it([g for g in B if g['period']==p]))
def sideinfo(g):
    if g['mk']=='Spread': 
        away=g['side']=='Away'; fav=(g['U']<0)==away; return ('away' if away else 'home'),('fav' if fav else 'dog')
    if g['mk']=='ML':
        away=g['side']=='Away'; fav=(imp(g['J'])>imp(g['K']))==away; return ('away' if away else 'home'),('fav' if fav else 'dog')
    return None,None
for s in ['away','home']: line('spread/ML side '+s,it([g for g in B if sideinfo(g)[0]==s]))
for s in ['fav','dog']: line('spread/ML '+s,it([g for g in B if sideinfo(g)[1]==s]))
for s in ['Over','Under']: line('totals+TT '+s,it([g for g in B if g['side']==s]))
# outliers
pl=sorted([g['prof'] for g in B],reverse=True); stake=sum(g['u'] for g in B)
print('top3 wins',[round(x,2) for x in pl[:3]],'total',round(sum(pl),2),'without top3',round(sum(pl[3:]),2),'ROI w/o top3 %+.1f%%'%(100*sum(pl[3:])/(stake-sum(g['u'] for g in sorted(B,key=lambda g:-g['prof'])[:3]))))
print('top5 share of profit %.0f%%'%(100*sum(pl[:5])/sum(pl)))
print('close odds rows', sum(1 for g in G if g['close'] is not None))
# ---------- T5 model calibration
print('## T5 model accuracy')
def stats(name,pairs):
    e=[a-b for a,b in pairs]; n=len(e)
    print(f'| {name} | {n} | {sum(abs(x) for x in e)/n:.2f} | {math.sqrt(sum(x*x for x in e)/n):.2f} | {sum(e)/n:+.2f} |')
for per in ['ALL','A 10/20-10/30','B 10/31-11/11','C 11/12-11/16']:
    S=[g for g in G if (per=='ALL' or g['period']==per) and g['U'] is not None]
    stats(f'margin MODEL {per}',[((g['an']-g['hn']),(g['ap']-g['hp'])) for g in S])
    stats(f'margin MARKET {per}',[((g['an']-g['hn']),-g['U']) for g in S])
    T=[g for g in G if (per=='ALL' or g['period']==per) and g['P'] is not None]
    stats(f'total MODEL {per}',[((g['an']+g['hn']),g['Q']) for g in T])
    stats(f'total MARKET {per}',[((g['an']+g['hn']),g['P']) for g in T])
print('## ML Brier')
for per in ['ALL','A 10/20-10/30','B 10/31-11/11','C 11/12-11/16']:
    S=[g for g in G if (per=='ALL' or g['period']==per) and g['J'] and g['K'] and g['mlpa'] is not None]
    y=[1 if g['an']>g['hn'] else 0 for g in S]
    mod=[g['mlpa'] for g in S]; mkt=[imp(g['J'])/(imp(g['J'])+imp(g['K'])) for g in S]
    bm=sum((p-o)**2 for p,o in zip(mod,y))/len(S); bk=sum((p-o)**2 for p,o in zip(mkt,y))/len(S)
    ll=lambda ps: -sum(o*math.log(max(1e-6,p))+(1-o)*math.log(max(1e-6,1-p)) for p,o in zip(ps,y))/len(S)
    print(f'| {per} | {len(S)} | model {bm:.4f} | market {bk:.4f} | logloss model {ll(mod):.3f} market {ll(mkt):.3f} |')
print('## ML calibration (model prob of the side it favors)')
S=[g for g in G if g['J'] and g['K'] and g['mlpa'] is not None]
bk=collections.defaultdict(list)
for g in S:
    p=g['mlpa']; fav_away=p>=.5; pp=p if fav_away else 1-p; won=(g['an']>g['hn'])==fav_away
    mk=imp(g['J'])/(imp(g['J'])+imp(g['K'])); mk=mk if fav_away else 1-mk
    b='50-60' if pp<.6 else '60-70' if pp<.7 else '70-80' if pp<.8 else '80-90' if pp<.9 else '90+'
    bk[b].append((pp,mk,won))
for b in ['50-60','60-70','70-80','80-90','90+']:
    L=bk[b]; n=len(L)
    if n: print(f'| {b} | {n} | model avg {100*sum(x[0] for x in L)/n:.1f}% | market avg {100*sum(x[1] for x in L)/n:.1f}% | actual {100*sum(x[2] for x in L)/n:.1f}% | {flag(n)} |')
# ---------- T6 disagreement
print('## T6 model-side ATS by disagreement (at recorded odds, 1u)')
def spread_pick(g):
    gap=(g['ap']-g['hp'])+g['U']   # >0 model likes away
    acov=(g['an']-g['hn'])+g['U']
    if acov==0: return None
    side_away=gap>0; won=(acov>0)==side_away; o=g['W'] if side_away else g['Z']
    return abs(gap),(dec(o) if won else -1,1,won)
for per in ['ALL','B+C 10/31-11/16']:
    S=[g for g in G if g['U'] is not None and g['W'] and g['Z'] and (per=='ALL' or g['period']!='A 10/20-10/30')]
    buck=collections.defaultdict(list)
    for g in S:
        r=spread_pick(g)
        if not r: continue
        gap,x=r; b='0-1.5' if gap<1.5 else '1.5-3' if gap<3 else '3-6' if gap<6 else '6+'
        buck[b].append(x)
    for b in ['0-1.5','1.5-3','3-6','6+']: line(f'spread gap {b} ({per})',buck[b])
for per in ['ALL','B+C 10/31-11/16']:
    S=[g for g in G if g['P'] is not None and g['S'] and g['T'] and (per=='ALL' or g['period']!='A 10/20-10/30')]
    buck=collections.defaultdict(list)
    for g in S:
        tot=g['an']+g['hn']
        if tot==g['P']: continue
        gap=g['Q']-g['P']; over=gap>0; won=(tot>g['P'])==over; o=g['S'] if over else g['T']
        b=('model Over ' if over else 'model Under ')+('0-3' if abs(gap)<3 else '3-6' if abs(gap)<6 else '6+')
        buck[b].append((dec(o) if won else -1,1,won))
    for b in sorted(buck): line(f'total {b} ({per})',buck[b])
# ---------- T7 market segments (ATS, at recorded odds, 1u on the named side)
print('## T7 segments: betting the named side every time')
def ats(g,away):
    acov=(g['an']-g['hn'])+g['U']
    if acov==0: return None
    won=(acov>0)==away; o=g['W'] if away else g['Z']; return (dec(o) if won else -1,1,won)
S=[g for g in G if g['U'] is not None and g['W'] and g['Z']]
seg=collections.defaultdict(list)
for g in S:
    for away in (True,False):
        x=ats(g,away)
        if not x: continue
        fav=(g['U']<0)==away; tag='away' if away else 'home'
        seg['home side' if not away else 'away side'].append(x)
        seg[('fav' if fav else 'dog')].append(x)
        spr=abs(g['U'])
        if fav: seg['fav '+('<=4.5' if spr<=4.5 else '5-9.5' if spr<10 else '10+')].append(x)
        mb2b=g['ab2b'] if away else g['hb2b']; ob2b=g['hb2b'] if away else g['ab2b']
        if mb2b and not ob2b: seg['team on B2B vs rested ('+tag+')'].append(x)
        mo=g['aout'] if away else g['hout']; oo=g['hout'] if away else g['aout']
        if mo is not None and oo is not None:
            if len(mo)>0 and len(oo)==0: seg['team missing 30+mpg player, opp full'].append(x)
            if len(mo)==0 and len(oo)>0: seg['team full, opp missing 30+mpg player'].append(x)
for k in ['home side','away side','fav','dog','fav <=4.5','fav 5-9.5','fav 10+','team on B2B vs rested (home)','team on B2B vs rested (away)','team missing 30+mpg player, opp full','team full, opp missing 30+mpg player']:
    line(k,seg[k])
bl=[g for g in G if abs(g['an']-g['hn'])>=20]; print('blowouts 20+:',len(bl),'of',len(G))
fav10=[g for g in S if abs(g['U'])>=10]; print('10+ favs:',len(fav10),'won outright',sum(1 for g in fav10 if ((g['an']>g['hn'])==(g['U']<0))),'covered',sum(1 for g in fav10 if (ats(g,g['U']<0) or (0,0,False))[2]))
mo=[g for g in G if g['aout'] is not None and g['hout'] is not None]; print('games with key-out proxy computed',len(mo),'of',len(G))

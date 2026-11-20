import pickle,collections,math
picks,G=pickle.load(open('work/crafted.pkl','rb'))
alias={}
def rec(xs): 
    w=sum(1 for x in xs if x>0); l=sum(1 for x in xs if x<0); p=sum(1 for x in xs if x==0)
    return f"{w}-{l}-{p} ({w/(w+l)*100:.0f}%)" if w+l else '0-0'
def units(xs): return sum(0.909 if x>0 else (-1 if x<0 else 0) for x in xs)
rows=[]
for p in picks:
    g=G.get((p['d'],p['a'],p['h']))
    if not g: continue
    am=g['ap']-g['hp']; tot=g['ap']+g['hp']; res=1 if p['res']=='Win' else -1
    if p['mk']=='Spread':
        away = p['team']==p['a']
        ours = (am if away else -am) + p['line']      # our projected cover margin for their side at their line
        mkt = g['mkt_away']
        rows.append(dict(mk='Spread',d=p['d'],era=g['era'],res=res,ours=ours,agree=ours>0,game=(p['d'],p['a'],p['h']),side=('away' if away else 'home'),
                         fav=p['line']<0))
    else:
        ours=(tot-p['line'])*(1 if p['ou']=='Over' else -1)
        rows.append(dict(mk='Total',d=p['d'],era=g['era'],res=res,ours=ours,agree=ours>0,game=(p['d'],p['a'],p['h']),side=p['ou']))
out=[]
for mk in ('Spread','Total'):
    xs=[r for r in rows if r['mk']==mk]
    out.append(f"\n== {mk}: CraftedNBA picks we matched {rec([r['res'] for r in xs])}")
    for lab,f in [('our model agrees (projects their side to cover their line)',lambda r:r['agree']),
                  ('our model agrees by 1+ pt (spread) / 2+ pt (total)',lambda r:r['ours']>=(1 if mk=='Spread' else 2)),
                  ('our model disagrees',lambda r:not r['agree'])]:
        ys=[r for r in xs if f(r)]; out.append(f"   {lab:62s} {len(ys):3d}  {rec([r['res'] for r in ys])}")
    for era in ('old','roster'):
        ys=[r for r in xs if r['era']==era]; ag=[r for r in ys if r['agree']]
        out.append(f"   {era:6s} era: their picks {rec([r['res'] for r in ys])}; we agreed on {len(ag)}/{len(ys)} -> {rec([r['res'] for r in ag])}")
    if mk=='Spread':
        for s in ('away','home'): out.append(f"   their {s} picks {rec([r['res'] for r in xs if r['side']==s])}")
        for s in (True,False): out.append(f"   their {'favorite' if s else 'underdog'} picks {rec([r['res'] for r in xs if r['fav']==s])}")
    else:
        for s in ('Over','Under'): out.append(f"   their {s} picks {rec([r['res'] for r in xs if r['side']==s])}")
# our own picks under their rule, graded at our Novig lines
ours_sp=[];ours_tot=[]; detail=collections.defaultdict(list)
for k,g in G.items():
    if g['an'] is None or not isinstance(g['an'],(int,float)): continue
    am=g['ap']-g['hp']; ac=g['an']-g['hn']
    if g['mkt_away'] is not None:
        gap=am-g['mkt_away']
        if abs(gap)>=1:
            side_away=gap>0; line=-g['mkt_away'] if side_away else g['mkt_away']
            m=(ac if side_away else -ac)+line; r=(m>0)-(m<0); ours_sp.append(r); detail[('sp',g['era'])].append(r)
            detail[('sp_side','away' if side_away else 'home')].append(r)
            band='1-3' if abs(gap)<3 else ('3-6' if abs(gap)<6 else '6+'); detail[('sp_gap',band)].append(r)
    if isinstance(g['P'],(int,float)):
        gap=(g['ap']+g['hp'])-g['P']
        if abs(gap)>=2:
            t=g['an']+g['hn']; r=((t-g['P'])*(1 if gap>0 else -1)); r=(r>0)-(r<0); ours_tot.append(r); detail[('tot',g['era'])].append(r)
            detail[('tot_side','Over' if gap>0 else 'Under')].append(r)
            band='2-3' if abs(gap)<3 else ('3-6' if abs(gap)<6 else '6+'); detail[('tot_gap',band)].append(r)
out.append(f"\n== OUR model with their rule (spread 1+ off, total 2+ off), our Novig lines, scored games 10/20-11/7")
out.append(f"   spreads {rec(ours_sp)}  {units(ours_sp):+.1f}u at -110 | totals {rec(ours_tot)}  {units(ours_tot):+.1f}u")
for k in sorted(detail): out.append(f"   {k}: {rec(detail[k])}")
# head to head overlap on same games
same=collections.Counter()
for r in rows:
    pass
print('\n'.join(out))
pickle.dump(rows,open('work/crafted_rows.pkl','wb'))

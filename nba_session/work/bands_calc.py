import json,math,itertools,collections
L=json.load(open('work/bands_legs.json'))
def band(v,cuts,fmt):
    if v is None: return None
    for i,c in enumerate(cuts):
        if v<c: return (i,fmt[i])
    return (len(cuts),fmt[-1])
def cutlab(cuts,unit='',pre=''):
    labs=[f"< {pre}{cuts[0]:g}{unit}"]+[f"{pre}{a:g} to {pre}{b:g}{unit}" for a,b in zip(cuts,cuts[1:])]+[f"{pre}{cuts[-1]:g}{unit}+"]
    return labs
def odds_band(o,prop):
    if prop.startswith('ML'):
        cuts=[(-250,'-250 or shorter'),(-150,'-249 to -150'),(-110,'-149 to -111'),(111,'-110 to +110'),(200,'+111 to +199')]
        for i,(c,l) in enumerate(cuts):
            if (o<=c if i==0 else o<c): return (i,l)
        return (5,'+200 or longer')
    cuts=[(-120,'-120 or shorter'),(-106,'-119 to -107'),(106,'-106 to +105'),(120,'+106 to +119')]
    for i,(c,l) in enumerate(cuts):
        if (o<=c if i==0 else o<c): return (i,l)
    return (4,'+120 or longer')
DIMS=collections.OrderedDict()
pc=[30,40,45,50,55,60,65,70]
DIMS['Model win %']=lambda l:band(l['model']*100,pc,cutlab(pc,'%'))
DIMS['Market no-vig %']=lambda l:band(l['nv']*100,pc,cutlab(pc,'%'))
DIMS['Odds']=lambda l:odds_band(l['odds'],l['prop'])
ec=[-8,-4,0,4,8,12]
DIMS['Edge']=lambda l:band(l['edge']*100,ec,cutlab(ec,'%'))
evc=[-10,0,5,10,20]
DIMS['EV per unit']=lambda l:band(l['ev']*100,evc,cutlab(evc,'%'))
gc=[-6,-3,0,3,6,10]
DIMS['Projection vs line (pts, bet direction)']=lambda l:band(l['gap'],gc,cutlab(gc,' pts'))
def linef(l):
    p=l['prop']
    if p.startswith('ML'): 
        return None
    if p.startswith('Spread'):
        v=l['line']; c=[-8.5,-4.5,-0.1,4.6,8.6]; labs=['Fav by 9+','Fav 5 to 8.5','Fav 0.5 to 4.5','Dog 0.5 to 4.5','Dog 5 to 8.5','Dog 9+']
        return band(v,c,labs)
    if p.startswith('Total'):
        return band(l['line'],[215,222,229,236],['< 215','215 to 221.5','222 to 228.5','229 to 235.5','236+'])
    return band(l['line'],[105,110,115,120],['< 105','105 to 109.5','110 to 114.5','115 to 119.5','120+'])
DIMS['Line']=linef
DIMS['Model vs market margin gap']=lambda l:band(abs(l['disM']) if l['disM'] is not None else None,[2,4,6],['0 to 2 pts','2 to 4 pts','4 to 6 pts','6+ pts'])
DIMS['Model vs market total gap']=lambda l:band(abs(l['disT']) if l['disT'] is not None else None,[3,6],['0 to 3 pts','3 to 6 pts','6+ pts'])
DIMS['Current-season weight']=lambda l:band(l['cw'],[0.001,0.15,0.3],['0 (prior only)','0.01 to 0.15','0.15 to 0.30','0.30+'])
DIMS['Favorite / underdog (price)']=lambda l:(0,'Favorite (minus odds)') if l['fav'] else (1,'Underdog (plus odds)')
DIMS['Model version']=lambda l:{'Old team model (10/20-10/29)':(0,'Old team model (10/20-10/29)'),'Injury v2 (10/30)':(1,'Injury v2 (10/30)'),'Roster model (10/31+)':(2,'Roster model (10/31+)')}[l['era']]
DIMS['On model card']=lambda l:(0,'On card') if l['card'] else (1,'Not on card')
PROPS=['ML Away','ML Home','Spread Away','Spread Home','Total Over','Total Under','Away TT Over','Away TT Under','Home TT Over','Home TT Under']
FILTERS={'all':lambda l:True,'model':lambda l:l['edge']>0,'card':lambda l:l['card']}
def stats(xs):
    w=sum(1 for l in xs if l['res']>0); lo=sum(1 for l in xs if l['res']<0); p=len(xs)-w-lo
    dec=[l for l in xs if l['res']!=0]
    exp=sum(l['nv'] for l in dec); var=sum(l['nv']*(1-l['nv']) for l in dec)
    u=sum(l['units'] for l in xs)
    return dict(n=len(xs),w=w,l=lo,p=p,win=(w/(w+lo) if w+lo else None),model=sum(l['model'] for l in xs)/len(xs),
                mkt=sum(l['nv'] for l in xs)/len(xs),units=round(u,2),roi=u/len(xs),z=((w-exp)/math.sqrt(var) if var>0 else None))
out={'props':PROPS,'dims':list(DIMS),'filters':list(FILTERS),'single':{},'pairs':{},'overall':{}}
for f,ff in FILTERS.items():
    for p in PROPS:
        xs=[l for l in L if l['prop']==p and ff(l)]
        out['overall'][f'{f}|{p}']=stats(xs) if xs else None
        for d,fn in DIMS.items():
            g=collections.defaultdict(list)
            for l in xs:
                b=fn(l)
                if b: g[b].append(l)
            out['single'][f'{f}|{p}|{d}']=[dict(band=b[1],order=b[0],**stats(v)) for b,v in sorted(g.items())]
        for d1,d2 in itertools.combinations(DIMS,2):
            g=collections.defaultdict(list)
            for l in xs:
                b1=DIMS[d1](l); b2=DIMS[d2](l)
                if b1 and b2: g[(b1,b2)].append(l)
            if g: out['pairs'][f'{f}|{p}|{d1}|{d2}']=[dict(b1=k[0][1],o1=k[0][0],b2=k[1][1],o2=k[1][0],**stats(v)) for k,v in sorted(g.items())]
# prop groups overall
json.dump(out,open('work/bands_out.json','w'))
print('single tables',len(out['single']),'pair tables',len(out['pairs']))
# quick view: model-side single tables for a few
for p in PROPS:
    s=out['overall'][f'model|{p}']; a=out['overall'][f'all|{p}']; c=out['overall'][f'card|{p}']
    f=lambda s:f"{s['w']}-{s['l']}-{s['p']} {s['units']:+.1f}u z{s['z']:+.1f}" if s else '-'
    print(f"{p:14s} model side {f(s):28s} card {f(c)}")

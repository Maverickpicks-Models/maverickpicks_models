import json,numpy as np,collections
G=json.load(open('work/deep_games.json'))
def dec(o): return 100/-o if o<0 else o/100
def am(o):  # american from odds value in tracking (already american)
    return o
def leg(res,odds): return (1 if res>0 else (-1 if res<0 else 0), (dec(odds) if res>0 else (-1 if res<0 else 0)) if odds else (0.909 if res>0 else (-1 if res<0 else 0)))
def sgn(x): return (x>0)-(x<0)
S=collections.defaultdict(list)
def add(name,g,res,odds): S[name].append((g['era'],)+leg(res,odds))
for g in G:
    A,H=g['an'],g['hn']; amg=A-H; tot=A+H
    if g['U'] is not None:
        cov_a=sgn(amg+g['U']); cov_h=-cov_a
        U=g['U']
        # S1 road B2B
        if g['a_b2b'] and not g['h_b2b']:
            add('S1 Home spread when only the away team is on a B2B',g,cov_h,g['Z'])
            if g['AA'] is not None: add('S1b Away TT Under when only away is on a B2B',g,sgn(g['AA']-A),g['AD'])
        if g['h_b2b'] and not g['a_b2b']:
            add('S1c Away spread when only the home team is on a B2B',g,cov_a,g['W'])
        if g['a_b2b'] and g['h_b2b']: pass
        # S2 juice
        nv=g['nv_away_sp']
        if nv is not None:
            fav_side = 'a' if nv>0.5 else 'h'
            p=max(nv,1-nv)
            r=cov_a if fav_side=='a' else cov_h; o=g['W'] if fav_side=='a' else g['Z']
            if p>=0.52: add('S2 Spread side Novig prices 52%+ (juiced side)',g,r,o)
            if 0.505<=p<0.52: add('S2b Spread side Novig prices 50.5-52%',g,r,o)
        # S5 structure
        if U<=-9.5: add('S5 Away favorite of 9.5+ covers',g,cov_a,g['W'])
        if U>=9.5: add('S5b Home favorite of 9.5+ covers',g,cov_h,g['Z'])
        if U>=9.5: add('S5c Away dog of 9.5+ covers',g,cov_a,g['W'])
        if U<=-9.5: add('S5d Home dog of 9.5+ covers',g,cov_h,g['Z'])
        if 0<U<=4.5: add('S5e Away dog 0.5-4.5',g,cov_a,g['W'])
        if -4.5<=U<0: add('S5f Home dog 0.5-4.5',g,cov_h,g['Z'])
        if U<0: add('S5g Road favorite (any)',g,cov_a,g['W'])
        if U>0: add('S5h Home favorite (any)',g,cov_h,g['Z'])
        # S8 fade model disagreement
        dm=(g['ap']-g['hp'])-(-U)   # >0 model likes away more than market
        if abs(dm)>=6:
            r=cov_h if dm>0 else cov_a; o=g['Z'] if dm>0 else g['W']
            add('S8 Fade model when 6+ pts off the spread',g,r,o)
        if 2<=abs(dm)<4:
            r=cov_a if dm>0 else cov_h; o=g['W'] if dm>0 else g['Z']
            add('S8b Follow model when 2-4 pts off the spread',g,r,o)
        if 3<=abs(dm)<6:
            r=cov_a if dm>0 else cov_h; o=g['W'] if dm>0 else g['Z']
            add('S8c Follow model when 3-6 pts off the spread',g,r,o)
    if g['P'] is not None:
        ov=sgn(tot-g['P'])
        add('S7 Every game Under',g,-ov,g['T'])
        if g['P']>=235: add('S6 Under when total 235+',g,-ov,g['T'])
        if g['P']<220: add('S6b Over when total under 220',g,ov,g['S'])
        nvo=g['nv_over']
        if nvo is not None and max(nvo,1-nvo)>=0.52:
            side=ov if nvo>0.5 else -ov; o=g['S'] if nvo>0.5 else g['T']
            add('S2c Total side Novig prices 52%+',g,side,o)
        dt=(g['ap']+g['hp'])-g['P']
        if abs(dt)>=6: add('S8d Fade model total when 6+ off',g,(-ov if dt>0 else ov),(g['T'] if dt>0 else g['S']))
        # S3 TT vs total consistency
        if g['AA'] is not None and g['AE'] is not None:
            diff=g['AA']+g['AE']-g['P']
            if diff>=1.5: add('S3 TT lines sum 1.5+ ABOVE game total: game Over',g,ov,g['S']); add('S3 TT lines sum 1.5+ ABOVE game total: both TT Unders',g,sgn(g['AA']-A),g['AD']); S['S3 TT lines sum 1.5+ ABOVE game total: both TT Unders'].append((g['era'],)+leg(sgn(g['AE']-H),g['AH']))
            if diff<=-1.5: add('S3b TT lines sum 1.5+ BELOW game total: game Under',g,-ov,g['T']); add('S3b TT lines sum 1.5+ BELOW game total: both TT Overs',g,sgn(A-g['AA']),g['AC']); S['S3b TT lines sum 1.5+ BELOW game total: both TT Overs'].append((g['era'],)+leg(sgn(H-g['AE']),g['AG']))
        # S4 spread-implied TT vs TT line
        if g['U'] is not None and g['AA'] is not None and g['AE'] is not None:
            ia=g['P']/2-g['U']/2; ih=g['P']/2+g['U']/2
            for line,imp_,act,o_over,o_under in ((g['AA'],ia,A,g['AC'],g['AD']),(g['AE'],ih,H,g['AG'],g['AH'])):
                if line-imp_>=1.5: add('S4 TT line 1.5+ above spread-implied: TT Under',g,sgn(line-act),o_under)
                if imp_-line>=1.5: add('S4b TT line 1.5+ below spread-implied: TT Over',g,sgn(act-line),o_over)
    # ML
    if g['nv_ml_away'] is not None and g['J'] is not None:
        p=g['nv_ml_away']; aw_win=sgn(amg)
        if p>=0.75: add('S9 ML away favorite 75%+',g,aw_win,g['J'])
        if p<=0.25: add('S9b ML home favorite 75%+',g,-aw_win,g['K'])
        if 0.40<=p<=0.60:
            add('S9c ML home side in 40-60% games',g,-aw_win,g['K'])
def rep(xs):
    w=sum(1 for x in xs if x[1]>0); l=sum(1 for x in xs if x[1]<0); u=sum(x[2] for x in xs)
    return w,l,u
print(f"{'strategy':58s} {'all':>16s} {'old (10/20-30)':>18s} {'roster (10/31+)':>18s}")
for k in sorted(S):
    xs=S[k]; a=rep(xs); o=rep([x for x in xs if x[0]=='old']); r=rep([x for x in xs if x[0]=='roster'])
    f=lambda t:f"{t[0]}-{t[1]} {t[2]:+5.1f}u"
    print(f"{k:58s} {f(a):>16s} {f(o):>18s} {f(r):>18s}")

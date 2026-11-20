import json,collections,sys
live=len(sys.argv)>1
H=json.load(open('work/rule_hits.json'))
if live: H=[h for h in H if h['d']>='2026-11-12']
def dec(o): return 100/-o if o<0 else o/100
P=collections.defaultdict(lambda:dict(rules=set(),won=None,odds=None))
for h in H:
    k=(h['gid'],h['mk'],h['side']); p=P[k]; p['rules'].add(h['rule']); p['won']=h['won']; p['odds']=h['odds']; p['d']=h['d']
def avoid_hit(k,p):
    g,mk,side=k; r=p['rules']
    return any(x.startswith('X') for x in r)
def summ(name,items):
    if not items: print(f'{name:55s}   --'); return
    w=sum(p['won'] for p in items); l=len(items)-w; pl=sum(dec(p['odds']) if p['won'] else -1 for p in items)
    print(f'{name:55s} {w:3d}-{l:<3d} {100*w/len(items):5.1f}%  ROI {100*pl/len(items):+6.1f}%')
plays={k:p for k,p in P.items() if k[1] in('spread','total')}
pos=lambda p:{r for r in p['rules'] if r[0] in 'CT'}
core=lambda p:{r for r in p['rules'] if r[0]=='C'}
test=lambda p:{r for r in p['rules'] if r[0]=='T'}
X=lambda p:{r for r in p['rules'] if r[0]=='X'}
pp={k:p for k,p in plays.items() if pos(p)}
# conflicts: opposite side in same market with positive rules
opp={'away':'home','home':'away','over':'under','under':'over'}
conf={k for k in pp if (k[0],k[1],opp[k[2]]) in pp}
print('== By number of rules agreeing (spread/total, positive rules, no conflict)')
clean={k:p for k,p in pp.items() if k not in conf}
for n in (1,2,3):
    summ(f'{n}{"+" if n==3 else ""} rule(s)',[p for p in clean.values() if (len(pos(p))>=3 if n==3 else len(pos(p))==n)])
print('== Core count')
for n in (0,1,2):
    summ(f'{n} core rules (any tests)',[p for p in clean.values() if len(core(p))==n])
print('== Core alone vs core + test')
summ('1 core, no test',[p for p in clean.values() if len(core(p))==1 and not test(p)])
summ('1 core + 1 test',[p for p in clean.values() if len(core(p))==1 and len(test(p))==1])
summ('1 core + 2+ tests',[p for p in clean.values() if len(core(p))==1 and len(test(p))>=2])
summ('2 core (+any)',[p for p in clean.values() if len(core(p))>=2])
print('== Test only')
for n in (1,2,3):
    summ(f'test only, {n}{"+" if n==3 else ""} tests',[p for p in clean.values() if not core(p) and (len(test(p))>=3 if n==3 else len(test(p))==n)])
print('== By market')
for mk in ('spread','total'):
    for n in (1,2,3):
        summ(f'{mk}: {n}{"+" if n==3 else ""} rules',[p for k,p in clean.items() if k[1]==mk and (len(pos(p))>=3 if n==3 else len(pos(p))==n)])
print('== Positive rule + an avoid rule on the same side')
summ('play also flagged by an X rule',[p for p in clean.values() if X(p)])
summ('play with no X flag',[p for p in clean.values() if not X(p)])
print('== Conflicts (rules on both sides of a market)')
cl=[pp[k] for k in conf]; summ('each side, all conflicted plays',cl)
cc=[pp[k] for k in conf if len(pos(pp[k]))>len(pos(pp[(k[0],k[1],opp[k[2]])]))]
summ('side with MORE rules in a conflict',cc)
cc2=[pp[k] for k in conf if core(pp[k]) and not core(pp[(k[0],k[1],opp[k[2]])])]
summ('core side vs test-only side (core side)',cc2)
print('== Spread + ML on same team')
ML={(k[0],k[2]):p for k,p in P.items() if k[1]=='ml'}
summ('spread play where C3 ML backs same team',[p for k,p in clean.items() if k[1]=='spread' and (k[0],k[2]) in ML])
summ('spread play where C3 ML backs other team',[p for k,p in clean.items() if k[1]=='spread' and (k[0],opp[k[2]]) in ML])
summ('C3 ML where a spread rule backs same team',[ML[(k[0],k[2])] for k,p in clean.items() if k[1]=='spread' and (k[0],k[2]) in ML])
summ('C3 ML where a spread rule backs other team',[ML[(k[0],opp[k[2]])] for k,p in clean.items() if k[1]=='spread' and (k[0],opp[k[2]]) in ML])
print('== Most common combos (2+ rules)')
cnt=collections.defaultdict(list)
for p in clean.values():
    if len(pos(p))>=2: cnt['+'.join(sorted(pos(p)))].append(p)
for c,L in sorted(cnt.items(),key=lambda x:-len(x[1]))[:12]: summ('  '+c,L)

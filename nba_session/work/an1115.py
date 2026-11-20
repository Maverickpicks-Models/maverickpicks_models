import json,collections
G=json.load(open('work/deep_games15.json'))
def pay(o): return 100/-o if o<0 else o/100
def rec(lst):
    w=sum(1 for x in lst if x>0); l=sum(1 for x in lst if x<0); return f"{w}-{l}"
# away cover amount
for g in G:
    if g['U'] is not None: g['ac']=(g['an']-g['hn'])+g['U']
# 1. B2B team ATS vs rested opp
print("== B2B team ATS (vs rested opp)")
for era in ['old','roster','all']:
    L=[];Lsu=[];Lh=[];La=[]
    for g in G:
        if g['U'] is None or g['a_b2b']==g['h_b2b'] or (era!='all' and g['era']!=era): continue
        c=g['ac'] if g['a_b2b'] else -g['ac']; L.append(c)
        (La if g['a_b2b'] else Lh).append(c)
    print(era,'ATS',rec(L),'avg cover %.1f'%(sum(L)/len(L)),'| B2B home',rec(Lh),'B2B road',rec(La))
# model margin error on B2B team games: model vs actual
E=[];Eo=[]
for g in G:
    if g['a_b2b']==g['h_b2b']: continue
    mm=g['hp']-g['ap']; am=g['hn']-g['an']; e=am-mm
    E.append(e if g['h_b2b'] else -e)   # positive = B2B team did better than model
print('B2B team vs model: avg %.1f n=%d'%(sum(E)/len(E),len(E)), ' roster era:', '%.1f'%(sum(e for e,g in zip(E,[g for g in G if g['a_b2b']!=g['h_b2b']]) if g['era']=='roster')/sum(1 for g in G if g['a_b2b']!=g['h_b2b'] and g['era']=='roster')))
# vs market
E2=[(g['ac'] if g['a_b2b'] else -g['ac']) for g in G if g['U'] is not None and g['a_b2b']!=g['h_b2b']]
# 2. ML favorites by no-vig bucket
print("== ML favorites by no-vig prob")
B=collections.defaultdict(list)
for g in G:
    p=g['nv_ml_away']
    if p is None: continue
    for side,pp,o,won in [('a',p,g['J'],g['an']>g['hn']),('h',1-p,g['K'],g['hn']>g['an'])]:
        if pp<0.6 or o is None: continue
        b='60-70' if pp<.7 else '70-80' if pp<.8 else '80-87' if pp<.87 else '87+'
        u=0.25/pay(o)  # stake to win .25
        B[b].append((won, 0.25 if won else -u, u))
        B['all'].append((won, 0.25 if won else -u, u))
for b in ['60-70','70-80','80-87','87+','all']:
    x=B[b]; n=len(x); w=sum(1 for t in x if t[0]); pl=sum(t[1] for t in x); st=sum(t[2] for t in x)
    print(b,f"{w}-{n-w}",'win%%=%.0f'%(100*w/n),'P/L %.2fu'%pl,'ROI %.1f%%'%(100*pl/st))
# 3. road favorites under 8 ATS
print("== Road favs <8 ATS")
for era in ['old','roster']:
    L=[g['ac'] for g in G if g['U'] is not None and -8<g['U']<0 and g['era']==era]
    print(era,rec(L))
# road fav <8 when road team rested and home team on B2B
L=[g['ac'] for g in G if g['U'] is not None and -8<g['U']<0 and g['h_b2b'] and not g['a_b2b']]
print('road fav<8 vs home B2B',rec(L))
L=[g['ac'] for g in G if g['U'] is not None and -8<g['U']<0 and not g['h_b2b']]
print('road fav<8 home not B2B',rec(L))

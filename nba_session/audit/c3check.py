exec(open('audit/angles34.py').read().split('# ---------- ANGLE 4')[0].split("print(f'ML vs spread fit")[0])
import collections
B=collections.defaultdict(list)
for r in rows:
    g=r['g']; p=max(r['p_ml'],1-r['p_ml'])
    if p<.6 or p>.87: continue
    fa=r['p_ml']>=.5; o=g['J'] if fa else g['K']; won=(g['an']>g['hn'])==fa
    risk=min(1,.25/dec(o)); pl=risk*dec(o) if won else -risk
    s=abs(g['U']); sb='<=4.5' if s<=4.5 else '5-9.5' if s<10 else '10+'
    pb='60-65' if p<.65 else '65-75' if p<.75 else '75-87'
    B[(pb,sb)].append((pl,risk,won)); B[('ALL',sb)].append((pl,risk,won)); B[(pb,'ALL')].append((pl,risk,won))
    if not (.65<=p<.75) and sb!='5-9.5': B[('RULE both filters','')].append((pl,risk,won))
    if sb!='5-9.5': B[('RULE spread filter only','')].append((pl,risk,won))
    if not (.65<=p<.75): B[('RULE price filter only','')].append((pl,risk,won))
    B[('RULE current','')].append((pl,risk,won))
for k in sorted(B):
    L=B[k]; w=sum(x[2] for x in L); pl=sum(x[0] for x in L); st=sum(x[1] for x in L)
    print(k,f'{w}-{len(L)-w}','%+.2fu ROI %+.1f%%'%(pl,100*pl/st))

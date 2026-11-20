exec(open('audit/angles34.py').read().split('# ---------- ANGLE 4')[0].split("print(f'ML vs spread fit")[0])
for name,cond in [('road fav <=4.5',lambda g:g['U']<0 and -g['U']<=4.5),('home fav <=4.5',lambda g:g['U']>0 and g['U']<=4.5),('road fav 5-7.5',lambda g:g['U']<0 and 5<=-g['U']<8)]:
    L=[];L2=[]
    for g in G:
        if g['U'] is None or not g['W'] or not cond(g): continue
        acov=(g['an']-g['hn'])+g['U']
        if acov==0: continue
        away=g['U']<0; won=(acov>0)==away; x=dec(g['W'] if away else g['Z']) if won else -1
        (L2 if g['d']>=dt.date(2026,10,31) else L).append(x)
    A=L+L2; w=sum(1 for x in A if x>0)
    print(name,f'{w}-{len(A)-w}','ROI %+.1f%%'%(100*sum(A)/len(A)),'| pre10/31 %+.1f%% n%d | 10/31+ %+.1f%% n%d'%(100*sum(L)/max(1,len(L)),len(L),100*sum(L2)/max(1,len(L2)),len(L2)))
# T10: ML fav spread<=4.5, nv 50-60
L=[]
for r in rows:
    g=r['g']; p=max(r['p_ml'],1-r['p_ml'])
    if abs(g['U'])>4.5 or p>=.6: continue
    fa=r['p_ml']>=.5; o=g['J'] if fa else g['K']; won=(g['an']>g['hn'])==fa; L.append((dec(o) if won else -1,g['d']))
w=sum(1 for x,_ in L if x>0); print('T10 ML fav <=4.5 nv<60',f'{w}-{len(L)-w}','ROI %+.1f%%'%(100*sum(x for x,_ in L)/len(L)),'| 10/31+',sum(1 for x,d in L if d>=dt.date(2026,10,31) and x>0),'-',sum(1 for x,d in L if d>=dt.date(2026,10,31) and x<0),'%+.1f%%'%(100*sum(x for x,d in L if d>=dt.date(2026,10,31))/max(1,sum(1 for x,d in L if d>=dt.date(2026,10,31)))))

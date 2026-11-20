import json,numpy as np
G=json.load(open('work/crafted_bt.json'))
def dec(o): return 100/-o if o<0 else o/100
act=np.array([g['an']-g['hn'] for g in G]); mkt=np.array([-g['U'] for g in G])
mod=np.array([g['ap']-g['hp'] for g in G]); cr=np.array([g['cr'] for g in G])
hca=np.array([-1.7+(1.75 if g['a_b2b'] else 0)*-1+(1.75 if g['h_b2b'] else 0) for g in G])
era=np.array([g['era'] for g in G])
# fit k: actual away margin ~ -k*cr + hca
k=np.linalg.lstsq(-cr[:,None],act-hca,rcond=None)[0][0]
print('n',len(G),'fitted k',round(k,2))
for kk in (0.5,0.67,k,1.0):
    imp=-kk*cr+hca
    print('k %.2f RMSE crafted %.2f | model %.2f | market %.2f'%(kk,np.sqrt(np.mean((imp-act)**2)),np.sqrt(np.mean((mod-act)**2)),np.sqrt(np.mean((mkt-act)**2))))
imp=-0.67*cr+hca
# residual test: does (crafted - market) predict (actual - market)?
gap=imp-mkt; res=act-mkt; mg=mod-mkt
for e in ('old','roster','all'):
    s=(era==e) if e!='all' else np.ones(len(G),bool)
    b=np.linalg.lstsq(np.c_[gap[s],mg[s],np.ones(s.sum())],res[s],rcond=None)[0]
    print(e,'n',s.sum(),'corr(crafted gap,res) %.2f  corr(model gap,res) %.2f  joint coef crafted %.2f model %.2f'%(np.corrcoef(gap[s],res[s])[0,1],np.corrcoef(mg[s],res[s])[0,1],b[0],b[1]))
def ats(mask,side):   # side +1 bet away, -1 bet home
    w=l=0;u=0
    for g,m,sd in zip(G,mask,side):
        if not m: continue
        cov=(g['an']-g['hn'])+g['U']   # away cover margin
        if cov==0: continue
        win=(cov>0) if sd>0 else (cov<0); o=g['W'] if sd>0 else g['Z']
        w+=win;l+=not win;u+=dec(o) if win else -1
    return f"{w}-{l} {u:+.1f}u"
side=np.sign(gap)
print('\nFollow replica Crafted when gap in band (all | old | roster):')
for lo,hi in ((0,1),(1,2),(2,3),(3,5),(5,99),(1,99),(2,99)):
    m=(abs(gap)>=lo)&(abs(gap)<hi)
    print(f'{lo}-{hi}',ats(m,side),'|',ats(m&(era=="old"),side),'|',ats(m&(era=="roster"),side))
agree=np.sign(gap)==np.sign(mg)
print('\nCrafted gap 1+ and our model same side:',ats((abs(gap)>=1)&agree,side),'| old',ats((abs(gap)>=1)&agree&(era=="old"),side),'| roster',ats((abs(gap)>=1)&agree&(era=="roster"),side))
print('Crafted gap 1+ and our model opposite:',ats((abs(gap)>=1)&~agree,side))
fav=np.array([(sd>0)==(g['U']<0) for g,sd in zip(G,side)])
print('Crafted gap 1+ on favorite',ats((abs(gap)>=1)&fav,side),' on dog',ats((abs(gap)>=1)&~fav,side))

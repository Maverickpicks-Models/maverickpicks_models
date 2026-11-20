import runpy,datetime as dt,numpy as np,io,contextlib
with contextlib.redirect_stdout(io.StringIO()): ns=runpy.run_path('work/xposs.py')
X,prof,n2c=ns['X'],ns['prof'],ns['n2c']
tov=np.array([x['tov'] for x in X]); q=np.quantile(tov,[1/3,2/3]); print('thirds',q.round(1))
import json
for g in json.load(open('work/run1111.json')):
    a,h=n2c[g['aw']],n2c[g['hm']]; d=dt.date(2026,11,11)
    pa,ph=prof(a,d),prof(h,d); t=pa['tov']+ph['ftov']+ph['tov']+pa['ftov']
    print(f"{a}@{h} {t:.1f}", 'LOW->Under' if t<q[0] else ('HIGH->Over' if t>=q[1] else 'mid'))

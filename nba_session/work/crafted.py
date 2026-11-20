import re,openpyxl,datetime,json,collections
lines=[l.strip() for l in open('crafted/c.txt') if l.strip()]
picks=[]
i=0
while i<len(lines):
    m=re.match(r'^(Oct|Nov) (\d+)$',lines[i])
    if m and i+3<len(lines) and '@' in lines[i+1]:
        mon=10 if m.group(1)=='Oct' else 11
        d=datetime.date(2026,mon,int(m.group(2)))
        a,h=lines[i+1].split(' @ ')
        mk=lines[i+2]; res=lines[i+3]
        if mk.startswith('Spread'):
            _,team,ln=mk.split(); picks.append(dict(d=d,a=a,h=h,mk='Spread',team=team,line=float(ln),res=res))
        else:
            _,ou,ln=mk.split(); picks.append(dict(d=d,a=a,h=h,mk='Total',ou=ou,line=float(ln),res=res))
        i+=4
    else: i+=1
print('crafted picks',len(picks),collections.Counter((p['mk'],p['res']) for p in picks))
wb=openpyxl.load_workbook('out_1108/chk.xlsx',data_only=True)
code={r[0]:r[1] for r in openpyxl.load_workbook('in1107/s.xlsx',read_only=True,data_only=True)['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}
alias={'GS':'GSW','SA':'SAS','NO':'NOP','NY':'NYK','UTAH':'UTA','WSH':'WAS','PHO':'PHX','BRK':'BKN','CHO':'CHA'}
ws=wb['Tracking']; G={}
for r in range(13,149):
    v=lambda c:ws.cell(r,c).value
    if not isinstance(v(1),datetime.datetime) or not isinstance(v(4),(int,float)): continue
    a,h=code.get(v(2)),code.get(v(3))
    U,X=v(21),v(24)
    sp = -U if (isinstance(U,(int,float)) and isinstance(X,(int,float)) and abs(U+X)<.01) else None  # market away margin
    G[(v(1).date(),a,h)]=dict(row=r,ap=v(4),hp=v(5),P=v(16),mkt_away=sp,an=v(40),hn=v(41),
        era='roster' if v(1).date()>=datetime.date(2026,10,31) else 'old')
json.dump({'picks':[{**p,'d':str(p['d'])} for p in picks]},open('work/crafted_picks.json','w'))
import pickle; pickle.dump((picks,G),open('work/crafted.pkl','wb'))
miss=[p for p in picks if (p['d'],alias.get(p['a'],p['a']),alias.get(p['h'],p['h'])) not in G]
print('unmatched',len(miss),[(str(p['d']),p['a'],p['h']) for p in miss][:20])

import openpyxl,datetime,json,collections
ws=openpyxl.load_workbook('out_1115/MaverickPicks_NBA_Simulations.xlsx',data_only=True)['Tracking']
num=lambda v: float(v) if isinstance(v,(int,float)) else None
def imp(o): return -o/(-o+100) if o<0 else 100/(o+100)
def nv(a,b):
    if a is None or b is None or a==0 or b==0: return None
    x,y=imp(a),imp(b); v=x+y-1
    if v>0.11 or v<-0.02: return None
    return x/(x+y)
G=[]
for r in range(13,198):
    c=lambda k: ws.cell(r,k).value
    d=c(1)
    if not isinstance(d,datetime.datetime) or num(c(40)) is None or num(c(4)) is None: continue
    d=d.date(); U,X=num(c(21)),num(c(24))
    sp_ok = U is not None and X is not None and abs(U+X)<.01 and abs(U)<30
    g=dict(row=r,d=str(d),aw=c(2),hm=c(3),ap=num(c(4)),hp=num(c(5)),acw=num(c(6)),hcw=num(c(7)),
      an=num(c(40)),hn=num(c(41)),P=num(c(16)),R=num(c(18)),S=num(c(19)),T=num(c(20)),
      U=U if sp_ok else None,V=num(c(22)),W=num(c(23)),Z=num(c(26)),
      AA=num(c(27)),AB=num(c(28)),AC=num(c(29)),AD=num(c(30)),AE=num(c(31)),AF=num(c(32)),AG=num(c(33)),AH=num(c(34)),
      H=num(c(8)),J=num(c(10)),K=num(c(11)))
    g['nv_away_sp']=nv(g['W'],g['Z']) if sp_ok else None
    g['nv_over']=nv(g['S'],g['T'])
    g['nv_ml_away']=nv(g['J'],g['K'])
    g['nv_att_over']=nv(g['AC'],g['AD']) if g['AA'] else None
    g['nv_htt_over']=nv(g['AG'],g['AH']) if g['AE'] else None
    g['era']='roster' if d>=datetime.date(2026,10,31) else 'old'
    G.append(g)
# back-to-back flags from all known game dates (box scores + tracking)
wb=openpyxl.load_workbook('out_1115/MaverickPicks_NBA_Simulations.xlsx',read_only=True,data_only=True)
code={r[0]:r[1] for r in wb['TeamShooting'].iter_rows(min_row=7,max_row=36,values_only=True)}
def dd(x): return (datetime.date(1899,12,30)+datetime.timedelta(days=int(x))) if isinstance(x,(int,float)) else (x.date() if x else None)
played=set()
for row in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True):
    if row[0] and row[2] is not None: played.add((dd(row[2]),row[0]))
for g in G:
    played.add((datetime.date.fromisoformat(g['d']),code[g['aw']])); played.add((datetime.date.fromisoformat(g['d']),code[g['hm']]))
for g in G:
    d=datetime.date.fromisoformat(g['d']); y=d-datetime.timedelta(days=1)
    g['a_b2b']=(y,code[g['aw']]) in played; g['h_b2b']=(y,code[g['hm']]) in played
    g['ab'],g['hb']=code[g['aw']],code[g['hm']]
json.dump(G,open('work/deep_games15.json','w'))
print(len(G),'games', sum(g['era']=='roster' for g in G),'roster era', sum(g['U'] is not None for g in G),'with spread', sum(g['a_b2b'] or g['h_b2b'] for g in G),'with a B2B team')

import re, sys, os, shutil, zipfile, json
from xml.sax.saxutils import escape
SRC, OUT = sys.argv[1], sys.argv[2]
work=OUT+"_x"; shutil.rmtree(work,ignore_errors=True)
with zipfile.ZipFile(SRC) as z: z.extractall(work)
p=os.path.join(work,'xl/worksheets/sheet2.xml'); s=open(p,encoding='utf-8').read()
def col2n(c):
    n=0
    for ch in c: n=n*26+ord(ch)-64
    return n
def n2col(n):
    t=""
    while n: n,r=divmod(n-1,26); t=chr(65+r)+t
    return t
CELL_RE=re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)',re.S)
def set_vals(sheet,rownum,vals):
    m=re.search(rf'<row r="{rownum}"[^>]*?(?:/>|>.*?</row>)',sheet,re.S); row=m.group(0)
    head=re.match(r'<row [^>]*?>',row).group(0)
    cells={}; order=[]
    for c in CELL_RE.finditer(row):
        cells[c.group(1)]=c.group(0); order.append(c.group(1))
    for col,v in vals.items():
        old=cells.get(col,f'<c r="{col}{rownum}"/>')
        sattr=re.search(r' s="(\d+)"',old); st=f' s="{sattr.group(1)}"' if sattr else ''
        if isinstance(v,str): cells[col]=f'<c r="{col}{rownum}"{st} t="inlineStr"><is><t xml:space="preserve">{escape(v)}</t></is></c>'
        else: cells[col]=f'<c r="{col}{rownum}"{st}><v>{repr(float(v)) if isinstance(v,float) else v}</v></c>'
        if col not in order: order.append(col)
    body="".join(cells[k] for k in sorted(order,key=col2n))
    return sheet[:m.start()]+head+body+"</row>"+sheet[m.end():]
D=json.load(open('work/run1118_530.json'))
fl=lambda v: f"+{v:g}" if v>0 else f"-{abs(v):g}"
B=json.load(open('work/bets_1118.json'))
BETS={}
for x in B: BETS.setdefault((x['aw'],x['hm']),[]).append((x['market'],x['side'],x['odds'],x['units'],x['rules']))
SC={('Houston Rockets','Indiana Pacers'):(119,104),('Memphis Grizzlies','Cleveland Cavaliers'):(124,121),('Milwaukee Bucks','Miami Heat'):(130,137),
('Philadelphia 76ers','Orlando Magic'):(121,116),('Washington Wizards','Toronto Raptors'):(103,99),('Chicago Bulls','Brooklyn Nets'):(137,107),
('Detroit Pistons','New Orleans Pelicans'):(122,109),('Atlanta Hawks','Oklahoma City Thunder'):(117,112),('Golden State Warriors','Dallas Mavericks'):(94,116),
('Boston Celtics','Denver Nuggets'):(101,105),('Utah Jazz','Los Angeles Lakers'):(109,97),('Phoenix Suns','Sacramento Kings'):(128,107)}
TAGS=json.load(open('work/rule_tags_backfill.json'))
s=set_vals(s,12,{'AW':'Rules'})
for r,t in TAGS.items(): s=set_vals(s,int(r),{'AW':t['rules']})
ROW=[232]
for i,g in enumerate(D):
    L={x['lab']:x for x in g['legs']}
    asp=g['sp'][0]; aw,hm=g['aw'],g['hm']; T=g['tot'][0]
    mla,mlh=L[f'{aw} ML'],L[f'{hm} ML']; spa,sph=L[f'{aw} {asp:+g}'],L[f'{hm} {-asp:+g}']
    ov,un=L[f'Over {T}'],L[f'Under {T}']
    keys=[(mla,f"ML {aw}"),(mlh,f"ML {hm}"),(spa,f"Spread {aw} {fl(asp)}"),(sph,f"Spread {hm} {fl(-asp)}"),(ov,f"Total Over {T:g}"),(un,f"Total Under {T:g}")]
    v={'A':46344,'B':aw,'C':hm,'D':g['ap'],'E':g['hp'],'F':g['acw'],'G':g['hcw'],'H':mla['model'],'I':mlh['model'],'J':mla['odds'],'K':mlh['odds'],
       'L':mla['edge'],'M':mlh['edge'],'N':mla['units'],'O':mlh['units'],'P':T,'Q':g['ap']+g['hp'],'R':ov['model'],'S':ov['odds'],'T':un['odds'],
       'U':asp,'V':spa['model'],'W':spa['odds'],'X':-asp,'Y':sph['model'],'Z':sph['odds']}
    if g['att'] and g['htt']:
        A_,H_=g['att'][0],g['htt'][0]
        ato,atu,hto,htu=L[f'{aw} TT Over {A_}'],L[f'{aw} TT Under {A_}'],L[f'{hm} TT Over {H_}'],L[f'{hm} TT Under {H_}']
        keys+=[(ato,f"TT {aw} Over {A_:g}"),(atu,f"TT {aw} Under {A_:g}"),(hto,f"TT {hm} Over {H_:g}"),(htu,f"TT {hm} Under {H_:g}")]
        v.update({'AA':A_,'AB':ato['model'],'AC':ato['odds'],'AD':atu['odds'],'AE':H_,'AF':hto['model'],'AG':hto['odds'],'AH':htu['odds']})
    v['AI']=' | '.join(k for x,k in keys if x['card']) or 'No plays'
    v['AN'],v['AO']=SC[(aw,hm)]
    for b in BETS.get((aw,hm),[None]):
        vv=dict(v)
        if b: mk,sd,od,u,ru=b; vv.update({'AJ':mk,'AK':sd,'AL':od,'AM':u,'AW':ru})
        s=set_vals(s,ROW[0],vv); print(ROW[0],aw,'@',hm,'|',vv.get('AJ',''),vv.get('AK',''),vv.get('AM','')); ROW[0]+=1
open(p,'w',encoding='utf-8').write(s)
wbp=os.path.join(work,'xl/workbook.xml'); w=open(wbp).read(); w=re.sub(r'<calcPr[^>]*/>','<calcPr calcId="191028" fullCalcOnLoad="1"/>',w); open(wbp,'w').write(w)
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for root,_,files in os.walk(work):
        for fn in files: full=os.path.join(root,fn); z.write(full,os.path.relpath(full,work))
print('ok')

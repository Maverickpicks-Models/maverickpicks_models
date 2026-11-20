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
D=json.load(open('work/run1109b.json'))
fl=lambda v: f"+{v:g}" if v>0 else f"-{abs(v):g}"
BETS={('Los Angeles Lakers','Atlanta Hawks'):('Spread','Away',100,0.5),
      ('Washington Wizards','Detroit Pistons'):('Spread','Home',108,0.5),
      ('Memphis Grizzlies','Toronto Raptors'):('Spread','Home',-113,0.5),
      ('Indiana Pacers','Dallas Mavericks'):('Spread','Away',-106,0.5),
      ('Denver Nuggets','Houston Rockets'):('Total','Under',111,0.5),
      ('New Orleans Pelicans','Golden State Warriors'):('Spread','Away',-104,0.5)}
for i,g in enumerate(D):
    L={x['lab']:x for x in g['legs']}
    asp=g['sp'][0]; aw,hm=g['aw'],g['hm']; T=g['tot'][0]
    mla,mlh=L[f'{aw} ML'],L[f'{hm} ML']; spa,sph=L[f'{aw} {asp:+g}'],L[f'{hm} {-asp:+g}']
    ov,un=L[f'Over {T}'],L[f'Under {T}']
    keys=[(mla,f"ML {aw}"),(mlh,f"ML {hm}"),(spa,f"Spread {aw} {fl(asp)}"),(sph,f"Spread {hm} {fl(-asp)}"),(ov,f"Total Over {T:g}"),(un,f"Total Under {T:g}")]
    v={'A':46335,'B':aw,'C':hm,'D':g['ap'],'E':g['hp'],'F':g['acw'],'G':g['hcw'],'H':mla['model'],'I':mlh['model'],'J':mla['odds'],'K':mlh['odds'],
       'L':mla['edge'],'M':mlh['edge'],'N':mla['units'],'O':mlh['units'],'P':T,'Q':g['ap']+g['hp'],'R':ov['model'],'S':ov['odds'],'T':un['odds'],
       'U':asp,'V':spa['model'],'W':spa['odds'],'X':-asp,'Y':sph['model'],'Z':sph['odds']}
    if g['att']:
        A_,H_=g['att'][0],g['htt'][0]
        ato,atu,hto,htu=L[f'{aw} TT Over {A_}'],L[f'{aw} TT Under {A_}'],L[f'{hm} TT Over {H_}'],L[f'{hm} TT Under {H_}']
        keys+=[(ato,f"TT {aw} Over {A_:g}"),(atu,f"TT {aw} Under {A_:g}"),(hto,f"TT {hm} Over {H_:g}"),(htu,f"TT {hm} Under {H_:g}")]
        v.update({'AA':A_,'AB':ato['model'],'AC':ato['odds'],'AD':atu['odds'],'AE':H_,'AF':hto['model'],'AG':hto['odds'],'AH':htu['odds']})
    v['AI']=' | '.join(k for x,k in keys if x['card']) or 'No plays'
    if (aw,hm) in BETS:
        mk,sd,od,u=BETS[(aw,hm)]; v.update({'AJ':mk,'AK':sd,'AL':od,'AM':u})
    s=set_vals(s,156+i,v); print(156+i,aw,'@',hm,'|',v.get('AJ',''),v.get('AK',''))
open(p,'w',encoding='utf-8').write(s)
wbp=os.path.join(work,'xl/workbook.xml'); w=open(wbp).read(); w=re.sub(r'<calcPr[^>]*/>','<calcPr calcId="191028" fullCalcOnLoad="1"/>',w); open(wbp,'w').write(w)
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for root,_,files in os.walk(work):
        for fn in files: full=os.path.join(root,fn); z.write(full,os.path.relpath(full,work))
print('ok')

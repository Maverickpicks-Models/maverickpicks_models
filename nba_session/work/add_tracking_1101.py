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
# 10/31 rows
D=json.load(open('work/run1101.json'))
fl=lambda v: f"+{v:g}" if v>0 else f"-{abs(v):g}"
for i,g in enumerate(D):
    L=g['legs']; mla,mlh,spa,sph,ov,un,ato,atu,hto,htu=L
    asp=g['sp'][0]
    keys=[(mla,f"ML {g['aw']}"),(mlh,f"ML {g['hm']}"),(spa,f"Spread {g['aw']} {fl(asp)}"),(sph,f"Spread {g['hm']} {fl(-asp)}"),
          (ov,f"Total Over {g['tot'][0]:g}"),(un,f"Total Under {g['tot'][0]:g}"),(ato,f"TT {g['aw']} Over {g['att'][0]:g}"),(atu,f"TT {g['aw']} Under {g['att'][0]:g}"),
          (hto,f"TT {g['hm']} Over {g['htt'][0]:g}"),(htu,f"TT {g['hm']} Under {g['htt'][0]:g}")]
    card=' | '.join(k for x,k in keys if x['card']) or 'No plays'
    v={'A':46327,'B':g['aw'],'C':g['hm'],'D':g['ap'],'E':g['hp'],'F':g['acw'],'G':g['hcw'],'H':mla['model'],'I':mlh['model'],'J':mla['odds'],'K':mlh['odds'],
       'L':mla['edge'],'M':mlh['edge'],'N':mla['units'],'O':mlh['units'],'P':g['tot'][0],'Q':g['ap']+g['hp'],'R':ov['model'],'S':ov['odds'],'T':un['odds'],
       'U':asp,'V':spa['model'],'W':spa['odds'],'X':-asp,'Y':sph['model'],'Z':sph['odds'],'AA':g['att'][0],'AB':ato['model'],'AC':ato['odds'],'AD':atu['odds'],
       'AE':g['htt'][0],'AF':hto['model'],'AG':hto['odds'],'AH':htu['odds'],'AI':card}
    s=set_vals(s,101+i,v); print(101+i,g['aw'],'@',g['hm'],'|',card)
open(p,'w',encoding='utf-8').write(s)
wbp=os.path.join(work,'xl/workbook.xml'); w=open(wbp).read(); w=re.sub(r'<calcPr[^>]*/>','<calcPr calcId="191028" fullCalcOnLoad="1"/>',w); open(wbp,'w').write(w)
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for root,_,files in os.walk(work):
        for fn in files: full=os.path.join(root,fn); z.write(full,os.path.relpath(full,work))
print('ok')

import re, sys, os, shutil, zipfile, json
sys.argv=[sys.argv[0]]+sys.argv[1:]
SRC,OUT,first,scores=sys.argv[1],sys.argv[2],int(sys.argv[3]),json.loads(sys.argv[4])
work=OUT+"_x"; shutil.rmtree(work,ignore_errors=True)
with zipfile.ZipFile(SRC) as z: z.extractall(work)
p=os.path.join(work,'xl/worksheets/sheet2.xml'); s=open(p,encoding='utf-8').read()
def col2n(c):
    n=0
    for ch in c: n=n*26+ord(ch)-64
    return n
CELL_RE=re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)',re.S)
def set_vals(sheet,rownum,vals):
    m=re.search(rf'<row r="{rownum}"[^>]*?(?:/>|>.*?</row>)',sheet,re.S); row=m.group(0)
    head=re.match(r'<row [^>]*?>',row).group(0)
    cells={}; order=[]
    for c in CELL_RE.finditer(row): cells[c.group(1)]=c.group(0); order.append(c.group(1))
    for col,v in vals.items():
        old=cells.get(col,f'<c r="{col}{rownum}"/>'); sattr=re.search(r' s="(\d+)"',old); st=f' s="{sattr.group(1)}"' if sattr else ''
        cells[col]=f'<c r="{col}{rownum}"{st}><v>{v}</v></c>'
        if col not in order: order.append(col)
    return sheet[:m.start()]+head+"".join(cells[k] for k in sorted(order,key=col2n))+"</row>"+sheet[m.end():]
for i,(a,h) in enumerate(scores): s=set_vals(s,first+i,{'AN':a,'AO':h})
open(p,'w',encoding='utf-8').write(s)
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for root,_,files in os.walk(work):
        for fn in files: full=os.path.join(root,fn); z.write(full,os.path.relpath(full,work))
print('ok')

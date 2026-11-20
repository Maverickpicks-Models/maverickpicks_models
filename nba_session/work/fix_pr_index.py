import re,sys
from xml.sax.saxutils import escape
d=sys.argv[1]
p=d+'/xl/worksheets/sheet18.xml'; s=open(p).read()
def unesc(x): return x.replace('&lt;','<').replace('&gt;','>').replace('&quot;','"').replace('&amp;','&')
T={col:unesc(re.search(r'<c r="%s20"[^>]*><f>(.*?)</f>'%col,s).group(1)) for col in 'ABDEFMN'}
for c,f in T.items(): assert '#REF' not in f,(c,f)
def build(col,r):
    f=re.sub(r"'26-27NBAPlayer'!\$([A-Z]+)\d+\b",lambda m:f"INDEX('26-27NBAPlayer'!${m.group(1)}:${m.group(1)},ROW()-4)",T[col])
    f=re.sub(r"\$([A-Z]+)20\b",lambda m:'$'+m.group(1)+str(r),f)
    return f
n=0
def fix(m):
    global n
    col,r,attrs=m.group(1),int(m.group(2)),m.group(3)
    if col not in T or not (6<=r<=805): return m.group(0)
    n+=1
    return f'<c r="{col}{r}"{attrs}><f>{escape(build(col,r))}</f></c>'
s=re.sub(r'<c r="([A-Z]+)(\d+)"([^>]*?)>(?:<f>[^<]*</f>|<f [^>]*/>|<f [^>]*>[^<]*</f>)(?:<v>[^<]*</v>|<v/>)?</c>',fix,s)
open(p,'w').write(s); print('rewritten',n,'REF left',s.count('#REF!')); print(build('A',51)); print(build('M',51)[-120:])

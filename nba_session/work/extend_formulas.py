"""Copy Tracking's per-row formulas from row SRC_ROW down to rows SRC_ROW+1..LAST (in place).
usage: python3 work/extend_formulas.py book.xlsx 320 360"""
import re, sys, os, shutil, zipfile, openpyxl, warnings
from xml.sax.saxutils import escape
warnings.filterwarnings('ignore')
fn, src, last = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
wb = openpyxl.load_workbook(fn, read_only=True)
row = list(wb['Tracking'].iter_rows(min_row=src, max_row=src))[0]
F = {c.column_letter: c.value for c in row if isinstance(c.value, str) and c.value.startswith('=')}
wb.close()
X = fn + '_ext'; shutil.rmtree(X, ignore_errors=True)
with zipfile.ZipFile(fn) as z: z.extractall(X)
p = X + '/xl/worksheets/sheet2.xml'; s = open(p, encoding='utf-8').read()
def col2n(c):
    n = 0
    for ch in c: n = n * 26 + ord(ch) - 64
    return n
for r in range(src + 1, last + 1):
    m = re.search(rf'<row r="{r}"[^>]*?(?:/>|>.*?</row>)', s, re.S)
    if m:
        row_xml = m.group(0)
        if row_xml.endswith('/>'): row_xml = row_xml[:-2] + '></row>'
    else:
        row_xml = f'<row r="{r}"></row>'
    head = re.match(r'<row [^>]*?>', row_xml).group(0)
    cells = {mm.group(1): mm.group(0) for mm in re.finditer(rf'<c r="([A-Z]+){r}"[^>]*?(?:/>|>.*?</c>)', row_xml, re.S)}
    for col, f in F.items():
        if col in cells and '<f' in cells[col]: continue
        if col in cells and '<v>' in cells[col]: continue          # a value someone typed: keep
        f2 = re.sub(rf'(?<=[A-Z$]){src}(?!\d)', str(r), f[1:])
        st = re.search(rf'<c r="{col}{src}" s="(\d+)"', s); st = f' s="{st.group(1)}"' if st else ''
        cells[col] = f'<c r="{col}{r}"{st}><f>{escape(f2)}</f></c>'
    new = head + ''.join(cells[k] for k in sorted(cells, key=col2n)) + '</row>'
    if m:
        s = s[:m.start()] + new + s[m.end():]
    else:   # insert in order
        nxt = None
        for mm in re.finditer(r'<row r="(\d+)"', s):
            if int(mm.group(1)) > r: nxt = mm.start(); break
        s = s[:nxt] + new + s[nxt:] if nxt else s.replace('</sheetData>', new + '</sheetData>')
open(p, 'w', encoding='utf-8').write(s)
os.remove(fn)
with zipfile.ZipFile(fn, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(X):
        for f_ in files:
            full = os.path.join(root, f_); z.write(full, os.path.relpath(full, X))
shutil.rmtree(X)
print('formula columns', sorted(F), 'extended to', last)

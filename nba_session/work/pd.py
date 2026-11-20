import openpyxl, re, unicodedata
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c)).lower().replace('.','').replace("'",'').strip()
def load(path='in14/nba.xlsx'):
    ws=openpyxl.load_workbook(path,data_only=True)['PlayerDefense']
    out={}
    for r in ws.iter_rows(min_row=2,values_only=True):
        m=re.match(r'(.+?)([A-Z]{2,3}) \| (\S+)$',str(r[1]))
        if not m: continue
        out[norm(m.group(1))]=dict(name=m.group(1),team=m.group(2),pos=m.group(3),age=r[2],mp=r[3],pm=r[14],drdb=r[15],dtov=r[16],md=r[10],vr=r[9])
    return out

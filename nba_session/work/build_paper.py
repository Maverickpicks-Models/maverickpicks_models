"""Add automatic paper grading of every card play to the MaverickPicks NBA workbook.
Edits the xlsx XML directly so charts, conditional formatting and validation survive."""
import re, sys, os, shutil, zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1], sys.argv[2]
work = OUT + "_x"
shutil.rmtree(work, ignore_errors=True)
with zipfile.ZipFile(SRC) as z: z.extractall(work)
P = lambda p: os.path.join(work, p)
rd = lambda p: open(P(p), encoding="utf-8").read()
def wr(p, s): open(P(p), "w", encoding="utf-8").write(s)

def col2n(c):
    n = 0
    for ch in c: n = n*26 + ord(ch)-64
    return n
def n2col(n):
    s = ""
    while n: n, r = divmod(n-1, 26); s = chr(65+r)+s
    return s

# ---------- cell builders ----------
def cf(ref, s, f): return f'<c r="{ref}" s="{s}"><f>{escape(f)}</f></c>'
def cs(ref, s, t): return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{escape(t)}</t></is></c>'
def cn(ref, s, v): return f'<c r="{ref}" s="{s}"><v>{v}</v></c>'

CELL_RE = re.compile(r'<c r="([A-Z]+)(\d+)"[^>]*?(?:/>|>.*?</c>)', re.S)
def set_cells(sheet, rownum, new, spans=None):
    """new: dict col -> cell xml (replaces/inserts), keeps column order."""
    m = re.search(rf'<row r="{rownum}"[^>]*?(?:/>|>.*?</row>)', sheet, re.S)
    row = m.group(0)
    head = re.match(r'<row [^>]*?>', row).group(0) if not row.endswith('/>') else row[:-2] + '>'
    cells = {c.group(1): c.group(0) for c in CELL_RE.finditer(row)}
    cells.update(new)
    if spans: head = re.sub(r'spans="[^"]*"', f'spans="{spans}"', head)
    body = "".join(cells[k] for k in sorted(cells, key=col2n))
    return sheet[:m.start()] + head + body + "</row>" + sheet[m.end():]

# ================= TRACKING (sheet2) =================
t = rd("xl/worksheets/sheet2.xml")
FIRST, LAST = 13, 312
R = lambda c: f"${c}${FIRST}:${c}${LAST}"

# side definitions: col, header, market label, key expr, margin expr
SIDES = [
 ("BA","P: ML away",   'ML',      '"ML "&$B{r}&" |"',                              '$AN{r}-$AO{r}',        '$J{r}'),
 ("BB","P: ML home",   'ML',      '"ML "&$C{r}&" |"',                              '$AO{r}-$AN{r}',        '$K{r}'),
 ("BC","P: Spr away",  'Spread',  '"Spread "&$B{r}&" "&TEXT($U{r},"+0.0;-0.0")&" |"', '$AN{r}-$AO{r}+$U{r}', '$W{r}'),
 ("BD","P: Spr home",  'Spread',  '"Spread "&$C{r}&" "&TEXT($X{r},"+0.0;-0.0")&" |"', '$AO{r}-$AN{r}+$X{r}', '$Z{r}'),
 ("BE","P: Over",      'Total',   '"Total Over "&TEXT($P{r},"0.0")&" |"',          '$AN{r}+$AO{r}-$P{r}',  '$S{r}'),
 ("BF","P: Under",     'Total',   '"Total Under "&TEXT($P{r},"0.0")&" |"',         '$P{r}-$AN{r}-$AO{r}',  '$T{r}'),
 ("BG","P: TT away O", 'TT Away', '"TT "&$B{r}&" Over "&TEXT($AA{r},"0.0")&" |"',  '$AN{r}-$AA{r}',        '$AC{r}'),
 ("BH","P: TT away U", 'TT Away', '"TT "&$B{r}&" Under "&TEXT($AA{r},"0.0")&" |"', '$AA{r}-$AN{r}',        '$AD{r}'),
 ("BI","P: TT home O", 'TT Home', '"TT "&$C{r}&" Over "&TEXT($AE{r},"0.0")&" |"',  '$AO{r}-$AE{r}',        '$AG{r}'),
 ("BJ","P: TT home U", 'TT Home', '"TT "&$C{r}&" Under "&TEXT($AE{r},"0.0")&" |"', '$AE{r}-$AO{r}',        '$AH{r}'),
]
SPANS = "1:63"

# header row 12
hdr = {"AW": cs("AW12",63,"Paper plays"), "AX": cs("AX12",63,"Paper W"), "AY": cs("AY12",63,"Paper L"),
       "AZ": cs("AZ12",63,"Paper u"), "BK": cs("BK12",63,"Game first row")}
for c,h,*_ in SIDES: hdr[c] = cs(f"{c}12",63,h)
t = set_cells(t, 12, hdr, SPANS)

# home-spread data fix (feed bug: price landed in the line) — rows read below
import openpyxl
wb = openpyxl.load_workbook(SRC, data_only=True); ws = wb["Tracking"]
fixed_rows = []
for r in range(FIRST, LAST+1):
    new = {}
    U, X, V = ws[f"U{r}"].value, ws[f"X{r}"].value, ws[f"V{r}"].value
    if isinstance(U,(int,float)) and isinstance(X,(int,float)) and abs(X+U) > 0.01 and isinstance(V,(int,float)):
        new["X"] = cn(f"X{r}", 67, repr(-U)); new["Y"] = cn(f"Y{r}", 31, repr(1-V)); fixed_rows.append(r)
    new["BK"] = cf(f"BK{r}", 69, f'IF($A{r}="","",COUNTIFS($A${FIRST}:$A{r},$A{r},$B${FIRST}:$B{r},$B{r},$C${FIRST}:$C{r},$C{r}))')
    for c,_,_,key,marg,odds in SIDES:
        k, m, o = key.format(r=r), marg.format(r=r), odds.format(r=r)
        f = (f'IF(OR($BK{r}<>1,$AN{r}="",$AO{r}="",ISERROR(SEARCH({k},$AI{r}&" |"))),"",'
             f'IF({m}>0,IF({o}<0,100/ABS({o}),{o}/100),IF({m}<0,-1,0)))')
        new[c] = cf(f"{c}{r}", 50, f)
    rng = f"$BA{r}:$BJ{r}"
    new["AW"] = cf(f"AW{r}", 69, f'IF(COUNT({rng})=0,"",COUNT({rng}))')
    new["AX"] = cf(f"AX{r}", 69, f'IF($AW{r}="","",COUNTIF({rng},">0"))')
    new["AY"] = cf(f"AY{r}", 69, f'IF($AW{r}="","",COUNTIF({rng},"<0"))')
    new["AZ"] = cf(f"AZ{r}", 50, f'IF($AW{r}="","",SUM({rng}))')
    t = set_cells(t, r, new, SPANS)

# ---- summary blocks (rows 3-9) ----
NR = '"<>Paper"'  # (kept for clarity; real block reads the bet columns, which hold only real bets)
t = set_cells(t, 3, {"A": cs("A3",29,"REAL BETS · from the bet columns (AJ:AM)"),
                     "T": cs("T3",29,"PAPER · every card play, auto-graded at 1u flat (AW:BJ)")})
# market table T:X, headline Z:AE
t = set_cells(t, 4, {"T": cs("T4",17,"Market"), "U": cs("U4",18,"Bets"), "V": cs("V4",18,"Wins"),
                     "W": cs("W4",18,"Units"), "X": cs("X4",18,"ROI"),
                     "Z": cs("Z4",41,"Bets"), "AA": cs("AA4",41,"Wins"), "AB": cs("AB4",41,"Losses"),
                     "AC": cs("AC4",41,"Pushes"), "AD": cs("AD4",41,"Units"), "AE": cs("AE4",41,"ROI")})
MK = [("ML","BA","BB"),("Spread","BC","BD"),("Total","BE","BF"),("TT Away","BG","BH"),("TT Home","BI","BJ")]
for i,(name,c1,c2) in enumerate(MK):
    r = 5+i; rg = f"${c1}${FIRST}:${c2}${LAST}"
    cells = {"T": cs(f"T{r}",48,name),
             "U": cf(f"U{r}",49,f"COUNT({rg})"),
             "V": cf(f"V{r}",49,f'COUNTIF({rg},">0")'),
             "W": cf(f"W{r}",50,f"SUM({rg})"),
             "X": cf(f"X{r}",33,f'IF(COUNTIF({rg},">0")+COUNTIF({rg},"<0")=0,"",SUM({rg})/(COUNTIF({rg},">0")+COUNTIF({rg},"<0")))')}
    if r == 5:
        cells.update({"Z": cf("Z5",42,f"SUM({R('AW')})"), "AA": cf("AA5",43,f"SUM({R('AX')})"),
                      "AB": cf("AB5",44,f"SUM({R('AY')})"), "AC": cf("AC5",45,"Z5-AA5-AB5"),
                      "AD": cf("AD5",46,f"SUM({R('AZ')})"), "AE": cf("AE5",47,'IF(AA5+AB5=0,"",AD5/(AA5+AB5))')})
    if r == 7:
        cells.update({"Z": cs("Z7",41,"Win %"), "AA": cs("AA7",41,"Units staked")})
    if r == 8:
        cells.update({"Z": cf("Z8",51,'IF(AA5+AB5=0,"",AA5/(AA5+AB5))'), "AA": cf("AA8",52,"AA5+AB5")})
    t = set_cells(t, r, cells)

# conditional formatting + validation stay; add CF for paper units
cfx = (f'<conditionalFormatting sqref="AZ{FIRST}:BJ{LAST} W5:W9 AD5"><cfRule type="cellIs" dxfId="3" priority="40" operator="greaterThan"><formula>0</formula></cfRule>'
       f'<cfRule type="cellIs" dxfId="2" priority="41" operator="lessThan"><formula>0</formula></cfRule></conditionalFormatting>')
t = t.replace("<dataValidations", cfx + "<dataValidations", 1)
t = re.sub(r'<dimension ref="[^"]*"/>', '<dimension ref="A1:BK314"/>', t)
# widths for the new columns
t = t.replace('<col min="49" max="60" width="13" style="2" customWidth="1"/>',
              '<col min="49" max="52" width="11" style="2" customWidth="1"/><col min="53" max="63" width="12" style="2" customWidth="1"/>')
wr("xl/worksheets/sheet2.xml", t)

# ================= RESULTS (sheet3) =================
s = rd("xl/worksheets/sheet3.xml")
s = set_cells(s, 3, {"A": cs("A3",79,"REAL BETS · money actually staked")})
s = set_cells(s, 11, {"G": cs("G11",77,"4. Real bets: fill Bet market, Bet side, Odds taken, Units. Paper plays grade themselves from the Card column.")})
s = set_cells(s, 16, {"A": cs("A16",79,"UNITS BY MARKET · real vs paper"), "G": cs("G16",79,"PROFIT BY REAL BET (units, log order)")})
s = set_cells(s, 33, {"A": cs("A33",79,"PAPER CARD · every play the card flagged, 1u flat, no money staked"),
                      **{c: f'<c r="{c}33" s="16"/>' for c in "BCDE"},
                      "G": cs("G33",77,"Use this to judge the model before you bet it. Pushes return the stake.")})
s = set_cells(s, 34, {"A": cs("A34",41,"Bets"), "C": cs("C34",41,"Wins"), "E": cs("E34",41,"Losses"),
                      "G": cs("G34",41,"Units"), "I": cs("I34",41,"ROI"), "K": cs("K34",41,"Win %")})
s = set_cells(s, 35, {"A": cf("A35",72,"Tracking!Z5"), "C": cf("C35",73,"Tracking!AA5"), "E": cf("E35",74,"Tracking!AB5"),
                      "G": cf("G35",75,"Tracking!AD5"), "I": cf("I35",76,"Tracking!AE5"), "K": cf("K35",76,"Tracking!Z8")})
s = re.sub(r'<row r="35"([^>]*)>', lambda m: '<row r="35"' + re.sub(r'\s(ht|customHeight)="[^"]*"','',m.group(1)) + ' ht="27.75" customHeight="1">', s, 1)
s = set_cells(s, 37, {"A": cs("A37",29,"PAPER BY MARKET"), **{c: f'<c r="{c}37" s="16"/>' for c in "BCDE"}})
s = set_cells(s, 38, {"A": cs("A38",17,"Market"), "B": cs("B38",18,"Bets"), "C": cs("C38",18,"Wins"),
                      "D": cs("D38",18,"Units"), "E": cs("E38",18,"ROI")})
for i in range(5):
    r, tr = 39+i, 5+i
    s = set_cells(s, r, {"A": cf(f"A{r}",48,f"Tracking!T{tr}"), "B": cf(f"B{r}",49,f"Tracking!U{tr}"),
                         "C": cf(f"C{r}",49,f"Tracking!V{tr}"), "D": cf(f"D{r}",78,f"Tracking!W{tr}"),
                         "E": cf(f"E{r}",33,f"Tracking!X{tr}")})
s = s.replace('<conditionalFormatting sqref="D9:D13">', '<conditionalFormatting sqref="D9:D13 D39:D43 G35">')
wr("xl/worksheets/sheet3.xml", s)

# ================= chart3: add Paper series + legend =================
c = rd("xl/charts/chart3.xml")
c = re.sub(r'<c:(num|str)Cache>.*?</c:(num|str)Cache>', '', c, flags=re.S)
c = c.replace('<c:tx><c:strRef><c:f>Results!$D$8</c:f></c:strRef></c:tx>', '<c:tx><c:v>Real</c:v></c:tx>')
ser = re.search(r'<c:ser>.*?</c:ser>', c, re.S).group(0)
ser2 = (ser.replace('<c:idx val="0"/><c:order val="0"/>','<c:idx val="1"/><c:order val="1"/>')
           .replace('<c:v>Real</c:v>','<c:v>Paper</c:v>').replace('FF7A18','38BDF8')
           .replace('Results!$D$9:$D$13','Results!$D$39:$D$43')
           .replace('{00000000-7AC6-4922-9D1E-644B7FE8663F}','{00000001-7AC6-4922-9D1E-644B7FE8663F}'))
c = c.replace(ser, ser + ser2, 1)
legend = ('<c:legend><c:legendPos val="b"/><c:overlay val="0"/><c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr>'
          '<a:defRPr sz="800" b="0"><a:solidFill><a:srgbClr val="8A94A8"/></a:solidFill><a:latin typeface="Arial"/></a:defRPr>'
          '</a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr></c:legend>')
c = c.replace('</c:plotArea><c:plotVisOnly', '</c:plotArea>' + legend + '<c:plotVisOnly', 1)
wr("xl/charts/chart3.xml", c)
c4 = rd("xl/charts/chart4.xml"); c4 = re.sub(r'<c:numCache>.*?</c:numCache>', '', c4, flags=re.S); wr("xl/charts/chart4.xml", c4)

# ================= workbook: recalc on open, drop calcChain =================
w = rd("xl/workbook.xml")
w = re.sub(r'<calcPr([^/]*)/>', lambda m: '<calcPr' + re.sub(r'\sfullCalcOnLoad="[^"]*"','',m.group(1)) + ' fullCalcOnLoad="1"/>', w)
wr("xl/workbook.xml", w)
os.remove(P("xl/calcChain.xml"))
rels = rd("xl/_rels/workbook.xml.rels"); rels = re.sub(r'<Relationship [^>]*calcChain[^>]*/>', '', rels); wr("xl/_rels/workbook.xml.rels", rels)
ct = rd("[Content_Types].xml"); ct = re.sub(r'<Override [^>]*calcChain[^>]*/>', '', ct); wr("[Content_Types].xml", ct)

# ---------- zip ----------
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        if item.filename == "xl/calcChain.xml": continue
        zout.write(P(item.filename), item.filename)
shutil.rmtree(work)
print("home-spread rows fixed:", fixed_rows)

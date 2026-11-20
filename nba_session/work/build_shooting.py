"""Add 3-point shooting-luck adjustment to the current-season team ratings.
New tabs: BoxScores (NBA.com player box scores), TeamBoxAdvanced (NBA.com team advanced box scores),
TeamShooting (formulas). Assumptions rows 43-46. Calculations B15:B16 / D15:D16 subtract the luck share.
XML edits so charts, conditional formatting and validation survive."""
import re, sys, os, shutil, zipfile, datetime
from xml.sax.saxutils import escape, unescape
import openpyxl

SRC, BOX, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
work = OUT + "_x"
shutil.rmtree(work, ignore_errors=True)
with zipfile.ZipFile(SRC) as z: z.extractall(work)
P = lambda p: os.path.join(work, p)
rd = lambda p: open(P(p), encoding="utf-8").read()
def wr(p, s): open(P(p), "w", encoding="utf-8").write(s)
def n2col(n):
    s = ""
    while n: n, r = divmod(n-1, 26); s = chr(65+r)+s
    return s
def cf(ref, s, f): return f'<c r="{ref}" s="{s}"><f>{escape(f)}</f></c>'
def cs(ref, s, t): return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{escape(str(t))}</t></is></c>'
def cn(ref, s, v): return f'<c r="{ref}" s="{s}"><v>{v}</v></c>'
S_TITLE, S_SUB, S_LABEL, S_HDR, S_NUM1, S_INT, S_KEY, S_BG, S_PCT = 39, 40, 4, 63, 36, 22, 88, 2, 31
EXCEL_EPOCH = datetime.datetime(1899, 12, 30)

# ---------- raw data sheets from the user's NBA.com export ----------
bwb = openpyxl.load_workbook(BOX, data_only=True)
def data_sheet(ws, date_cols, title):
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h).replace('\xa0', ' ') if h is not None else '' for h in rows[0]]
    out = []
    ncol = len(hdr)
    out.append(f'<row r="1" spans="1:{ncol}">' + "".join(cs(f"{n2col(i+1)}1", S_HDR, h) for i, h in enumerate(hdr)) + '</row>')
    for ri, r in enumerate(rows[1:], start=2):
        cells = []
        for ci, v in enumerate(r, start=1):
            ref = f"{n2col(ci)}{ri}"
            if v is None: continue
            if isinstance(v, datetime.datetime):
                cells.append(cn(ref, 0, (v - EXCEL_EPOCH).days))
            elif isinstance(v, (int, float)): cells.append(cn(ref, 0, v))
            else: cells.append(cs(ref, 0, str(v).replace('\xa0', ' ')))
        out.append(f'<row r="{ri}" spans="1:{ncol}">' + "".join(cells) + '</row>')
    last = f"{n2col(ncol)}{len(rows)}"
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
      f'<dimension ref="A1:{last}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
      '<sheetFormatPr defaultRowHeight="15"/><sheetData>' + "".join(out) + '</sheetData>'
      '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')
    return xml, hdr, len(rows)
box_xml, box_hdr, box_n = data_sheet(bwb['BoxScores'], [3], 'BoxScores')
adv_xml, adv_hdr, adv_n = data_sheet(bwb['TeamBoxScoresAdvanced'], [2], 'TeamBoxAdvanced')
assert box_hdr[1] == 'TEAM' and box_hdr[2] == 'MATCH UP' and box_hdr[10] == '3PM' and box_hdr[11] == '3PA', box_hdr
assert adv_hdr[0] == 'Team' and adv_hdr[4] == 'MIN' and adv_hdr[17] == 'PACE', adv_hdr

# ---------- Assumptions rows 43-46 ----------
A = rd("xl/worksheets/sheet3.xml")
NEW = [
 (44, "Shooting", "Remove 3-point shooting luck", "Yes", "Yes or No", "Current-season ORtg/DRtg (Calculations rows 15-16) lose the part of each team's and its opponents' 3-point % that is likely luck (TeamShooting tab).", "Box scores 10/31: 3-point % did not carry over from one half of the early season to the next (-0.18 offense, 0.05 defense)."),
 (45, "Shooting", "Team 3P% skill spread, offense", 0.015, "3P% SD", "How much teams truly differ in 3-point %. Luck share removed = sampling noise / (noise + this squared); shrinks as attempts pile up.", "About 1.5 points of 3P% between typical good and bad shooting teams."),
 (46, "Shooting", "Team 3P% skill spread, defense", 0.008, "3P% SD", "Same for 3-point % allowed. Defenses control it far less than offenses do, so more of it is treated as luck.", "Opponent 3P% is mostly noise even over a full season."),
]
rows = [f'<row r="43" spans="1:6" ht="24" customHeight="1">{cs("A43", 29, "SHOOTING LUCK  (current-season ratings, added 10/31)")}</row>']
for r, sec, name, val, unit, why, rat in NEW:
    vcell = cs(f"C{r}", 14, val) if isinstance(val, str) else cn(f"C{r}", 38 if r != 44 else 37, val)
    rows.append(f'<row r="{r}" spans="1:6" ht="36" customHeight="1">{cs(f"A{r}",80,sec)}{cs(f"B{r}",81,name)}{vcell}{cs(f"D{r}",82,unit)}{cs(f"E{r}",83,why)}{cs(f"F{r}",83,rat)}</row>')
A = A.replace("</sheetData>", "".join(rows) + "</sheetData>")
A = re.sub(r'<dataValidations count="(\d+)">', lambda m: f'<dataValidations count="{int(m.group(1))+1}"><dataValidation type="list" allowBlank="1" sqref="C44"><formula1>"Yes,No"</formula1></dataValidation>', A, count=1)
A = re.sub(r'<dimension ref="[^"]*"/>', '<dimension ref="A1:F46"/>', A)
wr("xl/worksheets/sheet3.xml", A)

# ---------- TeamShooting sheet ----------
BX = lambda c: f"BoxScores!${c}$2:${c}$5000"
AV = lambda c: f"TeamBoxAdvanced!${c}$2:${c}$1000"
cols = [("A","Team",24,S_LABEL),("B","Code",7,S_LABEL),("C","Games",7,S_INT),("D","Possessions",11,S_NUM1),
        ("E","3PM",7,S_INT),("F","3PA",7,S_INT),("G","3P%",8,S_PCT),("H","Opp 3PM",8,S_INT),("I","Opp 3PA",8,S_INT),("J","Opp 3P%",8,S_PCT),
        ("K","Off luck share",9,S_PCT),("L","Def luck share",9,S_PCT),("M","Off luck /100",9,S_NUM1),("N","Def luck /100",9,S_NUM1),("O","Net luck /100",9,S_KEY)]
LG = "$C$4"
tr = [f'<row r="1" spans="1:15" ht="30" customHeight="1">{cs("A1",S_TITLE,"3-POINT SHOOTING LUCK")}</row>',
      f'<row r="2" spans="1:15">{cs("A2",S_SUB,"From the BoxScores and TeamBoxAdvanced tabs (paste fresh NBA.com exports there, same columns). Luck = threes made above the league rate x 3, per 100 possessions, times the share of that gap that is likely noise. Calculations subtracts Off luck from current ORtg and Def luck from current DRtg when Assumptions C44 = Yes.")}</row>',
      f'<row r="4" spans="1:15">{cs("A4",S_LABEL,"League 3P%")}{cs("B4",S_LABEL,"")}' + cf("C4", S_PCT, "IFERROR(SUM($E$7:$E$36)/SUM($F$7:$F$36),0.35)") + '</row>',
      f'<row r="6" spans="1:15" ht="30" customHeight="1">' + "".join(cs(f"{c}6", S_HDR, h) for c, h, w, s in cols) + '</row>']
for i in range(30):
    r = 7 + i
    f = {
     "A": f"Teams!$D${2+i}", "B": f"Teams!$C${2+i}",
     "C": f'COUNTIFS({AV("A")},$B{r})',
     "D": f'SUMPRODUCT(({AV("A")}=$B{r})*N(+{AV("R")})*N(+{AV("E")}))/48',
     "E": f'SUMIFS({BX("K")},{BX("B")},$B{r})', "F": f'SUMIFS({BX("L")},{BX("B")},$B{r})',
     "G": f'IF($F{r}>0,$E{r}/$F{r},"")',
     "H": f'SUMIFS({BX("K")},{BX("C")},"*vs. "&$B{r})+SUMIFS({BX("K")},{BX("C")},"*@ "&$B{r})',
     "I": f'SUMIFS({BX("L")},{BX("C")},"*vs. "&$B{r})+SUMIFS({BX("L")},{BX("C")},"*@ "&$B{r})',
     "J": f'IF($I{r}>0,$H{r}/$I{r},"")',
     "K": f'IF($F{r}>0,({LG}*(1-{LG})/$F{r})/({LG}*(1-{LG})/$F{r}+Assumptions!$C$45^2),0)',
     "L": f'IF($I{r}>0,({LG}*(1-{LG})/$I{r})/({LG}*(1-{LG})/$I{r}+Assumptions!$C$46^2),0)',
     "M": f'IF($D{r}>0,$K{r}*($E{r}-{LG}*$F{r})*3/$D{r}*100,0)',
     "N": f'IF($D{r}>0,$L{r}*($H{r}-{LG}*$I{r})*3/$D{r}*100,0)',
     "O": f'$M{r}-$N{r}',
    }
    tr.append(f'<row r="{r}" spans="1:15">' + "".join(cf(f"{c}{r}", s, f[c]) for c, h, w, s in cols) + '</row>')
colxml = "<cols>" + "".join(f'<col min="{i+1}" max="{i+1}" width="{w}" style="{S_BG}" customWidth="1"/>' for i, (c, h, w, s) in enumerate(cols)) + f'<col min="16" max="30" width="8.7" style="{S_BG}" customWidth="1"/></cols>'
ts = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
 '<sheetPr><tabColor rgb="FFF5C451"/></sheetPr><dimension ref="A1:O36"/>'
 '<sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane ySplit="6" topLeftCell="A7" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
 '<sheetFormatPr defaultRowHeight="15"/>' + colxml + '<sheetData>' + "".join(tr) + '</sheetData>'
 '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')

# ---------- register 3 sheets ----------
existing = [int(x) for x in re.findall(r'sheet(\d+)\.xml', " ".join(os.listdir(P("xl/worksheets"))))]
nb, na, nt = max(existing) + 1, max(existing) + 2, max(existing) + 3
wr(f"xl/worksheets/sheet{nb}.xml", box_xml); wr(f"xl/worksheets/sheet{na}.xml", adv_xml); wr(f"xl/worksheets/sheet{nt}.xml", ts)
ct = rd("[Content_Types].xml")
for n in (nb, na, nt):
    ct = ct.replace("</Types>", f'<Override PartName="/xl/worksheets/sheet{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
wr("[Content_Types].xml", ct)
rels = rd("xl/_rels/workbook.xml.rels")
rids = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels)]; base = max(rids)
rels = rels.replace("</Relationships>", "".join(f'<Relationship Id="rId{base+k}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{n}.xml"/>' for k, n in ((1, nb), (2, na), (3, nt))) + "</Relationships>")
wr("xl/_rels/workbook.xml.rels", rels)
wb = rd("xl/workbook.xml")
sids = [int(x) for x in re.findall(r'sheetId="(\d+)"', wb)]
wb = wb.replace("</sheets>", f'<sheet name="TeamShooting" sheetId="{max(sids)+3}" r:id="rId{base+3}"/><sheet name="BoxScores" sheetId="{max(sids)+1}" r:id="rId{base+1}"/><sheet name="TeamBoxAdvanced" sheetId="{max(sids)+2}" r:id="rId{base+2}"/></sheets>')
wb = re.sub(r'<calcPr[^>]*/>', '<calcPr calcId="191028" fullCalcOnLoad="1"/>', wb)
wr("xl/workbook.xml", wb)

# ---------- Calculations hook ----------
C = rd("xl/worksheets/sheet5.xml")
def get_formula(sheet, ref):
    m = re.search(rf'<c r="{ref}"[^>]*?>.*?<f[^>]*>(.*?)</f>', sheet, re.S); return unescape(m.group(1))
def repl_formula(sheet, ref, new):
    m = re.search(rf'<c r="{ref}"([^>]*?)>(.*?)</c>', sheet, re.S)
    attrs = re.sub(r'\s*t="[^"]*"', '', m.group(1))
    return sheet[:m.start()] + f'<c r="{ref}"{attrs}><f>{escape(new)}</f></c>' + sheet[m.end():]
for col in ("B", "D"):
    for row, tcol in ((15, "M"), (16, "N")):
        old = get_formula(C, f"{col}{row}")
        new = f'{old}-IF(AND(Assumptions!$C$44="Yes",{col}$14>0),IFERROR(INDEX(TeamShooting!${tcol}$7:${tcol}$36,MATCH({col}$4,TeamShooting!$A$7:$A$36,0)),0),0)'
        C = repl_formula(C, f"{col}{row}", new)
wr("xl/worksheets/sheet5.xml", C)

if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(work):
        for fn in files:
            full = os.path.join(root, fn); z.write(full, os.path.relpath(full, work))
print("ok", OUT, "box rows", box_n, "adv rows", adv_n)

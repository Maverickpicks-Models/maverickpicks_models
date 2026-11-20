"""Add a roster-based (player) team rating to the MaverickPicks NBA workbook.
New sheets: PlayerRatings, TeamRatings. New Assumptions inputs rows 29-41.
Calculations prior ORtg/DRtg (B38:D39) switch to TeamRatings when Assumptions!C30 = "Roster".
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

def n2col(n):
    s = ""
    while n: n, r = divmod(n-1, 26); s = chr(65+r)+s
    return s
def col2n(c):
    n = 0
    for ch in c: n = n*26 + ord(ch)-64
    return n
def cf(ref, s, f): return f'<c r="{ref}" s="{s}"><f>{escape(f)}</f></c>'
def cs(ref, s, t): return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{escape(t)}</t></is></c>'
def cn(ref, s, v): return f'<c r="{ref}" s="{s}"><v>{v}</v></c>'

# style ids reused from the workbook (dark theme)
S_TITLE, S_SUB, S_SEC, S_LABEL, S_HDR = 39, 40, 29, 4, 63
S_NUM1, S_INT, S_NUM2, S_INPUT_T, S_INPUT_N, S_KEY = 36, 22, 88, 14, 37, 88
S_BG = 2

# ---------------- Assumptions inputs (sheet3) ----------------
A = rd("xl/worksheets/sheet3.xml")
NEW_INPUTS = [
 (30, "Roster", "Prior source", "Roster", "Roster or Team", "Roster = team prior built from players on the current roster (TeamRatings tab). Team = last season's team ratings regressed (old method).", "Roster tested better on the first 81 games (margin miss 15.2 vs 15.4)."),
 (31, "Roster", "Prior player weight", 800, "minutes", "Pseudo-minutes pulling a player's past BPM toward replacement level.", "Calibrated predicting 2025-26 teams from 2024-25 players."),
 (32, "Roster", "Current-season player weight", 1500, "minutes", "A player's 2026-27 BPM gets weight MP / (MP + this).", "Conservative: about 10% at 150 minutes."),
 (33, "Roster", "PlayerDefense PM weight", 1500, "minutes", "PM moves the defensive rating with weight MP / (MP + this).", "PM is noisy early in the season."),
 (34, "Roster", "PM league centre", 2.0, "points", "Minute-weighted league average of PlayerDefense PM.", "Measured 10/30: +1.99."),
 (35, "Roster", "Rookie OBPM", -2.0, "per 100", "Offensive rating for players with no prior NBA minutes.", "Calibrated."),
 (36, "Roster", "Rookie DBPM", -0.5, "per 100", "Defensive rating for players with no prior NBA minutes.", "Calibrated."),
 (37, "Roster", "Replacement OBPM", -1.5, "per 100", "Fill-in offense for minutes lost to players marked Out, and the prior mean.", "Standard replacement level is about -2 BPM in total."),
 (38, "Roster", "Replacement DBPM", -0.5, "per 100", "Fill-in defense for minutes lost to players marked Out, and the prior mean.", ""),
 (39, "Roster", "Offense scale", 0.92, "x", "Team offense vs league = this x minutes-weighted player OBPM.", "Fitted on 2025-26 teams."),
 (40, "Roster", "Defense scale", 0.95, "x", "Team defense vs league = this x minutes-weighted player DBPM.", "Fitted on 2025-26 teams."),
 (41, "Roster", "Age curve scale", 1, "x", "Young players get a bump, older players a decline (+1.0 at 21 or under to -0.9 at 32+), 70% to offense.", "1 = on, 0 = off."),
]
rows = [f'<row r="29" spans="1:6" ht="24" customHeight="1">{cs("A29", S_SEC, "ROSTER RATINGS  (player-based team prior, added 10/31)")}</row>']
for r, sec, name, val, unit, why, rat in NEW_INPUTS:
    vcell = cs(f"C{r}", 14, val) if isinstance(val, str) else cn(f"C{r}", 37, val)
    rows.append(f'<row r="{r}" spans="1:6" ht="36" customHeight="1">{cs(f"A{r}",80,sec)}{cs(f"B{r}",81,name)}{vcell}{cs(f"D{r}",82,unit)}{cs(f"E{r}",83,why)}{cs(f"F{r}",83,rat)}</row>')
A = A.replace("</sheetData>", "".join(rows) + "</sheetData>")
# dropdown for C30
if "<dataValidations" in A:
    A = re.sub(r'<dataValidations count="(\d+)">', lambda m: f'<dataValidations count="{int(m.group(1))+1}"><dataValidation type="list" allowBlank="1" sqref="C30"><formula1>"Roster,Team"</formula1></dataValidation>', A, count=1)
else:
    A = A.replace("<pageMargins", '<dataValidations count="1"><dataValidation type="list" allowBlank="1" sqref="C30"><formula1>"Roster,Team"</formula1></dataValidation></dataValidations><pageMargins', 1)
A = re.sub(r'<dimension ref="[^"]*"/>', '<dimension ref="A1:F41"/>', A)
wr("xl/worksheets/sheet3.xml", A)

AS = lambda r: f"Assumptions!$C${r}"
K_PRI, K_CUR, K_PM, PM_C, RK_O, RK_D, REP_O, REP_D, SC_O, SC_D, AGE = [AS(r) for r in range(31, 42)]

# ---------------- PlayerRatings sheet ----------------
N27, N26, N25 = "'26-27NBAPlayer'", "'25-26NBAPlayer'", "'24-25NBAPlayer'"
def rng(sh, c): return f"{sh}!${c}$2:${c}$1000"
FIRST, NROWS = 6, 800
cols = [  # (col, header, width, style, formula template using {r} for this row and {s} for source row)
 ("A","Player",22,S_LABEL,'IF(ISNUMBER('+N27+'!$F{s}),'+N27+'!$B{s},"")'),
 ("B","BBRef team",8,S_LABEL,'IF($A{r}="","",'+N27+'!$D{s})'),
 ("C","Team",22,S_LABEL,'IF($A{r}="","",IFERROR(INDEX(Teams!$D$2:$D$31,MATCH(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE($B{r},"BRK","BKN"),"CHO","CHA"),"PHO","PHX"),Teams!$C$2:$C$31,0)),""))'),
 ("D","Age",6,S_INT,'IF($A{r}="","",'+N27+'!$C{s})'),
 ("E","G (team)",7,S_INT,'IF($A{r}="","",'+N27+'!$F{s})'),
 ("F","MP (team)",8,S_INT,'IF($A{r}="","",'+N27+'!$H{s})'),
 ("G","Team games",7,S_INT,'IF($C{r}="","",_xlfn.MAXIFS($E$'+str(6)+':$E$'+str(805)+',$C$'+str(6)+':$C$'+str(805)+',$C{r}))'),
 ("H","Exp MPG",8,S_NUM1,'IF(OR($C{r}="",NOT(ISNUMBER($E{r}))),0,IF($E{r}<=0,0,MIN(48,$F{r}/$E{r})))'),
 ("I","Status",8,S_INPUT_T,None),
 ("J","Min override",9,S_INPUT_N,None),
 ("K","Active min",8,S_NUM1,'IF($C{r}="",0,IF(ISNUMBER($J{r}),$J{r},$H{r}*IF($I{r}="Out",0,IF($I{r}="D",0.25,IF($I{r}="Q",0.5,1)))))'),
 ("L","MP 26-27",8,S_INT,'IF($A{r}="","",IF(COUNTIFS('+rng(N27,"B")+',$A{r},'+rng(N27,"D")+',"*TM")>0,SUMIFS('+rng(N27,"H")+','+rng(N27,"B")+',$A{r},'+rng(N27,"D")+',"*TM"),$F{r}))'),
 ("M","OBPM 26-27",8,S_NUM1,'IF($A{r}="","",IF(COUNTIFS('+rng(N27,"B")+',$A{r},'+rng(N27,"D")+',"*TM")>0,SUMIFS('+rng(N27,"Y")+','+rng(N27,"B")+',$A{r},'+rng(N27,"D")+',"*TM"),N('+N27+'!$Y{s})))'),
 ("N","DBPM 26-27",8,S_NUM1,'IF($A{r}="","",IF(COUNTIFS('+rng(N27,"B")+',$A{r},'+rng(N27,"D")+',"*TM")>0,SUMIFS('+rng(N27,"Z")+','+rng(N27,"B")+',$A{r},'+rng(N27,"D")+',"*TM"),N('+N27+'!$Z{s})))'),
]
def prev(sh, label, cmp, cO, cD):
    tm = f'COUNTIFS({rng(sh,"B")},$A{{r}},{rng(sh,"D")},"*TM")>0'
    def pick(c): return f'IF($A{{r}}="","",IF({tm},SUMIFS({rng(sh,c)},{rng(sh,"B")},$A{{r}},{rng(sh,"D")},"*TM"),SUMIFS({rng(sh,c)},{rng(sh,"B")},$A{{r}})))'
    return [(cmp,f"MP {label}",8,S_INT,pick("H")),(cO,f"OBPM {label}",8,S_NUM1,pick("Y")),(cD,f"DBPM {label}",8,S_NUM1,pick("Z"))]
cols += prev(N26, "25-26", "O", "P", "Q") + prev(N25, "24-25", "R", "S", "T")
AGEF = f'IF($D{{r}}<=21,1,IF($D{{r}}<=23,0.6,IF($D{{r}}<=25,0.25,IF($D{{r}}<=28,0,IF($D{{r}}<=31,-0.4,-0.9)))))*{AGE}'
cols += [
 ("U","Prior wt",8,S_INT,'IF($A{r}="","",2*N($O{r})+N($R{r}))'),
 ("V","Prior O",8,S_NUM1,'IF($A{r}="","",IF($U{r}>0,(2*N($O{r})*N($P{r})+N($R{r})*N($S{r})+'+K_PRI+'*'+REP_O+')/($U{r}+'+K_PRI+')+0.7*'+AGEF+','+RK_O+'))'),
 ("W","Prior D",8,S_NUM1,'IF($A{r}="","",IF($U{r}>0,(2*N($O{r})*N($Q{r})+N($R{r})*N($T{r})+'+K_PRI+'*'+REP_D+')/($U{r}+'+K_PRI+')+0.3*'+AGEF+','+RK_D+'))'),
 ("X","Off rating",8,S_KEY,'IF($A{r}="","",($M{r}*$L{r}+$V{r}*'+K_CUR+')/($L{r}+'+K_CUR+'))'),
 ("Y","Def (BPM)",8,S_NUM1,'IF($A{r}="","",($N{r}*$L{r}+$W{r}*'+K_CUR+')/($L{r}+'+K_CUR+'))'),
 ("Z","PM",7,S_NUM1,'IF($A{r}="","",IFERROR(INDEX(PlayerDefense!$O$2:$O$1000,MATCH($A{r}&"*",PlayerDefense!$B$2:$B$1000,0)),""))'),
 ("AA","PM MP",7,S_INT,'IF($A{r}="","",IFERROR(INDEX(PlayerDefense!$D$2:$D$1000,MATCH($A{r}&"*",PlayerDefense!$B$2:$B$1000,0)),""))'),
 ("AB","Def rating",8,S_KEY,'IF($A{r}="","",IF(AND(ISNUMBER($Z{r}),ISNUMBER($AA{r})),$Y{r}+(-($Z{r}-'+PM_C+')-$Y{r})*$AA{r}/($AA{r}+'+K_PM+'),$Y{r}))'),
 ("AC","Min x Off",8,S_NUM1,'IF($C{r}="",0,$K{r}*$X{r})'),
 ("AD","Min x Def",8,S_NUM1,'IF($C{r}="",0,$K{r}*$AB{r})'),
 ("AE","Base min",8,S_NUM1,'IF($C{r}="",0,$H{r})'),
]
ncol = len(cols)
last = n2col(ncol)
xml_rows = []
xml_rows.append(f'<row r="1" spans="1:{ncol}" ht="30" customHeight="1">{cs("A1",S_TITLE,"PLAYER RATINGS")}</row>')
xml_rows.append(f'<row r="2" spans="1:{ncol}">{cs("A2",S_SUB,"One row per row of the 26-27NBAPlayer tab (paste new Basketball-Reference data there and this updates). Off/Def rating = per-100 vs average, blended from 2024-25, 2025-26 and 2026-27 BPM plus PlayerDefense PM. Settings: Assumptions rows 30-41.")}</row>')
xml_rows.append(f'<row r="3" spans="1:{ncol}">{cs("A3",S_SUB,"STATUS (yellow): type Out, D (doubtful, 25% of minutes) or Q (questionable, 50%). Lost minutes are filled at replacement level. Min override (yellow) sets expected minutes directly. Clear both after the game. With Status in use, leave the Matchup lineup cells at 0.")}</row>')
xml_rows.append(f'<row r="5" spans="1:{ncol}" ht="30" customHeight="1">' + "".join(cs(f"{c}5", S_HDR, h) for c, h, w, s, f in cols) + '</row>')
for i in range(NROWS):
    r, s = FIRST + i, 2 + i
    cells = []
    for c, h, w, st, f in cols:
        if f is None: cells.append(f'<c r="{c}{r}" s="{st}"/>')
        else: cells.append(cf(f"{c}{r}", st, f.format(r=r, s=s)))
    xml_rows.append(f'<row r="{r}" spans="1:{ncol}">' + "".join(cells) + '</row>')
colxml = "<cols>" + "".join(f'<col min="{col2n(c)}" max="{col2n(c)}" width="{w}" style="{S_BG}" customWidth="1"/>' for c, h, w, s, f in cols) + f'<col min="{ncol+1}" max="40" width="8.7" style="{S_BG}" customWidth="1"/></cols>'
LASTROW = FIRST + NROWS - 1
sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
 '<sheetPr><tabColor rgb="FFF5C451"/></sheetPr>'
 f'<dimension ref="A1:{last}{LASTROW}"/>'
 '<sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane xSplit="3" ySplit="5" topLeftCell="D6" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>'
 '<sheetFormatPr defaultRowHeight="15"/>' + colxml + '<sheetData>' + "".join(xml_rows) + '</sheetData>'
 f'<autoFilter ref="A5:{last}{LASTROW}"/>'
 f'<dataValidations count="1"><dataValidation type="list" allowBlank="1" sqref="I{FIRST}:I{LASTROW}"><formula1>"Out,D,Q"</formula1></dataValidation></dataValidations>'
 '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')

# ---------------- TeamRatings sheet ----------------
PR = lambda c: f"PlayerRatings!${c}${FIRST}:${c}${LASTROW}"
tcols = [
 ("A","Team",24,S_LABEL),("B","Base min",9,S_NUM1),("C","Active min",9,S_NUM1),("D","Lost min",9,S_NUM1),
 ("E","Player off",9,S_NUM1),("F","Player def",9,S_NUM1),("G","Off vs lg",9,S_NUM1),("H","Def vs lg",9,S_NUM1),
 ("I","Roster ORtg",10,S_KEY),("J","Roster DRtg",10,S_KEY),("K","Roster NRtg",10,S_KEY),("L","Players marked",9,S_INT)]
trows = [f'<row r="1" spans="1:12" ht="30" customHeight="1">{cs("A1",S_TITLE,"TEAM RATINGS FROM ROSTERS")}</row>',
 f'<row r="2" spans="1:12">{cs("A2",S_SUB,"Minutes-weighted player ratings for every team (each player's minutes per game played, so mark anyone not playing on PlayerRatings). Lost minutes (players marked on PlayerRatings) are filled at replacement level. Roster ORtg/DRtg feed Calculations rows 38-39 when Assumptions C30 = Roster.")}</row>',
 f'<row r="3" spans="1:12">{cs("A3",S_SUB,"ORtg = league ORtg + offense scale x player off.  DRtg = league DRtg - defense scale x player def (league values from Calculations B28:B29).")}</row>',
 f'<row r="5" spans="1:12" ht="30" customHeight="1">' + "".join(cs(f"{c}5", S_HDR, h) for c, h, w, s in tcols) + '</row>']
for i in range(30):
    r = 6 + i
    f = {
     "A": f'Teams!$D${2+i}',
     "B": f'SUMIFS({PR("AE")},{PR("C")},$A{r})',
     "C": f'SUMIFS({PR("K")},{PR("C")},$A{r})',
     "D": f'MAX(0,$B{r}-$C{r})',
     "E": f'IF($B{r}<=0,0,(SUMIFS({PR("AC")},{PR("C")},$A{r})+$D{r}*{REP_O})/$B{r}*5)',
     "F": f'IF($B{r}<=0,0,(SUMIFS({PR("AD")},{PR("C")},$A{r})+$D{r}*{REP_D})/$B{r}*5)',
     "G": f'{SC_O}*$E{r}', "H": f'{SC_D}*$F{r}',
     "I": f'Calculations!$B$28+$G{r}', "J": f'Calculations!$B$29-$H{r}', "K": f'$I{r}-$J{r}',
     "L": f'COUNTIFS({PR("C")},$A{r},{PR("I")},"?*")+COUNTIFS({PR("C")},$A{r},{PR("J")},">=0")',
    }
    trows.append(f'<row r="{r}" spans="1:12">' + "".join(cf(f"{c}{r}", s, f[c]) for c, h, w, s in tcols) + '</row>')
tcolxml = "<cols>" + "".join(f'<col min="{col2n(c)}" max="{col2n(c)}" width="{w}" style="{S_BG}" customWidth="1"/>' for c, h, w, s in tcols) + f'<col min="13" max="30" width="8.7" style="{S_BG}" customWidth="1"/></cols>'
tsheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
 '<sheetPr><tabColor rgb="FFF5C451"/></sheetPr><dimension ref="A1:L35"/>'
 '<sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane ySplit="5" topLeftCell="A6" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
 '<sheetFormatPr defaultRowHeight="15"/>' + tcolxml + '<sheetData>' + "".join(trows) + '</sheetData>'
 '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')

# ---------------- register sheets ----------------
existing = [int(x) for x in re.findall(r'sheet(\d+)\.xml', " ".join(os.listdir(P("xl/worksheets"))))]
n1, n2 = max(existing) + 1, max(existing) + 2
wr(f"xl/worksheets/sheet{n1}.xml", sheet)
wr(f"xl/worksheets/sheet{n2}.xml", tsheet)
ct = rd("[Content_Types].xml")
for n in (n1, n2):
    ct = ct.replace("</Types>", f'<Override PartName="/xl/worksheets/sheet{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
ct = ct.replace('<Override PartName="/xl/calcChain.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml"/>', '')
wr("[Content_Types].xml", ct)
rels = rd("xl/_rels/workbook.xml.rels")
rids = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels)]
r1, r2 = max(rids) + 1, max(rids) + 2
rels = re.sub(r'<Relationship Id="rId\d+" Type="[^"]*/calcChain" Target="calcChain.xml"/>', '', rels)
rels = rels.replace("</Relationships>", f'<Relationship Id="rId{r1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{n1}.xml"/><Relationship Id="rId{r2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{n2}.xml"/></Relationships>')
wr("xl/_rels/workbook.xml.rels", rels)
if os.path.exists(P("xl/calcChain.xml")): os.remove(P("xl/calcChain.xml"))
wb = rd("xl/workbook.xml")
sids = [int(x) for x in re.findall(r'sheetId="(\d+)"', wb)]
wb = wb.replace("</sheets>", f'<sheet name="PlayerRatings" sheetId="{max(sids)+1}" r:id="rId{r1}"/><sheet name="TeamRatings" sheetId="{max(sids)+2}" r:id="rId{r2}"/></sheets>')
nsheets = len(re.findall(r'<sheet ', wb))
wb = re.sub(r'<definedName name="_xlnm._FilterDatabase"', '<definedName name="_xlnm._FilterDatabase"', wb)
wb = wb.replace("</definedNames>", f'<definedName name="_xlnm._FilterDatabase" localSheetId="{nsheets-2}" hidden="1">PlayerRatings!$A$5:${last}${LASTROW}</definedName></definedNames>')
wb = re.sub(r'<calcPr[^>]*/>', '<calcPr calcId="191028" fullCalcOnLoad="1"/>', wb)
wr("xl/workbook.xml", wb)

# ---------------- Calculations hook (sheet5) ----------------
C = rd("xl/worksheets/sheet5.xml")
def repl_formula(sheet, ref, new):
    m = re.search(rf'<c r="{ref}"([^>]*?)>(.*?)</c>', sheet, re.S)
    attrs = re.sub(r'\s*t="[^"]*"', '', m.group(1))
    return sheet[:m.start()] + f'<c r="{ref}"{attrs}><f>{escape(new)}</f></c>' + sheet[m.end():]
def get_formula(sheet, ref):
    m = re.search(rf'<c r="{ref}"[^>]*?>.*?<f[^>]*>(.*?)</f>', sheet, re.S); return m.group(1)
from xml.sax.saxutils import unescape
for col, team in (("B", "B$4"), ("D", "D$4")):
    for row, tcol in ((38, "I"), (39, "J")):
        old = unescape(get_formula(C, f"{col}{row}"))
        new = f'IF(AND(Assumptions!$C$30="Roster",ISNUMBER(MATCH({team},TeamRatings!$A$6:$A$35,0))),INDEX(TeamRatings!${tcol}$6:${tcol}$35,MATCH({team},TeamRatings!$A$6:$A$35,0)),{old})'
        C = repl_formula(C, f"{col}{row}", new)
# relabel A38 / A39
def repl_label(sheet, ref, text):
    m = re.search(rf'<c r="{ref}"([^>]*?)(?:/>|>.*?</c>)', sheet, re.S)
    attrs = re.sub(r'\s*t="[^"]*"', '', m.group(1))
    return sheet[:m.start()] + f'<c r="{ref}"{attrs} t="inlineStr"><is><t>{escape(text)}</t></is></c>' + sheet[m.end():]
C = repl_label(C, "A38", "Prior ORtg (roster, or regressed team)")
C = repl_label(C, "A39", "Prior DRtg (roster, or regressed team)")
wr("xl/worksheets/sheet5.xml", C)

# ---------------- zip ----------------
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(work):
        for fn in files:
            full = os.path.join(root, fn); arc = os.path.relpath(full, work)
            z.write(full, arc)
print("ok", OUT, "sheets", n1, n2)

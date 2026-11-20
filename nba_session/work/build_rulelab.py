import openpyxl, sys, datetime, pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.utils import get_column_letter as L

SRC, RULES, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
src = openpyxl.load_workbook(SRC, data_only=True)["Tracking"]

# ---------- theme (matches the MaverickPicks workbooks) ----------
BG, BG2, HDR, BAND = "0B1020", "16203D", "182240", "1E2A4D"
TXT, MUT, CY, OR, GOLD, INP = "E6EAF2", "8A94A8", "38BDF8", "FF7A18", "FBBF24", "7DD3FC"
fill = lambda c: PatternFill("solid", fgColor=c)
F = lambda **k: Font(name="Arial", size=k.pop("sz", 9), color=k.pop("c", TXT), **k)
thin = Side(style="thin", color="2A3A6B")

wb = openpyxl.Workbook()
def sheet(name, tab, widths, rows=60, cols=30):
    ws = wb.create_sheet(name); ws.sheet_properties.tabColor = tab; ws.sheet_view.showGridLines = False
    for i in range(1, cols+1): ws.column_dimensions[L(i)].width = widths.get(i, 11)
    for r in range(1, rows+1):
        for c in range(1, cols+1): ws.cell(r, c).fill = fill(BG); ws.cell(r, c).font = F()
    return ws
def put(ws, ref, v, **st):
    c = ws[ref]; c.value = v
    c.font = st.get("font", F()); c.fill = fill(st.get("bg", BG))
    if "fmt" in st: c.number_format = st["fmt"]
    if "al" in st: c.alignment = st["al"]
    return c
def hdr(ws, row, c1, labels, bg=HDR):
    for i, t in enumerate(labels):
        put(ws, f"{L(c1+i)}{row}", t, font=F(b=True, sz=8, c=CY), bg=bg, al=Alignment(horizontal="center", vertical="center", wrap_text=True))
def band(ws, row, c1, c2, text):
    for c in range(c1, c2+1): put(ws, f"{L(c)}{row}", None, bg=BAND)
    put(ws, f"{L(c1)}{row}", text, font=F(b=True, sz=10), bg=BAND)

wb.remove(wb.active)

# ======================= README =======================
rd = sheet("Read Me", OR, {1: 3, 2: 120}, rows=45, cols=3)
put(rd, "B2", "MAVERICKPICKS NBA · RULE LAB", font=F(b=True, sz=16, c=OR))
lines = [
 ("HOW TO REFRESH", True),
 ("1. In the model workbook, copy Tracking!A13:AO312.  2. Here, click Log!A2 and Paste Values.  Legs and Rule Lab recalculate.", False),
 ("Only games with both final scores are graded. Every game becomes 10 legs: ML away/home, spread away/home, over/under, and both team-total overs/unders.", False),
 ("", False),
 ("HOW TO USE THE RULE LAB", True),
 ("Yellow cells are inputs. Leave a min or max blank for no limit. Ranges are inclusive (min ≤ value ≤ max).", False),
 ("Odds limits are American odds and follow price order: min −115 / max +115 means any price from −115 through +115. 'Odds ≥ +130' is min +130, max blank.", False),
 ("Proj gap = how many points the model's projection sits past the line in the bet's direction (Over 230.5 with a 234 projection = +3.5).", False),
 ("Edge = model % − no-vig %.  EV = model % × payout − (1 − model %).  All results are 1 unit flat at the logged odds; a push returns the stake.", False),
 ("", False),
 ("HOW TO READ THE NUMBERS", True),
 ("Mkt exp u = what the market's own no-vig prices say those bets should have returned (slightly negative = the vig).", False),
 ("z vs mkt = (units − Mkt exp u) ÷ standard deviation. p = chance of doing at least this well if the market prices were exactly right.", False),
 ("A p-value is only meaningful for a rule chosen BEFORE the results. Rules found by scanning hundreds of combinations will always include some low p-values by luck.", False),
 ("Forward = legs on or after the freeze date on Rule Lab. That is the honest test. Freeze a rule's settings, then judge it only on Forward results.", False),
 ("", False),
 ("WHAT THE 10/23 SCAN FOUND (16 games, 160 legs, 403 rules)", True),
 ("No rule survives correction for multiple testing (best Benjamini-Hochberg q = 0.55). 31 rules had p < 0.05, against about 20 expected by luck.", False),
 ("In 2,000 luck-only simulations (game outcomes redrawn from the market's no-vig prices), the best rule beat today's best z of 2.58 about 40% of the time.", False),
 ("So the shortlist on Rule Lab is a set of hypotheses to track forward, not edges. The Scan tab is a frozen snapshot; it does not recalculate.", False),
 ("", False),
 ("LIMITS", True),
 ("Legs from the same game are correlated (an Under and two team-total Unders usually win or lose together), so 26 legs can be closer to 12 independent results.", False),
 ("The log has two sides of every market, so every rule has a mirror image. A strong 'Under' rule is the same evidence as a weak 'Over' rule.", False),
 ("Early season: ratings are still almost all last season's prior. Rules that work now may not survive the switch to current-season ratings around 25 games.", False),
]
for i, (t, b) in enumerate(lines):
    put(rd, f"B{4+i}", t, font=F(b=b, sz=10 if b else 9, c=CY if b else TXT), al=Alignment(wrap_text=True, vertical="top"))

# ======================= LOG (paste target) =======================
lg = sheet("Log", "8A94A8", {1: 10, 2: 20, 3: 20, 35: 40}, rows=2, cols=41)
for c in range(1, 42):
    put(lg, f"{L(c)}1", src.cell(12, c).value, font=F(b=True, sz=8, c=CY), bg=HDR, al=Alignment(wrap_text=True, horizontal="center"))
lg.row_dimensions[1].height = 30
NLOG = 300
for i in range(NLOG):
    for c in range(1, 42):
        v = src.cell(13+i, c).value
        cell = lg.cell(2+i, c, v); cell.font = F(c=INP); cell.fill = fill(BG2)
        if c == 1: cell.number_format = "mm/dd/yy"
lg.freeze_panes = "D2"

# ======================= LEGS (formulas) =======================
lgw = {1: 6, 2: 6, 3: 5, 4: 9, 5: 34, 6: 8, 7: 30, 8: 7, 9: 7, 10: 7}
legs = wb.create_sheet("Legs"); legs.sheet_properties.tabColor = CY; legs.sheet_view.showGridLines = False
for i in range(1, 30): legs.column_dimensions[L(i)].width = lgw.get(i, 9)
heads = ["Valid","Log row","Leg #","Date","Game","Market","Bet","Side","Venue","Card play","Odds","Opp odds","Payout 1u",
         "Model %","No-vig %","Edge","EV","Proj gap","Line","Margin","Result","Win","Profit u","Mkt exp u","Mkt var","Lab match","Lab 1st of game"]
hdr(legs, 1, 1, heads); legs.row_dimensions[1].height = 28; legs.freeze_panes = "E2"
NLEG = NLOG*10
def g(col, r): return f"INDEX(Log!${col}$2:${col}${NLOG+1},$B{r})"
def ch(*xs): return "CHOOSE($C{r}+1," + ",".join(xs) + ")"
imp = lambda x: f"IF({x}<0,-{x}/(-{x}+100),100/({x}+100))"
for k in range(NLEG):
    r = k+2
    G = lambda c: g(c, r)
    f = {}
    f["B"] = f"=INT((ROW()-2)/10)+1"
    f["C"] = f"=MOD(ROW()-2,10)"
    f["A"] = f"=IF(AND(ISNUMBER({G('A')}),ISNUMBER({G('AN')}),ISNUMBER({G('AO')}),ISNUMBER({G('J')}),ISNUMBER({G('U')})),1,0)"
    v = lambda e, z="0": f'=IF($A{r}=1,{e},{z})'
    f["D"] = v(G('A'), '""')
    f["E"] = v(f'{G("B")}&" @ "&{G("C")}', '""')
    f["F"] = v(ch('"ML"','"ML"','"Spread"','"Spread"','"Total"','"Total"','"TT"','"TT"','"TT"','"TT"').format(r=r), '""')
    f["G"] = v(ch(f'{G("B")}&" ML"', f'{G("C")}&" ML"',
                  f'{G("B")}&" "&TEXT({G("U")},"+0.0;-0.0")', f'{G("C")}&" "&TEXT(-{G("U")},"+0.0;-0.0")',
                  f'"Over "&TEXT({G("P")},"0.0")', f'"Under "&TEXT({G("P")},"0.0")',
                  f'{G("B")}&" TT o"&TEXT({G("AA")},"0.0")', f'{G("B")}&" TT u"&TEXT({G("AA")},"0.0")',
                  f'{G("C")}&" TT o"&TEXT({G("AE")},"0.0")', f'{G("C")}&" TT u"&TEXT({G("AE")},"0.0")').format(r=r), '""')
    f["H"] = v(ch(f'IF({G("J")}>{G("K")},"Dog","Fav")', f'IF({G("K")}>{G("J")},"Dog","Fav")',
                  f'IF({G("U")}>0,"Dog","Fav")', f'IF({G("U")}>0,"Fav","Dog")',
                  '"Over"','"Under"','"Over"','"Under"','"Over"','"Under"').format(r=r), '""')
    f["I"] = v(ch('"Away"','"Home"','"Away"','"Home"','"—"','"—"','"Away"','"Away"','"Home"','"Home"').format(r=r), '""')
    keys = [f'"ML "&{G("B")}', f'"ML "&{G("C")}',
            f'"Spread "&{G("B")}&" "&TEXT({G("U")},"+0.0;-0.0")', f'"Spread "&{G("C")}&" "&TEXT(-{G("U")},"+0.0;-0.0")',
            f'"Total Over "&TEXT({G("P")},"0.0")', f'"Total Under "&TEXT({G("P")},"0.0")',
            f'"TT "&{G("B")}&" Over "&TEXT({G("AA")},"0.0")', f'"TT "&{G("B")}&" Under "&TEXT({G("AA")},"0.0")',
            f'"TT "&{G("C")}&" Over "&TEXT({G("AE")},"0.0")', f'"TT "&{G("C")}&" Under "&TEXT({G("AE")},"0.0")']
    f["J"] = v(f'IF(ISNUMBER(SEARCH({ch(*keys).format(r=r)}&" |",{G("AI")}&" |")),"Yes","No")', '""')
    f["K"] = v(ch(*[G(c) for c in ["J","K","W","Z","S","T","AC","AD","AG","AH"]]).format(r=r))
    f["L"] = v(ch(*[G(c) for c in ["K","J","Z","W","T","S","AD","AC","AH","AG"]]).format(r=r))
    f["M"] = v(f"IF(K{r}<0,100/ABS(K{r}),K{r}/100)")
    f["N"] = v(ch(G("H"), G("I"), G("V"), f'1-{G("V")}', G("R"), f'1-{G("R")}', G("AB"), f'1-{G("AB")}', G("AF"), f'1-{G("AF")}').format(r=r))
    f["O"] = v(f"{imp(f'K{r}')}/({imp(f'K{r}')}+{imp(f'L{r}')})")
    f["P"] = v(f"N{r}-O{r}")
    f["Q"] = v(f"N{r}*M{r}-(1-N{r})")
    f["R"] = v(ch(f'{G("D")}-{G("E")}', f'{G("E")}-{G("D")}', f'{G("D")}-{G("E")}+{G("U")}', f'{G("E")}-{G("D")}-{G("U")}',
                  f'{G("Q")}-{G("P")}', f'{G("P")}-{G("Q")}', f'{G("D")}-{G("AA")}', f'{G("AA")}-{G("D")}',
                  f'{G("E")}-{G("AE")}', f'{G("AE")}-{G("E")}').format(r=r))
    f["S"] = v(ch('0','0',f'ABS({G("U")})',f'ABS({G("U")})',G("P"),G("P"),G("AA"),G("AA"),G("AE"),G("AE")).format(r=r))
    f["T"] = v(ch(f'{G("AN")}-{G("AO")}', f'{G("AO")}-{G("AN")}', f'{G("AN")}-{G("AO")}+{G("U")}', f'{G("AO")}-{G("AN")}-{G("U")}',
                  f'{G("AN")}+{G("AO")}-{G("P")}', f'{G("P")}-{G("AN")}-{G("AO")}', f'{G("AN")}-{G("AA")}', f'{G("AA")}-{G("AN")}',
                  f'{G("AO")}-{G("AE")}', f'{G("AE")}-{G("AO")}').format(r=r))
    f["U"] = v(f'IF(T{r}>0,"W",IF(T{r}<0,"L","P"))', '""')
    f["V"] = v(f"IF(T{r}>0,1,0)")
    f["W"] = v(f"IF(T{r}>0,M{r},IF(T{r}<0,-1,0))")
    f["X"] = v(f"O{r}*M{r}-(1-O{r})")
    f["Y"] = v(f"O{r}*(1-O{r})*(M{r}+1)^2")
    for col, val in f.items(): legs[f"{col}{r}"] = val
fmts = {"D":"mm/dd/yy","K":"+0;-0;0","L":"+0;-0;0","M":"0.00","N":"0.0%","O":"0.0%","P":"+0.0%;-0.0%;0.0%","Q":"+0.0%;-0.0%;0.0%",
        "R":"+0.0;-0.0;0.0","S":"0.0","T":"+0;-0;0","W":"+0.00;-0.00;0.00","X":"+0.000;-0.000;0.000","Y":"0.000"}
for col, fm in fmts.items():
    for r in range(2, NLEG+2): legs[f"{col}{r}"].number_format = fm

# ======================= RULE LAB =======================
lab = sheet("Rule Lab", "FBBF24", {1: 44, 2: 9, 3: 9, 4: 9, 5: 9, 6: 9, 7: 9, 8: 9, 9: 9, 10: 9, 11: 9, 12: 9, 13: 9, 14: 9, 15: 9, 16: 9, 17: 9,
                                    18: 8, 19: 8, 20: 8, 21: 9, 22: 9, 23: 9, 24: 9, 25: 9, 26: 8, 27: 8, 28: 9, 29: 9}, rows=70, cols=30)
put(lab, "A1", "RULE LAB", font=F(b=True, sz=16, c=OR))
put(lab, "A2", "Mix and match filters. Yellow cells are inputs; blank min/max = no limit. Results are 1u flat at logged odds. Judge a frozen rule on its Forward columns only.", font=F(i=True, c=MUT))
put(lab, "A3", "Freeze date (Forward = on/after):", font=F(b=True, sz=8, c=CY))
put(lab, "C3", datetime.datetime(2026, 10, 23), font=F(b=True, c="0B1020"), bg="FDE68A", fmt="mm/dd/yy")
put(lab, "E3", "Change it to the day you lock a rule in. Each watchlist row can also set its own date range.", font=F(c=MUT))

LR = f"$2:$"; R2 = NLEG+1
col = lambda c: f"Legs!${c}$2:${c}${R2}"
CRIT = ["Market","Side","Venue","Card play","From date","To date","Odds min","Odds max","Model % min","Model % max",
        "Edge min","Edge max","EV min","EV max","Gap min","Gap max"]
OUTS = ["Legs","W","L","Units","ROI","Mkt exp u","z vs mkt","p","Fwd legs","Fwd W-L","Fwd units","Fwd ROI"]
def mask(r, c0=2):
    cc = lambda i: f"${L(c0+i)}{r}"
    pay = lambda x: f"IF({x}<0,100/ABS({x}),{x}/100)"
    t = [f"({col('A')}=1)"]
    for i, lc in enumerate(["F","H","I","J"]):
        t.append(f"((({cc(i)}=\"All\")+({cc(i)}=\"\")+({col(lc)}={cc(i)}))>0)")
    t.append(f"((ISBLANK({cc(4)})+({col('D')}>={cc(4)}))>0)")
    t.append(f"((ISBLANK({cc(5)})+({col('D')}<={cc(5)}))>0)")
    t.append(f"((ISBLANK({cc(6)})+({col('M')}>={pay(cc(6))}))>0)")
    t.append(f"((ISBLANK({cc(7)})+({col('M')}<={pay(cc(7))}))>0)")
    for i, lc in [(8,"N"),(10,"P"),(12,"Q"),(14,"R")]:
        t.append(f"((ISBLANK({cc(i)})+({col(lc)}>={cc(i)}))>0)")
        t.append(f"((ISBLANK({cc(i+1)})+({col(lc)}<={cc(i+1)}))>0)")
    return "*".join(t)
def outs(ws, r, o0, m):
    o = lambda i: f"{L(o0+i)}{r}"
    fwd = f"({col('D')}>=$C$3)"
    ws[o(0)] = f"=SUMPRODUCT({m})"
    ws[o(1)] = f'=SUMPRODUCT({m}*({col("U")}="W"))'
    ws[o(2)] = f'=SUMPRODUCT({m}*({col("U")}="L"))'
    ws[o(3)] = f"=SUMPRODUCT({m}*{col('W')})"
    ws[o(4)] = f'=IF({o(0)}=0,"",{o(3)}/{o(0)})'
    ws[o(5)] = f"=SUMPRODUCT({m}*{col('X')})"
    ws[o(6)] = f'=IF(SUMPRODUCT({m}*{col("Y")})=0,"",({o(3)}-{o(5)})/SQRT(SUMPRODUCT({m}*{col("Y")})))'
    ws[o(7)] = f'=IF({o(6)}="","",1-NORMSDIST({o(6)}))'
    ws[o(8)] = f"=SUMPRODUCT({m}*{fwd})"
    ws[o(9)] = f'=SUMPRODUCT({m}*{fwd}*({col("U")}="W"))&"-"&SUMPRODUCT({m}*{fwd}*({col("U")}="L"))'
    ws[o(10)] = f"=SUMPRODUCT({m}*{fwd}*{col('W')})"
    ws[o(11)] = f'=IF({o(8)}=0,"",{o(10)}/{o(8)})'
    fm = ["0","0","0","+0.00;-0.00;0.00","+0.0%;-0.0%;0.0%","+0.00;-0.00;0.00","+0.00;-0.00;0.00","0.000","0","@","+0.00;-0.00;0.00","+0.0%;-0.0%;0.0%"]
    for i in range(12):
        c = ws[o(i)]; c.number_format = fm[i]; c.font = F(b=i in (3, 10)); c.fill = fill(BG); c.alignment = Alignment(horizontal="center")

# --- builder (rows 5-12) ---
band(lab, 5, 1, 29, "RULE BUILDER")
hdr(lab, 6, 2, CRIT); put(lab, "A6", "Your rule", font=F(b=True, sz=8, c=CY), bg=HDR)
lab.row_dimensions[6].height = 26
put(lab, "A7", "Builder", font=F(b=True, c=OR))
builder = ["Total","Under","All","All",None,None,None,None,0.55,0.6499,None,None,None,None,None,None]
for i, v in enumerate(builder):
    c = put(lab, f"{L(2+i)}7", v, font=F(b=True, c="0B1020"), bg="FDE68A", al=Alignment(horizontal="center"))
    if i in (4, 5): c.number_format = "mm/dd/yy"
    if i in (8, 9, 10, 11, 12, 13): c.number_format = "0.0%"
    if i in (6, 7): c.number_format = "+0;-0;0"
hdr(lab, 9, 2, OUTS); put(lab, "A9", "Result", font=F(b=True, sz=8, c=CY), bg=HDR)
lab.row_dimensions[9].height = 26
put(lab, "A10", "All dates / Forward", font=F(c=MUT))
outs(lab, 10, 2, mask(7))
# builder breakdown by market
put(lab, "A12", "Builder by market", font=F(b=True, sz=8, c=CY), bg=HDR); hdr(lab, 12, 2, ["Legs","W","L","Units","ROI"])
for i, mk in enumerate(["ML","Spread","Total","TT"]):
    r = 13+i; put(lab, f"A{r}", mk, font=F(b=True, c=OR))
    m = mask(7) + f"*({col('F')}=\"{mk}\")"
    lab[f"B{r}"] = f"=SUMPRODUCT({m})"; lab[f"C{r}"] = f'=SUMPRODUCT({m}*({col("U")}="W"))'
    lab[f"D{r}"] = f'=SUMPRODUCT({m}*({col("U")}="L"))'; lab[f"E{r}"] = f"=SUMPRODUCT({m}*{col('W')})"
    lab[f"F{r}"] = f'=IF(B{r}=0,"",E{r}/B{r})'
    for c, fm in zip("BCDEF", ["0","0","0","+0.00;-0.00;0.00","+0.0%;-0.0%;0.0%"]):
        lab[f"{c}{r}"].number_format = fm; lab[f"{c}{r}"].font = F(); lab[f"{c}{r}"].alignment = Alignment(horizontal="center")

# --- watchlist (rows 19+) ---
band(lab, 18, 1, 29, "WATCHLIST · candidates and cautions from the 10/23 scan (hypotheses, not proven edges)")
hdr(lab, 19, 2, CRIT); hdr(lab, 19, 18, OUTS); put(lab, "A19", "Rule", font=F(b=True, sz=8, c=CY), bg=HDR)
lab.row_dimensions[19].height = 26
W = [
 ("CANDIDATE · Projection 3–6 pts past the line", ["All","All","All","All",None,None,None,None,None,None,None,None,None,None,3,5.99]),
 ("CANDIDATE · Model ≥60% at −115 to +115",     ["All","All","All","All",None,None,-115,115,0.60,None,None,None,None,None,None,None]),
 ("CANDIDATE · Unders, model 55–65%",            ["All","Under","All","All",None,None,None,None,0.55,0.6499,None,None,None,None,None,None]),
 ("CANDIDATE · Game-total Unders on the card",   ["Total","Under","All","Yes",None,None,None,None,None,None,None,None,None,None,None,None]),
 ("CAUTION · Card plays on underdogs",           ["All","Dog","All","Yes",None,None,None,None,None,None,None,None,None,None,None,None]),
 ("CAUTION · Edge ≥20%",                         ["All","All","All","All",None,None,None,None,None,None,0.20,None,None,None,None,None]),
 ("CAUTION · Projection ≥6 pts past the line",   ["All","All","All","All",None,None,None,None,None,None,None,None,None,None,6,None]),
 ("CAUTION · Price +130 or longer",              ["All","All","All","All",None,None,130,None,None,None,None,None,None,None,None,None]),
 ("BASELINE · Every card play",                  ["All","All","All","Yes",None,None,None,None,None,None,None,None,None,None,None,None]),
 ("BASELINE · Every leg (both sides)",           ["All","All","All","All",None,None,None,None,None,None,None,None,None,None,None,None]),
 ("BASELINE · All Unders",                       ["All","Under","All","All",None,None,None,None,None,None,None,None,None,None,None,None]),
]
W += [("Your rule", ["All","All","All","All"] + [None]*12)] * 5
for j, (name, crit) in enumerate(W):
    r = 20+j
    put(lab, f"A{r}", name, font=F(b=True, c=OR if name.startswith("CAND") else ("F87171" if name.startswith("CAUT") else (MUT if name.startswith("BASE") else INP))))
    for i, v in enumerate(crit):
        c = put(lab, f"{L(2+i)}{r}", v, font=F(c="0B1020"), bg="FDE68A", al=Alignment(horizontal="center"))
        if i in (4, 5): c.number_format = "mm/dd/yy"
        if i in (8, 9, 10, 11, 12, 13): c.number_format = "0.0%"
        if i in (6, 7): c.number_format = "+0;-0;0"
    outs(lab, r, 18, mask(r))
lab.freeze_panes = "B4"
last = 20+len(W)-1
# dropdowns
for rng, opts in [((2, "All,ML,Spread,Total,TT")), ((3, "All,Over,Under,Fav,Dog")), ((4, "All,Home,Away")), ((5, "All,Yes,No"))]:
    dv = DataValidation(type="list", formula1=f'"{opts}"', allow_blank=True); lab.add_data_validation(dv)
    dv.add(f"{L(rng)}7"); dv.add(f"{L(rng)}20:{L(rng)}{last}")
# colour units / ROI
for rng in [f"E10:F10", f"L10:M10", f"E13:F16", f"U20:V{last}", f"AB20:AC{last}"]:
    lab.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], font=Font(name="Arial", b=True, color="4ADE80")))
    lab.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], font=Font(name="Arial", b=True, color="F87171")))
put(lab, f"A{last+2}", "z vs mkt above ~2 on a rule picked in advance is interesting. On a rule found by scanning, expect a z near 2.5 from luck alone (see Read Me).", font=F(i=True, c=MUT))

# ======================= SCAN (snapshot) =======================
R = pd.read_pickle(RULES).sort_values("z_vs_market", ascending=False)
sc = sheet("Scan 10-23", "8A94A8", {1: 52, 2: 20}, rows=3, cols=21)
put(sc, "A1", "RULE SCAN SNAPSHOT · 10/23/26 · 16 games, 160 legs, 403 rules (snapshot values, does not recalculate)", font=F(b=True, sz=11, c=OR))
cols = [("rule","Rule"),("family","Family"),("legs","Legs"),("games","Games"),("W","W"),("L","L"),("flat_units","Units"),("roi","ROI"),
        ("mkt_expected_units","Mkt exp u"),("z_vs_market","z vs mkt"),("p_value","p"),("bh_q","BH q"),("wed_legs","Wed legs"),("wed_roi","Wed ROI"),
        ("tue_thu_legs","Tue+Thu legs"),("tue_thu_roi","Tue+Thu ROI"),("stable","Both halves +"),("avg_odds","Avg odds"),("avg_model_p","Avg model %"),
        ("avg_novig_p","Avg no-vig %"),("avg_edge","Avg edge")]
hdr(sc, 3, 1, [c[1] for c in cols]); sc.row_dimensions[3].height = 28
fmts = {"roi":"+0.0%;-0.0%;0.0%","flat_units":"+0.00;-0.00;0.00","mkt_expected_units":"+0.00;-0.00;0.00","z_vs_market":"+0.00;-0.00;0.00",
        "p_value":"0.000","bh_q":"0.000","wed_roi":"+0.0%;-0.0%;0.0%","tue_thu_roi":"+0.0%;-0.0%;0.0%","avg_odds":"+0;-0;0",
        "avg_model_p":"0.0%","avg_novig_p":"0.0%","avg_edge":"+0.0%;-0.0%;0.0%"}
for i, (_, row) in enumerate(R.iterrows()):
    for j, (k, _) in enumerate(cols):
        v = row[k]
        if k == "stable": v = "Yes" if v else "No"
        if isinstance(v, float) and pd.isna(v): v = None
        c = sc.cell(4+i, j+1, v.item() if hasattr(v, "item") else v); c.font = F(); c.fill = fill(BG)
        if k in fmts: c.number_format = fmts[k]
sc.auto_filter.ref = f"A3:{L(len(cols))}{3+len(R)}"; sc.freeze_panes = "B4"
n = 3+len(R)
for rng in [f"G4:H{n}"]:
    sc.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], font=Font(name="Arial", color="4ADE80")))
    sc.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], font=Font(name="Arial", color="F87171")))

wb.move_sheet("Rule Lab", offset=-(len(wb.sheetnames)-1)); wb.active = 0
wb.save(OUT); print("saved", OUT)

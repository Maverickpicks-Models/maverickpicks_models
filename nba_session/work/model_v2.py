import re,sys
from xml.sax.saxutils import escape
def istr(ref,st,txt): return f'<c r="{ref}" s="{st}" t="inlineStr"><is><t xml:space="preserve">{escape(txt)}</t></is></c>'
def num(ref,st,v): return f'<c r="{ref}" s="{st}"><v>{v}</v></c>'
def fml(ref,st,f): return f'<c r="{ref}" s="{st}"><f>{escape(f)}</f></c>'
# ---------- Assumptions
p='xl/worksheets/sheet3.xml'; s=open(p).read()
s=s.replace('<c r="C13" s="37"><v>1.5</v></c>','<c r="C13" s="37"><v>2.5</v></c>',1)
assert '<v>2.5</v>' in s
rows=[]
rows.append(f'<row r="48" spans="1:6" ht="24" customHeight="1">{istr("A48","29","RECENCY, PACE AND INJURY  (added 11/12)")}</row>')
spec=[(49,'Recency','Player minutes half-life',('n',6),'days; 0 = season MPG only','Exp MPG = recency-weighted minutes from BoxScores (last ~3 games count most).'),
      (50,'Recency','Latest box score date',('f','MAX(BoxScores!$D$2:$D$6000)'),'computed','Do not edit.'),
      (51,'Pace','Recent league pace window',('n',14),'days','League pace in the last N days vs season average (TeamBoxAdvanced PACE).'),
      (52,'Pace','Pace drift weight',('n',1),'0 to 1','1 = add the full recent pace change to every matchup.'),
      (53,'Pace','League pace drift',('f','IFERROR(AVERAGEIFS(TeamBoxAdvanced!$AR$2:$AR$2000,TeamBoxAdvanced!$AC$2:$AC$2000,">="&(MAX(TeamBoxAdvanced!$AC$2:$AC$2000)-$C$51+1))-AVERAGE(TeamBoxAdvanced!$AR$2:$AR$2000),0)'),'possessions, computed','Recent minus season league pace.'),
      (54,'Injury','Injury impact scale',('n',0.67),'1 = full; 0.67 = two-thirds','Share of an injured player\'s minutes treated as lost (Out/D/Q). Teams missing stars beat the line 17-9.')]
for r,a,b,c,d,e in spec:
    cc=num(f'C{r}','37',c[1]) if c[0]=='n' else fml(f'C{r}','38',c[1])
    rows.append(f'<row r="{r}" spans="1:6" ht="36" customHeight="1">{istr(f"A{r}","80",a)}{istr(f"B{r}","81",b)}{cc}{istr(f"D{r}","82",d)}{istr(f"E{r}","83",e)}</row>')
s=s.replace('</sheetData>',''.join(rows)+'</sheetData>',1)
s=s.replace('<dimension ref="A1:BH46"/>','<dimension ref="A1:BH54"/>')
open(p,'w').write(s)
# ---------- Calculations: pace drift
p='xl/worksheets/sheet5.xml'; s=open(p).read()
old='$B$31+Assumptions!$C$11*((B43-$B$31)+(D43-$B$31))'
assert old in s
s=s.replace(old,old+'+Assumptions!$C$52*Assumptions!$C$53',1)
s=re.sub(r'(<c r="B47"[^>]*>)(<f>[^<]*</f>)<v>[^<]*</v>',r'\1\2',s)
open(p,'w').write(s)
# ---------- PlayerRatings H (recency minutes) and K (injury scale)
p='xl/worksheets/sheet18.xml'; s=open(p).read()
def H(r):
    tc=f'INDEX(Teams!$C$2:$C$31,MATCH($C{r},Teams!$D$2:$D$31,0))'
    w=f'(N(+BoxScores!$D$2:$D$6000)>0)*0.5^(((Assumptions!$C$50-N(+BoxScores!$D$2:$D$6000))/Assumptions!$C$49)*(N(+BoxScores!$D$2:$D$6000)>0))'
    m=f'(BoxScores!$A$2:$A$6000=$A{r})*(BoxScores!$B$2:$B$6000={tc})'
    rec=f'SUMPRODUCT({m}*N(+BoxScores!$F$2:$F$6000)*{w})/SUMPRODUCT({m}*{w})'
    return f'IF(OR($C{r}="",NOT(ISNUMBER($E{r}))),0,IF($E{r}<=0,0,MIN(48,IF(Assumptions!$C$49<=0,$F{r}/$E{r},IFERROR({rec},$F{r}/$E{r})))))'
def K(r):
    return f'IF($C{r}="",0,IF(ISNUMBER($J{r}),$J{r},$H{r}*(1-Assumptions!$C$54*(1-IF($I{r}="Out",0,IF($I{r}="D",0.25,IF($I{r}="Q",0.5,1)))))))'
n=0
def fix(m):
    global n
    col,r,attrs=m.group(1),int(m.group(2)),m.group(3)
    if col not in ('H','K') or not 6<=r<=805: return m.group(0)
    n+=1
    attrs=re.sub(r' t="[^"]*"','',attrs)
    return f'<c r="{col}{r}"{attrs}><f>{escape(H(r) if col=="H" else K(r))}</f></c>'
s=re.sub(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>.*?</c>)',fix,s)
open(p,'w').write(s); print('PlayerRatings cells rewritten',n)

import re,sys
from xml.sax.saxutils import escape
d=sys.argv[1]; p=d+'/xl/worksheets/sheet18.xml'; s=open(p).read()
TC=lambda r:f'INDEX(Teams!$C$2:$C$31,MATCH($C{r},Teams!$D$2:$D$31,0))'
def F(col,r):
    if col=='AF': return f'IF($C{r}="",0,IFERROR(SUMPRODUCT((PlayerBoxAdvanced[PLAYER]=$A{r})*(PlayerBoxAdvanced[TEAM]={TC(r)})*N(+PlayerBoxAdvanced[USG%])*N(+PlayerBoxAdvanced[MIN]))/SUMPRODUCT((PlayerBoxAdvanced[PLAYER]=$A{r})*(PlayerBoxAdvanced[TEAM]={TC(r)})*N(+PlayerBoxAdvanced[MIN])),0))'
    if col=='AG': return f'IF($C{r}="",0,IFERROR(SUMIFS(PlayerBox[FGA],PlayerBox[PLAYER],$A{r},PlayerBox[TEAM],{TC(r)})/COUNTIFS(PlayerBox[PLAYER],$A{r},PlayerBox[TEAM],{TC(r)}),0))'
    LOSS='(($I$6:$I$805="Out")+($I$6:$I$805="D")*0.75+($I$6:$I$805="Q")*0.5)'
    own=f'(($I{r}="Out")+($I{r}="D")*0.75+($I{r}="Q")*0.5)'
    if col=='AH': return f'IF($C{r}="",0,SUMPRODUCT(($C$6:$C$805=$C{r})*$H$6:$H$805*{LOSS}*$AF$6:$AF$805)/4800-$H{r}*{own}*$AF{r}/4800)'
    if col=='AI': return f'IF(OR($C{r}="",$I{r}="Out",$H{r}<=0,$AF{r}<=0),"",$AF{r}-Assumptions!$C$57*$AF{r}*$AH{r}+Assumptions!$C$58*$AH{r})'
    if col=='AJ': return f'IF(OR($C{r}="",$I{r}="Out",$H{r}<=0),"",MIN(42,$H{r}*(1-{own})+SUMPRODUCT(($C$6:$C$805=$C{r})*$H$6:$H$805*{LOSS})*$H{r}*(1-{own})*MAX(0,42-$H{r})/MAX(1,SUMPRODUCT(($C$6:$C$805=$C{r})*$H$6:$H$805*(1-{LOSS})*(42-$H$6:$H$805)))))'
    if col=='AK': return f'IF(OR($AI{r}="",$H{r}<=0,$AF{r}<=0),"",$AG{r}*($AI{r}/$AF{r})*($AJ{r}/$H{r}))'
heads={'AF':'Season USG%','AG':'FGA/G','AH':'Team usage out','AI':'Proj USG%','AJ':'Proj MPG','AK':'Proj FGA'}
def addrow(m):
    r=int(m.group(1)); body=m.group(3)
    if r==5: extra=''.join(f'<c r="{c}5" s="63" t="inlineStr"><is><t>{escape(h)}</t></is></c>' for c,h in heads.items())
    elif 6<=r<=805: extra=''.join(f'<c r="{c}{r}" s="36"><f>{escape(F(c,r))}</f></c>' for c in heads)
    else: return m.group(0)
    return f'<row r="{r}"{m.group(2)}>{body}{extra}</row>'
s=re.sub(r'<row r="(\d+)"([^>]*)>(.*?)</row>',addrow,s,flags=re.S)
s=re.sub(r'(<row r="(\d+)")( spans="[^"]*")',lambda m:m.group(1)+(' spans="1:37"' if 5<=int(m.group(2))<=805 else m.group(3)),s)
open(p,'w').write(s)
# Assumptions: coefficients
a=d+'/xl/worksheets/sheet3.xml'; t=open(a).read()
def istr(ref,st,txt): return f'<c r="{ref}" s="{st}" t="inlineStr"><is><t xml:space="preserve">{escape(txt)}</t></is></c>'
rows=f'<row r="56" spans="1:6" ht="24" customHeight="1">{istr("A56","29","USAGE REDISTRIBUTION  (added 11/13, PlayerRatings AF:AK, display only)")}</row>'
for r,b,v,u,e in ((57,'Usage shift: own-usage term',0.75,'x','Teammate USG change = -0.75 x own USG x share out + 19.5 x share out (fitted on 3,045 player-games).'),
                  (58,'Usage shift: flat term',19.5,'USG pts per 100% out','Low-usage players absorb most of the missing shots; stars barely change.')):
    rows+=f'<row r="{r}" spans="1:6" ht="36" customHeight="1">{istr(f"A{r}","80","Usage")}{istr(f"B{r}","81",b)}<c r="C{r}" s="37"><v>{v}</v></c>{istr(f"D{r}","82",u)}{istr(f"E{r}","83",e)}</row>'
t=t.replace('</sheetData>',rows+'</sheetData>',1); t=re.sub(r'<dimension ref="A1:BH\d+"/>','<dimension ref="A1:BH58"/>',t)
open(a,'w').write(t); print('ok')

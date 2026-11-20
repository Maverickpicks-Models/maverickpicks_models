import csv, sys, os, html, datetime
from playwright.sync_api import sync_playwright

TSV, OUT = sys.argv[1], os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)

# abbr, city, nickname, accent color (tuned to read on a dark background)
T = {
 "Atlanta Hawks": ("ATL","Atlanta","Hawks","#E03A3E"),
 "Orlando Magic": ("ORL","Orlando","Magic","#1E8FE0"),
 "Milwaukee Bucks": ("MIL","Milwaukee","Bucks","#2E8B4E"),
 "Washington Wizards": ("WAS","Washington","Wizards","#E31837"),
 "Minnesota Timberwolves": ("MIN","Minnesota","Timberwolves","#78BE20"),
 "Miami Heat": ("MIA","Miami","Heat","#C8102E"),
 "Charlotte Hornets": ("CHA","Charlotte","Hornets","#00A0B0"),
 "Brooklyn Nets": ("BKN","Brooklyn","Nets","#A7ADB7"),
 "Chicago Bulls": ("CHI","Chicago","Bulls","#CE1141"),
 "Toronto Raptors": ("TOR","Toronto","Raptors","#A1A1A4"),
 "Indiana Pacers": ("IND","Indiana","Pacers","#FDBB30"),
 "New Orleans Pelicans": ("NOP","New Orleans","Pelicans","#C8A86B"),
 "Utah Jazz": ("UTA","Utah","Jazz","#8A63D2"),
 "Memphis Grizzlies": ("MEM","Memphis","Grizzlies","#5D76A9"),
 "Dallas Mavericks": ("DAL","Dallas","Mavericks","#1F7AE0"),
 "Houston Rockets": ("HOU","Houston","Rockets","#CE1141"),
 "Golden State Warriors": ("GSW","Golden State","Warriors","#FFC72C"),
 "Los Angeles Lakers": ("LAL","Los Angeles","Lakers","#8A4FD1"),
 "Phoenix Suns": ("PHX","Phoenix","Suns","#E56020"),
 "Portland Trail Blazers": ("POR","Portland","Trail Blazers","#E03A3E"),
 "Sacramento Kings": ("SAC","Sacramento","Kings","#8A5CC7"),
 "LA Clippers": ("LAC","LA","Clippers","#2F6FD6"),
 "Boston Celtics": ("BOS","Boston","Celtics","#2E9E5B"),
 "Detroit Pistons": ("DET","Detroit","Pistons","#1D6FD1"),
 "New York Knicks": ("NYK","New York","Knicks","#F58426"),
 "Philadelphia 76ers": ("PHI","Philadelphia","76ers","#1D6FD6"),
 "Cleveland Cavaliers": ("CLE","Cleveland","Cavaliers","#B8325A"),
 "Denver Nuggets": ("DEN","Denver","Nuggets","#FEC524"),
 "Oklahoma City Thunder": ("OKC","Oklahoma City","Thunder","#1E8FE0"),
 "San Antonio Spurs": ("SAS","San Antonio","Spurs","#A7ADB7"),
}

def num(s):
    try: return float(s.replace('%','').replace('+',''))
    except ValueError: return None
def pct(s): return num(s)/100
def imp(o): return -o/(-o+100) if o < 0 else 100/(o+100)
def dec(o): return 100/-o if o < 0 else o/100
def fodds(o): return f"+{int(o)}" if o > 0 else f"\u2212{abs(int(o))}"
def fline(x): return f"+{x:g}" if x > 0 else f"-{abs(x):g}"

def side(label, line, odds, model, opp_odds, key, plays):
    if odds is None or opp_odds is None or model is None:
        return dict(label=label, line=line, odds=odds, model=model, edge=None, play=key in plays, rule=key in plays, key=key)
    nv = imp(odds)/(imp(odds)+imp(opp_odds))
    edge = model - nv
    ev = model*dec(odds) - (1-model)
    rule = edge >= 0.04 and ev > 0 and model <= 0.78
    return dict(label=label, line=line, odds=odds, model=model, edge=edge,
                play=key in plays, rule=rule, key=key)

games, warnings = [], []
with open(TSV) as f:
    for r in csv.DictReader(f, delimiter='\t'):
        if r['Away'] in ('', '0'): continue
        aw, hm = r['Away'], r['Home']
        A, H = T[aw], T[hm]
        plays = set(p.strip() for p in r['Card'].split('|'))
        U = num(r['Away spread']); V = pct(r['Away cover %']) if num(r['Away cover %']) is not None else None
        hs = num(r['Home spread'])
        if U is not None and hs is not None and abs(hs + U) > 0.01:
            warnings.append(f"{A[0]}@{H[0]}: home spread logged as {r['Home spread']} (cover {r['Home cover %']}); card shows {fline(-U)} at {1-V:.1%}")
        R = pct(r['Over %']) if num(r['Over %']) is not None else None; AB = pct(r['Away TT over %']); AF = pct(r['Home TT over %'])
        g = dict(date=r['Game date'], A=A, H=H, ap=num(r['Away proj']), hp=num(r['Home proj']),
                 tp=num(r['Total proj']), mla=pct(r['ML away']), mlh=pct(r['ML home']))
        ja, kh = num(r['ML away odds']), num(r['ML home odds'])
        W, Z = num(r['Away spr odds']), num(r['Home spr odds'])
        S, Tu = num(r['Over odds']), num(r['Under odds'])
        P = num(r['Total line']); AA = num(r['Away TT line']); AE = num(r['Home TT line'])
        AC, AD = num(r['Away TT Over']), num(r['Away TT Under'])
        AG, AH = num(r['Home TT Over']), num(r['Home TT Under'])
        g['sections'] = [
          ("Moneyline", [
            side(A[2], "ML", ja, g['mla'], kh, f"ML {aw}", plays),
            side(H[2], "ML", kh, g['mlh'], ja, f"ML {hm}", plays)]),
          ("Spread", [
            side(A[2], fline(U) if U is not None else 'ML', W, V, Z, f"Spread {aw} {fline(U) if U is not None else ''}", plays),
            side(H[2], fline(-U) if U is not None else 'ML', Z, (1-V) if V is not None else None, W, f"Spread {hm} {fline(-U) if U is not None else ''}", plays)]),
          ("Game Total", [
            side("Over", f"{P:g}" if P is not None else 'ML', S, R, Tu, f"Total Over {P}", plays),
            side("Under", f"{P:g}" if P is not None else 'ML', Tu, (1-R) if R is not None else None, S, f"Total Under {P}", plays)]),
          (f"{A[2]} Team Total", [
            side("Over", f"{AA:g}", AC, AB, AD, f"TT {aw} Over {AA:g}", plays),
            side("Under", f"{AA:g}", AD, 1-AB, AC, f"TT {aw} Under {AA:g}", plays)]),
          (f"{H[2]} Team Total", [
            side("Over", f"{AE:g}", AG, AF, AH, f"TT {hm} Over {AE:g}", plays),
            side("Under", f"{AE:g}", AH, 1-AF, AG, f"TT {hm} Under {AE:g}", plays)]),
        ]
        # cross-check: every card play matched a row, and rule agrees
        keys = {s['key'] for _, ss in g['sections'] for s in ss}
        for p in plays:
            if p not in keys: warnings.append(f"{A[0]}@{H[0]}: card play not matched: {p}")
        for _, ss in g['sections']:
            for s in ss:
                if s['play'] != s['rule']:
                    warnings.append(f"{A[0]}@{H[0]}: rule/card mismatch on {s['key']} (edge {s['edge']:+.3f})")
        games.append(g)

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#05070B;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1,'cv11' 1}
.card{width:1080px;height:1350px;position:relative;overflow:hidden;color:#E9EDF4;
 background:radial-gradient(1200px 600px at 50% -10%,#18202E 0%,#0C1119 55%,#090D14 100%);display:flex;flex-direction:column}
.glow{position:absolute;top:-220px;width:620px;height:620px;border-radius:50%;filter:blur(110px);opacity:.28}
.top{display:flex;justify-content:space-between;align-items:center;padding:38px 56px 0;position:relative}
.brand{font-family:'Inter Display';font-weight:800;font-size:26px;letter-spacing:.14em}
.brand span{color:#F5C451}
.meta{font-size:17px;font-weight:600;letter-spacing:.16em;color:#8C97AA;text-transform:uppercase}
.hero{position:relative;display:grid;grid-template-columns:1fr 400px 1fr;align-items:center;padding:42px 56px 0}
.team{display:flex;flex-direction:column;gap:6px}
.team.h{align-items:flex-end;text-align:right}
.abbr{font-family:'Inter Display';font-weight:900;font-size:88px;line-height:.9;letter-spacing:-.02em}
.nick{font-size:22px;font-weight:600;color:#C9D1DE}
.tag{font-size:13px;font-weight:700;letter-spacing:.2em;color:#6F7A8D;text-transform:uppercase;margin-bottom:4px}
.bar{height:6px;width:64px;border-radius:3px;margin-bottom:12px}
.mid{text-align:center}
.ptag{font-size:13px;font-weight:700;letter-spacing:.22em;color:#F5C451;text-transform:uppercase}
.score{font-family:'Inter Display';font-weight:800;font-size:58px;letter-spacing:-.02em;margin-top:8px;white-space:nowrap}
.score i{font-style:normal;color:#4A5466;margin:0 8px;font-weight:500}
.sub{font-size:16px;color:#9AA4B5;margin-top:8px;font-weight:500}
.wp{padding:34px 56px 0}
.wpl{display:flex;justify-content:space-between;font-size:15px;font-weight:700;letter-spacing:.06em;margin-bottom:10px;color:#C9D1DE}
.wpl span.c{color:#6F7A8D;letter-spacing:.2em;font-size:13px}
.track{display:flex;height:12px;border-radius:6px;overflow:hidden;gap:3px}
.table{margin:30px 56px 0;border-radius:18px;background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);padding:8px 0 10px}
.hdr,.row{display:grid;grid-template-columns:1fr 120px 120px 120px 130px 104px;align-items:center;padding:0 28px}
.hdr{height:42px;font-size:12px;font-weight:700;letter-spacing:.18em;color:#6F7A8D;text-transform:uppercase}
.hdr div:not(:first-child),.row div:not(:first-child){text-align:right}
.sec{padding:16px 28px 6px;font-size:13px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:#8C97AA;border-top:1px solid rgba(255,255,255,.05);margin-top:2px}
.sec:first-of-type{border-top:none}
.row{height:52px;font-size:21px;font-weight:600;position:relative}
.row .lab{display:flex;align-items:center;gap:12px;color:#E9EDF4}
.row .dot{width:9px;height:9px;border-radius:50%}
.row .muted{color:#7F8A9C}
.pos{color:#3DDC97}.neg{color:#E86F78}.flat{color:#7F8A9C}
.row.play{background:linear-gradient(90deg,rgba(245,196,81,.16),rgba(245,196,81,.04));}
.row.play::before{content:'';position:absolute;left:0;top:6px;bottom:6px;width:4px;border-radius:2px;background:#F5C451}
.pill{display:inline-block;font-size:12px;font-weight:800;letter-spacing:.16em;color:#0B0F17;background:#F5C451;border-radius:6px;padding:5px 9px}
.foot{margin-top:auto;padding:0 56px 34px;display:flex;justify-content:space-between;align-items:flex-end;font-size:14px;color:#6F7A8D;line-height:1.5}
.foot b{color:#C9D1DE;font-weight:700}
.count{font-size:14px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#F5C451;text-align:right}
"""

def edge_cls(e): return "pos" if e >= 0.005 else ("neg" if e <= -0.005 else "flat")

def card(g):
    A, H = g['A'], g['H']
    d = datetime.datetime.strptime(g['date'], "%m/%d/%y")
    date = d.strftime("%a %b %-d, %Y").upper()
    margin = g['hp'] - g['ap']
    fav = H[0] if margin > 0 else A[0]
    nplays = sum(s['play'] for _, ss in g['sections'] for s in ss)
    rows = []
    for title, ss in g['sections']:
        rows.append(f'<div class="sec">{html.escape(title)}</div>')
        for s in ss:
            dot = ""
            if title in ("Moneyline", "Spread"):
                col = A[3] if s['label'] == A[2] else H[3]
                dot = f'<span class="dot" style="background:{col}"></span>'
            line = '<span class="muted">—</span>' if s['line'] == "ML" else s['line']
            rows.append(f'''<div class="row{' play' if s['play'] else ''}">
              <div class="lab">{dot}{html.escape(s['label'])}</div><div>{line.replace('-','\u2212')}</div><div{' class="flat"' if s['odds'] is None else ''}>{'—' if s['odds'] is None else fodds(s['odds'])}</div>
              <div class="muted">{'—' if s['model'] is None else format(s['model']*100,'.1f')+'%'}</div><div class="{'flat' if s['edge'] is None else edge_cls(s['edge'])}">{'—' if s['edge'] is None else ('+' if s['edge']>=0 else '\u2212')+f"{abs(s['edge'])*100:.1f}%"}</div>
              <div>{'<span class="pill">PLAY</span>' if s['play'] else ''}</div></div>''')
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="card" id="card">
 <div class="glow" style="left:-160px;background:{A[3]}"></div>
 <div class="glow" style="right:-160px;background:{H[3]}"></div>
 <div class="top"><div class="brand">MAVERICK<span>PICKS</span></div><div class="meta">NBA &nbsp;·&nbsp; {date}</div></div>
 <div class="hero">
  <div class="team"><div class="bar" style="background:{A[3]}"></div><div class="tag">Away</div><div class="abbr">{A[0]}</div><div class="nick">{A[1]} {A[2]}</div></div>
  <div class="mid"><div class="ptag">Projected Score</div>
   <div class="score">{g['ap']:.1f}<i>–</i>{g['hp']:.1f}</div>
   <div class="sub">Total {g['tp']:.1f} &nbsp;·&nbsp; {fav} by {abs(margin):.1f}</div></div>
  <div class="team h"><div class="bar" style="background:{H[3]}"></div><div class="tag">Home</div><div class="abbr">{H[0]}</div><div class="nick">{H[1]} {H[2]}</div></div>
 </div>
 <div class="wp">
  <div class="wpl"><span>{A[0]} {g['mla']*100:.1f}%</span><span class="c">WIN PROBABILITY</span><span>{g['mlh']*100:.1f}% {H[0]}</span></div>
  <div class="track"><div style="width:{g['mla']*100:.2f}%;background:{A[3]}"></div><div style="flex:1;background:{H[3]}"></div></div>
 </div>
 <div class="table">
  <div class="hdr"><div>Market</div><div>Line</div><div>Odds</div><div>Model</div><div>Edge</div><div></div></div>
  {''.join(rows)}
 </div>
 <div class="foot"><div>Edge = model probability minus no-vig market probability.<br><b>Odds: Novig</b> &nbsp;·&nbsp; 21+ &nbsp;·&nbsp; Bet responsibly.</div>
  <div class="count">{nplays} model play{'s' if nplays!=1 else ''}</div></div>
</div></body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1080,"height":1350}, device_scale_factor=2)
    for i, g in enumerate(games, 1):
        name = f"{i:02d}_{g['A'][0]}_at_{g['H'][0]}"
        h = os.path.join(OUT, name + ".html")
        open(h, "w").write(card(g))
        pg.goto("file://" + h)
        pg.wait_for_timeout(150)
        over = pg.evaluate("(()=>{const c=document.getElementById('card');const t=c.querySelector('.table').getBoundingClientRect();const f=c.querySelector('.foot').getBoundingClientRect();return [t.bottom,f.top]})()")
        if over[0] > over[1]: warnings.append(f"{name}: table overlaps footer {over}")
        pg.locator("#card").screenshot(path=os.path.join(OUT, name + ".png"))
    b.close()
print("\n".join(warnings) or "no warnings")

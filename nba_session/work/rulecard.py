import json, sys, os, html
from playwright.sync_api import sync_playwright
D = json.load(open(sys.argv[1])); OUT = os.path.abspath(sys.argv[2]); DATE = sys.argv[3]
P = D["plays"]
def fodds(o): return f"+{int(o)}" if o > 0 else f"−{abs(int(o))}"
RULES = {"A": "Projection 3–6 pts past the line", "B": "Model ≥60% at −115 to +115",
         "C": "Under, model 55–65%", "D": "Card game-total Under"}
tiers = [(3, "STRONGEST · matches 3 rules"), (2, "MATCHES 2 RULES"), (1, "MATCHES 1 RULE")]
rows = []
for n, title in tiers:
    grp = [p for p in P if len(p["rules"]) == n]
    if not grp: continue
    rows.append(f'<div class="sec">{title}<span>{len(grp)}</span></div>')
    for p in grp:
        line = p["line"].replace("-", "−")
        label = html.escape(p["play"]) + (f' <b>{line}</b>' if line else "")
        chips = "".join(f'<i class="{"on" if r in p["rules"] else ""}">{r}</i>' for r in "ABCD")
        rows.append(f'''<div class="row">
          <div class="g">{html.escape(p["game"])}</div><div class="p">{label}</div>
          <div class="n">{fodds(p["odds"])}</div><div class="n m">{p["model"]*100:.1f}%</div>
          <div class="n e">+{p["edge"]*100:.1f}%</div><div class="chips">{chips}</div></div>''')
legend = "".join(f'<div><i class="on">{k}</i>{html.escape(v)}</div>' for k, v in RULES.items())
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#05070B;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}
.card{width:1080px;position:relative;overflow:hidden;color:#E9EDF4;padding:40px 52px 36px;
 background:radial-gradient(1100px 520px at 50% -12%,#2A2210 0%,#0F131C 55%,#090D14 100%)}
.top{display:flex;justify-content:space-between;align-items:center}
.brand{font-family:'Inter Display';font-weight:800;font-size:26px;letter-spacing:.14em}.brand span{color:#F5C451}
.meta{font-size:17px;font-weight:600;letter-spacing:.16em;color:#8C97AA}
h1{font-family:'Inter Display';font-weight:900;font-size:64px;letter-spacing:-.01em;margin-top:34px;line-height:1}
h1 span{color:#F5C451}
.sub{font-size:18px;color:#9AA4B5;margin-top:12px;font-weight:500}
.tbl{margin-top:28px;border-radius:18px;background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);padding:6px 0 10px}
.hdr,.row{display:grid;grid-template-columns:200px minmax(0,1fr) 80px 86px 92px 136px;align-items:center;padding:0 24px;column-gap:10px}
.hdr{height:40px;font-size:12px;font-weight:700;letter-spacing:.18em;color:#6F7A8D;text-transform:uppercase}
.hdr .n,.row .n{text-align:right}.hdr .c,.chips{text-align:right}
.sec{display:flex;justify-content:space-between;padding:16px 24px 6px;font-size:13px;font-weight:800;letter-spacing:.18em;color:#F5C451;border-top:1px solid rgba(255,255,255,.06)}
.sec span{color:#6F7A8D}
.row{height:54px;font-size:19px;font-weight:600}
.row:nth-child(even){background:rgba(255,255,255,.015)}
.g{font-size:15px;color:#8C97AA;font-weight:600;white-space:nowrap}
.p{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}.p b{font-weight:700;color:#E9EDF4;margin-left:6px}
.m{color:#8C97AA}.e{color:#3DDC97}
.chips{display:flex;justify-content:flex-end;gap:6px}
i{font-style:normal;display:inline-flex;align-items:center;justify-content:center;width:25px;height:25px;border-radius:7px;font-size:13px;font-weight:800;
 color:#3A4456;border:1px solid #232C3D}
i.on{background:#F5C451;color:#0B0F17;border-color:#F5C451}
.legend{display:grid;grid-template-columns:1fr 1fr;gap:12px 28px;margin-top:26px;font-size:15px;color:#C9D1DE;font-weight:500}
.legend div{display:flex;align-items:center;gap:12px}
.foot{display:flex;justify-content:space-between;align-items:flex-end;margin-top:26px;font-size:14px;color:#6F7A8D;line-height:1.5}
.foot b{color:#C9D1DE}
.tag{font-size:13px;font-weight:800;letter-spacing:.16em;color:#F5C451;text-transform:uppercase;text-align:right}
"""
doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="card" id="card">
<div class="top"><div class="brand">MAVERICK<span>PICKS</span></div><div class="meta">NBA &nbsp;·&nbsp; {DATE}</div></div>
<h1>RULE <span>PLAYS</span></h1>
<div class="sub">{len(P)} plays across {len({p['game'] for p in P})} games that match MaverickPicks tracking rules · sorted by rules matched, then edge</div>
<div class="tbl"><div class="hdr"><div>Game</div><div>Play</div><div class="n">Odds</div><div class="n">Model</div><div class="n">Edge</div><div class="c">Rules</div></div>
{''.join(rows)}</div>
<div class="legend">{legend}</div>
<div class="foot"><div>Edge = model probability minus no-vig market probability.<br><b>Odds: DraftKings</b> &nbsp;·&nbsp; 21+ &nbsp;·&nbsp; Bet responsibly.</div>
<div class="tag">Rules in early testing<br><span style="color:#6F7A8D">Small sample · 1u flat tracking</span></div></div>
</div></body></html>"""
os.makedirs(os.path.dirname(OUT), exist_ok=True)
h = OUT.replace(".png", ".html"); open(h, "w").write(doc)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
    pg.goto("file://" + h); pg.wait_for_timeout(200)
    print("height", pg.evaluate("document.getElementById('card').getBoundingClientRect().height"))
    pg.locator("#card").screenshot(path=OUT); b.close()

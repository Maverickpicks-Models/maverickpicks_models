import json,sys,os,html
from playwright.sync_api import sync_playwright
spec=json.load(open(sys.argv[1])); out=sys.argv[2]
COL={'CORE':'#F5C451','TEST':'#8FA3C2','CRAFTED':'#3DD6C4'}
def sec(name,items,sub):
    rows=''.join(f'''<div class="it"><div class="g">{html.escape(i[0])}</div><div class="p">{html.escape(i[1])}</div><div class="tags">{''.join(f'<span class="tag" style="background:{COL[t]}">{t}</span>' for t in i[3])}</div><div class="u">{html.escape(i[2])}</div></div>''' for i in items)
    return f'<div class="sec"><div class="sh"><span class="dot" style="background:{COL[name]}"></span>{name}<span class="sub">{html.escape(sub)}</span></div>{rows}</div>'
body=''.join(sec(s['name'],s['items'],s['sub']) for s in spec['sections'])
H=f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#05070B;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}}
#card{{width:1080px;color:#E9EDF4;background:radial-gradient(1200px 600px at 50% -10%,#18202E 0%,#0C1119 55%,#090D14 100%);padding:40px 56px 36px}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.brand{{font-weight:800;font-size:26px;letter-spacing:.14em}} .brand span{{color:#F5C451}}
.meta{{font-size:17px;font-weight:600;letter-spacing:.16em;color:#8C97AA;text-transform:uppercase}}
h1{{font-size:54px;font-weight:900;letter-spacing:-.01em;margin:34px 0 6px}}
.lead{{font-size:19px;color:#9AA4B5;margin-bottom:22px}}
.sec{{margin-top:22px;border-radius:18px;background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);padding:14px 26px 10px}}
.sh{{display:flex;align-items:center;gap:12px;font-size:15px;font-weight:800;letter-spacing:.2em;color:#E9EDF4;margin-bottom:6px}}
.sub{{font-weight:600;letter-spacing:.04em;color:#7F8A9C;font-size:15px;margin-left:8px}}
.dot{{width:12px;height:12px;border-radius:3px}}
.it{{display:grid;grid-template-columns:150px 1fr 220px 70px;align-items:center;height:46px;border-top:1px solid rgba(255,255,255,.05);font-size:21px}}
.it:first-of-type{{border-top:none}}
.g{{color:#8C97AA;font-weight:700;font-size:17px;letter-spacing:.04em}} .p{{font-weight:700}}
.tags{{display:flex;gap:6px;justify-content:flex-end}}
.tag{{font-size:11px;font-weight:800;letter-spacing:.12em;color:#0B0F17;border-radius:6px;padding:4px 7px}}
.u{{text-align:right;color:#C9D1DE;font-weight:600;font-size:19px}}
.foot{{margin-top:26px;font-size:14px;color:#6F7A8D;line-height:1.6}} .foot b{{color:#C9D1DE}}
</style></head><body><div id="card">
<div class="top"><div class="brand">MAVERICK<span>PICKS</span></div><div class="meta">NBA · {html.escape(spec['date'])}</div></div>
<h1>Recommended Card</h1><div class="lead">{html.escape(spec['lead'])}</div>
{body}
<div class="foot">{spec['foot']}</div></div></body></html>"""
os.makedirs(os.path.dirname(os.path.abspath(out)),exist_ok=True)
hp=os.path.abspath(out).replace('.png','.html'); open(hp,'w').write(H)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1080,"height":1000},device_scale_factor=2)
    pg.goto('file://'+hp); pg.wait_for_timeout(150); pg.locator('#card').screenshot(path=out); b.close()
print('ok')

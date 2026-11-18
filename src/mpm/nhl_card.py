"""Discord graphics for the NHL card: one card per game plus "Tonight's Card".

html_game(result, when, records) / html_tonight(results, when, records) return self-contained HTML;
render(html, path) saves a PNG with Playwright (pip install playwright; python -m playwright install chromium).
records = {rule_code: (wins, losses, flat_roi)} from nhl.v_rule_record.
"""
from __future__ import annotations

from .nhl_model import payout

COL = {'SEA': '#0B3A4A', 'CAR': '#CE1126', 'WPG': '#041E42', 'CHI': '#CF0A2C', 'MIN': '#154734', 'BOS': '#1a1a1a',
       'EDM': '#041E42', 'TOR': '#00205B', 'COL': '#6F263D', 'MTL': '#AF1E2D', 'DET': '#CE1126', 'TBL': '#002868',
       'OTT': '#C52032', 'PIT': '#1a1a1a', 'NJD': '#CE1126', 'WSH': '#041E42', 'PHI': '#F74902', 'CBJ': '#002654',
       'FLA': '#C8102E', 'STL': '#002F87', 'BUF': '#003087', 'DAL': '#006847', 'SJS': '#006D75', 'UTA': '#4a6b8a',
       'NYI': '#00539B', 'ANA': '#B9975B', 'CGY': '#C8102E', 'LAK': '#1a1a1a', 'NYR': '#0038A8', 'VAN': '#00205B',
       'NSH': '#FFB81C', 'VGK': '#B4975A'}
LEG = ("Core: A TT under edge ≥4% · B TT 3.5 proj 3.25–3.5 under · D TT 3.5 proj >3.5 over · E 6.5 proj >6.5 over · "
       "X cross-prop · HU home dog under · Tests: C H F G2 BB GU LR OD UU XM XMB RF · Shadow: XU")
CSS_BASE = """*{box-sizing:border-box;margin:0;padding:0} body{background:#0d1117;font-family:Inter,Segoe UI,sans-serif;color:#e8edf3}
.card{width:1000px;padding:32px 34px;background:linear-gradient(160deg,#141b26,#0e131b)}
.top{display:flex;justify-content:space-between;align-items:center}.brand{font-weight:800;font-size:19px;letter-spacing:.5px}.brand b{color:#3ddc97}
.date{color:#8b96a5;font-size:13px;letter-spacing:2px;font-weight:600}
.chip{display:inline-block;border-radius:20px;padding:5px 11px;font-size:11px;font-weight:800;letter-spacing:1px;color:#0d1117;white-space:nowrap}
.chip.p{background:#3ddc97}.chip.t{background:#f2b84b}.chip.z{background:#6b7684}.chip.big{font-size:12px;padding:6px 13px}
.rr{font-size:12.5px;color:#c9d2dd}.rr b{color:#e8edf3}.pos{color:#3ddc97;font-weight:700}.neg{color:#ff6b6b;font-weight:600}
.foot{display:flex;justify-content:space-between;color:#5d6876;font-size:10.5px;margin-top:16px;gap:20px}"""


def _pct(x):
    return f"{x * 100:+.1f}%"


def rule_record(code: str, records: dict) -> str:
    out = []
    for t in [c.strip() for c in code.split(",") if c.strip()]:
        v = records.get(t)
        if not v or (v[0] + v[1]) == 0:
            out.append(f"<b>{t}</b> new")
        else:
            w, l, roi = v
            c = "#3ddc97" if roi >= 0 else "#ff6b6b"
            out.append(f"<b>{t}</b> {w}-{l} <span style='color:{c};font-weight:700'>{roi * 100:+.0f}% ROI</span>")
    return " · ".join(out)


def _label(pl, g) -> str:
    if pl.market == "ML":
        return f"{g.home if pl.side == 'Home' else g.away} moneyline"
    if pl.market == "Total":
        return f"Game total {pl.side.lower()} {pl.point:g}"
    team = g.away if pl.market == "TT Away" else g.home
    return f"{team} team total {pl.side.lower()} {pl.point:g}"


def _chip(pl) -> str:
    if pl.stake <= 0:
        return f'<span class="chip z">TRACK $0 · {pl.code}</span>'
    return f'<span class="chip {"p" if pl.core else "t"}">{"PLAY" if pl.core else "TEST"} ${pl.stake:.0f} · {pl.code}</span>'


def html_game(r, when: str, records: dict, names: dict | None = None) -> str:
    g, p, i = r.game, r.prices, r.info
    names = names or {}
    A, H = g.away, g.home
    TA, TH = i["TA"], i["TH"]
    rows = [("Total", "Over", g.total_line, g.over_price, r.la + r.lh, i["blend_over"], i["over_nv"]),
            ("Total", "Under", g.total_line, g.under_price, r.la + r.lh, 1 - i["blend_over"], 1 - i["over_nv"]),
            ("TT Away", "Over", TA[0], TA[1], r.la, p.team_over(TA[0], "a"), _nv(TA)),
            ("TT Away", "Under", TA[0], TA[2], r.la, 1 - p.team_over(TA[0], "a"), 1 - _nv(TA)),
            ("TT Home", "Over", TH[0], TH[1], r.lh, p.team_over(TH[0], "h"), _nv(TH)),
            ("TT Home", "Under", TH[0], TH[2], r.lh, 1 - p.team_over(TH[0], "h"), 1 - _nv(TH)),
            ("ML", "Away", None, g.ml_away, r.la, p.ml_away, 1 - i["nv_home"]),
            ("ML", "Home", None, g.ml_home, r.lh, p.ml_home, i["nv_home"])]
    pk = {(pl.market, pl.side): pl for pl in r.plays}
    tr = ""
    for mk, sd, L, o, pr, mod, nv in rows:
        e, evv, pl = mod - nv, mod * payout(o) - (1 - mod), pk.get((mk, sd))
        cls = "" if not pl else ("play" if pl.core and pl.stake > 0 else "test")
        name = {"Total": "Game total", "TT Away": f"{A} team total", "TT Home": f"{H} team total", "ML": f"{A if sd == 'Away' else H} ML"}[mk]
        side = "Win" if mk == "ML" else sd
        tr += (f'<tr class="{cls}"><td class="mk">{name}</td><td class="{side.lower()}">{side}</td><td>{"—" if L is None else format(L, "g")}</td>'
               f'<td>{o:+d}</td><td>{pr:.2f}</td><td>{mod * 100:.1f}%</td><td>{nv * 100:.1f}%</td>'
               f'<td class="{"pos" if e >= 0 else "neg"}">{_pct(e)}</td><td class="{"pos" if evv >= 0 else "neg"}">{_pct(evv)}</td>'
               f'<td class="fl">{_chip(pl) if pl else "<span class=dash>—</span>"}</td></tr>')
    lst = ""
    for pl in sorted(r.plays, key=lambda x: (-x.stake, not x.core)):
        mp = f" · bet at {pl.min_price:+d} or better" if pl.min_price is not None and pl.stake > 0 else ""
        lst += (f'<div class="pl">{_chip(pl)}<span class="pn">{_label(pl, g)}</span><span class="po">({pl.price:+d})</span>'
                f'<span class="pd">edge {_pct(pl.model_p - pl.fair_p)} · EV {_pct(pl.ev)}{mp}<br>'
                f'<span class="rr">Rule record: {rule_record(pl.code, records)}</span></span></div>')
    lst = lst or '<div class="none">No plays</div>'
    notes = "".join(f"<div class='nt'>• {n}</div>" for n in r.notes if not n.startswith("dropped"))
    ma, mh = p.ml_away, p.ml_home
    tt_src = "" if g.tt_source == "novig" else "<div class='nt'>• Team totals priced from the books (Novig has none in the feed); check the Novig price before betting.</div>"
    css = CSS_BASE + """
.hdr{display:flex;align-items:center;justify-content:space-between;margin:26px 0 22px}.team{display:flex;align-items:center;gap:14px;width:330px}.team.r{flex-direction:row-reverse;text-align:right}
.logo{width:72px;height:72px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:21px;border:3px solid #2a3442;color:#fff}
.tn{font-size:22px;font-weight:800}.ts{color:#8b96a5;font-size:12.5px;margin-top:4px}.score{text-align:center}.score .n{font-size:44px;font-weight:900}.score .n span{color:#3a4656}.score .l{color:#8b96a5;font-size:11px;letter-spacing:3px}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}.stat{background:#161e2a;border:1px solid #232d3b;border-radius:12px;padding:15px 14px}.k{color:#8b96a5;font-size:10.5px;letter-spacing:1.6px;font-weight:600}.v{font-size:21px;font-weight:800;margin-top:9px;white-space:nowrap}.v small{font-size:12.5px;color:#9aa5b4;font-weight:600;margin-left:4px}
table{width:100%;border-collapse:separate;border-spacing:0 8px;margin-top:18px;font-size:14.5px}th{color:#8b96a5;font-size:10.5px;letter-spacing:1.6px;font-weight:600;padding:0 6px}th:first-child{text-align:left;padding-left:14px}th:last-child{text-align:right}
td{background:#161e2a;padding:12px 6px;text-align:center;border-top:1px solid #232d3b;border-bottom:1px solid #232d3b}td:first-child{border-left:3px solid #232d3b;border-radius:8px 0 0 8px;text-align:left;padding-left:14px;font-weight:700}td:last-child{border-right:1px solid #232d3b;border-radius:0 8px 8px 0;text-align:right;padding-right:10px}
tr.play td{background:#13291f;border-color:#2b6a4a}tr.play td:first-child{border-left-color:#3ddc97}tr.test td{background:#2a2414;border-color:#6b5520}tr.test td:first-child{border-left-color:#f2b84b}
.over{color:#6fb6ff;font-weight:700}.under{color:#c49bff;font-weight:700}.dash{color:#4a5565}
.box{background:#161e2a;border:1px solid #232d3b;border-radius:12px;padding:18px 18px 8px;margin-top:10px}.bh{color:#8b96a5;font-size:10.5px;letter-spacing:2px;font-weight:600;margin-bottom:12px}
.pl{display:flex;align-items:center;gap:12px;padding-bottom:14px}.pn{font-size:17px;font-weight:800}.po{color:#9aa5b4;font-size:16px;font-weight:600}.pd{text-align:right;margin-left:auto;color:#9aa5b4;font-size:12.5px}.none{color:#6b7684;font-size:13px;padding-bottom:12px}
.nt{color:#8b96a5;font-size:12px;margin:2px 0 6px}"""
    OR, DR, GR = i["OR"], i["DR"], i["GR"]
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="card">
<div class="top"><div class="brand">MAVERICK<b>PICKS</b> · NHL MODEL</div><div class="date">{when}</div></div>
<div class="hdr"><div class="team"><div class="logo" style="background:{COL.get(A, '#333')}">{A}</div><div><div class="tn">{names.get(A, A)}</div><div class="ts">Away · G: {g.g_away or 'TBD'}{f' (#{GR[0]})' if GR[0] else ''}</div></div></div>
<div class="score"><div class="n">{r.la:.2f}<span>–</span>{r.lh:.2f}</div><div class="l">PROJECTED GOALS</div></div>
<div class="team r"><div class="logo" style="background:{COL.get(H, '#333')}">{H}</div><div><div class="tn">{names.get(H, H)}</div><div class="ts">Home · G: {g.g_home or 'TBD'}{f' (#{GR[1]})' if GR[1] else ''}</div></div></div></div>
<div class="stats">
<div class="stat"><div class="k">WIN PROBABILITY</div><div class="v">{A if ma >= mh else H} {max(ma, mh) * 100:.0f}%<small>{H if ma >= mh else A} {min(ma, mh) * 100:.0f}%</small></div></div>
<div class="stat"><div class="k">MONEYLINE</div><div class="v">{g.ml_away:+d}<small>{A}</small></div><div class="v" style="margin-top:2px">{g.ml_home:+d}<small>{H}</small></div></div>
<div class="stat"><div class="k">PROJECTED TOTAL</div><div class="v">{r.la + r.lh:.2f}<small>line {g.total_line:g}</small></div></div>
<div class="stat"><div class="k">OFFENSE RANK (XGF)</div><div class="v">{A} #{OR[0]}<small>{H} #{OR[1]}</small></div></div>
<div class="stat"><div class="k">DEFENSE RANK (XGA)</div><div class="v">{A} #{DR[0]}<small>{H} #{DR[1]}</small></div></div></div>
<table><tr><th>MARKET</th><th>SIDE</th><th>LINE</th><th>ODDS</th><th>PROJ</th><th>MODEL</th><th>NO-VIG</th><th>EDGE</th><th>EV</th><th>FLAG</th></tr>{tr}</table>
<div class="box"><div class="bh">PLAYS · STAKE ON A $1,000 BANKROLL</div>{lst}{tt_src}{notes}</div>
<div class="foot"><div>{LEG}<br>Rule record = live season record and flat ROI per bet. Stakes: quarter-Kelly; $0 = tracked, not bet. Data: MoneyPuck.com</div><div style="white-space:nowrap">Model picks, not guarantees · 21+</div></div>
</div></body></html>"""


def _nv(t):
    from .nhl_model import no_vig
    return no_vig(t[1], t[2])


def html_tonight(results, when: str, records: dict) -> str:
    rows, stake_core, stake_test, nc, nt, ntrack = "", 0.0, 0.0, 0, 0, 0
    for r in results:
        g = r.game
        for pl in sorted(r.plays, key=lambda x: -x.stake):
            if pl.stake <= 0:
                ntrack += 1
                continue
            if pl.core: stake_core += pl.stake; nc += 1
            else: stake_test += pl.stake; nt += 1
            rows += (f'<tr class="{"play" if pl.core else "test"}"><td>{g.start_et}</td><td class="g">{g.away} @ {g.home}</td>'
                     f'<td class="pn">{_label(pl, g)}</td><td>{pl.price:+d}</td><td>{pl.min_price:+d}</td><td>${pl.stake:.0f}</td>'
                     f'<td class="rr">{rule_record(pl.code, records)}</td><td>{_chip(pl)}</td></tr>')
    css = CSS_BASE + """h1{font-size:34px;font-weight:900;margin:22px 0 6px}.sum{display:flex;gap:10px;margin-bottom:14px}
table{width:100%;border-collapse:separate;border-spacing:0 6px;font-size:14px}th{color:#8b96a5;font-size:10.5px;letter-spacing:1.4px;font-weight:600;text-align:left;padding:0 8px}
td{background:#161e2a;padding:10px 8px;border-top:1px solid #232d3b;border-bottom:1px solid #232d3b}td:first-child{border-left:3px solid #232d3b;border-radius:8px 0 0 8px;color:#9aa5b4}td:last-child{border-radius:0 8px 8px 0;text-align:right}
tr.play td{background:#13291f;border-color:#2b6a4a}tr.play td:first-child{border-left-color:#3ddc97}tr.test td:first-child{border-left-color:#f2b84b}.g,.pn{font-weight:700}"""
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="card">
<div class="top"><div class="brand">MAVERICK<b>PICKS</b> · NHL MODEL</div><div class="date">{when}</div></div>
<h1>Tonight's Card</h1><div class="sum"><span class="chip p big">{nc} CORE · ${stake_core:.0f}</span><span class="chip t big">{nt} TEST{"" if nt == 1 else "S"} · ${stake_test:.0f}</span><span class="chip z big">{ntrack} TRACKED · $0</span></div>
<table><tr><th>TIME ET</th><th>GAME</th><th>PLAY</th><th>ODDS</th><th>MIN PRICE</th><th>STAKE</th><th>RULE RECORD · ROI</th><th style="text-align:right">RULE</th></tr>{rows}</table>
<div class="foot"><div>$1,000 bankroll · quarter-Kelly stakes · max $30 a bet, $40 a game, $120 a night · bet only at the min price or better · Data: MoneyPuck.com</div><div>Model picks, not guarantees · 21+</div></div></div></body></html>"""


def render(html: str, path: str) -> str:
    """Save a PNG (Playwright) next to the HTML; falls back to the HTML file if Playwright is missing."""
    html_path = path.rsplit(".", 1)[0] + ".html"
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return html_path
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1000, "height": 800}, device_scale_factor=2)
        pg.set_content(html)
        pg.locator(".card").screenshot(path=path)
        b.close()
    return path

"""Replay every rule over the whole 2026-27 season so far (11/25).

usage (from nba_session/):  WB=in1125/s3.xlsx python3 work/replay_season.py  -> work/replay_season.json + printed tables

For every game in the Tracking sheet (one row per game; the workbook's projection and the Novig lines logged that night,
so no hindsight in the model numbers) the v5.2 rules engine (work/rules.py) is run as of that date:
  * B2B and fatigue from the schedule; team ranks (T5) and turnover profiles (T2) as of the date (crafted_bt / xposs);
  * P1/P2/P3 from season-to-date, shooting-luck-adjusted ratings rebuilt from the box scores up to the day before
    (mpm.model.SeasonState), not today's sheets;
  * CraftedNBA (K1-K4, X6) and the injury list (T6) only on dates with a saved card config (cfg_MMDD.json, from 11/11);
  * Questionable-starter half stakes are not replayed (no historical injury reports here).
Each rule's recommendations are graded flat (1 unit each) and the engine's v5.2 plays are sized at $20 a unit with the
$30 game and $120 night caps (scaled down in proportion when over).
"""
import collections, datetime as dt, json, math, os, subprocess, sys, tempfile
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, '..', 'src'), os.path.join(ROOT, '..', 'tests')]
from sqlite_db import make_db               # noqa: E402
from mpm import load_workbook as LW, model as M   # noqa: E402

WB = os.environ.get('WB', 'in1125/s3.xlsx')
wb = openpyxl.load_workbook(WB, read_only=True, data_only=True)
name_of = {r[1]: r[0] for r in wb['TeamShooting'].iter_rows(min_row=7, max_row=36, values_only=True) if r[0]}
code_of = {v: k for k, v in name_of.items()}

# ---- games from Tracking (first row per game)
games = {}
for r in wb['Tracking'].iter_rows(min_row=13, max_col=49, values_only=True):
    if not r[1] or not hasattr(r[0], 'date') or r[39] is None or r[40] is None:
        continue
    key = (r[0].date(), r[1], r[2])
    if key in games or None in (r[3], r[4], r[15], r[20], r[19], r[18], r[22], r[25], r[9], r[10]):
        continue
    games[key] = r
print(f'{len(games)} graded games in Tracking, {min(k[0] for k in games)} to {max(k[0] for k in games)}')

def imp(o): return -o / (-o + 100) if o < 0 else 100 / (o + 100)
def dec(o): return 100 / -o if o < 0 else o / 100
def leg(mk, lab, odds, other, side, model=None):
    a, b = imp(odds), imp(other)
    return dict(mk=mk, lab=lab, price=round(a, 4), odds=int(odds), nv=a / (a + b), model=model, side=side)

def run_entry(r):
    aw, hm = r[1], r[2]; U, P = float(r[20]), float(r[15])
    legs = [leg('ML', f'{aw} ML', r[9], r[10], 'away'), leg('ML', f'{hm} ML', r[10], r[9], 'home'),
            leg('Spread', f'{aw} {U:+g}', r[22], r[25], 'away'), leg('Spread', f'{hm} {-U:+g}', r[25], r[22], 'home'),
            leg('Total', f'Over {P}', r[18], r[19], 'over'), leg('Total', f'Under {P}', r[19], r[18], 'under')]
    att = htt = None
    if r[26] is not None and r[28] is not None and r[29] is not None:
        att = [float(r[26]), imp(r[28]), imp(r[29])]
        legs.append(leg('TT', f'{aw} TT Over {att[0]}', r[28], r[29], 'over', r[27]))
    if r[30] is not None and r[32] is not None and r[33] is not None:
        htt = [float(r[30]), imp(r[32]), imp(r[33])]
        legs.append(leg('TT', f'{hm} TT Over {htt[0]}', r[32], r[33], 'over', r[31]))
    if not (att and htt):
        att = htt = None
    return dict(aw=aw, hm=hm, ap=float(r[3]), hp=float(r[4]), sp=[U, imp(r[22]), imp(r[25])], tot=[P, imp(r[18]), imp(r[19])],
                ml=[imp(r[9]), imp(r[10])], att=att, htt=htt, legs=legs)

# ---- season-to-date ratings (as of each date) from the box scores
db = make_db(); LW.load_box(db, wb)
d0, d1 = (str(x)[:10] for x in db.one("SELECT MIN(game_date), MAX(game_date) FROM nba.team_box_adv"))
st = M.SeasonState(db, d0, d1)
played = collections.defaultdict(set)
for t, d in db.q("SELECT team_code, game_date FROM nba.team_box"):
    played[t].add(dt.date.fromisoformat(str(d)[:10]))

def asof(day):
    out = {}
    lg = st.league(day)
    for code, name in name_of.items():
        adj = st.team(code, day)
        if not adj:
            continue
        M.A['remove_luck'] = False; raw = st.team(code, day); M.A['remove_luck'] = True
        out[name] = dict(o=adj['o'], d=adj['d'], p=adj['pace'], gp=adj['gp'], netluck=(raw['o'] - adj['o']) - (raw['d'] - adj['d']))
    out['_LP'], out['_LB'] = lg['pace'], lg['base']
    return out

# ---- run the engine date by date
by_day = collections.defaultdict(list)
for (d, aw, hm), r in sorted(games.items()):
    by_day[d].append(r)
tmp = tempfile.mkdtemp()
allrecs = []
for day, rows in sorted(by_day.items()):
    run = [run_entry(r) for r in rows]
    cfgp = os.path.join(ROOT, 'work', f'cfg_{day:%m%d}.json')
    base = json.load(open(cfgp)) if os.path.exists(cfgp) else {}
    b2b = [name_of[c] for c in name_of if (day - dt.timedelta(1)) in played.get(c, ())]
    cfg = dict(date=day.isoformat(), b2b=b2b, crafted=base.get('crafted', {}), stars_out=base.get('stars_out', []))
    rp, cp, ap = (os.path.join(tmp, f'{n}_{day:%m%d}.json') for n in ('run', 'cfg', 'asof'))
    json.dump(run, open(rp, 'w')); json.dump(cfg, open(cp, 'w')); json.dump(asof(day), open(ap, 'w'))
    env = dict(os.environ, WB=WB, ASOF=ap)
    res = subprocess.run([sys.executable, 'work/rules.py', rp, cp], cwd=ROOT, env=env, capture_output=True, text=True)
    if res.returncode:
        print(day, 'engine error:', res.stderr[-400:]); continue
    out = json.load(open(rp.replace('.json', '_recs.json')))
    for o, r in zip(out, rows):
        o['date'], o['score'], o['line'] = day.isoformat(), (r[39], r[40]), dict(U=float(r[20]), P=float(r[15]),
                                                                                  att=r[26], htt=r[30])
        o['crafted_day'] = bool(base.get('crafted'))
        allrecs.append(o)
    print(day, len(rows), 'games', 'crafted' if base.get('crafted') else '')

# ---- grading
def grade(o, mk, side, lab):
    a, h = o['score']; U, P = o['line']['U'], o['line']['P']
    if mk == 'spread':
        m = (a - h + U) if side == 'away' else (h - a - U)
    elif mk == 'total':
        m = (a + h - P) if side == 'over' else (P - a - h)
    elif mk == 'ml':
        m = (a - h) if side == 'away' else (h - a)
    else:
        return None
    return 'W' if m > 0 else 'L' if m < 0 else 'P'

def units(s):
    s = str(s)
    if s.startswith('risk'):
        return float(s.split()[1].rstrip('u')) + (0.25 if '(P2)' in s else 0)
    try:
        return float(s.split('u')[0])
    except ValueError:
        return 0.25

rule = collections.defaultdict(list)       # code -> [(res, odds, date)]
for o in allrecs:
    for r in o['recs']:
        if r.get('sec') == 'SKIP' or r['odds'] is None:
            continue
        g = grade(o, r['mk'], r['side'], r['lab'])
        if g:
            code = r['code'].split()[0]
            rule[code].append((g, r['odds'], o['date']))

# card simulation (v5.2 plays, $20 unit, $20 bet / $30 game / $120 night caps)
night = collections.defaultdict(list)
for o in allrecs:
    stakes = []
    for p in o['plays']:
        if p['mk'] == 'tt':
            continue
        g = grade(o, p['mk'], p['side'], p['lab'])
        if not g:
            continue
        usd = min(20.0, units(p['units']) * 20)
        stakes.append([usd, p, g])
    tot = sum(s[0] for s in stakes)
    if tot > 30:
        for s in stakes: s[0] *= 30 / tot
    night[o['date']] += stakes
card = []
for d, stakes in sorted(night.items()):
    tot = sum(s[0] for s in stakes)
    k = min(1, 120 / tot) if tot else 1
    pl = 0
    for usd, p, g in stakes:
        usd *= k
        r = usd * dec(p['odds']) if g == 'W' else -usd if g == 'L' else 0
        pl += r
        card.append(dict(date=d, lab=p['lab'], codes=p['codes'], usd=round(usd, 2), odds=p['odds'], res=g, pl=round(r, 2)))

def flat(rs):
    w = sum(x[0] == 'W' for x in rs); l = sum(x[0] == 'L' for x in rs)
    pr = [dec(x[1]) if x[0] == 'W' else -1 if x[0] == 'L' else 0 for x in rs]
    m = sum(pr) / len(pr); sd = math.sqrt(sum((v - m) ** 2 for v in pr) / max(1, len(pr) - 1)) or 1
    return w, l, len(rs) - w - l, 100 * m, m / (sd / math.sqrt(len(pr)))

print('\nRULE | bets | W-L-P | flat ROI | z | Oct | Nov 1-17 | Nov 18+')
for code in sorted(rule, key=lambda c: (c[0], int(''.join(ch for ch in c[1:3] if ch.isdigit()) or 0))):
    rs = rule[code]; w, l, p, roi, z = flat(rs)
    per = []
    for f in (lambda d: d < '2026-11-01', lambda d: '2026-11-01' <= d < '2026-11-18', lambda d: d >= '2026-11-18'):
        sub = [x for x in rs if f(x[2])]
        if sub:
            a, b, _, r_, _ = flat(sub); per.append(f'{a}-{b} {r_:+.0f}%')
        else:
            per.append('–')
    print(f'{code} | {len(rs)} | {w}-{l}-{p} | {roi:+.1f}% | {z:+.2f} | ' + ' | '.join(per))
risk = sum(c['usd'] for c in card); pl = sum(c['pl'] for c in card)
cw = sum(c['res'] == 'W' for c in card); cl = sum(c['res'] == 'L' for c in card)
print(f'\nv5.2 card replay: {len(card)} bets over {len(night)} nights, {cw}-{cl}, risked ${risk:,.0f}, P/L ${pl:+,.2f} ({100 * pl / risk:+.1f}%)')
mon = collections.defaultdict(lambda: [0, 0, 0, 0])
for c in card:
    k = 'Oct' if c['date'] < '2026-11-01' else 'Nov 1-17' if c['date'] < '2026-11-18' else 'Nov 18+'
    mon[k][0] += c['usd']; mon[k][1] += c['pl']; mon[k][2] += c['res'] == 'W'; mon[k][3] += c['res'] == 'L'
for k in ('Oct', 'Nov 1-17', 'Nov 18+'):
    if k in mon:
        v = mon[k]; print(f'  {k}: {v[2]}-{v[3]}, risked ${v[0]:,.0f}, P/L ${v[1]:+,.2f} ({100 * v[1] / v[0]:+.1f}%)')
json.dump(dict(rules={k: v for k, v in rule.items()}, card=card), open(os.path.join(ROOT, 'work', 'replay_season.json'), 'w'), indent=0)

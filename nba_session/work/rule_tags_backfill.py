"""Map Tracking bets (11/12+) to the rule codes the engine gave them, from work/runMMDD*_recs.json."""
import json, glob, re, collections, openpyxl, sys
WB = sys.argv[1]
def codes_of(r):
    if r.get('codes'): return r['codes']
    return [r['code'].split()[0]]
tags = collections.defaultdict(set)      # (date, game, mk, side) -> codes
for f in sorted(glob.glob('work/run11*_recs.json')):
    m = re.search(r'run(\d{2})(\d{2})', f); d = f'2026-{m.group(1)}-{m.group(2)}'
    if d < '2026-11-12': continue
    for g in json.load(open(f)):
        for r in g.get('plays', []) + g.get('recs', []):
            for c in codes_of(r): tags[(d, g['game'], r['mk'], r['side'])].add(c)
MK = {'spread': 'spread', 'ml': 'ml', 'total': 'total', 'tt away': 'tt_away', 'tt home': 'tt_home'}
wb = openpyxl.load_workbook(WB, read_only=True); ws = wb['Tracking']
out, miss = {}, []
for i, r in enumerate(ws.iter_rows(min_row=13, values_only=True), start=13):
    if not r[35] or not hasattr(r[0], 'date'): continue
    d = r[0].date().isoformat()
    if d < '2026-11-12': continue
    mk = MK.get(str(r[35]).lower(), str(r[35]).lower()); side = str(r[36]).lower()
    key_mk = 'total' if mk == 'total' else mk
    c = tags.get((d, f'{r[1]}|{r[2]}', key_mk, side))
    if mk.startswith('tt'):
        c = tags.get((d, f'{r[1]}|{r[2]}', 'tt', mk[3:] + '_' + side)) or c
    c = {re.sub(r'^(T2)[lh]$', r'\1', x) for x in c} if c else c
    code = '+'.join(sorted(c, key=lambda x: ('CKTX'.index(x[0]) if x[0] in 'CKTX' else 9, x))) if c else 'OFF'
    out[i] = dict(date=d, game=f'{r[1]} @ {r[2]}', bet=f'{r[35]} {r[36]}', rules=code)
    if not c: miss.append(out[i])
json.dump(out, open('work/rule_tags_backfill.json', 'w'), indent=1)
for i, v in out.items(): print(i, v['date'], v['game'][:40], v['bet'], '->', v['rules'])
print(len(out), 'bets,', len(miss), 'with no engine tag (OFF)')

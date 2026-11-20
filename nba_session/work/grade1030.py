import json, math
S={'CHA @ WAS':(79,95),'CHI @ BOS':(111,125),'ORL @ TOR':(121,114),'NYK @ PHI':(93,98),'DET @ BKN':(110,94),'IND @ MIA':(125,145),
   'LAC @ MIN':(101,127),'HOU @ DAL':(111,116),'LAL @ GS':(95,112),'DEN @ PHX':(127,120)}
json.dump(S,open('work/scores1030.json','w'))
def dec(o): return 100/-o if o<0 else o/100
def won(x,A,H):
    lab=x['lab']; mk=x['mk']; ga,gh=x['game'].split(' @ ')
    if mk=='ML': return (A>H) if x['side']=='away' else (H>A)
    if mk=='Spread':
        line=float(lab.split()[-1]); return (A-H+line>0) if x['side']=='away' else (H-A+line>0)
    if mk=='Total':
        line=float(lab.split()[-1]); T=A+H; return T>line if lab.startswith('Over') else T<line
    pts=A if x['side']=='away' else H; line=float(lab.split()[-1][1:])
    return pts>line if ' TT o' in lab else pts<line
out={}
for run in ['run1030','run1030b']:
    d=json.load(open(f'work/{run}.json'))
    for x in d['legs']:
        A,H=S[x['game']]; x['won']=won(x,A,H); x['pl']=dec(x['odds']) if x['won'] else -1
    out[run]=d
    c=[x for x in d['legs'] if x['card']]
    print(run,'CARD',sum(x['won'] for x in c),'-',sum(not x['won'] for x in c),round(sum(x['pl'] for x in c),2))
    for mk in ['ML','Spread','Total','TT']:
        cc=[x for x in c if x['mk']==mk]; print('  ',mk,sum(x['won'] for x in cc),'-',sum(not x['won'] for x in cc),round(sum(x['pl'] for x in cc),2))
    a=[x for x in d['legs'] if x['ruleA'] and x['edge']>0]
    print('  RuleA(all pos-edge)',sum(x['won'] for x in a),'-',sum(not x['won'] for x in a),round(sum(x['pl'] for x in a),2))
    e=[x for x in d['legs'] if x['ruleE']]
    print('  RuleE',[(x['lab'],x['won']) for x in e])
    dogs=[x for x in c if x['mk']=='ML' and x['odds']>=150]; print('  MLdogs150',[(x['lab'],x['won']) for x in dogs])
    unders=[x for x in c if x['lab'].startswith('Under') or ' TT u' in x['lab']]; overs=[x for x in c if x['lab'].startswith('Over') or ' TT o' in x['lab']]
    print('  unders',sum(x['won'] for x in unders),'-',sum(not x['won'] for x in unders),' overs',sum(x['won'] for x in overs),'-',sum(not x['won'] for x in overs))
json.dump(out,open('work/graded1030.json','w'),default=float)
# picks
def find(run,lab,game):
    return [x for x in out[run]['legs'] if x['lab']==lab and x['game']==game][0]
first=[('run1030','TOR -5.5','ORL @ TOR',1),('run1030','PHX +4.5','DEN @ PHX',1),('run1030','Under 235.5','CHI @ BOS',1),('run1030','MIA -8.5','IND @ MIA',.5),('run1030','LAC +7.5','LAC @ MIN',.5),('run1030','DAL +6.5','HOU @ DAL',.5)]
final=[('run1030b','CHA -1.5','CHA @ WAS',.5),('run1030b','Under 235.5','CHI @ BOS',1),('run1030b','ORL TT u110.5','ORL @ TOR',1),('run1030b','Under 237.5','IND @ MIA',1),('run1030b','LAC +7.5','LAC @ MIN',.5),('run1030b','DAL TT o108.5','HOU @ DAL',1)]
for name,L in [('FIRST',first),('FINAL',final)]:
    tot=0;w=0
    for run,lab,g,u in L:
        x=find(run,lab,g); p=x['pl']*u; tot+=p; w+=x['won']; print(f"  {name} {lab:16s} {x['odds']:+d} {u}u {'W' if x['won'] else 'L'} {p:+.2f}")
    print(name,w,'-',len(L)-w,round(tot,2))
# projections
for run in ['run1030','run1030b']:
    G=out[run]['games']; em=[];et=[];mm=[];mt=[];e0=[]
    for g in G:
        A,H=S[g['game']]; em.append((g['ap']-g['hp'])-(A-H)); mm.append(g['mkt_margin']-(A-H)); e0.append((g['ap0']-g['hp0'])-(A-H))
        et.append(g['ap']+g['hp']-(A+H)); mt.append(g['mkt_total']-(A+H))
    r=lambda L: math.sqrt(sum(v*v for v in L)/len(L))
    print(run,'margin RMSE model',round(r(em),2),'no-inj',round(r(e0),2),'market',round(r(mm),2),'| total RMSE model',round(r(et),2),'line',round(r(mt),2),'mean total err model',round(sum(et)/10,1),'line',round(sum(mt)/10,1))
for g in out['run1030b']['games']:
    A,H=S[g['game']]; g1=[x for x in out['run1030']['games'] if x['game']==g['game']][0]
    print(f"{g['game']:10s} act {A-H:+4d} T{A+H} | mkt {g['mkt_margin']:+5.1f} | noinj {g['ap0']-g['hp0']:+5.1f} v2.1 {g1['ap']-g1['hp']:+5.1f} v2.2 {g['ap']-g['hp']:+5.1f} | tot model {g['ap']+g['hp']:.1f} line {g['mkt_total']}")

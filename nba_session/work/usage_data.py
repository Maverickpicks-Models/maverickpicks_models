import openpyxl,json,collections,datetime as dt
wb=openpyxl.load_workbook('in1113/s.xlsx',read_only=True,data_only=True)
ws=wb['BoxScores']; hdr=[c for c in next(ws.iter_rows(min_row=1,max_row=1,values_only=True))]
ti={h:i for i,h in enumerate(hdr[:26])}; ai={(h or '').replace('\xa0',' '):i+27 for i,h in enumerate(hdr[27:])}
print(ai)
trad={};adv={}
for r in ws.iter_rows(min_row=2,values_only=True):
    if r[0] and r[3]:
        trad[(r[0],r[1],str(r[3])[:10])]=dict(min=r[ti['MIN']],pts=r[ti['PTS']],fga=r[ti['FGA']],fta=r[ti['FTA']],tov=r[ti['TOV']],ast=r[ti['AST']],p3a=r[ti['3PA']],mu=r[ti['MATCH UP']])
    if len(r)>27 and r[27] and r[30]:
        adv[(r[27],r[28],str(r[30])[:10])]=dict(usg=r[ai['USG%']],ts=r[ai['TS%']],ortg=r[ai['OffRtg']],pie=r[ai['PIE']],min=r[ai['MIN']])
print('trad',len(trad),'adv',len(adv),'matched',len(set(trad)&set(adv)))
T=collections.defaultdict(dict)
for t,te,d in wb['TeamBoxAdvanced'].iter_rows(min_row=2,values_only=True) if False else []: pass
team={}
for r in wb['TeamBoxAdvanced'].iter_rows(min_row=3,values_only=True):
    if len(r)>43 and r[26] and r[28] and not isinstance(r[28],str):
        team[(r[26],str(r[28])[:10])]=dict(ortg=r[31],drtg=r[32],pace=r[43],mu=r[27].replace('\xa0',' '))
print('team-games',len(team))
rows=[]
for k in set(trad)&set(adv):
    x=dict(trad[k]); x.update(adv[k]); x['p'],x['t'],x['d']=k; rows.append(x)
json.dump(dict(rows=rows,team={f'{a}|{b}':v for (a,b),v in team.items()}),open('work/usage_raw.json','w'),default=str)

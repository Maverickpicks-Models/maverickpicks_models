import openpyxl
BB2FULL={'ATL':'Atlanta Hawks','BOS':'Boston Celtics','BRK':'Brooklyn Nets','CHI':'Chicago Bulls','CHO':'Charlotte Hornets','CLE':'Cleveland Cavaliers',
 'DAL':'Dallas Mavericks','DEN':'Denver Nuggets','DET':'Detroit Pistons','GSW':'Golden State Warriors','HOU':'Houston Rockets','IND':'Indiana Pacers',
 'LAC':'LA Clippers','LAL':'Los Angeles Lakers','MEM':'Memphis Grizzlies','MIA':'Miami Heat','MIL':'Milwaukee Bucks','MIN':'Minnesota Timberwolves',
 'NOP':'New Orleans Pelicans','NYK':'New York Knicks','OKC':'Oklahoma City Thunder','ORL':'Orlando Magic','PHI':'Philadelphia 76ers','PHO':'Phoenix Suns',
 'POR':'Portland Trail Blazers','SAC':'Sacramento Kings','SAS':'San Antonio Spurs','TOR':'Toronto Raptors','UTA':'Utah Jazz','WAS':'Washington Wizards'}
def load_season(ws):
    """returns players: name -> dict(tot=(G,MP,O,D), teams={team:(G,MP,O,D)}, last_team, age, pos)"""
    P={}
    for r in ws.iter_rows(min_row=2,values_only=True):
        if r[1] in (None,'Player') or not isinstance(r[5],(int,float)): continue
        name,age,team,pos,G,GS,MP=r[1],r[2],r[3],r[4],r[5],r[6],r[7]
        O,D=r[24],r[25]
        if not isinstance(O,(int,float)): O=0.0
        if not isinstance(D,(int,float)): D=0.0
        rec=(G,GS or 0,MP or 0,O,D)
        p=P.setdefault(name,dict(age=age,pos=pos,teams={},tot=None,order=[]))
        if team and str(team).endswith('TM'): p['tot']=rec; p['multi']=True
        elif team in BB2FULL:
            p['teams'][BB2FULL[team]]=rec; p['order'].append(BB2FULL[team])
            if not p.get('multi'): p['tot']=rec
    for p in P.values():
        p['last_team']=p['order'][-1] if p['order'] else None
    return P
def load(path):
    wb=openpyxl.load_workbook(path,data_only=True)
    S={k:load_season(wb[s]) for k,s in [('27','26-27NBAPlayer'),('26','25-26NBAPlayer'),('25','24-25NBAPlayer')]}
    def rat(name):
        d={}
        for r in wb[name].iter_rows(min_row=2,values_only=True):
            if r[1] and isinstance(r[2],(int,float)): d[r[1]]=dict(gp=r[2],o=r[7],d=r[8],n=r[9],p=r[10])
        return d
    return wb,S,rat('Ratings_2025_26'),rat('Ratings_2026_27')

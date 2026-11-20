import pandas as pd, numpy as np
P=pd.read_excel('in17/box.xlsx',sheet_name='BoxScores')
T=pd.read_excel('in17/box.xlsx',sheet_name='TeamBoxScoresAdvanced')
T.columns=[c.replace('\xa0',' ') for c in T.columns]
for c in ['FG%','3P%','FT%']: P[c]=pd.to_numeric(P[c],errors='coerce')
P['date']=pd.to_datetime(P['GAME DATE']).dt.date; T['date']=pd.to_datetime(T['Game Date']).dt.date
def parse(mu):
    if ' @ ' in mu: a,b=mu.split(' @ '); return a,b,0
    a,b=mu.split(' vs. '); return a,b,1
P[['team','opp','home']]=P['MATCH UP'].apply(lambda s: pd.Series(parse(s)))
T[['team','opp','home']]=T['Match Up'].apply(lambda s: pd.Series(parse(s)))
# team totals from player box
agg=P.groupby(['date','team','opp','home']).agg(PTS=('PTS','sum'),FGM=('FGM','sum'),FGA=('FGA','sum'),TPM=('3PM','sum'),TPA=('3PA','sum'),
    FTM=('FTM','sum'),FTA=('FTA','sum'),OREB=('OREB','sum'),DREB=('DREB','sum'),TOV=('TOV','sum'),AST=('AST','sum'),MIN=('MIN','sum'),n=('PLAYER','count')).reset_index()
G=agg.merge(T[['date','team','OffRtg','DefRtg','NetRtg','PACE','OREB%','DREB%','TOV%','eFG%','TS%','W/L','MIN']].rename(columns={'MIN':'TMIN'}),on=['date','team'],how='left')
o=G[['date','team','PTS','FGA','TPM','TPA','FTA','OREB','DREB','TOV','FGM']].rename(columns={'team':'opp','PTS':'oPTS','FGA':'oFGA','TPM':'oTPM','TPA':'oTPA','FTA':'oFTA','OREB':'oOREB','DREB':'oDREB','TOV':'oTOV','FGM':'oFGM'})
G=G.merge(o,on=['date','opp'],how='left')
G['poss']=G['FGA']-G['OREB']+G['TOV']+0.44*G['FTA']
G['oposs']=G['oFGA']-G['oOREB']+G['oTOV']+0.44*G['oFTA']
G['POSS']=(G['poss']+G['oposs'])/2
G['ot']=(G['TMIN']-48)/5
G.to_pickle('work/box_G.pkl'); P.to_pickle('work/box_P.pkl')
if __name__=='__main__':
    print('player rows',len(P),'team-games',len(G),'games',len(G)//2,'dates',sorted(G['date'].unique())[0],sorted(G['date'].unique())[-1])
    print('missing adv',G['OffRtg'].isna().sum(),'opp missing',G['oPTS'].isna().sum())
    print(G['date'].value_counts().sort_index().to_dict())
    print('OT games', (G['TMIN']>48).sum()//2)
    print(G[['PTS','PACE','OffRtg','eFG%','TOV%','OREB%']].describe().round(2))

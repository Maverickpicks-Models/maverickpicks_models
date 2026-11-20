import pandas as pd, numpy as np
G=pd.read_pickle('work/box_G.pkl')
G['POSS']=G.PACE*G.TMIN/48  # NBA official possessions
lg3=G.TPM.sum()/G.TPA.sum(); lgFT=G.FTM.sum()/G.FTA.sum(); lg2=(G.FGM.sum()-G.TPM.sum())/(G.FGA.sum()-G.TPA.sum())
print(f"league 3P% {lg3:.3f} FT% {lgFT:.3f} 2P% {lg2:.3f} pace {G.POSS.mean():.1f} ORtg {100*G.PTS.sum()/G.POSS.sum():.1f}")
G['luck3']=(G.TPM/G.TPA-lg3)*G.TPA*3
G['luckFT']=(G.FTM/G.FTA-lgFT)*G.FTA
G['oluck3']=(G.oTPM/G.oTPA-lg3)*G.oTPA*3
G['xPTS']=G.PTS-G.luck3-G.luckFT
# variance decomposition of points around mean
v=np.var(G.PTS); print('SD pts',round(np.std(G.PTS),2),'SD xPTS (3P%/FT% neutral)',round(np.std(G.xPTS),2),'SD 3P luck',round(np.std(G.luck3),2),'corr pts~luck3',round(np.corrcoef(G.PTS,G.luck3)[0,1],2))
# pace vs efficiency share
G['eff']=100*G.PTS/G.POSS
import sys; sys.path.insert(0,"work"); import ols as sm
X=sm.add_constant(np.column_stack([G.POSS-G.POSS.mean(),G.eff-G.eff.mean()]))
r=sm.OLS(G.PTS,X); print('pts ~ poss + eff R2',round(r.rsquared,3),'| poss alone R2',round(np.corrcoef(G.PTS,G.POSS)[0,1]**2,3),'eff alone',round(np.corrcoef(G.PTS,G.eff)[0,1]**2,3))
# four factor components per team-game
G['efg']=(G.FGM+0.5*G.TPM)/G.FGA; G['tov']=G.TOV/G.poss; G['orb']=G.OREB/(G.OREB+G.oDREB); G['ftr']=G.FTM/G.FGA; G['tpar']=G.TPA/G.FGA
r=sm.OLS(G.eff,sm.add_constant(G[['efg','tov','orb','ftr']])); print('eff ~ four factors R2',round(r.rsquared,3))
# standardized importance
for c in ['efg','tov','orb','ftr']:
    print('  ',c,'corr with eff',round(np.corrcoef(G[c],G.eff)[0,1],2))
G.to_pickle('work/box_G2.pkl')
# team profiles
grp=G.groupby('team')
prof=pd.DataFrame({'GP':grp.size(),'PPG':grp.PTS.mean(),'OPPG':grp.oPTS.mean(),'Pace':grp.POSS.mean(),
  'ORtg':100*grp.PTS.sum()/grp.POSS.sum(),'DRtg':100*grp.oPTS.sum()/grp.POSS.sum(),
  'eFG':grp.apply(lambda d:(d.FGM.sum()+.5*d.TPM.sum())/d.FGA.sum()),'TOV%':grp.apply(lambda d:d.TOV.sum()/d.poss.sum()),
  'ORB%':grp.apply(lambda d:d.OREB.sum()/(d.OREB.sum()+d.oDREB.sum())),'FTr':grp.apply(lambda d:d.FTA.sum()/d.FGA.sum()),
  '3PAr':grp.apply(lambda d:d.TPA.sum()/d.FGA.sum()),'3P%':grp.apply(lambda d:d.TPM.sum()/d.TPA.sum()),'opp3P%':grp.apply(lambda d:d.oTPM.sum()/d.oTPA.sum()),
  'luck3_per100':grp.apply(lambda d:100*d.luck3.sum()/d.POSS.sum()),'oluck3_per100':grp.apply(lambda d:100*d.oluck3.sum()/d.POSS.sum())})
prof['NRtg']=prof.ORtg-prof.DRtg
prof['NRtg_luckadj']=(prof.ORtg-prof.luck3_per100)-(prof.DRtg-prof.oluck3_per100)
prof['luck_net']=prof.luck3_per100-prof.oluck3_per100
prof=prof.sort_values('NRtg',ascending=False)
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
print(prof.round(3))
prof.to_pickle('work/box_prof.pkl')

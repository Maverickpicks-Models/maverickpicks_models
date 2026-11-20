import csv, json, math, sys
sys.path.insert(0,'work')
from injod import team
rows=list(csv.DictReader(open('work/slate_1028b.tsv'),delimiter='\t'))
sc=json.load(open('work/scores1028.json'))
OLD={'Miami Heat':-0.3,'Washington Wizards':-0.5,'Indiana Pacers':-2.0,'Orlando Magic':-2.9,'Houston Rockets':-3.3,
 'Golden State Warriors':-0.8,'Minnesota Timberwolves':-3.0,'Utah Jazz':-1.8,'Oklahoma City Thunder':-5.2,'Dallas Mavericks':-1.1}
NEW={'Miami Heat':[('Pelle Larsson',.5,None)],'Washington Wizards':[('Justin Champagnie',.5,None)],
 'Indiana Pacers':[('Tyrese Haliburton',.5,None),('Andrew Nembhard',.5,None)],
 'Orlando Magic':[('Paolo Banchero',1,None),('Jalen Suggs',1,None)],'Houston Rockets':[('Alperen Sengun',1,None)],
 'Golden State Warriors':[('Yaxel Lendeborg',.5,None)],'Minnesota Timberwolves':[('Anthony Edwards',1,None)],
 'Utah Jazz':[('Lauri Markkanen',.5,None),('Jaren Jackson Jr.',1,None)],
 'Oklahoma City Thunder':[('Alex Caruso',1,None),('Chet Holmgren',1,None),('Jalen Williams',1,None),('Ajay Mitchell',.5,None)],
 'Dallas Mavericks':[('Kyrie Irving',.5,None),('Naji Marshall',.5,None)]}
keys=sorted(sc,key=int)
out=[]
for k,r in zip(keys,rows):
    a,h=r['Away'],r['Home']; ap,hp=float(r['Away proj']),float(r['Home proj'])
    aa,ha=OLD.get(a,0),OLD.get(h,0)
    ab=ap-(aa-ha)/2; hb=hp-(ha-aa)/2
    Oa,Da,ma,_=team(NEW.get(a,[])); Oh,Dh,mh,_=team(NEW.get(h,[]))
    an=ab-Oa+Dh; hn=hb-Oh+Da
    A,H=sc[k]; spr=float(r['Away spread']); tl=float(r['Total line'])
    out.append(dict(g=f"{a.split()[-1]}@{h.split()[-1]}",adj=bool(aa or ha),act_m=A-H,act_t=A+H,
      base_m=ab-hb,old_m=ap-hp,new_m=an-hn,mkt_m=-spr,base_t=ab+hb,old_t=ap+hp,new_t=an+hn,mkt_t=tl,
      Oa=Oa,Da=Da,Oh=Oh,Dh=Dh,ma=ma,mh=mh,act=(A,H),newp=(an,hn),oldp=(ap,hp)))
def rmse(L,key,act): return math.sqrt(sum((x[key]-x[act])**2 for x in L)/len(L))
for x in out:
    print(f"{x['g']:24s} act {x['act_m']:+4d} mkt {x['mkt_m']:+6.1f} base {x['base_m']:+6.1f} old {x['old_m']:+6.1f} new {x['new_m']:+6.1f} | tot act {x['act_t']} line {x['mkt_t']} old {x['old_t']:.1f} new {x['new_t']:.1f} | A O{x['Oa']:.1f} D{x['Da']:.1f} H O{x['Oh']:.1f} D{x['Dh']:.1f}")
for lab,L in [('all 12',out),('adjusted',[x for x in out if x['adj']])]:
    print(lab, 'margin RMSE base %.2f old %.2f new %.2f mkt %.2f'%tuple(rmse(L,k,'act_m') for k in ['base_m','old_m','new_m','mkt_m']),
          '| total RMSE old %.2f new %.2f line %.2f'%tuple(rmse(L,k,'act_t') for k in ['old_t','new_t','mkt_t']))
# team points error, injured teams
te_old=[];te_new=[]
for x in out:
    for i in (0,1):
        te_old.append(x['oldp'][i]-x['act'][i]); te_new.append(x['newp'][i]-x['act'][i])
print('team pts RMSE old %.2f new %.2f'%(math.sqrt(sum(e*e for e in te_old)/24),math.sqrt(sum(e*e for e in te_new)/24)))
json.dump(out,open('work/rescore1028.json','w'),default=float)

"""O+D injury value method (v2).
Per player: blended OBPM / DBPM = (current*MP_cur + prior*K) / (MP_cur + K)
  prior = minutes-weighted avg of last two seasons (latest season weight 2, older 1)
  no prior -> shrink toward rookie/generic level (-1.0 O, -0.5 D... uses REPL) with K=250
Loss vs replacement (generic O -1.5 / D -0.5, or named backup's blended ratings):
  O loss = (O - O_rep) * MPG/48  -> own points down
  D loss = (D - D_rep) * MPG/48  -> opponent points up
Status weight: out 1, Q/DTD 0.5.  Stacking multiplier: 1 + 0.15 per extra effective starter (players worth >=1.0), cap 1.30.
"""
import json, math, csv, sys
K_PRIOR, K_NOPRIOR = 600, 250
REP = (-1.5, -0.5)

# name: (cur G, cur MP, cur O, cur D, [(MP, O, D) 2025-26], [(MP,O,D) 2024-25], mpg_override)
P = {
 "Dejounte Murray": (4,129,0.7,-0.6,(389,0.8,0.5),(1012,-1.3,-0.3),None),
 "Jeremiah Fears": (4,92,-8.9,-5.2,(2112,-1.4,-1.3),None,None),
 "Jordan Poole": (4,64,-2.8,0.2,(933,-0.9,-2.6),(2001,2.0,-1.6),16.0),
 "Pelle Larsson": (5,153,-1.9,0.0,(1849,-1.2,0.0),None,None),
 "Justin Champagnie": (0,0,0,0,(1377,0.6,-1.0),(1340,-0.3,-0.2),20.0),
 "Tyrese Haliburton": (4,132,6.9,-0.1,None,(2451,5.7,0.2),None),
 "Andrew Nembhard": (4,131,1.2,-2.2,(1786,1.1,-1.9),(1881,-2.6,0.3),None),
 "Paolo Banchero": (2,68,6.1,1.2,(2502,1.4,0.0),(1582,3.4,0.2),None),
 "Jalen Suggs": (3,100,-5.0,0.0,(1574,0.7,1.8),None,None),
 "Alperen Sengun": (4,136,6.0,1.6,(2398,2.7,1.5),(2395,2.6,1.8),None),
 "Yaxel Lendeborg": (5,168,2.9,-2.6,None,None,None),
 "Anthony Edwards": (4,135,5.4,1.5,(2137,4.7,-0.1),(2871,4.4,0.0),None),
 "Lauri Markkanen": (4,114,2.5,-3.7,(1443,4.6,-2.0),(1476,1.8,-2.1),None),
 "Jaren Jackson Jr.": (4,104,-1.8,-1.5,(1454,-1.1,0.5),(2207,1.6,0.8),None),
 "Alex Caruso": (4,76,9.1,4.1,(1020,-1.4,3.3),(1041,0.1,3.9),None),
 "Chet Holmgren": (3,90,1.0,0.6,(1997,2.4,1.9),None,None),
 "Jalen Williams": (3,95,-3.0,0.7,(936,1.1,1.0),(2237,2.7,1.4),None),
 "Ajay Mitchell": (5,127,4.1,3.3,(1473,0.3,1.6),None,None),
 "Kyrie Irving": (4,108,2.6,0.5,None,(1804,3.9,-0.5),None),
 "Naji Marshall": (3,83,-0.1,-0.6,(2184,-0.7,0.1),(1919,-0.3,-0.5),None),
}

def blend(name):
    g, mp, o, d, s1, s2, mpg = P[name]
    seasons = [(x, 2) for x in [s1] if x] + [(x, 1) for x in [s2] if x]
    if seasons:
        w = sum(x[0]*k for x, k in seasons)
        po = sum(x[0]*k*x[1] for x, k in seasons)/w
        pd = sum(x[0]*k*x[2] for x, k in seasons)/w
        K = K_PRIOR
    else:
        po, pd, K = REP[0], REP[1], K_NOPRIOR
    bo = (o*mp + po*K)/(mp+K); bd = (d*mp + pd*K)/(mp+K)
    if mpg is None: mpg = mp/g
    return bo, bd, mpg

def value(name, repl=None):
    bo, bd, mpg = blend(name)
    ro, rd = (blend(repl)[:2] if repl else REP)
    sh = mpg/48
    return (bo-ro)*sh, (bd-rd)*sh, bo, bd, mpg

def team(players):
    """players: list of (name, weight, repl). Returns O loss, D loss (positive = hurts team), detail."""
    rows = []
    for n, w, r in players:
        o, d, bo, bd, mpg = value(n, r)
        rows.append(dict(name=n, w=w, o=o*w, d=d*w, bo=bo, bd=bd, mpg=mpg, full=o+d))
    neff = sum(r["w"] for r in rows if r["full"] >= 1.0)
    mult = min(1.30, 1 + 0.15*max(0, neff-1))
    O = max(0, sum(r["o"] for r in rows))*mult if rows else 0
    D = sum(r["d"] for r in rows)*mult
    return O, D, mult, rows

if __name__ == "__main__":
    for n in P:
        o, d, bo, bd, mpg = value(n)
        print(f"{n:20s} O {bo:+5.2f} D {bd:+5.2f} mpg {mpg:4.1f}  Oloss {o:+5.2f} Dloss {d:+5.2f} tot {o+d:+5.2f}")
    print("Murray vs Fears", [round(x,2) for x in value("Dejounte Murray","Jeremiah Fears")])

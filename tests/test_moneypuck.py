import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sqlite_db import make_db
from mpm import moneypuck as mp

TEAMS = ("team,season,name,team,position,situation,games_played,xGoalsPercentage,xGoalsFor,goalsFor\n"
         "SJS,2026,SJS,SJS,Team Level,all,20,0.45,55.5,60\n"
         "SJS,2026,SJS,SJS,Team Level,5on4,20,0.9,9.1,10\n"
         "T.B,2026,T.B,T.B,Team Level,all,21,0.52,63.0,66\n")
GOALIES = ("playerId,season,name,team,position,situation,games_played,icetime,xGoals,goals\n"
           "8480382,2026,Yaroslav Askarov,SJS,G,all,14,48000,41.5,40\n"
           "8480382,2026,Yaroslav Askarov,SJS,G,5on5,14,40000,30.2,29\n")


class Resp:
    def __init__(self, text): self.status_code = 200; self.content = ("﻿" + text).encode()


class HTTP:
    def __init__(self): self.urls = []
    def get(self, url, timeout, headers):
        self.urls.append(url)
        return Resp(TEAMS if url.endswith("teams.csv") else GOALIES)


def test_fetch_and_reload(tmp_path=None):
    import tempfile
    folder = tmp_path or tempfile.mkdtemp()
    db = make_db()
    http = HTTP()
    out = mp.fetch(db, str(folder), season=2026, http=http)
    assert http.urls[0].endswith("/seasonSummary/2026/regular/teams.csv")
    assert out == {"teams": 12, "goalies": 8}, out    # 3 rows x 4 stats, 2 rows x 4 stats
    # MoneyPuck's dotted codes (T.B, N.J, S.J, L.A) resolve through core.team_aliases
    assert db.one("SELECT team_code FROM nhl.mp_stat WHERE entity_id='TBL' AND stat='goalsFor'")[0] == "TBL"
    assert db.one("SELECT value FROM nhl.mp_stat WHERE entity='goalie' AND entity_id='8480382' AND situation='all' "
                  "AND stat='xGoals'")[0] == 41.5
    mp.fetch(db, str(folder), season=2026, http=HTTP())                # same day: replaced, not doubled
    assert db.one("SELECT COUNT(*) FROM nhl.mp_stat")[0] == 20
    assert len(os.listdir(folder)) == 2


if __name__ == "__main__":
    test_fetch_and_reload(); print("test_moneypuck OK")

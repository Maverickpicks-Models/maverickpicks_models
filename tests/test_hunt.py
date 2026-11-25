"""Angle hunt runs end to end on a synthetic two-season database and freezes its list before validating."""
import datetime as dt
import glob
import json
import random
from sqlite_db import make_db
from mpm import history, hunt
from test_mine import _season, _odds, TEAMS


def test_hunt_report(tmp_path):
    db = make_db(); rnd = random.Random(7)
    for i, t in enumerate(TEAMS):
        db.x("INSERT INTO core.teams VALUES ('NBA',?,?,?,?,?,?)", (t, t, 30 + i * 2, -120 + i * 8, -8 + i // 2, 5280 if t == "AAA" else 100))
    s1, g1 = _season(db, dt.date(2025, 11, 1), 70, rnd)
    s2, g2 = _season(db, dt.date(2026, 10, 25), 30, rnd)
    history.log_from_db(db, "2025-26", "2025-10-01", "2026-06-30")
    history.log_from_db(db, "2026-27", "2026-10-01", "2027-06-30")
    _odds(db, s1, g1); _odds(db, s2, g2)
    text = hunt.run(db, "2025-26", "2026-27", str(tmp_path))
    print(text[:5000])
    for part in ("angles tested", "## 1. Frozen angles", "## 2. Held on both seasons", "## 3. Multivariate model",
                 "## 4. Reverse check", "Ridge logistic"):
        assert part in text, part
    fz = json.load(open(glob.glob(str(tmp_path / "hunt_frozen_2025-26_*.json"))[0]))
    assert fz["discover"] == "2025-26" and "cuts" in fz

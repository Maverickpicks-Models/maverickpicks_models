"""Season quarters report runs end to end on a synthetic two-season database."""
import datetime as dt
import random
from sqlite_db import make_db
from mpm import history, quarters
from test_mine import _season, _odds


def test_quarters_report(tmp_path):
    db = make_db(); rnd = random.Random(3)
    s1, g1 = _season(db, dt.date(2025, 11, 1), 80, rnd)
    s2, g2 = _season(db, dt.date(2026, 11, 1), 20, rnd)
    history.log_from_db(db, "2025-26", "2025-10-01", "2026-06-30")
    history.log_from_db(db, "2026-27", "2026-10-01", "2027-06-30")
    _odds(db, s1, g1); _odds(db, s2, g2)
    text = quarters.run(db, "2025-26", "2026-27", str(tmp_path), min_gp=4)
    print(text)
    for part in ("## A. The market", "## B. Our rules", "### Steady", "## D.", "## E.", "## Check: 2026-27"):
        assert part in text, part
    assert "| Home covers |" in text and "Follow hot conditions" in text
    assert "spreads:any when home=yes" in text            # planted edge shows up as steady
    assert quarters.same_window(dt.date(2026, 11, 10), [dt.date(2025, 12, 1), dt.date(2026, 1, 15), dt.date(2026, 3, 1)]) == 1

"""Daily MoneyPuck season-summary download -> nhl.mp_stat (point-in-time snapshots).

MoneyPuck publishes teams.csv and goalies.csv per season (one row per team/goalie x situation):
  https://moneypuck.com/moneypuck/playerData/seasonSummary/{season}/regular/{teams|goalies}.csv
season = first year of the season (2026 = 2026-27).

Terms (moneypuck.com/data.htm): free for non-commercial use and journalists; other uses need MoneyPuck's
permission, and MoneyPuck must be credited wherever its data feeds something you publish. Get permission
before scheduling this job for a commercial operation (register_tasks.ps1 only adds it with -MoneyPuck).

Usage:
  python -m mpm.moneypuck --fetch C:\\MaverickPicks\\moneypuck            # download today's files and load them
  python -m mpm.moneypuck --fetch C:\\MaverickPicks\\moneypuck --season 2025
  python -m mpm.moneypuck --file C:\\...\\goalies.csv --kind goalies --as-of 2026-11-18   # load a saved file
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import os
import sys
from zoneinfo import ZoneInfo

from .db import DB, session
from .nhl_workbook import mp_long_rows, season_of, store_mp

URL = "https://moneypuck.com/moneypuck/playerData/seasonSummary/{season}/regular/{kind}.csv"
KINDS = {"teams": "team", "goalies": "goalie"}
ET = ZoneInfo("America/New_York")


def parse_csv(text: str):
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []
    return rows[0], [r for r in rows[1:] if r]


def load_text(db: DB, text: str, kind: str, snap: dt.date, season: int) -> int:
    hdr, rows = parse_csv(text)
    if not hdr or "situation" not in [h.strip().lower() for h in hdr]:
        raise ValueError(f"{kind}: not a MoneyPuck season-summary CSV (no 'situation' column)")
    recs = mp_long_rows(db, hdr, rows, KINDS[kind], snap, "moneypuck", season)
    n = store_mp(db, recs, "moneypuck")
    print(f"{kind} {season}: {len(rows)} rows -> {n} stats (snapshot {snap})")
    return n


def fetch(db: DB, folder: str, season: int | None = None, http=None) -> dict:
    import requests
    http = http or requests.Session()
    today = dt.datetime.now(ET).date()
    season = season or season_of(today)
    os.makedirs(folder, exist_ok=True)
    out = {}
    for kind in KINDS:
        url = URL.format(season=season, kind=kind)
        r = http.get(url, timeout=60, headers={"User-Agent": "MaverickPicks data pipeline (daily season summary)"})
        if r.status_code != 200:
            raise RuntimeError(f"{url} -> HTTP {r.status_code}")
        text = r.content.decode("utf-8-sig")
        path = os.path.join(folder, f"{season}_{kind}_{today.isoformat()}.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        out[kind] = load_text(db, text, kind, today, season)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", metavar="FOLDER", help="download teams.csv and goalies.csv into FOLDER and load them")
    ap.add_argument("--season", type=int, help="first year of the season (default: current)")
    ap.add_argument("--file", help="load a saved CSV instead of downloading")
    ap.add_argument("--kind", choices=KINDS, help="teams or goalies (with --file)")
    ap.add_argument("--as-of", help="snapshot date for --file (default today ET)")
    a = ap.parse_args(argv)
    with session() as db:
        if a.file:
            if not a.kind:
                ap.error("--kind is required with --file")
            snap = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.now(ET).date()
            with open(a.file, encoding="utf-8-sig") as fh:
                load_text(db, fh.read(), a.kind, snap, a.season or season_of(snap))
        elif a.fetch:
            fetch(db, a.fetch, a.season)
        else:
            ap.error("use --fetch FOLDER or --file PATH --kind teams|goalies")


if __name__ == "__main__":
    sys.exit(main())

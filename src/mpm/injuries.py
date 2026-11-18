"""Parse the official NBA injury report PDF into rows and store them.

The PDF is a table: Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason.
Date/time/matchup/team are only printed on the first row of each block, and long reasons wrap onto
lines above and below the player's line, so we rebuild rows from word positions.

Usage:
  python -m mpm.injuries "C:\\Downloads\\Injury-Report_2026-11-17_06_00PM.pdf"
  python -m mpm.injuries --dry-run report.pdf        # print rows, no database
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys

import pdfplumber

STATUSES = ("Out", "Doubtful", "Questionable", "Probable", "Available")
COLS = ["game_date", "game_time", "matchup", "team", "player", "status", "reason"]
HEAD_RE = re.compile(r"Injury Report:\s*(\d{2}/\d{2}/\d{2})\s+(\d{1,2}:\d{2})\s*(AM|PM)", re.I)


def _lines(words, tol=2.5):
    rows = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0] - w["top"]) <= tol:
            rows[-1][1].append(w)
        else:
            rows.append([w["top"], [w]])
    return rows


def _header_x(words):
    """x positions of the column headers (falls back to the standard layout)."""
    xs = {}
    seq = [(w["text"], w["x0"]) for w in words if w["top"] < 125]
    for i, (t, x) in enumerate(seq):
        nxt = seq[i + 1][0] if i + 1 < len(seq) else ""
        if t == "Game" and nxt == "Date": xs["game_date"] = x
        elif t == "Game" and nxt == "Time": xs["game_time"] = x
        elif t == "Matchup": xs["matchup"] = x
        elif t == "Team": xs["team"] = x
        elif t == "Player" and nxt == "Name": xs["player"] = x
        elif t == "Current" and nxt == "Status": xs["status"] = x
        elif t == "Reason": xs["reason"] = x
    default = dict(game_date=23, game_time=120, matchup=200, team=264, player=425, status=586, reason=666)
    return {k: xs.get(k, v) for k, v in default.items()}


def parse(path: str):
    """Return (report_time_et: datetime, rows: list[dict])."""
    report_time, out = None, []
    cur = dict(game_date=None, game_time=None, matchup=None, team=None)
    hx = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=1)
            text = " ".join(w["text"] for w in words if w["top"] < 70)
            m = HEAD_RE.search(text)
            if m and not report_time:
                report_time = dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3).upper()}", "%m/%d/%y %I:%M %p")
            if hx is None or any(w["text"] == "Matchup" for w in words):
                hx = _header_x(words)
            bounds = sorted(hx.items(), key=lambda kv: kv[1])
            page_players, extras = [], []
            for top, ws in _lines([w for w in words if w["top"] > 70]):
                line = " ".join(w["text"] for w in ws)
                if re.match(r"^Page \d+ of \d+$", line) or line.startswith("Game Date") or "Injury Report:" in line:
                    continue
                cells = {c: [] for c in COLS}
                for w in ws:
                    col = bounds[0][0]
                    for name, x in bounds:
                        if w["x0"] >= x - 3:
                            col = name
                    cells[col].append(w["text"])
                cells = {k: " ".join(v) for k, v in cells.items() if v}
                for k in ("game_date", "game_time", "matchup", "team"):
                    if k in cells:
                        if k == "game_date":      # a new block resets the narrower fields
                            cur.update(game_time=None, matchup=None, team=None)
                        if k == "game_time":
                            cur.update(matchup=None, team=None)
                        if k == "matchup":
                            cur.update(team=None)
                        cur[k] = cells[k]
                status = cells.get("status", "")
                player = cells.get("player", "")
                nys = "NOT YET SUBMITTED" in line.upper()
                if status in STATUSES or nys:
                    page_players.append(dict(top=top, game_date=cur["game_date"], game_time=cur["game_time"],
                                             matchup=cur["matchup"], team=cur["team"],
                                             player="" if nys else player,
                                             status="NOT YET SUBMITTED" if nys else status,
                                             reason=[] if nys else [(top, cells.get("reason", ""))]))
                elif "reason" in cells or "player" in cells:
                    extras.append((top, cells))
            first_top = page_players[0]["top"] if page_players else 1e9
            for top, cells in extras:
                cand = [r for r in page_players if r["status"] != "NOT YET SUBMITTED"]
                near = min(cand, key=lambda r: abs(r["top"] - top)) if cand else None
                if near is not None and abs(near["top"] - top) <= 16:
                    p = near
                elif top < first_top and out:          # reason wrapped over the page break
                    p = out[-1]; top = 1e9
                else:
                    continue
                if "reason" in cells:
                    p["reason"].append((top, cells["reason"]))
                if "player" in cells and "NOT YET" not in cells["player"].upper():
                    p["player"] = (cells["player"] + " " + p["player"]) if top < p.get("top", 0) else (p["player"] + " " + cells["player"])
            out.extend(page_players)
    for r in out:
        r["reason"] = " ".join(t for _, t in sorted(r["reason"]) if t).strip() or None
        r["player"] = r["player"].strip()
        r.pop("top", None)
        r["game_date"] = dt.datetime.strptime(r["game_date"], "%m/%d/%Y").date() if r["game_date"] else None
        r["matchup"] = (r["matchup"] or "").replace(" ", "")
    return report_time, out


def store(db, path: str, league: str = "NBA") -> int:
    rtime, rows = parse(path)
    if rtime is None:
        raise ValueError(f"No report time found in {path}")
    old = db.one("SELECT report_id FROM core.injury_reports WHERE league=? AND report_time_et=?", (league, rtime.isoformat(sep=" ")))
    if old:
        db.x("DELETE FROM core.injury_status WHERE report_id=?", (old[0],))
        rid = int(old[0])
    else:
        rid = db.insert_id("core.injury_reports", {"league": league, "report_time_et": rtime.isoformat(sep=" "),
                                                   "source_file": path}, "report_id")
    seen = set()
    recs = []
    for r in rows:
        k = (r["matchup"], r["team"], r["player"] or "(team not submitted)")
        if k in seen:
            continue
        seen.add(k)
        recs.append((rid, r["game_date"].isoformat() if r["game_date"] else None, r["matchup"], r["team"] or "",
                     k[2], r["status"], r["reason"]))
    db.many("INSERT INTO core.injury_status (report_id, game_date, matchup, team_name, player, status, reason) "
            "VALUES (?,?,?,?,?,?,?)", recs)
    print(f"{rtime:%Y-%m-%d %I:%M %p}: {len(recs)} rows stored (report_id {rid})")
    return rid


REPORT_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{d:%Y-%m-%d}_{d:%I_%M%p}.pdf"


def fetch_latest(folder: str, lookback_hours: int = 6) -> str | None:
    """Download the most recent official report (they post on the hour/half-hour/quarter-hour)."""
    import os
    import requests
    from zoneinfo import ZoneInfo
    now = dt.datetime.now(ZoneInfo("America/New_York")).replace(second=0, microsecond=0, tzinfo=None)
    t = now - dt.timedelta(minutes=now.minute % 15)
    for _ in range(lookback_hours * 4):
        url = REPORT_URL.format(d=t)
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, url.rsplit("/", 1)[1])
            with open(path, "wb") as fh:
                fh.write(r.content)
            print(f"downloaded {url}")
            return path
        t -= dt.timedelta(minutes=15)
    print("no report found in the last", lookback_hours, "hours")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fetch", metavar="FOLDER", help="download the latest official report into FOLDER and load it")
    a = ap.parse_args(argv)
    if a.fetch:
        p = fetch_latest(a.fetch)
        a.pdf = ([p] if p else [])
    if a.dry_run:
        for f in a.pdf:
            t, rows = parse(f)
            print(f"# {f}: report {t}, {len(rows)} rows")
            for r in rows:
                print(f"{r['game_date']} {r['matchup']:8s} {(r['team'] or '')[:24]:24s} {r['player'][:28]:28s} {r['status']:13s} {r['reason'] or ''}")
        return
    from .db import session
    with session() as db:
        for f in a.pdf:
            store(db, f)


if __name__ == "__main__":
    sys.exit(main())

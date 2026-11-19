"""Watch list for tonight's bets + alerts when the injury report changes a player in a game we bet.

Set tonight's list (Claude gives you this line with the card; it replaces the list for that date):
  python -m mpm.watch set --date 2026-11-19 "DET@NOP|Pistons -4.5 ($13)|8:05PM" "BOS@DEN|Celtics -2.5 ($9)|9:35PM"
  python -m mpm.watch list
  python -m mpm.watch check            # compare the latest two reports now (also runs after every report download)
  python -m mpm.watch test             # show a test alert

An alert fires, once per player and status, when before tip a player who averages 20+ minutes
(or isn't in the box scores yet) moves to Out or Doubtful, or comes back from Out/Doubtful/Questionable.
Alerts pop up on screen (Windows notification) and are appended to C:\\MaverickPicks\\alerts.log.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import unicodedata

BAD = ("Out", "Doubtful")
MIN_MPG = 20.0


def _norm(name: str) -> str:
    """'Cunningham, Cade' / 'Cade Cunningham' / 'Pippen Jr., Scotty' -> 'cade cunningham' / 'scotty pippen'."""
    if "," in name:
        last, first = [x.strip() for x in name.split(",", 1)]
        name = f"{first} {last}"
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    return " ".join(s.split())


def _time(s: str):
    s = s.strip().upper().replace(" ", "")
    for f in ("%I:%M%p", "%I%p", "%H:%M"):
        try:
            return dt.datetime.strptime(s, f).time()
        except ValueError:
            pass
    raise ValueError(f"bad tip time {s!r} (use 8:05PM)")


def _tip_txt(t) -> str:
    t = t if isinstance(t, dt.time) else _time(str(t)[:5])
    return t.strftime("%I:%M %p").lstrip("0")


def set_list(db, game_date: str, items: list[str], league="NBA") -> int:
    db.x("DELETE FROM core.watchlist WHERE league=? AND game_date=?", (league, game_date))
    n = 0
    for it in items:
        parts = [p.strip() for p in it.split("|")]
        if len(parts) < 2:
            raise ValueError(f"expected MATCHUP|BET|TIP, got {it!r}")
        tip = _time(parts[2]).strftime("%H:%M:%S") if len(parts) > 2 and parts[2] else None
        db.x("INSERT INTO core.watchlist (league, game_date, matchup, bet_label, tip_et) VALUES (?,?,?,?,?)",
             (league, game_date, parts[0].replace(" ", "").upper(), parts[1], tip))
        n += 1
    return n


def _mpg(db) -> dict:
    rows = db.q("SELECT player, AVG(CAST(mins AS float)) FROM nba.player_box WHERE mins > 0 GROUP BY player")
    return {_norm(p): float(m) for p, m in rows}


def check(db, report_id=None, league="NBA", now=None, notify=True) -> list[str]:
    """Compare a report (default: the latest) with the one before it for watched games; return alert lines."""
    if report_id is None:
        r = db.one("SELECT MAX(report_id) FROM core.injury_reports WHERE league=?", (league,))
        report_id = r[0] if r else None
    if report_id is None:
        return []
    cur = db.one("SELECT report_time_et FROM core.injury_reports WHERE report_id=?", (report_id,))
    rtime = cur[0] if isinstance(cur[0], dt.datetime) else dt.datetime.fromisoformat(str(cur[0]))
    prev = db.one("SELECT MAX(report_id) FROM core.injury_reports WHERE league=? AND report_time_et < ?",
                  (league, rtime.isoformat(sep=" ")))
    prev_id = prev[0] if prev else None
    now = now or dt.datetime.now()
    watch = db.q("SELECT game_date, matchup, bet_label, tip_et FROM core.watchlist WHERE league=? AND game_date=?",
                 (league, rtime.date().isoformat()))
    if not watch:
        return []
    bets: dict[str, list] = {}
    for gd, m, label, tip in watch:
        bets.setdefault(m, []).append((label, tip))
    old = {}
    if prev_id:
        for m, p, s in db.q("SELECT matchup, player, status FROM core.injury_status WHERE report_id=?", (prev_id,)):
            old[(m, p)] = s
    mpg = _mpg(db)
    out = []
    for m, team, p, s, reason in db.q("SELECT matchup, team_name, player, status, reason FROM core.injury_status "
                                      "WHERE report_id=?", (report_id,)):
        if m not in bets or p == "(team not submitted)":
            continue
        tips = [t for _, t in bets[m] if t is not None]
        if tips:
            tip = min(t if isinstance(t, dt.time) else _time(str(t)[:5]) for t in tips)
            if now.date() == rtime.date() and now.time() >= tip:
                continue                                    # game already started
        if "G League" in (reason or ""):
            continue
        was = old.get((m, p))
        went_bad = s in BAD and was != s and not (s == "Doubtful" and was == "Out")
        came_back = s in ("Available", "Probable") and was in ("Out", "Doubtful", "Questionable")
        if not (went_bad or came_back):
            continue
        avg = mpg.get(_norm(p))
        if avg is not None and avg < MIN_MPG:
            continue
        if db.one("SELECT 1 FROM core.injury_alerts WHERE league=? AND game_date=? AND matchup=? AND player=? AND status=?",
                  (league, rtime.date().isoformat(), m, p, s)):
            continue
        db.x("INSERT INTO core.injury_alerts (league, game_date, matchup, player, status, report_id) VALUES (?,?,?,?,?,?)",
             (league, rtime.date().isoformat(), m, p, s, report_id))
        first_last = " ".join(reversed([x.strip() for x in p.split(",", 1)])) if "," in p else p
        mins = f"{avg:.0f} mpg" if avg is not None else "mpg unknown"
        labels = "; ".join(lab + (f" ({_tip_txt(t)} tip)" if t else "") for lab, t in bets[m])
        line = (f"{first_last} ({team}, {mins}) {was or 'not listed'} -> {s.upper()} on the "
                f"{rtime:%I:%M %p} report. Affects {m}: {labels}")
        out.append(line)
    for line in out:
        print("ALERT:", line)
        _log(line)
        if notify:
            toast("MaverickPicks injury alert", line)
    return out


def _log(line: str):
    folder = os.environ.get("MPM_LOG_DIR", r"C:\MaverickPicks\logs")
    path = os.path.join(os.path.dirname(folder.rstrip("\\/")) or folder, "alerts.log")
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{dt.datetime.now():%Y-%m-%d %H:%M}  {line}\n")
    except OSError:
        pass


TOAST_PS = r"""
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $x.GetElementsByTagName('text')
$null = $t.Item(0).AppendChild($x.CreateTextNode($env:MPM_TOAST_TITLE))
$null = $t.Item(1).AppendChild($x.CreateTextNode($env:MPM_TOAST_BODY))
$toast = [Windows.UI.Notifications.ToastNotification]::new($x)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe').Show($toast)
"""


def toast(title: str, body: str):
    """Windows notification (no extra installs). Silently does nothing elsewhere."""
    if os.name != "nt":
        return
    env = dict(os.environ, MPM_TOAST_TITLE=title, MPM_TOAST_BODY=body)
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", TOAST_PS],
                       env=env, timeout=30, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        pass


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set"); s.add_argument("--date", default=dt.date.today().isoformat()); s.add_argument("items", nargs="+")
    l = sub.add_parser("list"); l.add_argument("--date", default=dt.date.today().isoformat())
    sub.add_parser("check")
    sub.add_parser("test")
    a = ap.parse_args(argv)
    if a.cmd == "test":
        toast("MaverickPicks injury alert", "Test: alerts are working.")
        print("sent a test notification")
        return
    from .db import session
    with session() as db:
        if a.cmd == "set":
            print(f"{set_list(db, a.date, a.items)} bets on the watch list for {a.date}")
        elif a.cmd == "list":
            for row in db.q("SELECT matchup, bet_label, tip_et FROM core.watchlist WHERE game_date=? ORDER BY tip_et, matchup", (a.date,)):
                print(*row)
        else:
            if not check(db):
                print("no new alerts")


if __name__ == "__main__":
    sys.exit(main())

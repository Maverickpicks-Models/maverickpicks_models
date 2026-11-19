"""Tonight's NHL card from the database.

Reads the latest odds snapshot for the day (pregame, else open), the latest MoneyPuck tables and model
settings, applies the rulebook and bankroll plan, writes core.model_runs + core.recommendations, and
renders the Discord graphics.

Moneyline and game total: Novig. Team totals: Novig if the feed has them, otherwise the books' consensus
(Pinnacle's no-vig price if it has the line, else the median across books) with an estimated Novig price;
every team-total play then carries a minimum Novig price to check in the app.

Usage (PowerShell):
  python -m mpm.nhl_slate --goalie "BOS=Swayman!" --goalie "DET=Talbot" --out C:\\MaverickPicks\\cards
      "!" after a name = confirmed on goaliepost (needed for the GU rule). Last names are enough.
  python -m mpm.nhl_slate --date 2026-11-18 --dry-run      # print the card, write nothing
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import difflib
import statistics
import sys
import unicodedata
from zoneinfo import ZoneInfo

from .db import DB, session
from .nhl_model import Model, american, no_vig
from .nhl_rules import RULEBOOK, Game, Slate, evaluate, size_slate

ET = ZoneInfo("America/New_York")
BET_BOOK = "novig"
SHARP = "pinnacle"
EST_VIG = 0.01            # estimated Novig margin per side when a price has to come from the books


def latest_snapshot(db: DB, gdate: dt.date):
    """Latest NHL snapshot that has prices for games on gdate (pregame preferred, then open)."""
    for purpose in ("pregame", "open"):
        row = db.one("SELECT MAX(s.snapshot_id) FROM core.odds_snapshots s JOIN core.odds o ON o.snapshot_id=s.snapshot_id "
                     "JOIN core.games g ON g.game_id=o.game_id WHERE s.league='NHL' AND s.purpose=? AND g.game_date=?",
                     (purpose, gdate.isoformat()))
        if row and row[0]:
            return int(row[0]), purpose
    return None, None


def _pairs(rows):
    """rows of (bookmaker, side, team_code, point, price) -> {(book, team, point): (over, under)}."""
    out = {}
    for bk, side, team, point, price in rows:
        d = out.setdefault((bk, team, float(point) if point is not None else None), {})
        d[side] = int(price)
    return {k: (v["over"], v["under"]) for k, v in out.items() if "over" in v and "under" in v}


def consensus(pairs: dict, team, point):
    """No-vig over probability for team/point: Pinnacle if present, else the median across books."""
    probs = {bk: no_vig(o, u) for (bk, t, pt), (o, u) in pairs.items() if t == team and pt == point and bk != BET_BOOK}
    if not probs:
        return None
    return probs[SHARP] if SHARP in probs else statistics.median(probs.values())


def _half(pt) -> bool:
    """x.5 lines only: whole-number lines can push and are priced differently."""
    return pt is not None and abs(pt - int(pt) - 0.5) < 1e-9


def _est_prices(p_over: float):
    return american(min(.97, p_over + EST_VIG)), american(min(.97, 1 - p_over + EST_VIG))


def market_for_game(db: DB, snap: int, gid: int, away: str, home: str):
    q = lambda mk: db.q("SELECT bookmaker, side, team_code, point, price_american FROM core.odds "
                        "WHERE snapshot_id=? AND game_id=? AND market=?", (snap, gid, mk))
    h2h = {(bk, side): int(pr) for bk, side, _, _, pr in q("h2h")}
    if (BET_BOOK, "away") in h2h and (BET_BOOK, "home") in h2h:
        ml_a, ml_h = h2h[(BET_BOOK, "away")], h2h[(BET_BOOK, "home")]
    else:
        books = {bk for bk, _ in h2h}
        ps = [no_vig(h2h[(b, "home")], h2h[(b, "away")]) for b in books if (b, "home") in h2h and (b, "away") in h2h]
        if not ps:
            return None
        ph = statistics.median(ps); ml_h, ml_a = _est_prices(ph)
    tot = {k: v for k, v in _pairs(q("totals")).items() if _half(k[2])}
    if not tot:
        return None
    # main line = the one most books list (books post one main total; alternates come from few books)
    count = {}
    for (bk, _, pt) in tot:
        count[pt] = count.get(pt, 0) + 1
    med = lambda pt: statistics.median(no_vig(*ou) for (bk, _, p_), ou in tot.items() if p_ == pt)
    line = max(count, key=lambda pt: (count[pt], -abs(med(pt) - .5)))
    if (BET_BOOK, None, line) in tot:
        o, u = tot[(BET_BOOK, None, line)]
    else:
        o, u = _est_prices(med(line))
    tts = {k: v for k, v in _pairs(q("team_totals")).items() if _half(k[2])}   # Novig only posts x.5 lines
    src, out = "novig", {}
    for team in (away, home):
        mine = [(pt, ou) for (bk, t, pt), ou in tts.items() if bk == BET_BOOK and t == team]
        if mine:
            out[team] = [(pt, o_, u_) for pt, (o_, u_) in mine]
            continue
        src = "consensus"
        pts = sorted({pt for (bk, t, pt) in tts if t == team})
        out[team] = [(pt, *_est_prices(consensus(tts, team, pt))) for pt in pts if consensus(tts, team, pt) is not None]
    if not out.get(away) or not out.get(home):
        return None
    return dict(ml_away=ml_a, ml_home=ml_h, total_line=line, over_price=o, under_price=u,
                away_tts=out[away], home_tts=out[home], tt_source=src)


def _plain(x: str) -> str:
    """Lower-case, accents removed; also repairs UTF-8 text mangled by a Windows console ('MerilÃ¤inen')."""
    x = str(x)
    if "Ã" in x:
        try:
            x = x.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    x = unicodedata.normalize("NFKD", x)
    return "".join(c for c in x if not unicodedata.combining(c)).lower().strip()


def parse_goalies(model: Model, args) -> tuple[dict, set]:
    """'BOS=Swayman!' -> {'BOS': 'Jeremy Swayman'}, confirmed {'Jeremy Swayman'}."""
    out, conf = {}, set()
    for a in args or []:
        team, _, name = a.partition("=")
        team, name = team.strip().upper(), name.strip()
        c = name.endswith("!")
        name = name.rstrip("!").strip()
        cands = [g["name"] for g in model.goalies if g["team_code"] == team]
        key = lambda x: _plain(x).split()[-1] if _plain(x).split() else ""
        full = next((n for n in cands if _plain(n) == _plain(name)), None) or \
            next((n for n in cands if key(n) == key(name)), None)
        if not full:                      # typo or partial name: closest last name on that team
            close = difflib.get_close_matches(key(name), [key(n) for n in cands], n=1, cutoff=0.75)
            full = next((n for n in cands if close and key(n) == close[0]), None)
        if full and key(full) != key(name):
            print(f"note: {team} goalie '{name}' read as {full}")
        full = full or name
        if full not in cands:
            print(f"note: {team} goalie '{name}' not in the MoneyPuck table - priced as league average")
        out[team] = full
        if c:
            conf.add(full)
    return out, conf


def back_to_back(db: DB, gdate: dt.date) -> set:
    rows = db.q("SELECT away_code, home_code FROM core.games WHERE league='NHL' AND game_date=?",
                ((gdate - dt.timedelta(days=1)).isoformat(),))
    return {t for r in rows for t in r}


def build(db: DB, gdate: dt.date, goalie_args=None, extra_b2b=()):
    model = Model.from_db(db)
    snap, purpose = latest_snapshot(db, gdate)
    if not snap:
        raise SystemExit(f"No NHL odds snapshot with games on {gdate}. Run: python -m mpm.oddsapi --league NHL --purpose pregame")
    goalies, conf = parse_goalies(model, goalie_args)
    b2b = back_to_back(db, gdate) | {t.upper() for t in extra_b2b}
    sl = Slate(model, conf, b2b)
    games = db.q("SELECT game_id, away_code, home_code, start_utc FROM core.games WHERE league='NHL' AND game_date=? "
                 "ORDER BY start_utc, game_id", (gdate.isoformat(),))
    results, skipped = [], []
    for gid, away, home, start in games:
        mk = market_for_game(db, snap, gid, away, home)
        if not mk:
            skipped.append(f"{away}@{home}: no team totals in snapshot {snap} ({purpose})")
            continue
        when = ""
        if start:
            s = dt.datetime.fromisoformat(str(start)).replace(tzinfo=dt.timezone.utc).astimezone(ET)
            when = s.strftime("%I:%M %p").lstrip("0")
        g = Game(away, home, goalies.get(away), goalies.get(home), mk["ml_away"], mk["ml_home"], mk["total_line"],
                 mk["over_price"], mk["under_price"], mk["away_tts"], mk["home_tts"], when, mk["tt_source"])
        r = evaluate(sl, g)
        r.game_id = gid
        results.append(r)
    night = size_slate(results)
    return dict(results=results, snapshot_id=snap, purpose=purpose, night=night, skipped=skipped, b2b=b2b, model=model)


def save(db: DB, out: dict, version: str) -> int:
    rid = db.insert_id("core.model_runs", {"league": "NHL", "model_version": version, "rulebook": RULEBOOK,
                                           "snapshot_id": out["snapshot_id"]}, "run_id")
    rec = []
    for r in out["results"]:
        db.x("INSERT INTO core.projections (run_id, game_id, away_pts, home_pts, away_win_p, away_cover_p, over_p) "
             "VALUES (?,?,?,?,?,?,?)", (rid, r.game_id, round(r.la, 3), round(r.lh, 3), round(r.prices.ml_away, 4), None,
                                       round(r.info["blend_over"], 4)))
        for pl in r.plays:
            section = "PAPER" if pl.stake <= 0 else ("CORE" if pl.core else "TEST")
            note = (pl.note or "") + (f" min price {pl.min_price:+d}" if pl.min_price is not None else "")
            rec.append((rid, r.game_id, pl.market, pl.side, pl.point, pl.price, round(pl.stake / 10, 2), section, pl.code,
                        note.strip()[:300]))
    db.many("INSERT INTO core.recommendations (run_id, game_id, market, side, point, price_american, units, section, "
            "rule_codes, note) VALUES (?,?,?,?,?,?,?,?,?,?)", rec)
    return rid


def records(db: DB) -> dict:
    try:
        return {c: (int(w or 0), int(l or 0), float(roi or 0)) for c, w, l, roi in
                db.q("SELECT rule_code, wins, losses, roi_flat FROM nhl.v_rule_record")}
    except Exception:
        return {}


def team_names(db: DB) -> dict:
    return {c: n for c, n in db.q("SELECT team_code, team_name FROM core.teams WHERE league='NHL'")}


def print_card(out: dict):
    print(f"NHL card - odds snapshot {out['snapshot_id']} ({out['purpose']}), back-to-backs: {', '.join(sorted(out['b2b'])) or 'none'}")
    for r in out["results"]:
        g = r.game
        print(f"\n{g.start_et:>8}  {g.away} @ {g.home}  {r.la:.2f}-{r.lh:.2f}  G: {g.g_away or '?'} / {g.g_home or '?'}"
              f"  (team totals: {g.tt_source})")
        for pl in sorted(r.plays, key=lambda x: -x.stake):
            tag = "TRACK" if pl.stake <= 0 else ("CORE " if pl.core else "TEST ")
            pt = "" if pl.point is None else f" {pl.point:g}"
            print(f"   {tag} ${pl.stake:5.2f}  {pl.market} {pl.side}{pt} {pl.price:+d}  [{pl.code}]  min {pl.min_price:+d}  "
                  f"EV {pl.ev * 100:+.1f}%")
        for n in r.notes:
            print("      -", n)
    for s in out["skipped"]:
        print("skipped", s)
    print(f"\nNight total: ${out['night']:.2f} (cap $120)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="game date (ET), default today")
    ap.add_argument("--goalie", action="append", help='TEAM=Name, "!" = confirmed (e.g. "BOS=Swayman!")')
    ap.add_argument("--b2b", default="", help="extra back-to-back teams, comma-separated")
    ap.add_argument("--out", default=r"C:\MaverickPicks\cards", help="folder for the graphics")
    ap.add_argument("--dry-run", action="store_true", help="print only; do not save or render")
    a = ap.parse_args(argv)
    gdate = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(ET).date()
    with session() as db:
        out = build(db, gdate, a.goalie, [t for t in a.b2b.split(",") if t])
        print_card(out)
        if not out["results"]:
            tip = (" The open pull has no team totals; run after the 6:00 PM pregame pull "
                   "(or: python -m mpm.oddsapi --league NHL --purpose pregame)." if out["purpose"] == "open" else "")
            print(f"\nNothing priced - no run saved, no graphics.{tip}")
            return 1
        if a.dry_run:
            return
        rid = save(db, out, "nhl-engine 1")
        from . import nhl_card
        recs, names = records(db), team_names(db)
        folder = os.path.join(a.out, gdate.isoformat())
        os.makedirs(folder, exist_ok=True)
        when = gdate.strftime("%a · %b %d, %Y").upper()
        files = [nhl_card.render(nhl_card.html_tonight(out["results"], when, recs), os.path.join(folder, "00_tonights_card.png"))]
        for i, r in enumerate(out["results"], 1):
            files.append(nhl_card.render(nhl_card.html_game(r, f"{when} · {r.game.start_et} ET", recs, names),
                                         os.path.join(folder, f"{i:02d}_{r.game.away}_at_{r.game.home}.png")))
        print(f"\nSaved run {rid}. Graphics in {folder}:")
        for f in files:
            print("  ", os.path.basename(f))


if __name__ == "__main__":
    sys.exit(main())

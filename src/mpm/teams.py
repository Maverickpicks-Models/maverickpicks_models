"""Team name -> code resolution using core.team_aliases (cached per process)."""
from __future__ import annotations

import unicodedata

_cache: dict[tuple[str, str], str] = {}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.replace(".", "").lower().split())


def load(db) -> None:
    _cache.clear()
    for league, alias, code in db.q("SELECT league, alias, team_code FROM core.team_aliases"):
        _cache[(league, _norm(alias))] = code


def code(db, league: str, name: str) -> str:
    if not _cache:
        load(db)
    c = _cache.get((league, _norm(name)))
    if c is None:
        raise KeyError(f"Unknown {league} team name: {name!r} - add it to core.team_aliases")
    return c

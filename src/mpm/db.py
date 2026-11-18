"""Database access for MaverickPicks Models.

Production: SQL Server via pyodbc + Windows authentication (no passwords in code).
Tests: an in-memory SQLite stand-in (see tests/sqlite_schema.py) so the logic can be
checked without SQL Server.

Settings (environment variables, all optional):
    MPM_SQL_SERVER   default "ECG-L028"
    MPM_SQL_DB       default "MaverickPicks"
    MPM_SQL_DRIVER   default "ODBC Driver 18 for SQL Server"
"""
from __future__ import annotations

import os
from contextlib import contextmanager


class DB:
    def __init__(self, conn, kind: str):
        self.conn = conn
        self.kind = kind  # "mssql" or "sqlite"

    # ---- basic helpers -------------------------------------------------
    def q(self, sql: str, params=()):
        cur = self.conn.cursor()
        cur.execute(self._p(sql), params)
        try:
            return cur.fetchall()
        except Exception:
            return []

    def one(self, sql: str, params=()):
        rows = self.q(sql, params)
        return rows[0] if rows else None

    def x(self, sql: str, params=()):
        cur = self.conn.cursor()
        cur.execute(self._p(sql), params)
        return cur

    def many(self, sql: str, rows):
        rows = list(rows)
        if not rows:
            return 0
        cur = self.conn.cursor()
        if self.kind == "mssql":
            cur.fast_executemany = True
        cur.executemany(self._p(sql), rows)
        return len(rows)

    def insert_id(self, table: str, cols: dict, id_col: str) -> int:
        names = ", ".join(cols)
        marks = ", ".join("?" for _ in cols)
        if self.kind == "mssql":
            row = self.q(f"INSERT INTO {table} ({names}) OUTPUT INSERTED.{id_col} VALUES ({marks})", tuple(cols.values()))
            return int(row[0][0])
        cur = self.x(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(cols.values()))
        return int(cur.lastrowid)

    def commit(self):
        self.conn.commit()

    def _p(self, sql: str) -> str:
        return sql  # both pyodbc and sqlite3 use "?" placeholders

    # ---- config ----------------------------------------------------------
    def config(self, key: str, default=None):
        row = self.one("SELECT config_value FROM core.config WHERE config_key = ?", (key,))
        return row[0] if row else default


def connect() -> DB:
    import pyodbc  # imported here so tests run without it

    server = os.environ.get("MPM_SQL_SERVER", "ECG-L028")
    dbname = os.environ.get("MPM_SQL_DB", "MaverickPicks")
    driver = os.environ.get("MPM_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    cs = (f"DRIVER={{{driver}}};SERVER={server};DATABASE={dbname};"
          "Trusted_Connection=yes;TrustServerCertificate=yes;")
    return DB(pyodbc.connect(cs, autocommit=False), "mssql")


@contextmanager
def session(db: DB | None = None):
    own = db is None
    db = db or connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.conn.rollback()
        raise
    finally:
        if own:
            db.conn.close()

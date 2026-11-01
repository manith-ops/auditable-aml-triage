"""Append-only audit log in SQLite. Every analyst action is one new row; rows can never change.

Immutability is enforced by database triggers: any UPDATE or DELETE is rejected by SQLite itself,
not just avoided by this code. (Prototype: no login system, so the analyst name is self-declared.)
"""
import os
import sqlite3                                   # SQLite: a database stored in a single file, built into Python
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("AUDIT_DB", "artifacts/audit.db")     # can be overridden, e.g. for tests

DECISIONS = ("escalate", "dismiss", "more_info")  # what an analyst may decide about an alert

SCHEMA = """
create table if not exists audit_log (
    id            integer primary key autoincrement,       -- grows by one per action; gaps would show tampering
    ts_utc        text    not null,                        -- when it happened (UTC)
    analyst       text    not null,                        -- who
    alert_id      integer not null,
    raw_row_id    integer not null,                        -- which transaction
    decision      text    not null check (decision in ('escalate', 'dismiss', 'more_info')),
    note          text,
    score         real,                                    -- the model score the analyst saw
    model_version text    not null,                        -- which model produced the alert
    prompt_version text                                    -- reserved for the LLM summary step
);
create trigger if not exists audit_log_no_update before update on audit_log
begin select raise(abort, 'audit_log is append-only: updates are not allowed'); end;
create trigger if not exists audit_log_no_delete before delete on audit_log
begin select raise(abort, 'audit_log is append-only: deletes are not allowed'); end;
"""


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)                    # creates the table and the two triggers if they do not exist yet
    return con


def record(analyst: str, alert_id: int, raw_row_id: int, decision: str,
           note: str, score: float, model_version: str, prompt_version: str | None = None) -> int:
    """Add one row to the log. Returns its id."""
    if not analyst.strip():
        raise ValueError("analyst name is required")
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    with _connect() as con:                      # 'with' commits on success and rolls back on error
        cur = con.execute(
            "insert into audit_log (ts_utc, analyst, alert_id, raw_row_id, decision, note, score, model_version, prompt_version)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?)",           # ? placeholders: values are passed separately (prevents SQL injection)
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), analyst.strip(), int(alert_id),
             int(raw_row_id), decision, note.strip(), float(score), model_version, prompt_version),
        )
        return cur.lastrowid


def read_all() -> list[dict]:
    """Return every row, newest first."""
    con = _connect()
    con.row_factory = sqlite3.Row                # rows behave like dictionaries
    rows = con.execute("select * from audit_log order by id desc").fetchall()
    con.close()
    return [dict(r) for r in rows]

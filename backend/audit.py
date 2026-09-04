"""
backend/audit.py

Append-only audit log (ARCHITECTURE.md Section 7).

Two backends, selected automatically by whether DATABASE_URL is set:
  - Postgres (DATABASE_URL set): the canonical design. Run
    scripts/postgres_setup.sql ONCE with an admin connection first -- it
    creates the table and a restricted `razorguard_app` role with GRANT
    INSERT, SELECT only (no UPDATE/DELETE/DDL). Point DATABASE_URL at that
    restricted role's credentials for the running application, NOT the
    admin ones. This is the actual DB-level permission guarantee
    ARCHITECTURE.md Section 7 specifies.
  - SQLite (DATABASE_URL unset, or get_connection(force_sqlite=True)):
    local-dev fallback. No per-role GRANT system exists in SQLite, so the
    INSERT/SELECT-only guarantee there is enforced only at the APPLICATION
    layer (this module simply exposes no update/delete function) and by
    pytest, not by the database itself.

*** A REAL BUG FOUND IN PRACTICE, AND HOW IT'S FIXED HERE ***
Every function in this module originally re-checked `DATABASE_URL` in the
environment independently to decide which SQL dialect to use, INSTEAD of
checking what kind of connection object it was actually given. With
DATABASE_URL set globally in a shell (e.g. while testing the live Postgres
path), tests/test_audit.py's fixture -- which explicitly builds a
tmp_path-based SQLite connection expecting an isolated, disposable database
-- was silently redirected to a REAL Postgres instance instead, because
get_connection() ignored its own db_path argument whenever DATABASE_URL was
present. That's a real production-database contamination risk from running
tests, not just a test-isolation nicety, and it was caught by a user running
the suite with DATABASE_URL configured for other work.

Fixed two ways:
  1. get_connection() now accepts `force_sqlite: bool = False` so a caller
     can explicitly demand the SQLite fallback regardless of DATABASE_URL.
     tests/test_audit.py's fixture now always passes force_sqlite=True.
  2. append_audit_entry() and get_audit_trail() now detect which dialect to
     use by inspecting the CONNECTION OBJECT they were actually handed
     (_is_postgres_connection), not by re-reading the environment variable a
     second and third time. This closes the whole bug class: even if
     DATABASE_URL is set, a function that's handed a real sqlite3 connection
     will now always use SQLite syntax against it, and vice versa --
     correctness follows the object you have, not a global you don't control.

*** VERIFICATION STATUS ***
The SQLite path is genuinely exercised by tests/test_audit.py (real SQLite
file, real INSERT/SELECT), now isolated from DATABASE_URL via force_sqlite.
tests/test_postgres_audit.py mocks psycopg2.connect to verify query shape.
tests/test_postgres_audit_live.py (opt-in, skipped unless DATABASE_URL is
actually set) verifies real behavior against a real server, including that
the restricted role's DELETE is genuinely denied -- this is the first real,
non-mocked verification of the Postgres path, contributed by a user actually
running this against their own free Postgres instance.

No UPDATE/DELETE function exists in this module AT ALL, for either backend --
not merely unused, mirroring the "no PUT/DELETE /audit* route" rule in
ARCHITECTURE.md Section 3. Hash-chaining is NOT implemented (documented
scope cut, ARCHITECTURE.md Section 7) -- this log is append-only, never
described as immutable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _using_postgres(force_sqlite: bool = False) -> bool:
    return bool(os.environ.get("DATABASE_URL")) and not force_sqlite


def _is_postgres_connection(conn) -> bool:
    """Detects dialect from the CONNECTION OBJECT itself, not the
    environment -- see module docstring for why this matters. Uses
    isinstance against psycopg2's real connection class (rather than
    checking type(conn).__module__ directly) so that a MagicMock built with
    spec=psycopg2.extensions.connection in tests is correctly detected too
    -- MagicMock fakes isinstance checks when given a spec, which a raw
    module-name string comparison would not have honored."""
    try:
        import psycopg2.extensions

        return isinstance(conn, psycopg2.extensions.connection)
    except ImportError:
        return False


def get_connection(db_path: str = "razorguard_audit.db", force_sqlite: bool = False):
    """
    Returns a connection. If DATABASE_URL is set, connects to Postgres
    (db_path is ignored) -- UNLESS force_sqlite=True, in which case the
    SQLite fallback is used regardless of DATABASE_URL. See module docstring
    for why force_sqlite exists.
    """
    if _using_postgres(force_sqlite):
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        # Deliberately does NOT run CREATE TABLE here: the restricted
        # razorguard_app role has no DDL privileges by design (see
        # scripts/postgres_setup.sql) -- table creation is an admin-only,
        # one-time, out-of-band step, not something the running app can or
        # should be able to do.
        return conn

    import sqlite3

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            case_id TEXT NOT NULL,
            model_risk_outputs TEXT,
            evidence_used TEXT,
            agent_output TEXT,
            policy_decision TEXT,
            human_action TEXT
        )
        """
    )
    conn.commit()
    return conn


def append_audit_entry(
    conn,
    case_id: str,
    model_risk_outputs: dict,
    evidence_used: dict,
    agent_output: dict | None,
    policy_decision: dict,
    human_action: dict | None = None,
) -> int:
    """The ONLY write function in this module, for either backend -- pure
    INSERT, no update path exists anywhere in this file. Returns the new row id."""
    ts = datetime.now(timezone.utc)

    if _is_postgres_connection(conn):
        # JSONB columns take dicts directly via psycopg2's adapter -- no
        # manual json.dumps needed, and querying later gets back real dicts,
        # not strings that need re-parsing (see get_audit_trail).
        from psycopg2.extras import Json

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs
                    (timestamp, case_id, model_risk_outputs, evidence_used, agent_output, policy_decision, human_action)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ts,
                    case_id,
                    Json(model_risk_outputs),
                    Json(evidence_used),
                    Json(agent_output) if agent_output is not None else None,
                    Json(policy_decision),
                    Json(human_action) if human_action is not None else None,
                ),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id

    cur = conn.execute(
        """
        INSERT INTO audit_logs
            (timestamp, case_id, model_risk_outputs, evidence_used, agent_output, policy_decision, human_action)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts.isoformat(),
            case_id,
            json.dumps(model_risk_outputs),
            json.dumps(evidence_used),
            json.dumps(agent_output) if agent_output is not None else None,
            json.dumps(policy_decision),
            json.dumps(human_action) if human_action is not None else None,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_audit_trail(conn, case_id: str) -> list[dict]:
    """The ONLY read function, for either backend -- SELECT only, per the
    INSERT/SELECT-only design."""
    columns = [
        "id", "timestamp", "case_id", "model_risk_outputs", "evidence_used",
        "agent_output", "policy_decision", "human_action",
    ]

    if _is_postgres_connection(conn):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, timestamp, case_id, model_risk_outputs, evidence_used, agent_output, "
                "policy_decision, human_action FROM audit_logs WHERE case_id = %s ORDER BY id ASC",
                (case_id,),
            )
            rows = cur.fetchall()
        # JSONB columns already come back as real dicts via psycopg2 -- no
        # json.loads needed, unlike the SQLite/TEXT-column path below.
        return [dict(zip(columns, row)) for row in rows]

    rows = conn.execute(
        "SELECT id, timestamp, case_id, model_risk_outputs, evidence_used, agent_output, policy_decision, human_action "
        "FROM audit_logs WHERE case_id = ? ORDER BY id ASC",
        (case_id,),
    ).fetchall()
    return [dict(zip(columns, row)) for row in rows]


# NOTE: there is deliberately no update_audit_entry() or delete_audit_entry()
# function in this file, for either backend, and none should ever be added --
# see module docstring.
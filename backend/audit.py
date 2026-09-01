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
  - SQLite (DATABASE_URL unset): local-dev fallback. No per-role GRANT
    system exists in SQLite, so the INSERT/SELECT-only guarantee there is
    enforced only at the APPLICATION layer (this module simply exposes no
    update/delete function) and by pytest, not by the database itself.

*** VERIFICATION STATUS ***
The SQLite path is genuinely exercised by tests/test_audit.py (real SQLite
file, real INSERT/SELECT). The Postgres path's SQL has been checked for
syntax correctness and psycopg2's API used correctly, but has NOT been run
against a real Postgres server in this sandbox -- there is no Postgres
daemon available here (confirmed: no `psql` binary, no server process).
tests/test_postgres_audit.py mocks psycopg2.connect to verify the query
shapes and parameter binding are correct, which is NOT the same as proving
the real SQL runs against a real server. Run it for real against your own
Postgres instance (Neon, Supabase, or any Postgres) before trusting it.

No UPDATE/DELETE function exists in this module AT ALL, for either backend —
not merely unused, mirroring the "no PUT/DELETE /audit* route" rule in
ARCHITECTURE.md Section 3. Hash-chaining is NOT implemented (documented
scope cut, ARCHITECTURE.md Section 7) -- this log is append-only, never
described as immutable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _using_postgres() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def get_connection(db_path: str = "razorguard_audit.db"):
    """
    Returns a connection. If DATABASE_URL is set, connects to Postgres
    (db_path is ignored). Otherwise falls back to the local SQLite file at
    db_path -- the dev-time substitute, not the canonical design.
    """
    if _using_postgres():
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

    if _using_postgres():
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

    if _using_postgres():
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

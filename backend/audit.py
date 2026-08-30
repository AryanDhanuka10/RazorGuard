"""
backend/audit.py

Append-only audit log (ARCHITECTURE.md Section 7).

*** ENVIRONMENT NOTE — read before assuming this matches the canonical spec ***
ARCHITECTURE.md specifies Postgres with a database role restricted to
INSERT/SELECT only (no UPDATE/DELETE grants) — a DB-level guarantee. This
sandbox has no Postgres daemon available (confirmed in REPO_STATE.md), so
this module uses SQLite instead. SQLite has no per-role GRANT system, so the
INSERT/SELECT-only guarantee here is enforced only at the APPLICATION layer
(this module simply never exposes an update/delete function) and by the
pytest suite (tests/test_audit.py) — NOT by a database-level permission,
unlike the canonical Postgres design. This is a real, documented gap: when
deployed against actual Postgres, the DB-level grant restriction from
ARCHITECTURE.md Section 7 must still be applied — this module does not
replace that requirement, it only demonstrates the application-level half of it.

No UPDATE/DELETE function exists in this module AT ALL — not merely unused,
mirroring the "no PUT/DELETE /audit* route" rule in ARCHITECTURE.md Section 3.
Hash-chaining is NOT implemented (documented scope cut, ARCHITECTURE.md
Section 7) — this log is append-only, never described as immutable.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def get_connection(db_path: str = "razorguard_audit.db") -> sqlite3.Connection:
    # check_same_thread=False: FastAPI (and its TestClient) may serve requests
    # on a different thread than the one that created this connection. SQLite
    # forbids cross-thread use by default (see FAILURE_LOG.md "SQLite
    # cross-thread audit-log error under FastAPI TestClient"). This module
    # still only ever issues one INSERT and one SELECT statement — disabling
    # SQLite's same-thread check does not weaken the INSERT/SELECT-only
    # design, it only permits calling those same two operations from
    # request-handling threads.
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
    conn: sqlite3.Connection,
    case_id: str,
    model_risk_outputs: dict,
    evidence_used: dict,
    agent_output: dict | None,
    policy_decision: dict,
    human_action: dict | None = None,
) -> int:
    """The ONLY write function in this module — pure INSERT, no update path
    exists anywhere in this file. Returns the new row id."""
    cur = conn.execute(
        """
        INSERT INTO audit_logs
            (timestamp, case_id, model_risk_outputs, evidence_used, agent_output, policy_decision, human_action)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
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


def get_audit_trail(conn: sqlite3.Connection, case_id: str) -> list[dict]:
    """The ONLY read function — SELECT only, per the INSERT/SELECT-only design."""
    rows = conn.execute(
        "SELECT id, timestamp, case_id, model_risk_outputs, evidence_used, agent_output, policy_decision, human_action "
        "FROM audit_logs WHERE case_id = ? ORDER BY id ASC",
        (case_id,),
    ).fetchall()
    columns = [
        "id", "timestamp", "case_id", "model_risk_outputs", "evidence_used",
        "agent_output", "policy_decision", "human_action",
    ]
    return [dict(zip(columns, row)) for row in rows]


# NOTE: there is deliberately no update_audit_entry() or delete_audit_entry()
# function in this file, and none should ever be added — see module docstring.

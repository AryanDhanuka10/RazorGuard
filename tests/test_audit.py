import os
import ast
import sqlite3

import pytest

from backend.audit import get_connection, append_audit_entry, get_audit_trail


@pytest.fixture
def conn(tmp_path):
    db_path = str(tmp_path / "test_audit.db")
    c = get_connection(db_path)
    yield c
    c.close()


def test_append_and_retrieve_audit_entry(conn):
    row_id = append_audit_entry(
        conn,
        case_id="case_1",
        model_risk_outputs={"risk": 0.8},
        evidence_used={"cluster_id": "c1"},
        agent_output={"verdict": "escalate"},
        policy_decision={"tier": "high", "action": "escalate_for_approval"},
    )
    assert row_id == 1
    trail = get_audit_trail(conn, "case_1")
    assert len(trail) == 1
    assert trail[0]["case_id"] == "case_1"


def test_audit_trail_accumulates_multiple_entries_for_same_case(conn):
    append_audit_entry(conn, "case_2", {}, {}, None, {"tier": "low"})
    append_audit_entry(conn, "case_2", {}, {}, {"verdict": "escalate"}, {"tier": "high"}, human_action={"approved": True})
    trail = get_audit_trail(conn, "case_2")
    assert len(trail) == 2
    assert trail[1]["human_action"] is not None


def test_no_update_or_delete_function_exists_in_module():
    """Structural guard mirroring the 'no PUT/DELETE /audit* route' rule
    (ARCHITECTURE.md Section 3) — parse the module and assert no function
    with 'update' or 'delete' in its name is ever defined."""
    module_path = os.path.join(os.path.dirname(__file__), "..", "backend", "audit.py")
    with open(module_path) as f:
        tree = ast.parse(f.read())
    fn_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    for name in fn_names:
        assert "update" not in name.lower()
        assert "delete" not in name.lower()


def test_sqlite_connection_has_no_application_level_update_path(conn):
    """Even though SQLite itself has no per-role GRANT system (documented gap
    in backend/audit.py's module docstring — Postgres isn't available in this
    sandbox), confirm at least that raw UPDATE/DELETE via this same connection
    would only be possible by writing new code, not by calling anything this
    module exposes."""
    append_audit_entry(conn, "case_3", {}, {}, None, {"tier": "low"})
    # This module exposes no delete/update function — attempting the "attack"
    # requires dropping to raw SQL directly against the connection, which is
    # exactly the point: the risk lives at the DB-permission layer, which is
    # a real, documented gap in this sandbox (see module docstring), not
    # something this test can close without a real Postgres role to grant.
    conn.execute("DELETE FROM audit_logs WHERE case_id = ?", ("case_3",))
    conn.commit()
    trail = get_audit_trail(conn, "case_3")
    assert trail == []  # confirms the gap is real, not falsely claimed closed

"""
tests/test_postgres_audit.py

Mocked tests for backend/audit.py's Postgres code path. psycopg2.connect is
mocked, so NO real Postgres server is touched. These tests verify the SQL
query shapes, parameter binding, and backend-selection logic are correct --
they do NOT prove the real SQL runs successfully against a real Postgres
server (see backend/audit.py's module docstring, and
tests/test_postgres_audit_live.py for that). Run scripts/postgres_setup.sql
and a real Postgres instance before trusting the Postgres path in production.

Mock connections use spec=psycopg2.extensions.connection so that
isinstance()-based dialect detection in backend/audit.py's
_is_postgres_connection() correctly recognizes them as "Postgres-shaped" --
without spec, a bare MagicMock() is NOT an instance of psycopg2's connection
class, and would be silently (and wrongly) treated as SQLite.
"""
import psycopg2.extensions
from unittest.mock import MagicMock, patch

from backend.audit import get_connection, append_audit_entry, get_audit_trail, _using_postgres


def _mock_postgres_connection():
    return MagicMock(spec=psycopg2.extensions.connection)


def test_using_postgres_detection_follows_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _using_postgres() is False
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    assert _using_postgres() is True


def test_force_sqlite_overrides_database_url(monkeypatch):
    """Regression test for the real bug this fixes: with DATABASE_URL set,
    force_sqlite=True must still route to SQLite -- this is what protects
    tests/test_audit.py's fixture from silently hitting a real Postgres
    instance whenever a developer happens to have DATABASE_URL exported in
    their shell for other work."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    assert _using_postgres(force_sqlite=True) is False
    assert _using_postgres(force_sqlite=False) is True


def test_get_connection_uses_psycopg2_when_database_url_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    with patch("psycopg2.connect") as mock_connect:
        mock_connect.return_value = _mock_postgres_connection()
        get_connection()
    mock_connect.assert_called_once_with("postgresql://user:pass@host/db")


def test_get_connection_force_sqlite_ignores_database_url(monkeypatch, tmp_path):
    """The other half of the force_sqlite regression test: get_connection()
    itself must actually return a usable SQLite connection when
    force_sqlite=True, even with DATABASE_URL set -- not just report the
    right boolean from _using_postgres()."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    db_path = str(tmp_path / "forced_sqlite.db")
    with patch("psycopg2.connect") as mock_connect:
        conn = get_connection(db_path, force_sqlite=True)
    mock_connect.assert_not_called()
    # A real, working SQLite connection -- prove it by actually using it.
    row_id = append_audit_entry(
        conn, case_id="c1", model_risk_outputs={}, evidence_used={}, agent_output=None, policy_decision={}
    )
    assert row_id is not None
    conn.close()


def test_append_audit_entry_uses_postgres_placeholders_and_jsonb(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    mock_conn = _mock_postgres_connection()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [42]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    row_id = append_audit_entry(
        mock_conn, case_id="case_1", model_risk_outputs={"risk": 0.8},
        evidence_used={"cluster_id": "c1"}, agent_output={"verdict": "escalate"},
        policy_decision={"tier": "high"},
    )

    assert row_id == 42
    mock_conn.commit.assert_called_once()
    sql_text = mock_cursor.execute.call_args[0][0]
    assert "%s" in sql_text  # psycopg2 placeholder style, not SQLite's "?"
    assert "RETURNING id" in sql_text
    assert "INSERT INTO audit_logs" in sql_text
    assert "UPDATE" not in sql_text.upper()
    assert "DELETE" not in sql_text.upper()


def test_append_audit_entry_uses_postgres_dialect_based_on_connection_not_env(monkeypatch):
    """Regression test for the real bug: even with DATABASE_URL UNSET,
    append_audit_entry must still use Postgres syntax when handed a
    Postgres-shaped connection -- dialect must follow the object, not a
    global that might disagree with it."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    mock_conn = _mock_postgres_connection()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [7]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    row_id = append_audit_entry(
        mock_conn, case_id="case_2", model_risk_outputs={}, evidence_used={}, agent_output=None, policy_decision={}
    )
    assert row_id == 7
    sql_text = mock_cursor.execute.call_args[0][0]
    assert "%s" in sql_text


def test_get_audit_trail_uses_postgres_placeholder_and_returns_dicts(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    mock_conn = _mock_postgres_connection()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        (1, "2026-01-01T00:00:00Z", "case_1", {"risk": 0.8}, {}, {"verdict": "escalate"}, {"tier": "high"}, None)
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    trail = get_audit_trail(mock_conn, "case_1")

    assert len(trail) == 1
    assert trail[0]["case_id"] == "case_1"
    # JSONB columns come back as real dicts already, no json.loads step —
    # confirmed by asserting the value is a dict, not a JSON string.
    assert isinstance(trail[0]["model_risk_outputs"], dict)
    sql_text = mock_cursor.execute.call_args[0][0]
    assert "%s" in sql_text
    assert "UPDATE" not in sql_text.upper()
    assert "DELETE" not in sql_text.upper()


def test_get_connection_never_calls_execute_on_postgres_branch(monkeypatch):
    """Behavioral guard (more robust than string-matching source code, which
    breaks on legitimate docstring prose): connecting to Postgres must never
    call .execute()/.cursor() on the connection at all — table creation is
    exclusively scripts/postgres_setup.sql's job, run once by an admin."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    with patch("psycopg2.connect") as mock_connect:
        mock_conn = _mock_postgres_connection()
        mock_connect.return_value = mock_conn
        get_connection()
    mock_conn.cursor.assert_not_called()
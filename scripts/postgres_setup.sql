-- scripts/postgres_setup.sql
--
-- Run ONCE, using an ADMIN/superuser connection string (e.g. the "owner"
-- connection string most free Postgres hosts like Neon or Supabase give you
-- by default) — never using the restricted application role this script
-- creates. This is the actual DB-level permission grant ARCHITECTURE.md
-- Section 7 specifies, closing the gap that SQLite (the dev-time
-- substitute) could only enforce at the application layer.
--
-- After running this once, your application's runtime DATABASE_URL should
-- use the razorguard_app role's credentials, NOT the admin/owner ones.

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    case_id TEXT NOT NULL,
    model_risk_outputs JSONB,
    evidence_used JSONB,
    agent_output JSONB,
    policy_decision JSONB,
    human_action JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_case_id ON audit_logs (case_id);

-- Restricted application role. Pick your own password (use a secrets
-- manager / your host's env var UI in production — never commit a real
-- password to this file).
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'razorguard_app') THEN
        CREATE ROLE razorguard_app LOGIN PASSWORD 'CHANGE_ME_BEFORE_RUNNING';
    END IF;
END
$$;

-- The actual guarantee: this role can INSERT and SELECT, and nothing else.
-- No UPDATE, no DELETE, no DDL (can't ALTER/DROP the table), no access to
-- any other table in the database.
-- Replace <your_database_name> below with your actual database name (most
-- Postgres GRANT statements require a literal name, not a function call).
GRANT CONNECT ON DATABASE <your_database_name> TO razorguard_app;
GRANT USAGE ON SCHEMA public TO razorguard_app;
GRANT INSERT, SELECT ON audit_logs TO razorguard_app;
GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO razorguard_app;

-- Explicit revoke, belt-and-suspenders: even if a future migration script
-- accidentally does something broader (e.g. `GRANT ALL`), re-running this
-- file re-asserts the restriction.
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON audit_logs FROM razorguard_app;

-- Verify (run manually after the above, still as admin):
--   SELECT grantee, privilege_type FROM information_schema.role_table_grants
--   WHERE table_name = 'audit_logs' AND grantee = 'razorguard_app';
-- Expect exactly: INSERT, SELECT. Nothing else should appear.

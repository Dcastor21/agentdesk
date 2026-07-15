-- F02: workspaces, users, sessions with RLS
-- One transaction so tables never exist without RLS protection.
--
-- RLS discriminator: app.workspace_id (text) set per-transaction by the API
-- via set_config(). NULLIF(..., '') guards against the empty-string that
-- Postgres returns when the variable was never set in older PG versions.

BEGIN;

-- ─── workspaces ──────────────────────────────────────────────────────────────

CREATE TABLE workspaces (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspace_isolation ON workspaces
    FOR ALL
    USING      (id = NULLIF(current_setting('app.workspace_id', true), '')::uuid)
    WITH CHECK (id = NULLIF(current_setting('app.workspace_id', true), '')::uuid);

-- ─── users ────────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id  UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    clerk_user_id TEXT        NOT NULL UNIQUE,
    email         TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspace_isolation ON users
    FOR ALL
    USING      (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid)
    WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid);

-- ─── sessions ─────────────────────────────────────────────────────────────────

CREATE TABLE sessions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic        TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspace_isolation ON sessions
    FOR ALL
    USING      (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid)
    WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid);

-- Grant DML to authenticated (Supabase's non-superuser role for JWT-verified
-- requests). The postgres role is a superuser and bypasses RLS; all app and
-- test queries must run as authenticated for policies to be enforced.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON workspaces, users, sessions
    TO authenticated;

COMMIT;

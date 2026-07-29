BEGIN;

SELECT pg_advisory_xact_lock(
    hashtextextended('open-dataops-platform:security-schema:v1', 0)
);

CREATE SCHEMA IF NOT EXISTS security;

CREATE TABLE IF NOT EXISTS security.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ,
    CONSTRAINT users_username_lowercase_check
        CHECK (username = lower(username)),
    CONSTRAINT users_username_format_check
        CHECK (username ~ '^[a-z0-9][a-z0-9._-]{2,63}$'),
    CONSTRAINT users_password_hash_nonblank_check
        CHECK (length(btrim(password_hash)) > 0),
    CONSTRAINT users_updated_at_check
        CHECK (updated_at >= created_at)
);

CREATE TABLE IF NOT EXISTS security.roles (
    role_id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT roles_name_nonblank_check
        CHECK (length(btrim(name)) > 0),
    CONSTRAINT roles_description_nonblank_check
        CHECK (length(btrim(description)) > 0)
);

CREATE TABLE IF NOT EXISTS security.user_roles (
    user_id UUID NOT NULL
        REFERENCES security.users (user_id) ON DELETE CASCADE,
    role_id SMALLINT NOT NULL
        REFERENCES security.roles (role_id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX IF NOT EXISTS user_roles_role_user_idx
    ON security.user_roles (role_id, user_id);

INSERT INTO security.roles (name, description)
VALUES
    ('Admin', 'Full platform administration'),
    ('Operator', 'Operational platform access'),
    ('ReadOnly', 'Read-only platform metadata access')
ON CONFLICT (name) DO UPDATE
SET description = EXCLUDED.description;

COMMIT;

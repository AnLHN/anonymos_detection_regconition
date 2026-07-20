import os

import psycopg

DSN = os.getenv("POSTGRES_DSN", "host=localhost port=7001 dbname=face_db user=face_user password=face_password")
ADMIN_SUPER_PASSWORD = os.getenv("ADMIN_SUPER_PASSWORD", "ntc123!@#")

SQL = """
CREATE TABLE IF NOT EXISTS employees (
    id BIGSERIAL PRIMARY KEY,
    emp_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT '',
    photo_path TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS camera_sources (
    id BIGSERIAL PRIMARY KEY,
    camera_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'rtsp',
    source_url TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id BIGSERIAL PRIMARY KEY,
    rule_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    warning_level TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS unknown_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    camera_id TEXT NOT NULL,
    track_id INTEGER,
    zone TEXT NOT NULL DEFAULT 'none',
    status TEXT NOT NULL,
    label TEXT NOT NULL,
    score DOUBLE PRECISION,
    warning_type TEXT NOT NULL,
    warning_level TEXT NOT NULL,
    reason TEXT NOT NULL,
    rule_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    recognition_threshold DOUBLE PRECISION,
    detection_threshold DOUBLE PRECISION,
    bbox JSONB NOT NULL,
    best_match JSONB,
    snapshot_full TEXT NOT NULL,
    snapshot_face TEXT,
    review_status TEXT NOT NULL DEFAULT 'new',
    reviewed_at TIMESTAMP,
    reviewed_by TEXT,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGSERIAL PRIMARY KEY,
    camera_id TEXT,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS camera_worker_status (
    camera_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    read_fps DOUBLE PRECISION NOT NULL DEFAULT 0,
    camera_fps DOUBLE PRECISION NOT NULL DEFAULT 0,
    ai_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
    last_error TEXT,
    last_seen_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    before_data JSONB,
    after_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_login_events (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT true,
    ip_address TEXT,
    user_agent TEXT,
    device_os TEXT,
    browser TEXT,
    location TEXT,
    isp TEXT,
    is_vpn BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_employees_emp_code ON employees (emp_code);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees (department);
CREATE INDEX IF NOT EXISTS idx_unknown_events_created_at ON unknown_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_unknown_events_camera_id ON unknown_events (camera_id);
CREATE INDEX IF NOT EXISTS idx_unknown_events_warning_level ON unknown_events (warning_level);
CREATE INDEX IF NOT EXISTS idx_unknown_events_review_status ON unknown_events (review_status);
CREATE INDEX IF NOT EXISTS idx_system_metrics_camera_created ON system_metrics (camera_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_camera_worker_status_seen ON camera_worker_status (last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_created ON audit_logs (actor, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_login_events_user_created ON user_login_events (username, created_at DESC);

ALTER TABLE unknown_events
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS deleted_by TEXT,
    ADD COLUMN IF NOT EXISTS delete_reason TEXT,
    ADD COLUMN IF NOT EXISTS is_editable BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS edit_unlocked_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS edit_unlocked_by TEXT,
    ADD COLUMN IF NOT EXISTS edit_lock_reason TEXT;
CREATE INDEX IF NOT EXISTS idx_unknown_events_deleted_at ON unknown_events (deleted_at);

ALTER TABLE unknown_events
    ADD COLUMN IF NOT EXISTS rule_config JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE unknown_events
    ADD COLUMN IF NOT EXISTS recognition_threshold DOUBLE PRECISION;
ALTER TABLE unknown_events
    ADD COLUMN IF NOT EXISTS detection_threshold DOUBLE PRECISION;

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT now();

ALTER TABLE accounts
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS role SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT now();

UPDATE accounts
SET role = 0
WHERE role IS NULL;

DELETE FROM accounts older
USING accounts newer
WHERE older.username = newer.username
  AND older.ctid < newer.ctid;

CREATE SEQUENCE IF NOT EXISTS accounts_id_seq;
SELECT setval('accounts_id_seq', COALESCE((SELECT MAX(id) FROM accounts), 0) + 1, false);
ALTER TABLE accounts
    ALTER COLUMN id SET DEFAULT nextval('accounts_id_seq'),
    ALTER COLUMN role SET DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_username_unique
ON accounts (username);

CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_email_unique
ON accounts (email)
WHERE email IS NOT NULL;

DELETE FROM camera_sources
WHERE source_type <> 'rtsp'
   OR source_url !~* '^rtsps?://';

ALTER TABLE camera_sources
    DROP CONSTRAINT IF EXISTS camera_sources_rtsp_only;
ALTER TABLE camera_sources
    ADD CONSTRAINT camera_sources_rtsp_only
    CHECK (source_type = 'rtsp' AND source_url ~* '^rtsps?://');

INSERT INTO alert_rules (rule_code, name, warning_level, config)
VALUES
    ('stable_unknown_face', 'Stable unknown face', 'low', '{"stable_seconds": 1.5, "legacy_stable_frames": 12, "cooldown_seconds": 300}'::jsonb),
    ('unknown_outside_working_hours', 'Unknown outside working hours', 'high', '{"start": "08:00", "end": "17:30", "cooldown_seconds": 180}'::jsonb),
    ('unknown_loitering_at_gate', 'Unknown loitering at gate', 'medium', '{"gate_zones": ["gate"], "frames": 12, "cooldown_seconds": 180}'::jsonb),
    ('unknown_entered_restricted_area', 'Unknown entered restricted area', 'critical', '{"restricted_zones": ["restricted_area", "server_room", "warehouse"], "cooldown_seconds": 60}'::jsonb),
    ('unverified_in_restricted_area', 'Unverified in restricted area', 'medium', '{"restricted_zones": ["restricted_area", "server_room", "warehouse"], "cooldown_seconds": 180}'::jsonb)
ON CONFLICT (rule_code) DO UPDATE
SET name = EXCLUDED.name,
    warning_level = EXCLUDED.warning_level,
    config = alert_rules.config || EXCLUDED.config,
    updated_at = now();
"""

ADMIN_SUPER_SQL = """
INSERT INTO accounts (username, email, password_hash, role, is_active)
VALUES ('admin_super', 'admin_super@example.local', %(admin_super_password)s, 9, true)
ON CONFLICT (username) DO UPDATE
SET role = 9,
    is_active = true,
    password_hash = EXCLUDED.password_hash,
                                                                                                                                                                                                                                                                                                                                                                    updated_at = now();
"""


def main() -> None:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            cur.execute(ADMIN_SUPER_SQL, {"admin_super_password": ADMIN_SUPER_PASSWORD})
        conn.commit()
    print("Initialized production event schema.")


if __name__ == "__main__":
    main()

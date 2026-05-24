import psycopg

DSN = "host=localhost port=7001 dbname=face_db user=face_user password=face_password"

SQL = """
CREATE TABLE IF NOT EXISTS camera_sources (
    id BIGSERIAL PRIMARY KEY,
    camera_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'webcam',
    source_url TEXT NOT NULL DEFAULT '0',
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

CREATE INDEX IF NOT EXISTS idx_unknown_events_created_at ON unknown_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_unknown_events_camera_id ON unknown_events (camera_id);
CREATE INDEX IF NOT EXISTS idx_unknown_events_warning_level ON unknown_events (warning_level);
CREATE INDEX IF NOT EXISTS idx_unknown_events_review_status ON unknown_events (review_status);
CREATE INDEX IF NOT EXISTS idx_system_metrics_camera_created ON system_metrics (camera_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_created ON audit_logs (actor, created_at DESC);

INSERT INTO camera_sources (camera_id, name, source_type, source_url, location, config)
VALUES ('webcam_0', 'Local Webcam 0', 'webcam', '0', 'local', '{"frame_skip": 10, "process_width": 480}'::jsonb)
ON CONFLICT (camera_id) DO NOTHING;

INSERT INTO alert_rules (rule_code, name, warning_level, config)
VALUES
    ('stable_unknown_face', 'Stable unknown face', 'low', '{"stable_frames": 5}'::jsonb),
    ('unknown_outside_working_hours', 'Unknown outside working hours', 'high', '{"start": "08:00", "end": "17:30"}'::jsonb),
    ('unknown_loitering_at_gate', 'Unknown loitering at gate', 'medium', '{"frames": 8}'::jsonb),
    ('unknown_entered_restricted_area', 'Unknown entered restricted area', 'critical', '{}'::jsonb),
    ('unverified_in_restricted_area', 'Unverified in restricted area', 'medium', '{}'::jsonb)
ON CONFLICT (rule_code) DO NOTHING;
"""


def main() -> None:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
    print("Initialized production event schema.")


if __name__ == "__main__":
    main()

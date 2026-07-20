export type Health = {
  status: string;
  postgres: boolean;
  qdrant: boolean;
  redis?: boolean;
  workers?: { running: number; total: number };
};

export type SystemAnalytics = {
  updated_at: string;
  prometheus: { connected: boolean; url: string };
  summary: {
    alerts: number;
    api_requests_per_second: number;
    cameras: number;
    users: number;
  };
  services: { name: string; status: 'ok' | 'warning' | 'error' | 'hidden' | string }[];
  resources: {
    cpu_percent: number;
    ram_percent: number;
    disk_percent: number;
    linux_metrics_enabled: boolean;
    source?: 'prometheus' | 'native' | 'none' | string;
  };
  throughput: {
    backend_rps: number;
    error_5xx_rps: number;
    auth_failed_rps: number;
  };
  storage: {
    qdrant_vectors: number;
    postgres_connections: number;
    redis_memory_bytes: number;
    employee_vectors: number;
  };
  security: {
    risk_level: 'ok' | 'warning' | 'critical' | string;
    ddos_score: number;
    signals: { code: string; value: number; status: 'ok' | 'warning' | 'critical' | 'unknown' | string; message: string }[];
    recent_audit: { actor: string; action: string; entity_type: string; entity_id: string; created_at: string | null }[];
  };
};

export type Alert = {
  event_id: string;
  camera_id: string;
  track_id: number | null;
  zone: string;
  status: string;
  label: string;
  score: number | null;
  reason?: string;
  warning_type: string;
  warning_level: string;
  rule_config?: Record<string, unknown>;
  recognition_threshold?: number | null;
  detection_threshold?: number | null;
  review_status: string;
  snapshot_full: string;
  snapshot_face: string | null;
  created_at: string;
  note?: string | null;
  is_editable?: boolean;
  deleted_at?: string | null;
  deleted_by?: string | null;
  delete_reason?: string | null;
};

export type Camera = {
  camera_id: string;
  name: string;
  source_type: string;
  source_url: string;
  location: string;
  is_active: boolean;
  config: Record<string, unknown>;
  worker_status?: string | null;
  read_fps?: number | null;
  camera_fps?: number | null;
  ai_latency_ms?: number | null;
  last_error?: string | null;
  last_seen_at?: string | null;
};

export type CameraRuntime = {
  camera_id: string;
  name?: string | null;
  location?: string | null;
  worker_status?: string | null;
  read_fps: number;
  camera_fps: number;
  ai_latency_ms: number;
  model_fps: number;
  ai_update_fps?: number;
  stream_fps?: number;
  model_latency_fps?: number;
  frame_id?: number | null;
  source_width?: number | null;
  source_height?: number | null;
  tracks_count: number;
  tracks?: CameraRuntimeTrack[];
  zones?: CameraZones;
  meta_age_seconds?: number | null;
  updated_at?: string | null;
  is_realtime: boolean;
  last_error?: string | null;
};

export type CameraRuntimeTrack = {
  track_id: number | string | null;
  label: string;
  status: 'known' | 'unknown' | 'unverified' | string;
  identity_status?: 'tracking' | 'known' | 'unknown' | 'unverified' | string;
  score: number | null;
  bbox: number[];
  zone: string;
  unknown_alert_sent?: boolean;
  unknown_alert_event_id?: string | null;
};

export type ZonePoint = [number, number];

export type CameraZones = Record<string, ZonePoint[]>;

export type Rule = {
  rule_code: string;
  name: string;
  warning_level: string;
  is_enabled: boolean;
  config: Record<string, unknown>;
};

export type Employee = {
  id: number;
  emp_code: string;
  name: string;
  department: string;
  photo_path: string;
  is_active: boolean;
};

export type EmployeeEnrollPayload = {
  emp_code: string;
  name: string;
  department: string;
  camera_id: string;
};

export type CameraPayload = {
  camera_id: string;
  name: string;
  source_type: string;
  source_url: string;
  location: string;
  is_active: boolean;
  config: Record<string, unknown>;
};

export type CurrentUser = {
  username: string;
  role: number;
  role_name: string;
  permissions: string[];
};

export type UserAccount = CurrentUser & {
  email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type UserLoginEvent = {
  id: number;
  action: string;
  success: boolean;
  ip_address: string | null;
  user_agent: string | null;
  device_os: string | null;
  browser: string | null;
  location: string | null;
  isp: string | null;
  is_vpn: boolean | null;
  created_at: string;
};

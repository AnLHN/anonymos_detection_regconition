import { clearToken } from './auth';
import { API_BASE } from './config';
import type { Alert, Camera, CameraPayload, CameraRuntime, CameraZones, CurrentUser, Employee, EmployeeEnrollPayload, Health, Rule, SystemAnalytics, UserAccount, UserLoginEvent } from './types';

const REQUEST_TIMEOUT_MS = 10000;

export type AlertFilters = {
  limit?: number;
  offset?: number;
  camera_id?: string;
  review_status?: string;
  warning_level?: string;
  warning_type?: string;
  zone?: string;
  created_from?: string;
  created_to?: string;
  q?: string;
  include_deleted?: boolean;
};

export class AuthExpiredError extends Error {}

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, path: string, detail?: string) {
    super(detail || `API lỗi: ${path}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function responseDetail(response: Response): Promise<string | undefined> {
  try {
    const data = await response.json();
    if (typeof data?.detail === 'string') return data.detail;
  } catch {
    return undefined;
  }
  return undefined;
}

async function request<T>(path: string, token?: string | null, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: options.signal || controller.signal,
      headers: {
        ...(options.headers || {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`API timeout: ${path}`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
  if ((response.status === 401 || response.status === 403) && token) {
    clearToken();
    const detail = await responseDetail(response);
    throw new AuthExpiredError(detail || 'Phiên đăng nhập hết hạn');
  }
  if (!response.ok) throw new ApiError(response.status, path, await responseDetail(response));
  return response.json();
}

export async function login(username: string, password: string) {
  return request<{ access_token: string; token_type: string }>('/auth/login', null, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
}

export async function register(username: string, email: string, password: string) {
  return request<{ access_token: string; token_type: string }>('/auth/register', null, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });
}

export function getHealth(token: string) {
  return request<Health>('/system/health', token);
}

export function getSystemAnalytics(token: string) {
  return request<SystemAnalytics>('/system/analytics', token);
}

export function getMe(token: string) {
  return request<CurrentUser>('/auth/me', token);
}

export function logout(token: string) {
  return request<{ status: string }>('/auth/logout', token, { method: 'POST' });
}

export function getAlerts(token: string, filters: AlertFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return request<Alert[]>(`/alerts${query ? `?${query}` : ''}`, token);
}

export function getAlert(token: string, eventId: string) {
  return request<Alert>(`/alerts/${encodeURIComponent(eventId)}`, token);
}

export function updateAlertStatus(token: string, eventId: string, reviewStatus: string, note: string) {
  const params = new URLSearchParams({ review_status: reviewStatus, note });
  return request<Alert>(`/alerts/${encodeURIComponent(eventId)}/status?${params.toString()}`, token, { method: 'PATCH' });
}

export function deleteAlert(token: string, eventId: string, deleteReason?: string) {
  const body = deleteReason?.trim() ? { delete_reason: deleteReason.trim() } : {};
  return request<{ status: string }>(`/alerts/${encodeURIComponent(eventId)}`, token, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export function deleteAlertsBulk(token: string, eventIds: string[], deleteReason?: string) {
  const body = deleteReason?.trim() ? { event_ids: eventIds, delete_reason: deleteReason.trim() } : { event_ids: eventIds };
  return request<{ status: string; deleted: number }>('/alerts', token, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export function restoreAlert(token: string, eventId: string, reason: string) {
  return request<Alert>(`/alerts/${encodeURIComponent(eventId)}/restore`, token, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
}

export function setAlertEditLock(token: string, eventId: string, isEditable: boolean, reason: string) {
  return request<Alert>(`/alerts/${encodeURIComponent(eventId)}/edit-lock`, token, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_editable: isEditable, reason }),
  });
}

export function repairAlert(token: string, eventId: string, payload: Partial<Pick<Alert, 'camera_id' | 'zone' | 'warning_type' | 'warning_level' | 'review_status' | 'note' | 'reason'>>) {
  return request<Alert>(`/alerts/${encodeURIComponent(eventId)}`, token, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function getCameras(token: string) {
  return request<Camera[]>('/cameras', token);
}

export function getCameraRuntime(token: string) {
  return request<CameraRuntime[]>('/cameras/runtime', token);
}

export function getCameraMeta(token: string, cameraId: string) {
  return request<CameraRuntime>(`/cameras/${encodeURIComponent(cameraId)}/meta`, token);
}

export function getCameraZones(token: string, cameraId: string) {
  return request<CameraZones>(`/cameras/${encodeURIComponent(cameraId)}/zones`, token);
}

export function updateCameraZones(token: string, cameraId: string, zones: CameraZones) {
  return request<{ camera_id: string; zones: CameraZones }>(`/cameras/${encodeURIComponent(cameraId)}/zones`, token, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zones }),
  });
}


export function saveCamera(token: string, payload: CameraPayload) {
  return request<{ status: string }>('/cameras', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateCamera(token: string, cameraId: string, payload: Omit<CameraPayload, 'camera_id'>) {
  return request<{ status: string }>(`/cameras/${encodeURIComponent(cameraId)}`, token, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function reloadCamera(token: string, cameraId: string) {
  return request<{ status: string; camera_fps?: number; cooldown_seconds?: number }>(`/cameras/${encodeURIComponent(cameraId)}/reload`, token, { method: 'POST' });
}

export function getRules(token: string) {
  return request<Rule[]>('/rules', token);
}

export type RulePayload = {
  rule_code: string;
  name: string;
  warning_level: string;
  is_enabled: boolean;
  config: Record<string, unknown>;
};

export function createRule(token: string, payload: RulePayload) {
  return request<{ status: string }>('/rules', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateRule(token: string, ruleCode: string, payload: { is_enabled: boolean; warning_level: string; config: Record<string, unknown> }) {
  return request<{ status: string }>(`/rules/${encodeURIComponent(ruleCode)}`, token, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function getEmployees(token: string) {
  return request<Employee[]>('/employees', token);
}

export function enrollEmployeeFromCamera(token: string, payload: EmployeeEnrollPayload) {
  return request<Employee>('/employees/enroll-from-camera', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function getUsers(token: string) {
  return request<UserAccount[]>('/users', token);
}

export function getUserLoginHistory(token: string, username: string) {
  return request<UserLoginEvent[]>(`/users/${encodeURIComponent(username)}/login-history`, token);
}

export function clearUserLoginHistory(token: string, username: string) {
  return request<{ status: string; deleted: number }>(`/users/${encodeURIComponent(username)}/login-history`, token, { method: 'DELETE' });
}

export function deleteUserLoginHistoryEvent(token: string, username: string, eventId: number) {
  return request<{ status: string; deleted: number }>(`/users/${encodeURIComponent(username)}/login-history/${encodeURIComponent(eventId)}`, token, { method: 'DELETE' });
}

export function createUser(token: string, payload: { username: string; email?: string | null; password: string; role: number; is_active: boolean }) {
  return request<{ status: string }>('/users', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateUser(token: string, username: string, payload: { email?: string | null; password?: string; role?: number; is_active?: boolean }) {
  return request<{ status: string }>(`/users/${encodeURIComponent(username)}`, token, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function deactivateUser(token: string, username: string) {
  return request<{ status: string }>(`/users/${encodeURIComponent(username)}`, token, { method: 'DELETE' });
}

export function snapshotUrl(path: string | null | undefined) {
  if (!path) return '';
  const normalized = String(path).replace(/\\/g, '/');
  const filename = normalized.split('/').filter(Boolean).at(-1);
  if (!filename) return '';
  return `${API_BASE}/snapshots/${encodeURIComponent(filename)}`;
}

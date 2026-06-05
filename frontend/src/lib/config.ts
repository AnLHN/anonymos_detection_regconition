function normalizeApiBase(value: string | undefined): string {
  if (!value) return '/api';
  if (/^[A-Za-z]:[\\/]/.test(value) || value.startsWith('file:')) return '/api';
  return value;
}

export const API_BASE = normalizeApiBase(process.env.NEXT_PUBLIC_API_BASE);
export const GRAFANA_DASHBOARD_URL = process.env.NEXT_PUBLIC_GRAFANA_DASHBOARD_URL || 'http://localhost:3001/d/unknown-detection-monitoring/unknown-detection-monitoring?kiosk';

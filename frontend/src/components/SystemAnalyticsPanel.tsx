'use client';

import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { useAdminData } from '@/components/AdminShell';
import { getSystemAnalytics } from '@/lib/api';
import { hasPermission } from '@/lib/permissions';
import type { SystemAnalytics } from '@/lib/types';

export default function SystemAnalyticsPanel() {
  const { currentUser, token } = useAdminData();
  const [analytics, setAnalytics] = useState<SystemAnalytics | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (hasPermission(currentUser, 'system:read') && token) {
      void loadAnalytics();
      const timer = window.setInterval(loadAnalytics, 5000);
      return () => window.clearInterval(timer);
    }
    return undefined;
  }, [currentUser, token]);

  async function loadAnalytics() {
    setIsLoading(true);
    setError('');
    try {
      setAnalytics(await getSystemAnalytics(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được System Analytics');
    } finally {
      setIsLoading(false);
    }
  }

  const services = (analytics?.services || []).filter((service) => service.status !== 'hidden' && service.name !== 'grafana');
  const securitySignals = analytics?.security.signals || [];
  const updatedText = analytics?.updated_at ? new Date(analytics.updated_at).toLocaleTimeString('vi-VN') : 'chưa cập nhật';
  const riskLabel = useMemo(() => riskText(analytics?.security.risk_level), [analytics?.security.risk_level]);
  const resourceStatusText = getResourceStatusText(analytics?.resources.linux_metrics_enabled, analytics?.resources.source);

  if (!hasPermission(currentUser, 'system:read')) {
    return (
      <section className="card">
        <h2>Không có quyền truy cập</h2>
        <p className="muted">Chỉ tài khoản quản trị mới xem được bảng giám sát hệ thống.</p>
      </section>
    );
  }

  return (
    <section className="native-analytics-page">
      <div className="native-analytics-header">
        <div>
          <h2>Giám sát hệ thống</h2>
          <p>Giám sát hiệu năng thiết bị và tài nguyên hệ thống theo thời gian thực.</p>
        </div>
        <div className="analytics-refresh">
          <span className={analytics?.prometheus.connected ? 'status-dot ok' : 'status-dot error'} />
          <span>Cập nhật mỗi 5s · {updatedText}</span>
          <button type="button" className="secondary" onClick={loadAnalytics} disabled={isLoading}>
            {isLoading ? 'Đang tải' : 'Refresh'}
          </button>
        </div>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="analytics-kpis">
        <AnalyticsKpi value={analytics?.summary.alerts ?? 0} label="Cảnh báo" />
        <AnalyticsKpi value={`${formatNumber(analytics?.summary.api_requests_per_second || 0)} req/s`} label="API traffic" />
        <AnalyticsKpi value={analytics?.summary.cameras ?? 0} label="Camera active" />
        <AnalyticsKpi value={analytics?.summary.users ?? 0} label="Người dùng" />
      </div>

      <div className="analytics-section-title">
        <h3>Tài nguyên hệ thống real-time native</h3>
        <span>{resourceStatusText}</span>
      </div>

      <div className="analytics-resource-grid">
        <article className="analytics-panel service-panel">
          <h3>Trạng thái dịch vụ</h3>
          <div className="service-chip-grid">
            {services.map((service) => (
              <span className={`service-chip service-${service.status}`} key={service.name}>
                <i /> {service.name}
              </span>
            ))}
          </div>
        </article>
        <GaugeCard label="CPU" value={analytics?.resources.cpu_percent || 0} tone="blue" disabled={!analytics?.resources.linux_metrics_enabled} />
        <GaugeCard label="RAM" value={analytics?.resources.ram_percent || 0} tone="violet" disabled={!analytics?.resources.linux_metrics_enabled} />
        <GaugeCard label="DISK" value={analytics?.resources.disk_percent || 0} tone="amber" disabled={!analytics?.resources.linux_metrics_enabled} />
      </div>

      <div className="analytics-grid-two">
        <article className="analytics-panel">
          <h3>Security Signals</h3>
          <p className="analytics-note">Các tín hiệu này là chỉ báo vận hành từ Prometheus/backend, không phải IDS/WAF đầy đủ. VPN/firewall chỉ chính xác khi đã nối access log Nginx/VPN gateway.</p>
          <div className={`security-risk risk-${analytics?.security.risk_level || 'unknown'}`}>
            <strong>{riskLabel}</strong>
            <span>DDoS score {formatNumber(analytics?.security.ddos_score || 0)}/100</span>
          </div>
          <div className="security-signal-list">
            {securitySignals.map((signal) => (
              <div className={`security-signal signal-${signal.status}`} key={signal.code}>
                <span>{securityText(signal.code)}</span>
                <strong>{signal.value ? formatNumber(signal.value) : statusText(signal.status)}</strong>
                <small>{signal.message}</small>
              </div>
            ))}
          </div>
        </article>

        <article className="analytics-panel">
          <h3>Lưu lượng & hiệu năng</h3>
          <div className="throughput-row">
            <MetricStrip value={`${formatNumber(analytics?.throughput.auth_failed_rps || 0)} req/s`} label="auth fail" tone="danger" />
            <MetricStrip value={`${formatNumber(analytics?.throughput.error_5xx_rps || 0)} req/s`} label="backend 5xx" tone="warning" />
            <MetricStrip value={`${formatNumber(analytics?.throughput.backend_rps || 0)} req/s`} label="backend" tone="blue" />
          </div>
          <div className="audit-list">
            <strong>Audit gần đây</strong>
            {(analytics?.security.recent_audit || []).length ? analytics?.security.recent_audit.map((item) => (
              <span key={`${item.action}-${item.entity_id}-${item.created_at}`}>
                {item.actor} · {item.action} · {item.entity_type}
              </span>
            )) : <span>Chưa có audit action gần đây</span>}
          </div>
        </article>
      </div>

      <div className="analytics-storage-grid">
        <StorageCard label="Qdrant vectors" value={formatCompact(analytics?.storage.qdrant_vectors || analytics?.storage.employee_vectors || 0)} />
        <StorageCard label="Postgres conns" value={formatNumber(analytics?.storage.postgres_connections || 0)} />
        <StorageCard label="Redis memory" value={formatBytes(analytics?.storage.redis_memory_bytes || 0)} />
        <StorageCard label="Prometheus" value={analytics?.prometheus.connected ? 'Online' : 'Offline'} />
      </div>
    </section>
  );
}

function AnalyticsKpi({ value, label }: { value: string | number; label: string }) {
  return <article className="analytics-kpi"><strong>{value}</strong><span>{label}</span></article>;
}

function GaugeCard({ label, value, tone, disabled }: { label: string; value: number; tone: string; disabled?: boolean }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <article className={`analytics-panel gauge-card gauge-${tone} ${disabled ? 'is-disabled' : ''}`}>
      <div className="gauge-ring" style={{ '--gauge': `${clamped}%` } as CSSProperties}>
        <strong>{disabled ? '--' : `${Math.round(clamped)}%`}</strong>
      </div>
      <span>{label}</span>
    </article>
  );
}

function MetricStrip({ value, label, tone }: { value: string; label: string; tone: string }) {
  return <div className={`metric-strip metric-${tone}`}><strong>{value}</strong><span>{label}</span></div>;
}

function StorageCard({ label, value }: { label: string; value: string }) {
  return <article className="storage-card"><span>{label}</span><strong>{value}</strong></article>;
}

function formatNumber(value: number) {
  return Number(value || 0).toFixed(value >= 10 ? 0 : 2);
}

function formatCompact(value: number) {
  return Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value || 0);
}

function formatBytes(value: number) {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index ? 2 : 0)} ${units[index]}`;
}

function securityText(code: string) {
  const labels: Record<string, string> = {
    failed_login: 'Đăng nhập sai',
    forbidden_access: 'Truy cập bị chặn',
    scan_404: 'Quét URL lạ',
    backend_errors: 'Lỗi backend',
    ddos_pressure: 'Áp lực DDoS',
    vpn_visibility: 'VPN / firewall',
  };
  return labels[code] || code;
}

function riskText(level?: string) {
  if (level === 'critical') return 'Rủi ro cao';
  if (level === 'warning') return 'Cần theo dõi';
  if (level === 'ok') return 'Ổn định';
  return 'Chưa đủ dữ liệu';
}

function getResourceStatusText(isEnabled?: boolean, source?: string) {
  if (!isEnabled) return 'Host metrics chưa bật';
  if (source === 'native') return 'Host metrics native';
  if (source === 'prometheus') return 'Host metrics Prometheus';
  return 'Host metrics online';
}

function statusText(status: string) {
  if (status === 'ok') return 'OK';
  if (status === 'warning') return 'Watch';
  if (status === 'critical') return 'Risk';
  return 'N/A';
}

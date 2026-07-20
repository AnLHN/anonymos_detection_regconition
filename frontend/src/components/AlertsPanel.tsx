'use client';

import { MouseEvent, useEffect, useMemo, useState } from 'react';
import { alertDetailReason, alertLevelText, alertSummary, alertTitle, translateZone, warningTypeText } from '@/lib/alertText';
import { getAlert, getAlerts, snapshotUrl, type AlertFilters } from '@/lib/api';
import DateTimeFilterInput from '@/components/DateTimeFilterInput';
import { formatDateTime, formatRelativeTime } from '@/lib/timeText';
import type { Alert } from '@/lib/types';

const DEFAULT_PAGE_SIZE = 6;
const PAGE_SIZE_OPTIONS = [6, 10, 20, 50];
const LEVEL_OPTIONS = ['low', 'medium', 'high', 'critical'];

export default function AlertsPanel({ token, alerts, onMarkRead }: { token: string; alerts: Alert[]; onRefresh: () => Promise<void>; onMarkRead: (eventId: string) => void }) {
  const [selected, setSelected] = useState<Alert | null>(null);
  const [showTech, setShowTech] = useState(false);
  const [loading, setLoading] = useState(false);
  const [filtering, setFiltering] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [filteredAlerts, setFilteredAlerts] = useState(alerts);
  const [filters, setFilters] = useState<AlertFilters>({ limit: 100 });
  const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / pageSize));
  const pageStart = (page - 1) * pageSize;
  const visibleAlerts = filteredAlerts.slice(pageStart, pageStart + pageSize);
  const criticalCount = alerts.filter((alert) => alert.warning_level === 'critical').length;
  const unresolvedCount = alerts.filter((alert) => !alert.deleted_at && alert.review_status !== 'resolved_known').length;
  const cameraCovered = uniqueOptions(alerts.map((alert) => alert.camera_id)).length;
  const cameraOptions = useMemo(() => uniqueOptions(alerts.map((alert) => alert.camera_id)), [alerts]);
  const typeOptions = useMemo(() => uniqueOptions(alerts.map((alert) => alert.warning_type)), [alerts]);
  const zoneOptions = useMemo(() => uniqueOptions(alerts.map((alert) => alert.zone).filter((zone) => zone && zone !== 'none')), [alerts]);

  useEffect(() => {
    if (hasActiveAlertFilters(filters)) {
      return;
    }
    setFilteredAlerts(alerts);
  }, [alerts, filters]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        closeDetail();
      }
    }

    if (selected || loading) {
      document.body.classList.add('modal-open');
      window.addEventListener('keydown', closeOnEscape);
    }

    return () => {
      document.body.classList.remove('modal-open');
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [selected, loading]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  async function loadDetail(eventId: string) {
    setLoading(true);
    onMarkRead(eventId);
    try {
      setSelected(await getAlert(token, eventId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được chi tiết cảnh báo');
    } finally {
      setLoading(false);
    }
  }

  function closeDetail() {
    setSelected(null);
    setLoading(false);
    setShowTech(false);
  }

  function closeFromBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) {
      closeDetail();
    }
  }

  async function applyFilters(nextFilters = filters) {
    setFiltering(true);
    setError('');
    try {
      const data = await getAlerts(token, { ...nextFilters, limit: 100, offset: 0 });
      setFilteredAlerts(data);
      setPage(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không lọc được cảnh báo');
    } finally {
      setFiltering(false);
    }
  }

  function updateFilter(key: keyof AlertFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value || undefined }));
  }

  function resetFilters() {
    const nextFilters: AlertFilters = { limit: 100 };
    setFilters(nextFilters);
    void applyFilters(nextFilters);
  }

  function updatePageSize(value: string) {
    setPageSize(Number(value) || DEFAULT_PAGE_SIZE);
    setPage(1);
  }

  return (
    <>
      <article className="card">
        <div className="alert-list-heading">
          <div>
            <h2>Lịch sử cảnh báo</h2>
          </div>
          <span>{unresolvedCount} chưa xử lý · {criticalCount} critical · {cameraCovered} camera</span>
        </div>
        <div className="filter-bar alert-filter-bar">
          <label className="filter-search">
            Tìm kiếm
            <input value={filters.q || ''} onChange={(event) => updateFilter('q', event.target.value)} placeholder="Tên, camera, lý do..." />
          </label>
          <label>
            Camera
            <select value={filters.camera_id || ''} onChange={(event) => updateFilter('camera_id', event.target.value)}>
              <option value="">Tất cả camera</option>
              {cameraOptions.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label>
            Mức độ
            <select value={filters.warning_level || ''} onChange={(event) => updateFilter('warning_level', event.target.value)}>
              <option value="">Tất cả mức độ</option>
              {LEVEL_OPTIONS.map((value) => <option key={value} value={value}>{alertLevelText(value)}</option>)}
            </select>
          </label>
          <label>
            Loại cảnh báo
            <select value={filters.warning_type || ''} onChange={(event) => updateFilter('warning_type', event.target.value)}>
              <option value="">Tất cả loại</option>
              {typeOptions.map((value) => <option key={value} value={value}>{warningTypeText(value)}</option>)}
            </select>
          </label>
          <label>
            Khu vực
            <select value={filters.zone || ''} onChange={(event) => updateFilter('zone', event.target.value)}>
              <option value="">Tất cả khu vực</option>
              {zoneOptions.map((value) => <option key={value} value={value}>{translateZone(value)}</option>)}
            </select>
          </label>
          <div className="filter-break" />
          <label className="filter-date-field">
            Từ ngày
            <DateTimeFilterInput boundary="start" value={filters.created_from || ''} onChange={(value) => updateFilter('created_from', value)} />
          </label>
          <label className="filter-date-field">
            Đến ngày
            <DateTimeFilterInput boundary="end" value={filters.created_to || ''} onChange={(value) => updateFilter('created_to', value)} />
          </label>
          <label className="filter-page-size">
            Số dòng/trang
            <select value={pageSize} onChange={(event) => updatePageSize(event.target.value)}>
              {PAGE_SIZE_OPTIONS.map((value) => <option key={value} value={value}>{value} dòng</option>)}
            </select>
          </label>
          <div className="filter-actions alert-filter-actions">
            <button type="button" onClick={() => applyFilters()} disabled={filtering}>{filtering ? 'Đang lọc...' : 'Áp dụng'}</button>
            <button type="button" className="secondary" onClick={resetFilters}>Xóa lọc</button>
          </div>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <div className="list alert-page-list">
          {filteredAlerts.length ? visibleAlerts.map((alert) => (
            <div className={`item alert-row alert-row-horizontal ${alert.deleted_at ? 'is-deleted' : ''}`} key={alert.event_id}>
              <div className="alert-row-left">
                <span className={`badge alert-badge level-${alert.warning_level}`}>
                  {alertLevelText(alert.warning_level)}
                </span>
                <span className="alert-row-type">
                  {alert.warning_type ? warningTypeText(alert.warning_type).toUpperCase() : 'CẢNH BÁO KHÁC'}
                </span>
              </div>
              <div className="alert-row-center">
                <strong className="alert-row-title">{alertTitle(alert)}</strong>
                <span className="alert-row-meta">
                  Camera: <strong>{alert.camera_id}</strong>
                  {alert.zone && alert.zone !== 'none' && (
                    <> · Vùng: <strong>{translateZone(alert.zone)}</strong></>
                  )}
                  {alert.deleted_at && <span className="badge danger-badge" style={{ marginLeft: 8 }}>Đã xóa</span>}
                </span>
              </div>
              <div className="alert-row-right">
                <span className="alert-row-time" title={formatDateTime(alert.created_at)}>
                  {formatRelativeTime(alert.created_at)}
                </span>
                <button className="button secondary alert-row-action" type="button" onClick={() => loadDetail(alert.event_id)}>
                  Chi tiết
                </button>
              </div>
            </div>
          )) : <div className="item"><strong>Chưa có cảnh báo</strong><span>Không có cảnh báo phù hợp với bộ lọc hiện tại</span></div>}
        </div>
        {filteredAlerts.length > pageSize ? (
          <div className="alerts-pagination">
            <button type="button" className="secondary" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}>
              Trước
            </button>
            <span>Trang {page} / {totalPages}</span>
            <button type="button" className="secondary" onClick={() => setPage((value) => Math.min(totalPages, value + 1))} disabled={page >= totalPages}>
              Sau
            </button>
          </div>
        ) : null}
      </article>
      {(loading || selected) ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={closeFromBackdrop}>
          <section className="alert-modal" role="dialog" aria-modal="true" aria-labelledby="alert-detail-title">
            <div className="modal-header">
              <div>
                <span className="modal-kicker">Chi tiết cảnh báo</span>
                <h2 id="alert-detail-title">{selected ? alertTitle(selected) : 'Đang tải cảnh báo...'}</h2>
              </div>
              <button type="button" className="modal-close" aria-label="Đóng chi tiết cảnh báo" onClick={closeDetail}>×</button>
            </div>
            {loading ? <div className="detail-empty">Đang tải chi tiết...</div> : selected ? (
              <div className="modal-body">
                <div className="alert-summary-panel">
                  <div>
                    <span className={`badge alert-badge level-${selected.warning_level}`}>{alertLevelText(selected.warning_level)}</span>
                    {selected.deleted_at ? <span className="badge danger-badge">Đã xóa</span> : null}
                  </div>
                  <p>{alertDetailReason(selected)}</p>
                </div>

                <div className="detail-grid detail-grid-priority">
                  <Detail label="Camera" value={selected.camera_id} />
                  <Detail label="Thời gian" value={`${formatRelativeTime(selected.created_at)} · ${formatDateTime(selected.created_at)}`} />
                  <Detail label="Khu vực" value={selected.zone === 'none' ? 'Không xác định' : selected.zone} />
                  <Detail label="Đối tượng" value={selected.label} />
                </div>

                <div className="snapshots">
                  <Snapshot label="Full frame" path={selected.snapshot_full} />
                </div>

                <details
                  className={`technical-details ${showTech ? 'is-open' : ''}`}
                  open={showTech}
                  onToggle={(e) => setShowTech(e.currentTarget.open)}
                >
                  <summary className="technical-details-summary">
                    <span>Thông tin kỹ thuật</span>
                    <span className="arrow">{showTech ? '▲' : '▼'}</span>
                  </summary>
                  <div className="detail-grid">
                    <Detail label="Event ID" value={selected.event_id} />
                    <Detail label="Track" value={selected.track_id ?? ''} />
                    <Detail label="Độ khớp" value={selected.score ?? ''} />
                    <Detail label="Ngưỡng nhận diện" value={selected.recognition_threshold ?? ''} />
                    <Detail label="Ngưỡng detect mặt" value={selected.detection_threshold ?? ''} />
                    <Detail label="Config rule" value={JSON.stringify(selected.rule_config || {})} />
                  </div>
                </details>
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
    </>
  );
}

function Detail({ label, value }: { label: string; value: string | number }) {
  return <div><span>{label}</span><strong>{String(value)}</strong></div>;
}

function Snapshot({ label, path }: { label: string; path?: string | null }) {
  if (!path) return null;
  return <figure><figcaption>{label}</figcaption><img src={snapshotUrl(path)} alt={label} /></figure>;
}

function uniqueOptions(values: string[]) {
  return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

function hasActiveAlertFilters(filters: AlertFilters) {
  return Boolean(
    filters.camera_id
    || filters.review_status
    || filters.warning_level
    || filters.warning_type
    || filters.zone
    || filters.created_from
    || filters.created_to
    || filters.q,
  );
}

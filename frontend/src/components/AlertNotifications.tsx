'use client';

import { MouseEvent, useEffect, useMemo, useState } from 'react';
import { alertDetailReason, alertLevelText, alertSummary, alertTitle } from '@/lib/alertText';
import { snapshotUrl } from '@/lib/api';
import { formatDateTime, formatRelativeTime } from '@/lib/timeText';
import type { Alert } from '@/lib/types';

const MAX_VISIBLE_POPUPS = 3;

export default function AlertNotifications({
  alerts,
  readIds,
  enabled,
  onMarkRead,
  onMarkAllRead,
}: {
  alerts: Alert[];
  readIds: string[];
  enabled: boolean;
  onMarkRead: (eventId: string) => void;
  onMarkAllRead: (eventIds: string[]) => void;
}) {
  const activeAlerts = useMemo(() => alerts.filter((alert) => !alert.deleted_at), [alerts]);
  const readIdSet = useMemo(() => new Set(readIds), [readIds]);
  const [selected, setSelected] = useState<Alert | null>(null);
  const [showTech, setShowTech] = useState(false);
  const unreadAlerts = activeAlerts.filter((alert) => !readIdSet.has(alert.event_id));
  const visibleAlerts = unreadAlerts.slice(0, MAX_VISIBLE_POPUPS);
  const hiddenUnreadCount = Math.max(0, unreadAlerts.length - visibleAlerts.length);

  useEffect(() => {
    if (selected) {
      document.body.classList.add('modal-open');
    }
    return () => document.body.classList.remove('modal-open');
  }, [selected]);

  function markRead(eventId: string) {
    onMarkRead(eventId);
  }

  function openAlert(alert: Alert) {
    markRead(alert.event_id);
    setSelected(alert);
  }

  function closeAlert() {
    setSelected(null);
    setShowTech(false);
  }

  function closeFromBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) {
      closeAlert();
    }
  }

  function markAllRead() {
    onMarkAllRead(activeAlerts.map((alert) => alert.event_id));
  }

  if (!enabled) {
    return null;
  }

  return (
    <>
      {visibleAlerts.length || hiddenUnreadCount ? (
        <div className="alert-popups" aria-live="polite" aria-label="Thông báo cảnh báo">
          {unreadAlerts.length >= 2 ? (
            <div className="alert-popups-header">
              <span>Thông báo mới ({unreadAlerts.length})</span>
              <button type="button" className="alert-popups-clear-all" onClick={markAllRead}>Đóng tất cả</button>
            </div>
          ) : null}
          {visibleAlerts.map((alert) => (
            <article className={`alert-popup level-${alert.warning_level}`} key={alert.event_id}>
              <div className="alert-popup-left-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
              </div>
              <div className="alert-popup-content">
                <strong>{alertTitle(alert)}: {alertSummary(alert)}</strong>
                <small>{formatDateTime(alert.created_at)}</small>
              </div>
              <div className="alert-popup-actions">
                <button type="button" className="alert-popup-action-btn" onClick={() => markRead(alert.event_id)}>Thu gọn</button>
              </div>
            </article>
          ))}
          {hiddenUnreadCount ? (
            <article className="alert-popup level-medium alert-popup-summary">
              <div className="alert-popup-left-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
              <div className="alert-popup-content">
                <strong>Còn {hiddenUnreadCount} thông báo chưa đọc ngoài các mục ở trên</strong>
                <small>Vui lòng chuyển qua tab "Cảnh báo" để xem toàn bộ danh sách</small>
              </div>
              <div className="alert-popup-actions">
                <button type="button" className="alert-popup-action-btn" onClick={markAllRead}>Đóng tất cả</button>
              </div>
            </article>
          ) : null}
        </div>
      ) : null}

      {selected ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={closeFromBackdrop}>
          <section className="alert-modal notification-alert-modal" role="dialog" aria-modal="true" aria-labelledby="notification-alert-title">
            <div className="modal-header">
              <div>
                <span className="modal-kicker">Chi tiết cảnh báo</span>
                <h2 id="notification-alert-title">{alertTitle(selected)}</h2>
              </div>
              <button type="button" className="modal-close" aria-label="Đóng chi tiết cảnh báo" onClick={closeAlert}>×</button>
            </div>
            <div className="modal-body">
              <div className="alert-summary-panel">
                <div>
                  <span className={`badge alert-badge level-${selected.warning_level}`}>{alertLevelText(selected.warning_level)}</span>
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

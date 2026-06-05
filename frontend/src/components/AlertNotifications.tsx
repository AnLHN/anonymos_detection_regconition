'use client';

import { FormEvent, MouseEvent, useEffect, useMemo, useRef, useState } from 'react';
import { alertDetailReason, alertLevelText, alertSummary, alertTitle, reviewText } from '@/lib/alertText';
import { snapshotUrl, updateAlertStatus } from '@/lib/api';
import { formatDateTime, formatRelativeTime } from '@/lib/timeText';
import type { Alert } from '@/lib/types';

const MAX_POPUPS = 2;
const AUTO_HIDE_MS = 8000;

export default function AlertNotifications({ alerts, enabled, token, onRefresh }: { alerts: Alert[]; enabled: boolean; token: string; onRefresh: () => Promise<void> }) {
  const newestAlerts = useMemo(() => alerts.filter((alert) => !alert.deleted_at).slice(0, 20), [alerts]);
  const [dismissedIds, setDismissedIds] = useState<string[]>([]);
  const [readIds, setReadIds] = useState<string[]>([]);
  const [isCenterOpen, setIsCenterOpen] = useState(false);
  const [selected, setSelected] = useState<Alert | null>(null);
  const [reviewMessage, setReviewMessage] = useState('');
  const [error, setError] = useState('');
  const [soundEnabled, setSoundEnabled] = useState(false);
  const previousImportantIdsRef = useRef<string[]>([]);
  const unreadAlerts = newestAlerts.filter((alert) => !readIds.includes(alert.event_id));
  const importantUnreadCount = unreadAlerts.filter((alert) => isHighSeverity(alert.warning_level)).length;
  const popupCandidates = newestAlerts.filter((alert) => !dismissedIds.includes(alert.event_id));
  const visibleAlerts = enabled ? popupCandidates.slice(0, MAX_POPUPS) : [];
  const hiddenAlerts = enabled ? popupCandidates.slice(MAX_POPUPS) : [];

  useEffect(() => {
    if (!enabled) return;
    const timers = visibleAlerts
      .filter((alert) => !isHighSeverity(alert.warning_level))
      .map((alert) => window.setTimeout(() => dismiss(alert.event_id), AUTO_HIDE_MS));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [enabled, visibleAlerts.map((alert) => alert.event_id).join('|')]);

  useEffect(() => {
    if (selected) {
      document.body.classList.add('modal-open');
    }
    return () => document.body.classList.remove('modal-open');
  }, [selected]);

  useEffect(() => {
    if (!enabled || !soundEnabled) return;
    const importantIds = unreadAlerts.filter((alert) => isHighSeverity(alert.warning_level)).map((alert) => alert.event_id);
    const hasNewImportant = importantIds.some((eventId) => !previousImportantIdsRef.current.includes(eventId));
    previousImportantIdsRef.current = importantIds;
    if (hasNewImportant) {
      playNotificationTone();
    }
  }, [enabled, soundEnabled, unreadAlerts.map((alert) => alert.event_id).join('|')]);

  function dismiss(eventId: string) {
    setDismissedIds((current) => current.includes(eventId) ? current : [...current, eventId]);
  }

  function markRead(eventId: string) {
    setReadIds((current) => current.includes(eventId) ? current : [...current, eventId]);
    dismiss(eventId);
  }

  function openAlert(alert: Alert) {
    markRead(alert.event_id);
    setSelected(alert);
    setReviewMessage('');
    setError('');
  }

  function closeAlert() {
    setSelected(null);
    setReviewMessage('');
    setError('');
  }

  function closeFromBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) {
      closeAlert();
    }
  }

  function markAllRead() {
    setReadIds((current) => [...new Set([...current, ...newestAlerts.map((alert) => alert.event_id)])]);
    setDismissedIds((current) => [...new Set([...current, ...newestAlerts.map((alert) => alert.event_id)])]);
  }

  async function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const formData = new FormData(event.currentTarget);
    try {
      const updated = await updateAlertStatus(token, selected.event_id, String(formData.get('review_status') || 'new'), String(formData.get('note') || ''));
      setSelected(updated);
      setReviewMessage('Đã cập nhật trạng thái cảnh báo.');
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không cập nhật được cảnh báo');
    }
  }

  if (!enabled) {
    return null;
  }

  return (
    <>
      <div className="notification-bell-wrap">
        <button type="button" className={`notification-bell ${importantUnreadCount ? 'has-important' : ''}`} aria-label="Mở trung tâm thông báo" onClick={() => setIsCenterOpen((value) => !value)}>
          🔔
          {unreadAlerts.length ? <span className="notification-badge">{unreadAlerts.length}</span> : null}
        </button>
        {isCenterOpen ? (
          <section className="notification-center" aria-label="Trung tâm thông báo">
            <div className="notification-center-header">
              <div>
                <strong>Thông báo cảnh báo</strong>
                <span>{unreadAlerts.length} chưa đọc{importantUnreadCount ? ` · ${importantUnreadCount} quan trọng` : ''}</span>
              </div>
              <div className="notification-center-actions">
                <label className="inline-check notification-sound-toggle"><input type="checkbox" checked={soundEnabled} onChange={(event) => setSoundEnabled(event.target.checked)} /> Âm báo</label>
                <button type="button" className="secondary" onClick={markAllRead}>Đánh dấu đã xem</button>
              </div>
            </div>
            <div className="notification-list">
              {newestAlerts.length ? newestAlerts.map((alert) => (
                <article className={`notification-item ${readIds.includes(alert.event_id) ? 'is-read' : ''} ${isHighSeverity(alert.warning_level) && !readIds.includes(alert.event_id) ? 'is-important' : ''}`} key={alert.event_id}>
                  <div>
                    <strong>{alertTitle(alert)}</strong>
                    <span>{alertSummary(alert)}</span>
                    <small>{formatDateTime(alert.created_at)} · {reviewText(alert.review_status)}</small>
                  </div>
                  <div className="notification-item-actions">
                    <span className={`badge alert-badge level-${alert.warning_level}`}>{alertLevelText(alert.warning_level)}</span>
                    <button type="button" className="secondary" onClick={() => openAlert(alert)}>Xem</button>
                  </div>
                </article>
              )) : <div className="detail-empty"><strong>Chưa có thông báo</strong><span>Thông báo cảnh báo mới sẽ xuất hiện tại đây.</span></div>}
            </div>
          </section>
        ) : null}
      </div>

      {(visibleAlerts.length || hiddenAlerts.length) ? (
        <div className="alert-popups" aria-live="polite" aria-label="Thông báo cảnh báo mới">
          {visibleAlerts.map((alert) => (
            <article className={`alert-popup level-${alert.warning_level} ${isHighSeverity(alert.warning_level) ? 'requires-action' : ''}`} key={alert.event_id}>
              <div className="alert-popup-header">
                <span>{isHighSeverity(alert.warning_level) ? 'Cảnh báo quan trọng' : 'Cảnh báo mới'}</span>
                <button type="button" className="alert-popup-close" aria-label="Đóng thông báo" onClick={() => dismiss(alert.event_id)}>×</button>
              </div>
              <strong>{alertTitle(alert)}</strong>
              <p>{alertSummary(alert)}</p>
              <div className="alert-popup-meta">
                <span>{formatRelativeTime(alert.created_at)}</span>
                <span>{alertLevelText(alert.warning_level)}</span>
              </div>
              <button type="button" className="secondary alert-popup-action" onClick={() => openAlert(alert)}>
                Xem ngay
              </button>
            </article>
          ))}
          {hiddenAlerts.length > 0 ? (
            <article className="alert-popup alert-popup-summary">
              <strong>Có {hiddenAlerts.length} cảnh báo mới khác</strong>
              <p>{summarizeAlertLocations(hiddenAlerts)}</p>
              <button type="button" className="secondary alert-popup-action" onClick={() => setIsCenterOpen(true)}>Xem tất cả</button>
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
                  <span className="badge">{reviewText(selected.review_status)}</span>
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
                <Snapshot label="Face crop" path={selected.snapshot_face} />
              </div>
              <form className="review-form" onSubmit={handleReview}>
                <label>
                  Trạng thái xử lý
                  <select name="review_status" defaultValue={selected.review_status}>
                    {['new', 'reviewing', 'confirmed', 'false_positive', 'ignored'].map((value) => <option key={value} value={value}>{reviewText(value)}</option>)}
                  </select>
                </label>
                <label>
                  Ghi chú xử lý
                  <textarea name="note" rows={3} defaultValue={selected.note || ''} placeholder="Ví dụ: đã kiểm tra camera, không cần xử lý thêm..." />
                </label>
                <div className="modal-actions">
                  <button type="submit">Đã xử lý / Lưu trạng thái</button>
                  <button type="button" className="secondary" onClick={() => closeAlert()}>Bỏ qua</button>
                </div>
                {reviewMessage ? <span className="success">{reviewMessage}</span> : null}
                {error ? <span className="error">{error}</span> : null}
              </form>
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

function playNotificationTone() {
  try {
    const AudioContextClass = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) return;
    const context = new AudioContextClass();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = 880;
    oscillator.type = 'sine';
    gain.gain.value = 0.04;
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    window.setTimeout(() => {
      oscillator.stop();
      void context.close();
    }, 180);
  } catch {
    // Browser audio policies may block sound until the user interacts.
  }
}

function isHighSeverity(level: string) {
  return level === 'high' || level === 'critical';
}

function summarizeAlertLocations(alerts: Alert[]) {
  const cameras = [...new Set(alerts.map((alert) => alert.camera_id).filter(Boolean))].slice(0, 3);
  if (!cameras.length) return 'Được gom lại để tránh tràn màn hình.';
  return cameras.join(', ');
}

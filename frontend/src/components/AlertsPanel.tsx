'use client';

import { FormEvent, MouseEvent, useEffect, useMemo, useState } from 'react';
import { alertDetailReason, alertLevelText, alertSummary, alertTitle, reviewText } from '@/lib/alertText';
import { deleteAlert, deleteAlertsBulk, getAlert, getAlerts, snapshotUrl, updateAlertStatus, type AlertFilters } from '@/lib/api';
import { formatDateTime, formatRelativeTime } from '@/lib/timeText';
import type { Alert } from '@/lib/types';

const DEFAULT_PAGE_SIZE = 6;
const PAGE_SIZE_OPTIONS = [6, 10, 20, 50];
const REVIEW_OPTIONS = ['new', 'reviewing', 'confirmed', 'false_positive', 'ignored'];
const LEVEL_OPTIONS = ['low', 'medium', 'high', 'critical'];

type DeleteTarget =
  | { type: 'single'; alert: Alert }
  | { type: 'bulk'; eventIds: string[] };

export default function AlertsPanel({ token, alerts, onRefresh, isSuperAdmin = false }: { token: string; alerts: Alert[]; onRefresh: () => Promise<void>; isSuperAdmin?: boolean }) {
  const [selected, setSelected] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(false);
  const [filtering, setFiltering] = useState(false);
  const [error, setError] = useState('');
  const [reviewMessage, setReviewMessage] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [selectedAlertIds, setSelectedAlertIds] = useState<string[]>([]);
  const [pendingDelete, setPendingDelete] = useState<DeleteTarget | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [managementMode, setManagementMode] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [filteredAlerts, setFilteredAlerts] = useState(alerts);
  const [filters, setFilters] = useState<AlertFilters>({ limit: 100 });
  const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / pageSize));
  const pageStart = (page - 1) * pageSize;
  const visibleAlerts = filteredAlerts.slice(pageStart, pageStart + pageSize);
  const canManageAlerts = isSuperAdmin && managementMode;
  const selectableVisibleAlerts = canManageAlerts ? visibleAlerts.filter((alert) => !alert.deleted_at) : [];
  const selectedVisibleCount = selectableVisibleAlerts.filter((alert) => selectedAlertIds.includes(alert.event_id)).length;
  const isPageSelected = selectableVisibleAlerts.length > 0 && selectedVisibleCount === selectableVisibleAlerts.length;
  const cameraOptions = useMemo(() => uniqueOptions(alerts.map((alert) => alert.camera_id)), [alerts]);
  const typeOptions = useMemo(() => uniqueOptions(alerts.map((alert) => alert.warning_type)), [alerts]);
  const zoneOptions = useMemo(() => uniqueOptions(alerts.map((alert) => alert.zone).filter((zone) => zone && zone !== 'none')), [alerts]);

  useEffect(() => {
    setFilteredAlerts(alerts);
  }, [alerts]);

  useEffect(() => {
    if (!isSuperAdmin && managementMode) {
      setManagementMode(false);
      setSelectedAlertIds([]);
    }
  }, [isSuperAdmin, managementMode]);

  useEffect(() => {
    setSelectedAlertIds((current) => current.filter((eventId) => filteredAlerts.some((alert) => alert.event_id === eventId && !alert.deleted_at)));
  }, [filteredAlerts]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        if (pendingDelete) {
          setPendingDelete(null);
          return;
        }
        closeDetail();
      }
    }

    if (selected || loading || pendingDelete) {
      document.body.classList.add('modal-open');
      window.addEventListener('keydown', closeOnEscape);
    }

    return () => {
      document.body.classList.remove('modal-open');
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [selected, loading, pendingDelete]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  async function loadDetail(eventId: string) {
    setLoading(true);
    setReviewMessage('');
    setActionMessage('');
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
    setReviewMessage('');
  }

  function closeFromBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) {
      closeDetail();
    }
  }

  async function refreshAlerts(nextFilters = filters) {
    await onRefresh();
    await applyFilters(nextFilters);
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
    setSelectedAlertIds([]);
    void applyFilters(nextFilters);
  }

  function updatePageSize(value: string) {
    setPageSize(Number(value) || DEFAULT_PAGE_SIZE);
    setPage(1);
  }

  function toggleManagementMode() {
    setManagementMode((current) => {
      const next = !current;
      if (!next) setSelectedAlertIds([]);
      setPendingDelete(null);
      setActionMessage('');
      setError('');
      return next;
    });
  }

  function updateIncludeDeleted(checked: boolean) {
    const nextFilters = { ...filters, include_deleted: checked || undefined };
    setFilters(nextFilters);
    setSelectedAlertIds([]);
    void applyFilters(nextFilters);
  }

  async function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const formData = new FormData(event.currentTarget);
    const updated = await updateAlertStatus(token, selected.event_id, String(formData.get('review_status') || 'new'), String(formData.get('note') || ''));
    setSelected(updated);
    setReviewMessage('Đã cập nhật trạng thái xử lý.');
    await onRefresh();
  }

  function toggleSelectedAlert(eventId: string, checked: boolean) {
    setSelectedAlertIds((current) => {
      if (checked) return current.includes(eventId) ? current : [...current, eventId];
      return current.filter((item) => item !== eventId);
    });
  }

  function togglePageSelection(checked: boolean) {
    const pageIds = selectableVisibleAlerts.map((alert) => alert.event_id);
    setSelectedAlertIds((current) => {
      if (!checked) return current.filter((eventId) => !pageIds.includes(eventId));
      return [...current, ...pageIds.filter((eventId) => !current.includes(eventId))];
    });
  }

  async function handleBulkDelete() {
    setError('');
    setActionMessage('');
    if (!canManageAlerts) return;
    if (!selectedAlertIds.length) {
      setError('Chọn ít nhất một cảnh báo cần xóa.');
      return;
    }
    setPendingDelete({ type: 'bulk', eventIds: [...selectedAlertIds] });
  }

  async function handleDeleteOne(alert: Alert) {
    setError('');
    setActionMessage('');
    if (!canManageAlerts || alert.deleted_at) return;
    setPendingDelete({ type: 'single', alert });
  }

  async function confirmDelete() {
    if (!pendingDelete || deleting) return;
    setDeleting(true);
    setError('');
    setActionMessage('');
    try {
      if (pendingDelete.type === 'single') {
        await deleteAlert(token, pendingDelete.alert.event_id);
        setActionMessage('Đã xóa cảnh báo.');
        setSelectedAlertIds((current) => current.filter((eventId) => eventId !== pendingDelete.alert.event_id));
        if (selected?.event_id === pendingDelete.alert.event_id) {
          setSelected(null);
        }
      } else {
        const result = await deleteAlertsBulk(token, pendingDelete.eventIds);
        setActionMessage(`Đã xóa ${result.deleted} cảnh báo.`);
        setSelectedAlertIds([]);
      }
      setPendingDelete(null);
      await refreshAlerts(filters);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không xóa được cảnh báo.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <article className="card">
        <div className="alert-list-heading">
          <div>
            <h2>Lịch sử cảnh báo</h2>
            <p>Mức độ dùng để ưu tiên xử lý cảnh báo.</p>
          </div>
          <span>{filteredAlerts.length ? `${pageStart + 1}-${Math.min(pageStart + pageSize, filteredAlerts.length)} / ${filteredAlerts.length}` : '0 / 0'}</span>
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
            Trạng thái
            <select value={filters.review_status || ''} onChange={(event) => updateFilter('review_status', event.target.value)}>
              <option value="">Tất cả trạng thái</option>
              {REVIEW_OPTIONS.map((value) => <option key={value} value={value}>{reviewText(value)}</option>)}
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
              {typeOptions.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label>
            Khu vực
            <select value={filters.zone || ''} onChange={(event) => updateFilter('zone', event.target.value)}>
              <option value="">Tất cả khu vực</option>
              {zoneOptions.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="filter-date-field">
            Từ ngày
            <input type="datetime-local" value={filters.created_from || ''} onChange={(event) => updateFilter('created_from', event.target.value)} />
          </label>
          <label className="filter-date-field">
            Đến ngày
            <input type="datetime-local" value={filters.created_to || ''} onChange={(event) => updateFilter('created_to', event.target.value)} />
          </label>
          <label className="filter-page-size">
            Số dòng/trang
            <select value={pageSize} onChange={(event) => updatePageSize(event.target.value)}>
              {PAGE_SIZE_OPTIONS.map((value) => <option key={value} value={value}>{value} dòng</option>)}
            </select>
          </label>
          {isSuperAdmin ? (
            <label className="inline-check filter-check">
              <input type="checkbox" checked={!!filters.include_deleted} onChange={(event) => updateIncludeDeleted(event.target.checked)} /> Hiện cảnh báo đã xóa
            </label>
          ) : null}
          <div className="filter-actions alert-filter-actions">
            <button type="button" onClick={() => applyFilters()} disabled={filtering}>{filtering ? 'Đang lọc...' : 'Áp dụng'}</button>
            <button type="button" className="secondary" onClick={resetFilters}>Xóa lọc</button>
            {isSuperAdmin ? (
              <button type="button" className={managementMode ? 'danger alert-management-toggle' : 'secondary alert-management-toggle'} onClick={toggleManagementMode} aria-pressed={managementMode}>
                {managementMode ? 'Đang cho phép chỉnh sửa/xóa' : 'Cho phép chỉnh sửa/xóa'}
              </button>
            ) : null}
          </div>
        </div>
        {canManageAlerts ? (
          <div className="alert-bulk-bar is-compact">
            <label className="inline-check alert-select-page">
              <input type="checkbox" checked={isPageSelected} onChange={(event) => togglePageSelection(event.target.checked)} disabled={!selectableVisibleAlerts.length} />
              Chọn trang này
            </label>
            <span>{selectedAlertIds.length} cảnh báo đã chọn</span>
            <button type="button" className="danger" onClick={handleBulkDelete} disabled={!selectedAlertIds.length}>
              Xóa cảnh báo đã chọn
            </button>
          </div>
        ) : null}
        {error ? <p className="error">{error}</p> : null}
        {actionMessage ? <p className="success">{actionMessage}</p> : null}
        <div className="list alert-page-list">
          {filteredAlerts.length ? visibleAlerts.map((alert) => (
            <div className={`item alert-row ${alert.deleted_at ? 'is-deleted' : ''} ${canManageAlerts ? 'is-managing' : ''}`} key={alert.event_id}>
              {canManageAlerts ? (
                <input
                  className="alert-row-check"
                  type="checkbox"
                  checked={selectedAlertIds.includes(alert.event_id)}
                  onChange={(event) => toggleSelectedAlert(alert.event_id, event.target.checked)}
                  disabled={!!alert.deleted_at}
                  aria-label={`Chọn ${alertTitle(alert)}`}
                />
              ) : null}
              <button className="item-button alert-row-main" type="button" onClick={() => loadDetail(alert.event_id)}>
                <strong>
                  <span>{alertTitle(alert)}</span>
                  <span className={`badge alert-badge level-${alert.warning_level}`}>{alertLevelText(alert.warning_level)}</span>
                  {alert.deleted_at ? <span className="badge danger-badge">Đã xóa</span> : null}
                </strong>
                <span>{alertSummary(alert)} · {formatRelativeTime(alert.created_at)}</span>
              </button>
              {canManageAlerts && !alert.deleted_at ? (
                <button type="button" className="alert-row-delete" onClick={() => handleDeleteOne(alert)} aria-label={`Xóa ${alertTitle(alert)}`} title="Xóa cảnh báo">
                  <TrashIcon />
                </button>
              ) : null}
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
                    <span className="badge">{reviewText(selected.review_status)}</span>
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
                  <Snapshot label="Face crop" path={selected.snapshot_face} />
                </div>

                <form className="review-form" onSubmit={handleReview}>
                  <label>
                    Trạng thái xử lý
                    <select name="review_status" defaultValue={selected.review_status}>
                      {REVIEW_OPTIONS.map((value) => <option key={value} value={value}>{reviewText(value)}</option>)}
                    </select>
                  </label>
                  <label>
                    Ghi chú xử lý
                    <textarea name="note" rows={3} defaultValue={selected.note || ''} placeholder="Ví dụ: đã kiểm tra camera, không cần xử lý thêm..." />
                  </label>
                  <div className="modal-actions">
                    <button type="submit">Cập nhật</button>
                    <button type="button" className="secondary" onClick={closeDetail}>Đóng</button>
                  </div>
                  {reviewMessage ? <span className="success">{reviewMessage}</span> : null}
                </form>

                <details className="technical-details">
                  <summary>Thông tin kỹ thuật</summary>
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
      {pendingDelete ? (
        <div className="alert-confirm-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget && !deleting) setPendingDelete(null);
        }}>
          <section className="alert-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="alert-delete-title">
            <span className="modal-kicker">Xác nhận thao tác</span>
            <h3 id="alert-delete-title">{deleteDialogTitle(pendingDelete)}</h3>
            <p>{deleteDialogDescription(pendingDelete)}</p>
            <div className="alert-confirm-actions">
              <button type="button" className="secondary" onClick={() => setPendingDelete(null)} disabled={deleting}>
                Hủy
              </button>
              <button type="button" className="danger" onClick={confirmDelete} disabled={deleting}>
                {deleting ? 'Đang xóa...' : 'Xóa'}
              </button>
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

function TrashIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
      <path d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 6h2v9h-2V9Zm4 0h2v9h-2V9ZM7 9h10l-.7 11H7.7L7 9Z" />
    </svg>
  );
}

function deleteDialogTitle(target: DeleteTarget) {
  if (target.type === 'bulk') return `Xóa ${target.eventIds.length} cảnh báo đã chọn?`;
  return 'Xóa cảnh báo này?';
}

function deleteDialogDescription(target: DeleteTarget) {
  if (target.type === 'bulk') return 'Các cảnh báo đã chọn sẽ được đưa vào trạng thái đã xóa và vẫn được lưu trong audit log.';
  return `"${alertTitle(target.alert)}" sẽ được đưa vào trạng thái đã xóa và vẫn được lưu trong audit log.`;
}

function uniqueOptions(values: string[]) {
  return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

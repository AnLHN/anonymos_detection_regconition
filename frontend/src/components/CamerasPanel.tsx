'use client';

import { FormEvent, MouseEvent, useEffect, useState } from 'react';
import { reloadCamera, saveCamera, updateCamera } from '@/lib/api';
import type { Camera } from '@/lib/types';

type CameraModalMode = 'create' | 'edit' | null;
const DEFAULT_RELOAD_COOLDOWN_SECONDS = 30;

export default function CamerasPanel({
  token,
  cameras,
  onRefresh,
  canCreate = false,
  canUpdate = false,
}: {
  token: string;
  cameras: Camera[];
  onRefresh: () => Promise<void>;
  canCreate?: boolean;
  canUpdate?: boolean;
}) {
  const [selected, setSelected] = useState<Camera | null>(null);
  const [modalMode, setModalMode] = useState<CameraModalMode>(null);
  const [saving, setSaving] = useState(false);
  const [reloadingCameraId, setReloadingCameraId] = useState('');
  const [reloadCooldownUntil, setReloadCooldownUntil] = useState<Record<string, number>>({});
  const [nowTick, setNowTick] = useState(() => Date.now());
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const modalCamera = modalMode === 'edit' ? selected : null;

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') closeModal();
    }

    if (modalMode) {
      document.body.classList.add('modal-open');
      window.addEventListener('keydown', closeOnEscape);
    }

    return () => {
      document.body.classList.remove('modal-open');
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [modalMode]);

  useEffect(() => {
    const timer = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  function openCreateModal() {
    setSelected(null);
    setModalMode('create');
    setMessage('');
    setError('');
  }

  function openEditModal(camera: Camera) {
    setSelected(camera);
    setModalMode('edit');
    setMessage('');
    setError('');
  }

  function closeModal() {
    if (saving) return;
    setModalMode(null);
    setSelected(null);
    setError('');
  }

  function closeFromBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) closeModal();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const cameraId = String(formData.get('camera_id') || '').trim();
    const sourceUrl = String(formData.get('source_url') || '').trim();

    if (!sourceUrl.toLowerCase().startsWith('rtsp://') && !sourceUrl.toLowerCase().startsWith('rtsps://')) {
      setMessage('');
      setError('Camera chỉ nhận luồng RTSP.');
      return;
    }
    if (modalMode === 'create' && !cameraId) {
      setMessage('');
      setError('Nhập mã camera trước khi lưu.');
      return;
    }

    const alwaysOn = formData.get('always_on') === 'on';
    const payload = {
      name: String(formData.get('name') || '').trim(),
      source_type: 'rtsp',
      source_url: sourceUrl,
      location: String(formData.get('location') || '').trim(),
      is_active: formData.get('is_active') === 'on',
      config: {
        ...(modalCamera?.config || {}),
        always_on: alwaysOn,
        mjpeg_idle_timeout: alwaysOn ? 0 : modalCamera?.config?.mjpeg_idle_timeout,
      },
    };

    setSaving(true);
    setMessage('');
    setError('');
    try {
      if (modalMode === 'edit' && modalCamera) {
        await updateCamera(token, modalCamera.camera_id, payload);
      } else {
        await saveCamera(token, { camera_id: cameraId, ...payload });
      }
      setMessage('Đã lưu camera. Restart worker/backend nếu luồng đang chạy vẫn dùng URL cũ.');
      setModalMode(null);
      setSelected(null);
      form.reset();
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không lưu được camera');
    } finally {
      setSaving(false);
    }
  }

  async function handleReloadCamera(camera: Camera) {
    const cooldownRemaining = getReloadCooldownRemaining(camera.camera_id);
    if (cooldownRemaining > 0) {
      setMessage('');
      setError(`Camera ${camera.name || camera.camera_id} dang trong cooldown ${cooldownRemaining}s.`);
      return;
    }
    setReloadingCameraId(camera.camera_id);
    setMessage('');
    setError('');
    try {
      const result = await reloadCamera(token, camera.camera_id);
      const cooldownSeconds = result.cooldown_seconds || DEFAULT_RELOAD_COOLDOWN_SECONDS;
      setReloadCooldownUntil((current) => ({
        ...current,
        [camera.camera_id]: Date.now() + cooldownSeconds * 1000,
      }));
      setMessage(`Đã reload camera ${camera.name || camera.camera_id}.`);
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không reload được camera');
    } finally {
      setReloadingCameraId('');
    }
  }

  function getReloadCooldownRemaining(cameraId: string) {
    return Math.max(0, Math.ceil(((reloadCooldownUntil[cameraId] || 0) - nowTick) / 1000));
  }

  function shouldShowCameraError(camera: Camera) {
    return Boolean(camera.last_error && camera.worker_status !== 'running');
  }

  return (
    <>
      <article className="card camera-management-card">
      <div className="section-heading compact-heading camera-page-heading">
        <div>
          <h2>Camera</h2>
          <p>Quản lý nguồn RTSP, tên hiển thị và trạng thái kích hoạt.</p>
        </div>
        {canCreate ? <button type="button" className="camera-add-button" onClick={openCreateModal}>
          Thêm camera
        </button> : null}
      </div>

      {message ? <p className="success">{message}</p> : null}
      {error && !modalMode ? <p className="error">{error}</p> : null}

      <div className="list camera-list">
        {cameras.length ? cameras.map((camera) => (
          <article className="item camera-list-item camera-list-row" key={camera.camera_id}>
            <button className="camera-list-main" type="button" onClick={() => canUpdate && openEditModal(camera)} disabled={!canUpdate}>
              <strong>
                <span>{camera.name}</span>
                <span className="badge">{camera.is_active ? 'Active' : 'Inactive'}</span>
                <span className="badge muted-badge">{camera.worker_status || 'Offline'}</span>
              </strong>
              <span>{camera.location || camera.camera_id}</span>
              {shouldShowCameraError(camera) ? <span className="error">{camera.last_error}</span> : null}
            </button>
            <div className="camera-actions">
              <button
                type="button"
                className="secondary camera-edit-button"
                onClick={() => openEditModal(camera)}
                disabled={!canUpdate}
              >
                Sửa
              </button>
              <button
                type="button"
                className="secondary camera-reload-button"
                onClick={() => handleReloadCamera(camera)}
                disabled={!canUpdate || !camera.is_active || reloadingCameraId === camera.camera_id || getReloadCooldownRemaining(camera.camera_id) > 0}
              >
                {reloadingCameraId === camera.camera_id ? 'Đang reload...' : 'Reload'}
              </button>
            </div>
          </article>
        )) : (
          <div className="item">
            <strong>Chưa có camera</strong>
            <span>Bấm Thêm camera để cấu hình nguồn RTSP đầu tiên.</span>
          </div>
        )}
      </div>
    </article>

      {modalMode ? (
        <div className="camera-modal-backdrop" role="presentation" onMouseDown={closeFromBackdrop}>
          <section className="camera-modal" role="dialog" aria-modal="true" aria-labelledby="camera-modal-title">
            <div className="modal-header">
              <div>
                <span className="modal-kicker">{modalMode === 'edit' ? 'Chỉnh sửa luồng' : 'Thêm luồng mới'}</span>
                <h2 id="camera-modal-title">{modalMode === 'edit' ? modalCamera?.name || 'Sửa camera' : 'Thêm camera'}</h2>
              </div>
              <button type="button" className="modal-close" aria-label="Đóng cấu hình camera" onClick={closeModal} disabled={saving}>×</button>
            </div>

            <form className="compact-form camera-form camera-modal-form" onSubmit={handleSubmit} key={modalCamera?.camera_id || 'new-camera'}>
              <div className="camera-form-grid">
                <label>
                  Mã camera
                  <input name="camera_id" placeholder="door_67b" defaultValue={modalCamera?.camera_id || ''} disabled={Boolean(modalCamera)} required />
                </label>
                <label>
                  Tên camera
                  <input name="name" placeholder="Cửa ra vào 67B" defaultValue={modalCamera?.name || ''} required />
                </label>
                <label className="camera-url-field">
                  RTSP URL
                  <input name="source_url" placeholder="rtsp://user:password@ip:554/stream" defaultValue={modalCamera?.source_url || ''} required />
                </label>
                <label>
                  Vị trí
                  <input name="location" placeholder="Sảnh chính, cổng phụ..." defaultValue={modalCamera?.location || ''} />
                </label>
              </div>
              <div className="form-footer camera-modal-footer">
                <div className="camera-modal-toggles">
                  <label className="custom-switch">
                    <input name="is_active" type="checkbox" defaultChecked={modalCamera ? modalCamera.is_active : true} />
                    <span className="switch-slider" />
                    <span>Camera đang hoạt động</span>
                  </label>
                  <label className="custom-switch">
                    <input name="always_on" type="checkbox" defaultChecked={Boolean(modalCamera?.config?.always_on)} />
                    <span className="switch-slider" />
                    <span>Luôn bật camera này</span>
                  </label>
                </div>
                <div className="form-actions">
                  <button type="submit" disabled={saving}>{saving ? 'Đang lưu...' : 'Lưu camera'}</button>
                  <button type="button" className="secondary" onClick={closeModal} disabled={saving}>Hủy</button>
                </div>
              </div>
              {error ? <p className="error">{error}</p> : null}
            </form>
          </section>
        </div>
      ) : null}
    </>
  );
}

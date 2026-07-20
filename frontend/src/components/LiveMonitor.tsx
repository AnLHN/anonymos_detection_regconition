'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { getCameraMeta, getCameraRuntime, getCameraZones, updateCameraZones } from '@/lib/api';
import { API_BASE } from '@/lib/config';
import type { Camera, CameraRuntime, CameraRuntimeTrack, CameraZones, CurrentUser, ZonePoint } from '@/lib/types';

const STREAM_WIDTH = 1280;
const STREAM_HEIGHT = 720;
const RUNTIME_POLL_INTERVAL_MS = 2000;
const OVERLAY_META_POLL_INTERVAL_MS = 350;
const MAX_STREAM_RETRIES = 3;

type LiveState = 'idle' | 'connecting' | 'running' | 'stopped' | 'error';
type DisplayMode = 'fps' | 'stream';

type StreamStats = {
  displayFps: number;
  state: LiveState;
};

export default function LiveMonitor({ token, cameras, currentUser }: { token: string; cameras: Camera[]; currentUser?: CurrentUser | null }) {
  const [displayMode, setDisplayMode] = useState<DisplayMode>('stream');
  const [cameraFilter, setCameraFilter] = useState('all');
  const [streamStats, setStreamStats] = useState<Record<string, StreamStats>>({});
  const [runtimeByCamera, setRuntimeByCamera] = useState<Record<string, CameraRuntime>>({});
  const canEditZones = Number(currentUser?.role || 0) >= 9;
  const rtspCameras = useMemo(() => cameras.filter((camera) => camera.source_type === 'rtsp' && camera.is_active), [cameras]);
  const cameraSlots = useMemo(() => rtspCameras.map((camera) => camera.camera_id), [rtspCameras]);
  const cameraSlotsKey = cameraSlots.join('|');

  useEffect(() => {
    let cancelled = false;

    async function loadRuntime() {
      try {
        const rows = await getCameraRuntime(token);
        if (!cancelled) {
          setRuntimeByCamera(Object.fromEntries(rows.map((runtime) => [runtime.camera_id, runtime])));
        }
      } catch {
        if (!cancelled) setRuntimeByCamera({});
      }
    }

    void loadRuntime();
    const timer = window.setInterval(loadRuntime, RUNTIME_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [token]);

  useEffect(() => {
    if (cameraFilter !== 'all' && !cameraSlots.includes(cameraFilter)) {
      setCameraFilter('all');
    }
  }, [cameraFilter, cameraSlots, cameraSlotsKey]);

  const visibleCameraIds = useMemo(() => (
    cameraFilter === 'all' ? cameraSlots : cameraSlots.filter((cameraId) => cameraId === cameraFilter)
  ), [cameraFilter, cameraSlots]);

  const updateTileStats = useCallback((cameraId: string, stats: StreamStats) => {
    setStreamStats((current) => ({ ...current, [cameraId]: stats }));
  }, []);

  return (
    <section className="ops-camera-center">
      <div className="ops-camera-toolbar">
        <label>
          Hiển thị
          <select value={displayMode} onChange={(event) => setDisplayMode(event.target.value as DisplayMode)}>
            <option value="fps">Chỉ FPS</option>
            <option value="stream">Stream + Detect</option>
          </select>
        </label>
        <label>
          Camera
          <select value={cameraFilter} onChange={(event) => setCameraFilter(event.target.value)}>
            <option value="all">Tất cả camera</option>
            {rtspCameras.map((camera) => (
              <option key={camera.camera_id} value={camera.camera_id}>
                {camera.name || camera.camera_id}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className={displayMode === 'fps' ? 'ops-camera-grid ops-camera-grid-fps' : 'ops-camera-grid ops-camera-grid-stream'}>
        {visibleCameraIds.map((cameraId) => {
          const camera = cameras.find((item) => item.camera_id === cameraId);
          const runtime = runtimeByCamera[cameraId];
          return displayMode === 'fps' ? (
            <CameraFpsCard key={cameraId} cameraId={cameraId} camera={camera} runtime={runtime} stats={streamStats[cameraId]} />
          ) : (
            <CameraStreamTile
              key={cameraId}
              token={token}
              cameraId={cameraId}
              camera={camera}
              runtime={runtime}
              onStats={updateTileStats}
              canEditZones={canEditZones}
            />
          );
        })}
        {!visibleCameraIds.length ? (
          <article className="ops-camera-empty">
            <strong>Không có camera phù hợp</strong>
            <span>Thử đổi chế độ xem hoặc kiểm tra lại worker camera.</span>
          </article>
        ) : null}
      </div>
    </section>
  );
}

function CameraFpsCard({ cameraId, camera, runtime, stats }: { cameraId: string; camera?: Camera; runtime?: CameraRuntime; stats?: StreamStats }) {
  const fps = getCameraFps(camera, runtime, stats);
  return (
    <article className="ops-camera-fps-card">
      <header>
        <div>
          <strong>{camera?.name || runtime?.name || cameraId}</strong>
          <span>{camera?.location || runtime?.location || cameraId}</span>
        </div>
        <StatusChip camera={camera} runtime={runtime} stats={stats} />
      </header>
      <p>RTSP {fps.rtsp} | Resize {fps.resize} | Model {fps.model}</p>
      <div className="ops-fps-triplet">
        <FpsPill label="RTSP" value={fps.rtsp} />
        <FpsPill label="Resize" value={fps.resize} />
        <FpsPill label="Model" value={fps.model} />
      </div>
      <footer>
        <span>Nhận diện thời gian thực</span>
        <strong>{detectionSummary(camera, runtime)}</strong>
      </footer>
      <DetectionList runtime={runtime} />
    </article>
  );
}

function FpsPill({ label, value }: { label: string; value: string }) {
  return (
    <span>
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  );
}

function CameraStreamTile({
  token,
  cameraId,
  camera,
  runtime,
  onStats,
  canEditZones,
}: {
  token: string;
  cameraId: string;
  camera?: Camera;
  runtime?: CameraRuntime;
  onStats: (cameraId: string, stats: StreamStats) => void;
  canEditZones: boolean;
}) {
  const [liveState, setLiveState] = useState<LiveState>('idle');
  const [displayFps, setDisplayFps] = useState(0);
  const [error, setError] = useState('');
  const [overlayRuntime, setOverlayRuntime] = useState<CameraRuntime | undefined>(runtime);
  const [zoneEditorOpen, setZoneEditorOpen] = useState(false);
  const [zones, setZones] = useState<CameraZones>({});
  const [draftZoneName, setDraftZoneName] = useState('gate');
  const [draftPoints, setDraftPoints] = useState<ZonePoint[]>([]);
  const [zoneMessage, setZoneMessage] = useState('');
  const [savingZones, setSavingZones] = useState(false);
  const [frameSize, setFrameSize] = useState({ width: STREAM_WIDTH, height: STREAM_HEIGHT });
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const manualStoppedRef = useRef(false);
  const mountedRef = useRef(false);
  const retryCountRef = useRef(0);
  const frameCounterRef = useRef({ count: 0, startedAt: 0 });
  const stats = { displayFps, state: liveState };
  const displayRuntime = overlayRuntime || runtime;
  const fps = getCameraFps(camera, displayRuntime, stats);
  const overlayFrameSize = runtimeSourceSize(displayRuntime, frameSize);
  const overlayZones = zoneEditorOpen ? zones : displayRuntime?.zones || {};

  useEffect(() => {
    setOverlayRuntime(runtime);
  }, [runtime]);

  useEffect(() => {
    mountedRef.current = true;
    if (camera?.is_active !== false) {
      void startStream();
    } else {
      stopStream();
    }
    return () => {
      mountedRef.current = false;
      stopStream();
    };
  }, [cameraId, token, camera?.is_active]);

  useEffect(() => {
    onStats(cameraId, stats);
  }, [cameraId, displayFps, liveState, onStats]);

  useEffect(() => {
    if (camera?.is_active === false) return;
    let cancelled = false;

    async function loadOverlayMeta() {
      try {
        const nextRuntime = await getCameraMeta(token, cameraId);
        if (!cancelled) setOverlayRuntime(nextRuntime);
      } catch {
        // Keep the last usable metadata so the raw stream continues rendering.
      }
    }

    void loadOverlayMeta();
    const timer = window.setInterval(loadOverlayMeta, OVERLAY_META_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [camera?.is_active, cameraId, token]);

  useEffect(() => {
    if (!canEditZones || !zoneEditorOpen) return;
    let cancelled = false;
    setZoneMessage('');
    getCameraZones(token, cameraId)
      .then((loadedZones) => {
        if (!cancelled) setZones(loadedZones);
      })
      .catch((err) => {
        if (!cancelled) setZoneMessage(err instanceof Error ? err.message : 'Không tải được ROI');
      });
    return () => {
      cancelled = true;
    };
  }, [cameraId, canEditZones, token, zoneEditorOpen]);

  async function startStream() {
    stopStream(false);
    if (camera?.is_active === false) {
      setLiveState('stopped');
      return;
    }
    manualStoppedRef.current = false;
    setError('');
    setDisplayFps(0);
    frameCounterRef.current = { count: 0, startedAt: performance.now() };
    setLiveState('connecting');
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(`${API_BASE}/cameras/${encodeURIComponent(cameraId)}/raw.mjpeg`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error(`MJPEG API lỗi: ${response.status}`);
      if (!mountedRef.current || controller.signal.aborted) return;
      retryCountRef.current = 0;
      setLiveState('running');
      await drawMjpegStream(response.body, controller.signal, drawFrame);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      if (!mountedRef.current) return;
      setLiveState('error');
      setError(err instanceof Error ? err.message : 'Không kết nối được camera');
      scheduleRetry();
    }
  }

  function stopStream(markManual = true) {
    if (markManual) {
      manualStoppedRef.current = true;
    }
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    if (mountedRef.current) {
      setLiveState('stopped');
    }
  }

  function scheduleRetry() {
    if (manualStoppedRef.current || retryTimerRef.current || retryCountRef.current >= MAX_STREAM_RETRIES) return;
    retryCountRef.current += 1;
    retryTimerRef.current = setTimeout(() => {
      retryTimerRef.current = null;
      if (mountedRef.current && !manualStoppedRef.current) {
        void startStream();
      }
    }, 3000);
  }

  async function drawFrame(blob: Blob) {
    let bitmap: ImageBitmap;
    try {
      bitmap = await createImageBitmap(blob);
    } catch {
      return;
    }
    try {
      if (!mountedRef.current) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const context = canvas.getContext('2d');
      if (!context) return;
      if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        setFrameSize({ width: bitmap.width, height: bitmap.height });
      }
      context.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height);
    } finally {
      bitmap.close();
    }
    const counter = frameCounterRef.current;
    counter.count += 1;
    const elapsed = performance.now() - counter.startedAt;
    if (elapsed >= 1000) {
      setDisplayFps((counter.count * 1000) / elapsed);
      frameCounterRef.current = { count: 0, startedAt: performance.now() };
    }
  }

  function addDraftPoint(event: MouseEvent<SVGSVGElement>) {
    if (!zoneEditorOpen) return;
    const svg = event.currentTarget;
    const rect = svg.getBoundingClientRect();
    const frameWidth = overlayFrameSize.width;
    const frameHeight = overlayFrameSize.height;
    const x = Math.round(((event.clientX - rect.left) / Math.max(rect.width, 1)) * frameWidth);
    const y = Math.round(((event.clientY - rect.top) / Math.max(rect.height, 1)) * frameHeight);
    setDraftPoints((current) => [...current, [clamp(x, 0, frameWidth), clamp(y, 0, frameHeight)]]);
  }

  async function saveDraftZone() {
    const zoneName = draftZoneName.trim();
    if (!zoneName) {
      setZoneMessage('Tên ROI không được rỗng');
      return;
    }
    if (draftPoints.length < 3) {
      setZoneMessage('ROI cần tối thiểu 3 điểm');
      return;
    }
    const nextZones = { ...zones, [zoneName]: draftPoints };
    setSavingZones(true);
    setZoneMessage('');
    try {
      const response = await updateCameraZones(token, cameraId, nextZones);
      setZones(response.zones);
      setDraftPoints([]);
      setZoneMessage('Đã lưu ROI');
    } catch (err) {
      setZoneMessage(err instanceof Error ? err.message : 'Không lưu được ROI');
    } finally {
      setSavingZones(false);
    }
  }

  async function deleteSelectedZone() {
    const zoneName = draftZoneName.trim();
    if (!zoneName || !zones[zoneName]) {
      setZoneMessage('ROI chưa tồn tại');
      return;
    }
    const nextZones = { ...zones };
    delete nextZones[zoneName];
    setSavingZones(true);
    setZoneMessage('');
    try {
      const response = await updateCameraZones(token, cameraId, nextZones);
      setZones(response.zones);
      setDraftPoints([]);
      setZoneMessage('Đã xóa ROI');
    } catch (err) {
      setZoneMessage(err instanceof Error ? err.message : 'Không xóa được ROI');
    } finally {
      setSavingZones(false);
    }
  }

  return (
    <article className="ops-camera-stream-card">
      <header className="ops-camera-stream-header">
        <div className="ops-camera-stream-heading">
          <strong title={camera?.name || displayRuntime?.name || cameraId}>{camera?.name || displayRuntime?.name || cameraId}</strong>
          <div className="ops-camera-stream-metrics" aria-label="Camera performance metrics">
            <span className="ops-camera-stream-metric">RTSP {fps.rtsp}</span>
            <span className="ops-camera-stream-metric">Resize {fps.resize}</span>
            <span className="ops-camera-stream-metric">Model {fps.model}</span>
          </div>
        </div>
        {canEditZones ? (
          <button
            type="button"
            className={zoneEditorOpen ? 'ops-roi-toggle is-active' : 'ops-roi-toggle'}
            onClick={() => {
              setZoneEditorOpen((current) => !current);
              setDraftPoints([]);
              setZoneMessage('');
            }}
          >
            ROI
          </button>
        ) : null}
      </header>
      <div className="ops-camera-media">
        <canvas ref={canvasRef} className="ops-camera-canvas" width={STREAM_WIDTH} height={STREAM_HEIGHT} />
        <StreamOverlay
          runtime={displayRuntime}
          zones={overlayZones}
          draftPoints={draftPoints}
          activeZoneName={draftZoneName}
          frameSize={overlayFrameSize}
          editable={canEditZones && zoneEditorOpen}
          onAddPoint={addDraftPoint}
        />
        <span className={`ops-camera-state state-${liveState}`}>{formatLiveState(liveState, displayRuntime)}</span>
      </div>
      {canEditZones && zoneEditorOpen ? (
        <div className="ops-roi-toolbar">
          <label>
            ROI
            <input value={draftZoneName} onChange={(event) => setDraftZoneName(event.target.value)} placeholder="gate" />
          </label>
          <button type="button" onClick={() => setDraftPoints((current) => current.slice(0, -1))} disabled={!draftPoints.length || savingZones}>
            Undo
          </button>
          <button type="button" onClick={() => setDraftPoints([])} disabled={!draftPoints.length || savingZones}>
            Clear
          </button>
          <button type="button" onClick={deleteSelectedZone} disabled={savingZones}>
            Delete
          </button>
          <button type="button" className="is-primary" onClick={saveDraftZone} disabled={savingZones}>
            Save
          </button>
          <span>{draftPoints.length} điểm</span>
          {zoneMessage ? <em>{zoneMessage}</em> : null}
        </div>
      ) : null}
      <footer>
        <span>Nhận diện thời gian thực</span>
        <strong>{detectionSummary(camera, displayRuntime)}</strong>
      </footer>
      <DetectionList runtime={displayRuntime} />
      {error ? <p className="ops-camera-error">{error}</p> : null}
    </article>
  );
}

function StreamOverlay({
  runtime,
  zones,
  draftPoints,
  activeZoneName,
  frameSize,
  editable,
  onAddPoint,
}: {
  runtime?: CameraRuntime;
  zones: CameraZones;
  draftPoints: ZonePoint[];
  activeZoneName: string;
  frameSize: { width: number; height: number };
  editable: boolean;
  onAddPoint: (event: MouseEvent<SVGSVGElement>) => void;
}) {
  const frameWidth = frameSize.width || STREAM_WIDTH;
  const frameHeight = frameSize.height || STREAM_HEIGHT;
  const tracks = normalizedRuntimeTracks(runtime).filter((track) => track.bbox.length === 4);
  return (
    <svg
      className={editable ? 'ops-stream-overlay is-editing' : 'ops-stream-overlay'}
      viewBox={`0 0 ${frameWidth} ${frameHeight}`}
      preserveAspectRatio="none"
      onClick={editable ? onAddPoint : undefined}
      role="presentation"
    >
      {Object.entries(zones).map(([zoneName, points]) => (
        <g key={zoneName} className={`ops-roi-zone ${zoneClass(zoneName)}`}>
          <polygon points={pointsToSvg(points)} />
          {points.map((point, index) => <circle key={`${zoneName}-${index}`} cx={point[0]} cy={point[1]} r="5" />)}
          {points[0] ? <text x={points[0][0]} y={Math.max(18, points[0][1] - 10)}>{zoneName}</text> : null}
        </g>
      ))}
      {tracks.map((track, index) => (
        <TrackOverlay key={`${track.track_id ?? 'track'}-${index}`} track={track} />
      ))}
      {draftPoints.length ? (
        <g className={`ops-roi-zone is-draft ${zoneClass(activeZoneName)}`}>
          <polyline points={pointsToSvg(draftPoints)} />
          {draftPoints.map((point, index) => <circle key={`draft-${index}`} cx={point[0]} cy={point[1]} r="7" />)}
        </g>
      ) : null}
    </svg>
  );
}

function TrackOverlay({ track }: { track: CameraRuntimeTrack }) {
  const [x1, y1, x2, y2] = track.bbox;
  const x = Math.min(x1, x2);
  const y = Math.min(y1, y2);
  const width = Math.max(1, Math.abs(x2 - x1));
  const height = Math.max(1, Math.abs(y2 - y1));
  const label = displayTrackLabel(track);
  const score = typeof track.score === 'number' ? ` ${track.score.toFixed(2)}` : '';
  return (
    <g className={`ops-track-overlay ${detectionStatusClass(track.status)}`}>
      <rect x={x} y={y} width={width} height={height} />
      <text x={x} y={Math.max(18, y - 8)}>{label}{score}</text>
    </g>
  );
}

function DetectionList({ runtime }: { runtime?: CameraRuntime }) {
  const tracks = knownRuntimeTracks(runtime);
  if (!runtime?.is_realtime) {
    return <p className="ops-detection-note">Chưa có meta realtime</p>;
  }
  if (!tracks.length) {
    return <p className="ops-detection-note">Chưa có người quen</p>;
  }
  return (
    <div className="ops-detection-list" aria-label="Realtime detections">
      {tracks.map((track, index) => (
        <span key={`${track.track_id ?? 'track'}-${index}`} className={`ops-detection-pill ${detectionStatusClass(track.status)}`}>
          <strong>{displayTrackLabel(track)}</strong>
          {track.score !== null && track.score !== undefined ? <small>{track.score.toFixed(3)}</small> : null}
          {track.zone && track.zone !== 'none' ? <small>{track.zone}</small> : null}
        </span>
      ))}
    </div>
  );
}

function StatusChip({ camera, runtime, stats }: { camera?: Camera; runtime?: CameraRuntime; stats?: StreamStats }) {
  const connected = isCameraConnected(camera, runtime, stats);
  const label = runtime?.is_realtime ? 'Realtime' : connected ? 'Online' : 'Standby';
  return <span className={connected ? 'ops-status-chip is-online' : 'ops-status-chip'}>{label}</span>;
}

async function drawMjpegStream(stream: ReadableStream<Uint8Array>, signal: AbortSignal, onFrame: (blob: Blob) => Promise<void>) {
  const reader = stream.getReader();
  let buffer = new Uint8Array();
  try {
    while (!signal.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      if (!value) continue;
      buffer = concatBytes(buffer, value);
      let start = findJpegMarker(buffer, 0xff, 0xd8);
      let end = findJpegMarker(buffer, 0xff, 0xd9);
      while (start >= 0 && end > start) {
        const frame = buffer.slice(start, end + 2);
        buffer = buffer.slice(end + 2);
        await onFrame(new Blob([frame], { type: 'image/jpeg' }));
        if (signal.aborted) break;
        start = findJpegMarker(buffer, 0xff, 0xd8);
        end = findJpegMarker(buffer, 0xff, 0xd9);
      }
      if (buffer.length > 2_000_000) buffer = new Uint8Array();
    }
  } finally {
    reader.releaseLock();
  }
}

function concatBytes(left: Uint8Array, right: Uint8Array) {
  const output = new Uint8Array(left.length + right.length);
  output.set(left);
  output.set(right, left.length);
  return output;
}

function findJpegMarker(buffer: Uint8Array, first: number, second: number) {
  for (let index = 0; index < buffer.length - 1; index += 1) {
    if (buffer[index] === first && buffer[index + 1] === second) return index;
  }
  return -1;
}

function getCameraFps(camera?: Camera, runtime?: CameraRuntime, stats?: StreamStats) {
  const rtsp = positive(runtime?.camera_fps) || positive(camera?.camera_fps) || positive(stats?.displayFps);
  const resize = positive(runtime?.read_fps) || positive(camera?.read_fps) || positive(runtime?.stream_fps) || positive(stats?.displayFps);
  const model = positive(runtime?.model_fps) || positive(runtime?.ai_update_fps);
  return {
    rtsp: formatFps(rtsp),
    resize: formatFps(resize),
    model: formatFps(model),
  };
}

function isCameraConnected(camera?: Camera, runtime?: CameraRuntime, stats?: StreamStats) {
  return runtime?.is_realtime || stats?.state === 'running' || camera?.worker_status === 'running' || Number(camera?.read_fps || 0) > 0;
}

function detectionSummary(camera?: Camera, runtime?: CameraRuntime) {
  if (camera?.last_error || runtime?.last_error) return 'Cần kiểm tra';
  const tracks = knownRuntimeTracks(runtime);
  if (tracks.length) return `${tracks.length} người quen`;
  return runtime?.is_realtime ? 'Chưa có nhận diện' : 'Chưa có meta realtime';
}

function knownRuntimeTracks(runtime?: CameraRuntime): CameraRuntimeTrack[] {
  return normalizedRuntimeTracks(runtime).filter((track) => track.status === 'known' && track.label.trim() && track.label !== 'Known');
}

function normalizedRuntimeTracks(runtime?: CameraRuntime): CameraRuntimeTrack[] {
  return (runtime?.tracks || []).map((track) => {
    const status = normalizeTrackStatus(track.status);
    return {
      ...track,
      status,
      label: normalizeTrackLabel(status, track.label),
      score: typeof track.score === 'number' && Number.isFinite(track.score) ? track.score : null,
    };
  });
}

function normalizeTrackStatus(status?: string | null) {
  const normalized = String(status || '').toLowerCase();
  return ['known', 'unknown', 'unverified'].includes(normalized) ? normalized : 'unverified';
}

function normalizeTrackLabel(status: string, label?: string | null) {
  const trimmed = String(label || '').trim();
  if (status === 'known') return trimmed || 'Known';
  if (status === 'unknown') return 'Unknown';
  return 'Unverified';
}

function displayTrackLabel(track: CameraRuntimeTrack) {
  return normalizeTrackLabel(normalizeTrackStatus(track.status), track.label);
}

function detectionStatusClass(status?: string | null) {
  const normalized = normalizeTrackStatus(status);
  if (normalized === 'unknown') return 'is-unknown';
  if (normalized === 'unverified') return 'is-unverified';
  return 'is-known';
}

function pointsToSvg(points: ZonePoint[]) {
  return points.map((point) => `${point[0]},${point[1]}`).join(' ');
}

function zoneClass(zoneName: string) {
  const normalized = zoneName.trim().toLowerCase();
  if (normalized.includes('restricted')) return 'is-restricted';
  if (normalized.includes('gate')) return 'is-gate';
  return 'is-custom';
}

function runtimeSourceSize(runtime: CameraRuntime | undefined, fallback: { width: number; height: number }) {
  const width = positive(runtime?.source_width);
  const height = positive(runtime?.source_height);
  return {
    width: width || fallback.width || STREAM_WIDTH,
    height: height || fallback.height || STREAM_HEIGHT,
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function positive(value?: number | null) {
  const number = Number(value || 0);
  return Number.isFinite(number) && number > 0 ? number : 0;
}

function formatFps(value?: number | null) {
  return Number(value || 0).toFixed(1);
}

function formatLiveState(state: LiveState, runtime?: CameraRuntime) {
  if (state === 'connecting') return 'connecting';
  if (state === 'running') return runtime?.is_realtime ? 'realtime' : 'live';
  if (state === 'error') return 'error';
  if (state === 'stopped') return 'stopped';
  return 'standby';
}

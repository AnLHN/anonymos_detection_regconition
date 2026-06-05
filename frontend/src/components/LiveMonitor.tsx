'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getCameraRuntime } from '@/lib/api';
import { API_BASE } from '@/lib/config';
import type { Camera, CameraRuntime } from '@/lib/types';

const STREAM_WIDTH = 1280;
const STREAM_HEIGHT = 720;

type LiveState = 'idle' | 'connecting' | 'running' | 'stopped' | 'error';
type DisplayMode = 'fps' | 'stream';

type StreamStats = {
  displayFps: number;
  state: LiveState;
};

export default function LiveMonitor({ token, cameras }: { token: string; cameras: Camera[] }) {
  const [displayMode, setDisplayMode] = useState<DisplayMode>('stream');
  const [cameraFilter, setCameraFilter] = useState('all');
  const [streamStats, setStreamStats] = useState<Record<string, StreamStats>>({});
  const [runtimeByCamera, setRuntimeByCamera] = useState<Record<string, CameraRuntime>>({});
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
    const timer = window.setInterval(loadRuntime, 1000);
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

  const connectedCount = cameraSlots.filter((cameraId) => (
    isCameraConnected(cameras.find((item) => item.camera_id === cameraId), runtimeByCamera[cameraId], streamStats[cameraId])
  )).length;
  const pipelineCount = cameraSlots.filter((cameraId) => (
    isPipelineRunning(cameras.find((item) => item.camera_id === cameraId), runtimeByCamera[cameraId], streamStats[cameraId])
  )).length;

  const updateTileStats = useCallback((cameraId: string, stats: StreamStats) => {
    setStreamStats((current) => ({ ...current, [cameraId]: stats }));
  }, []);

  return (
    <section className="ops-camera-center">
      <div className="ops-camera-stats">
        <CameraSummary label="Tổng luồng" value={cameraSlots.length} />
        <CameraSummary label="Đang kết nối" value={connectedCount} />
        <CameraSummary label="Pipeline đang chạy" value={pipelineCount} />
      </div>

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

function CameraSummary({ label, value }: { label: string; value: number }) {
  return (
    <article className="ops-camera-summary">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
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
}: {
  token: string;
  cameraId: string;
  camera?: Camera;
  runtime?: CameraRuntime;
  onStats: (cameraId: string, stats: StreamStats) => void;
}) {
  const [liveState, setLiveState] = useState<LiveState>('idle');
  const [displayFps, setDisplayFps] = useState(0);
  const [error, setError] = useState('');
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const manualStoppedRef = useRef(false);
  const mountedRef = useRef(false);
  const frameCounterRef = useRef({ count: 0, startedAt: 0 });
  const stats = { displayFps, state: liveState };
  const fps = getCameraFps(camera, runtime, stats);

  useEffect(() => {
    mountedRef.current = true;
    void startStream();
    return () => {
      mountedRef.current = false;
      stopStream();
    };
  }, [cameraId, token]);

  useEffect(() => {
    onStats(cameraId, stats);
  }, [cameraId, displayFps, liveState, onStats]);

  async function startStream() {
    stopStream(false);
    manualStoppedRef.current = false;
    setError('');
    setDisplayFps(0);
    frameCounterRef.current = { count: 0, startedAt: performance.now() };
    setLiveState('connecting');
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(`${API_BASE}/cameras/${encodeURIComponent(cameraId)}/mjpeg`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error(`MJPEG API lỗi: ${response.status}`);
      if (!mountedRef.current || controller.signal.aborted) return;
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
    setLiveState('stopped');
  }

  function scheduleRetry() {
    if (manualStoppedRef.current || retryTimerRef.current) return;
    retryTimerRef.current = setTimeout(() => {
      retryTimerRef.current = null;
      if (mountedRef.current && !manualStoppedRef.current) {
        void startStream();
      }
    }, 3000);
  }

  async function drawFrame(blob: Blob) {
    const bitmap = await createImageBitmap(blob);
    try {
      if (!mountedRef.current) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const context = canvas.getContext('2d');
      if (!context) return;
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
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

  return (
    <article className="ops-camera-stream-card">
      <header>
        <strong>{camera?.name || runtime?.name || cameraId}</strong>
        <span>RTSP {fps.rtsp} | Resize {fps.resize} | Model {fps.model}</span>
      </header>
      <div className="ops-camera-media">
        <canvas ref={canvasRef} className="ops-camera-canvas" width={STREAM_WIDTH} height={STREAM_HEIGHT} />
        <span className={`ops-camera-state state-${liveState}`}>{formatLiveState(liveState, runtime)}</span>
      </div>
      <footer>
        <span>Nhận diện thời gian thực</span>
        <strong>{detectionSummary(camera, runtime)}</strong>
      </footer>
      {error ? <p className="ops-camera-error">{error}</p> : null}
    </article>
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
  const resize = positive(runtime?.read_fps) || positive(camera?.read_fps) || positive(stats?.displayFps);
  const model = positive(runtime?.model_fps) || latencyToFps(runtime?.ai_latency_ms) || latencyToFps(camera?.ai_latency_ms) || positive(stats?.displayFps);
  return {
    rtsp: formatFps(rtsp),
    resize: formatFps(resize),
    model: formatFps(model),
  };
}

function isCameraConnected(camera?: Camera, runtime?: CameraRuntime, stats?: StreamStats) {
  return runtime?.is_realtime || stats?.state === 'running' || camera?.worker_status === 'running' || Number(camera?.read_fps || 0) > 0;
}

function isPipelineRunning(camera?: Camera, runtime?: CameraRuntime, stats?: StreamStats) {
  return isCameraConnected(camera, runtime, stats) && (positive(runtime?.model_fps) > 0 || positive(camera?.ai_latency_ms) > 0 || positive(stats?.displayFps) > 0);
}

function detectionSummary(camera?: Camera, runtime?: CameraRuntime) {
  if (camera?.last_error || runtime?.last_error) return 'Cần kiểm tra';
  if (runtime?.tracks_count) return `${runtime.tracks_count} nhận diện`;
  return runtime?.is_realtime ? 'Chưa có nhận diện' : 'Chưa có meta realtime';
}

function positive(value?: number | null) {
  const number = Number(value || 0);
  return Number.isFinite(number) && number > 0 ? number : 0;
}

function latencyToFps(value?: number | null) {
  const latency = positive(value);
  return latency ? 1000 / Math.max(latency, 1) : 0;
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

'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type React from 'react';
import { AuthExpiredError, getAlerts, getCameras, getEmployees, getHealth, getMe, getRules, logout } from '@/lib/api';
import { clearToken, getToken } from '@/lib/auth';
import { hasPermission } from '@/lib/permissions';
import type { Alert, Camera, CurrentUser, Employee, Health, Rule } from '@/lib/types';
import AlertNotifications from './AlertNotifications';
import LiveMonitor from './LiveMonitor';

const ALERT_POLL_INTERVAL_MS = 5000;

export type AdminPage = 'dashboard' | 'alerts' | 'cameras' | 'rules' | 'employees' | 'users' | 'system';

export type AdminData = {
  token: string;
  currentUser: CurrentUser | null;
  health: Health | null;
  healthCheckedAt: string | null;
  alerts: Alert[];
  alertReadIds: string[];
  cameras: Camera[];
  rules: Rule[];
  employees: Employee[];
  markAlertRead: (eventId: string) => void;
  markAlertsRead: (eventIds: string[]) => void;
  refresh: () => Promise<void>;
};

const NAV_ITEMS: { key: AdminPage; label: string; href: string; description: string; permission?: string }[] = [
  { key: 'dashboard', label: 'Tổng quan', href: '/', description: 'Giám sát camera và nhận diện' },
  { key: 'cameras', label: 'Camera', href: '/cameras', description: 'Quản lý nguồn camera' },
  { key: 'alerts', label: 'Cảnh báo', href: '/alerts', description: 'Xem và xử lý cảnh báo' },
  { key: 'rules', label: 'Thiết lập vận hành', href: '/rules', description: 'Quy tắc và khung giờ' },
  { key: 'employees', label: 'Nhân viên', href: '/employees', description: 'Danh sách nhân viên' },
  { key: 'users', label: 'Tài khoản', href: '/users', description: 'Tài khoản và phân quyền', permission: 'users:read' },
  { key: 'system', label: 'Hệ thống', href: '/system', description: 'Tài nguyên hệ thống', permission: 'system:read' },
];

const PAGE_META: Record<AdminPage, { title: string; description: string }> = {
  dashboard: {
    title: 'Tổng quan',
    description: '',
  },
  alerts: {
    title: 'Cảnh báo',
    description: '',
  },
  cameras: {
    title: 'Camera',
    description: '',
  },
  rules: {
    title: 'Thiết lập vận hành',
    description: '',
  },
  employees: {
    title: 'Nhân viên',
    description: '',
  },
  users: {
    title: 'Tài khoản',
    description: '',
  },
  system: {
    title: 'Hệ thống',
    description: '',
  },
};

const AdminDataContext = createContext<AdminData | null>(null);
const ALERT_READ_STORAGE_KEY = 'unknown_detection_read_alert_ids';
const ALERT_SESSION_BASELINE_KEY = 'unknown_detection_alert_session_seeded';

export function useAdminData() {
  const value = useContext(AdminDataContext);
  if (!value) throw new Error('useAdminData must be used inside AdminShell');
  return value;
}

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [token, setTokenState] = useState<string | null>(null);
  const [hasCheckedToken, setHasCheckedToken] = useState(false);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertReadIds, setAlertReadIds] = useState<string[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [healthCheckedAt, setHealthCheckedAt] = useState<string | null>(null);
  const [hasLoadedAlertReadIds, setHasLoadedAlertReadIds] = useState(false);
  const [error, setError] = useState('');
  const [sidebarClock, setSidebarClock] = useState(() => new Date());
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem('unknown_detection_sidebar_collapsed');
      if (stored === 'true') {
        setIsSidebarCollapsed(true);
      }
    } catch {
      // Ignored
    }
  }, []);

  function toggleSidebar() {
    const nextState = !isSidebarCollapsed;
    setIsSidebarCollapsed(nextState);
    try {
      window.localStorage.setItem('unknown_detection_sidebar_collapsed', String(nextState));
    } catch {
      // Ignored
    }
  }

  useEffect(() => {
    const stored = getToken();
    if (stored && stored !== token) {
      setTokenState(stored);
      void loadDashboard(stored);
    }
    setHasCheckedToken(true);
  }, [pathname]);

  useEffect(() => {
    if (!hasCheckedToken || token || isAuthPage(pathname)) {
      return;
    }
    const stored = getToken();
    if (stored) {
      setTokenState(stored);
      void loadDashboard(stored);
      return;
    }
    if (!stored) {
      router.replace('/login');
    }
  }, [hasCheckedToken, pathname, router, token]);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(ALERT_READ_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setAlertReadIds(parsed.filter((value) => typeof value === 'string'));
        }
      }
    } catch {
      setAlertReadIds([]);
    } finally {
      setHasLoadedAlertReadIds(true);
    }
  }, []);

  useEffect(() => {
    if (!token || isAuthPage(pathname)) {
      return;
    }

    const activeToken = token;

    let cancelled = false;

    async function pollAlerts() {
      try {
        const latestAlerts = await getAlerts(activeToken, { limit: 50, offset: 0 });
        if (cancelled) {
          return;
        }
        setAlerts((current) => sameAlerts(current, latestAlerts) ? current : latestAlerts);
      } catch (err) {
        if (err instanceof AuthExpiredError) {
          clearToken();
          setTokenState(null);
          setCurrentUser(null);
        }
      }
    }

    const timer = window.setInterval(() => {
      void pollAlerts();
    }, ALERT_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [pathname, token]);

  useEffect(() => {
    if (!hasLoadedAlertReadIds || hasSessionAlertBaseline()) {
      return;
    }

    setSessionAlertBaseline();
    const activeIds = alerts.filter((alert) => !alert.deleted_at).map((alert) => alert.event_id);
    if (!activeIds.length) {
      return;
    }

    setAlertReadIds((current) => {
      const next = [...new Set([...current, ...activeIds])];
      if (next.length === current.length) {
        return current;
      }
      persistAlertReadIds(next);
      return next;
    });
  }, [alerts, hasLoadedAlertReadIds]);

  useEffect(() => {
    if (!alerts.length) return;
    const activeIds = new Set(alerts.filter((alert) => !alert.deleted_at).map((alert) => alert.event_id));
    setAlertReadIds((current) => {
      const next = current.filter((eventId) => activeIds.has(eventId));
      if (next.length === current.length) return current;
      persistAlertReadIds(next);
      return next;
    });
  }, [alerts]);

  useEffect(() => {
    const timer = window.setInterval(() => setSidebarClock(new Date()), 30000);
    return () => window.clearInterval(timer);
  }, []);

  async function loadDashboard(activeToken = token) {
    if (!activeToken) return;
    setError('');
    try {
      const meData = await getMe(activeToken);
      const [healthData, alertsData, camerasData, rulesData, employeesData] = await Promise.all([
        hasPermission(meData, 'system:read') ? getHealth(activeToken) : Promise.resolve(null),
        getAlerts(activeToken),
        getCameras(activeToken),
        getRules(activeToken),
        getEmployees(activeToken),
      ]);
      setCurrentUser(meData);
      setHealth(healthData);
      setHealthCheckedAt(healthData ? new Date().toISOString() : null);
      setAlerts(alertsData);
      setCameras(camerasData);
      setRules(rulesData);
      setEmployees(employeesData);
    } catch (err) {
      if (err instanceof AuthExpiredError) {
        setTokenState(null);
        setCurrentUser(null);
        return;
      }
      setError(err instanceof Error ? err.message : 'Không tải được dữ liệu hệ thống');
    }
  }

  async function handleLogout() {
    if (token) {
      try {
        await logout(token);
      } catch {
        // Local logout still proceeds if the server is unreachable.
      }
    }
    clearToken();
    setTokenState(null);
    setCurrentUser(null);
    router.replace('/login');
  }

  function markAlertsRead(eventIds: string[]) {
    if (!eventIds.length) return;
    setAlertReadIds((current) => {
      const next = [...new Set([...current, ...eventIds])];
      persistAlertReadIds(next);
      return next;
    });
  }

  function markAlertRead(eventId: string) {
    markAlertsRead([eventId]);
  }

  const activePage = getActivePage(pathname);
  const pageMeta = PAGE_META[activePage];
  const unreadAlertCount = alerts.filter((alert) => !alert.deleted_at && !alertReadIds.includes(alert.event_id)).length;
  const adminData = useMemo(
    () => ({
      token: token || '',
      currentUser,
      health,
      healthCheckedAt,
      alerts,
      alertReadIds,
      cameras,
      rules,
      employees,
      markAlertRead,
      markAlertsRead,
      refresh: () => loadDashboard(token),
    }),
    [alertReadIds, alerts, cameras, currentUser, employees, health, healthCheckedAt, rules, token],
  );

  if (isAuthPage(pathname)) {
    return <>{children}</>;
  }

  if (!hasCheckedToken || !token) {
    return (
      <main className="login-shell">
        <section className="card login-card">
          <div className="login-brand">
            <Image src="/ntc-logo.png" alt="NTC" width={120} height={72} priority />
            <h1>NTC Stranger Detect</h1>
          </div>
          <p>Vui lòng đăng nhập để tiếp tục vào dashboard giám sát.</p>
          <Link className="button" href="/login">Đến trang đăng nhập</Link>
        </section>
      </main>
    );
  }

  return (
    <main className={isSidebarCollapsed ? "admin-shell collapsed" : "admin-shell"}>
      <aside className="sidebar">
        <div className="brand" onClick={toggleSidebar} style={{ cursor: 'pointer' }} title={isSidebarCollapsed ? "Mở rộng menu" : "Thu gọn menu"}>
          <span className="brand-logo-mark">
            <Image className="brand-logo" src="/ntc-logo.png" alt="NTC" width={48} height={48} priority />
          </span>
          <div className="brand-copy">
            <strong>NTC Stranger Detect</strong>
            <span>Trung tâm kiểm soát nhận diện</span>
          </div>
        </div>
        <div className="sidebar-nav-scroll">
          <nav className="nav-list" aria-label="Main navigation">
            {NAV_ITEMS.filter((item) => !item.permission || hasPermission(currentUser, item.permission)).map((item) => (
              <Link key={item.key} className={activePage === item.key ? 'nav-item active' : 'nav-item'} href={item.href}>
                <span className="nav-item-icon" aria-hidden="true">{navBadge(item.label)}</span>
                <span className="nav-item-copy">
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
                {item.key === 'alerts' && unreadAlertCount ? <span className="nav-alert-count">{unreadAlertCount}</span> : null}
              </Link>
            ))}
          </nav>
        </div>
        <div className="sidebar-account">
          <div className="sidebar-meta-card sidebar-pill-card">
            <span>{formatSidebarDateTime(sidebarClock)}</span>
          </div>
          <div className="sidebar-user sidebar-user-compact sidebar-pill-card">
            <div>
              <strong>{currentUser?.username || 'unknown'}</strong>
              <em>{roleLabel(currentUser?.role || 0)}</em>
            </div>
          </div>
          <button type="button" className="sidebar-logout" onClick={handleLogout}>Đăng xuất</button>
        </div>
      </aside>
      <section className="main-content">
        <AdminDataContext.Provider value={adminData}>
          <AlertNotifications alerts={alerts} readIds={alertReadIds} enabled={true} onMarkRead={markAlertRead} onMarkAllRead={markAlertsRead} />
          <header className="topbar">
            <div className="topbar-copy">
              <span className="eyebrow">Điều hành tập trung</span>
              <h1>{pageMeta.title}</h1>
              {pageMeta.description ? <p>{pageMeta.description}</p> : null}
            </div>
            <div className="topbar-orb" aria-hidden="true" />
          </header>
          {error ? <p className="error notice">{error}</p> : null}
          {children}
          {activePage === 'dashboard' && cameras.length ? <LiveMonitor token={token} cameras={cameras} currentUser={currentUser} /> : null}
        </AdminDataContext.Provider>
      </section>
    </main>
  );
}

function isAuthPage(pathname: string) {
  return pathname.startsWith('/login') || pathname.startsWith('/register');
}

function getActivePage(pathname: string): AdminPage {
  if (pathname.startsWith('/alerts')) return 'alerts';
  if (pathname.startsWith('/cameras')) return 'cameras';
  if (pathname.startsWith('/rules')) return 'rules';
  if (pathname.startsWith('/employees')) return 'employees';
  if (pathname.startsWith('/users')) return 'users';
  if (pathname.startsWith('/system')) return 'system';
  return 'dashboard';
}

function roleLabel(role: number) {
  if (role >= 9) return 'Quản trị hệ thống';
  return 'Quản lý vận hành';
}

function userInitial(username?: string | null) {
  return (username || '?').trim().charAt(0).toUpperCase() || '?';
}

function navBadge(label: string) {
  const words = label.split(/\s+/).filter(Boolean);
  if (!words.length) return '•';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0] || ''}${words[1][0] || ''}`.toUpperCase();
}

function formatSidebarDateTime(value: Date) {
  return value.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

function persistAlertReadIds(eventIds: string[]) {
  try {
    window.localStorage.setItem(ALERT_READ_STORAGE_KEY, JSON.stringify(eventIds));
  } catch {
    // Browsers can block localStorage in private/restricted modes.
  }
}

function hasSessionAlertBaseline() {
  try {
    return window.sessionStorage.getItem(ALERT_SESSION_BASELINE_KEY) === '1';
  } catch {
    return false;
  }
}

function setSessionAlertBaseline() {
  try {
    window.sessionStorage.setItem(ALERT_SESSION_BASELINE_KEY, '1');
  } catch {
    // Browsers can block sessionStorage in private/restricted modes.
  }
}

function sameAlerts(current: Alert[], next: Alert[]) {
  if (current.length !== next.length) {
    return false;
  }
  return current.every((alert, index) => {
    const candidate = next[index];
    return Boolean(candidate)
      && alert.event_id === candidate.event_id
      && alert.review_status === candidate.review_status
      && alert.deleted_at === candidate.deleted_at
      && alert.note === candidate.note;
  });
}

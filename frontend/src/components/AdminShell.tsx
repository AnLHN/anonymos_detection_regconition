'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type React from 'react';
import { AuthExpiredError, getAlerts, getCameras, getEmployees, getHealth, getMe, getRules, logout } from '@/lib/api';
import { clearToken, getToken } from '@/lib/auth';
import { hasPermission } from '@/lib/permissions';
import type { Alert, Camera, CurrentUser, Employee, Health, Rule } from '@/lib/types';
import AlertNotifications from './AlertNotifications';
import LiveMonitor from './LiveMonitor';

export type AdminPage = 'dashboard' | 'alerts' | 'cameras' | 'rules' | 'employees' | 'users' | 'system';

export type AdminData = {
  token: string;
  currentUser: CurrentUser | null;
  health: Health | null;
  healthCheckedAt: string | null;
  alerts: Alert[];
  cameras: Camera[];
  rules: Rule[];
  employees: Employee[];
  refresh: () => Promise<void>;
};

const NAV_ITEMS: { key: AdminPage; label: string; href: string; permission?: string }[] = [
  { key: 'dashboard', label: 'Dashboard', href: '/' },
  { key: 'alerts', label: 'Alerts', href: '/alerts' },
  { key: 'cameras', label: 'Cameras', href: '/cameras' },
  { key: 'rules', label: 'Rules', href: '/rules' },
  { key: 'employees', label: 'Employees', href: '/employees' },
  { key: 'users', label: 'Users', href: '/users', permission: 'users:read' },
  { key: 'system', label: 'System Monitor', href: '/system', permission: 'system:read' },
];

const PAGE_META: Record<AdminPage, { title: string; description: string }> = {
  dashboard: {
    title: 'Trung tâm camera',
    description: 'Theo dõi nhanh luồng camera, trạng thái pipeline và nhận diện thời gian thực.',
  },
  alerts: {
    title: 'Alerts',
    description: 'Duyệt, kiểm tra ảnh và cập nhật trạng thái cảnh báo.',
  },
  cameras: {
    title: 'Cameras',
    description: 'Quản lý nguồn camera, vị trí và trạng thái worker.',
  },
  rules: {
    title: 'Rules',
    description: 'Tinh chỉnh rule cảnh báo và mức độ ưu tiên.',
  },
  employees: {
    title: 'Employees',
    description: 'Danh sách nhân sự đang dùng cho đối chiếu nhận diện.',
  },
  users: {
    title: 'Users',
    description: 'Quản lý tài khoản và phân quyền vận hành.',
  },
  system: {
    title: 'System Monitor',
    description: 'Bảng giám sát native từ Prometheus cho health, tài nguyên, lưu lượng và tín hiệu bảo mật.',
  },
};

const AdminDataContext = createContext<AdminData | null>(null);

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
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [healthCheckedAt, setHealthCheckedAt] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);

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
    setIsAccountMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isAccountMenuOpen) return;
    function handleDocumentMouseDown(event: MouseEvent) {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setIsAccountMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleDocumentMouseDown);
    return () => document.removeEventListener('mousedown', handleDocumentMouseDown);
  }, [isAccountMenuOpen]);

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

  const activePage = getActivePage(pathname);
  const pageMeta = PAGE_META[activePage];
  const adminData = useMemo(
    () => ({
      token: token || '',
      currentUser,
      health,
      healthCheckedAt,
      alerts,
      cameras,
      rules,
      employees,
      refresh: () => loadDashboard(token),
    }),
    [alerts, cameras, currentUser, employees, health, healthCheckedAt, rules, token],
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
            <h1>NTC Anonymous Detection & Recognition</h1>
          </div>
          <p>Vui lòng đăng nhập để tiếp tục vào dashboard giám sát.</p>
          <Link className="button" href="/login">Đến trang đăng nhập</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-shell">
      <aside className="sidebar">
        <div className="brand">
          <Image className="brand-logo" src="/ntc-logo.png" alt="NTC" width={78} height={48} priority />
          <div className="brand-copy">
            <strong>NTC Anonymous Detection & Recognition</strong>
            <span>Admin Console</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          {NAV_ITEMS.filter((item) => !item.permission || hasPermission(currentUser, item.permission)).map((item) => (
            <Link key={item.key} className={activePage === item.key ? 'nav-item active' : 'nav-item'} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-account" ref={accountMenuRef}>
          <button
            type="button"
            className="sidebar-user sidebar-user-compact sidebar-user-trigger"
            title={`${currentUser?.username || 'unknown'} - ${roleLabel(currentUser?.role || 0)}`}
            aria-expanded={isAccountMenuOpen}
            aria-controls="sidebar-account-popover"
            onClick={() => setIsAccountMenuOpen((value) => !value)}
          >
            <span className="sidebar-user-avatar">{userInitial(currentUser?.username)}</span>
            <div>
              <strong>{currentUser?.username || 'unknown'}</strong>
              <em>{roleLabel(currentUser?.role || 0)}</em>
            </div>
          </button>
          {isAccountMenuOpen ? (
            <div id="sidebar-account-popover" className="sidebar-account-popover">
              <button type="button" onClick={handleLogout}>Đăng xuất</button>
            </div>
          ) : null}
        </div>
      </aside>
      <section className="main-content">
        <header className="topbar">
          <div>
            <h1>{pageMeta.title}</h1>
            <p>{pageMeta.description}</p>
          </div>
        </header>
        {error ? <p className="error notice">{error}</p> : null}
        <AdminDataContext.Provider value={adminData}>
          {children}
          <AlertNotifications alerts={alerts} enabled={activePage === 'dashboard'} token={token} onRefresh={() => loadDashboard(token)} />
          {activePage === 'dashboard' && cameras.length ? <LiveMonitor token={token} cameras={cameras} /> : null}
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
  if (role >= 9) return 'Quyền tối cao';
  if (role >= 5) return 'Quản trị';
  if (role >= 1) return 'Trực ca';
  return 'Chỉ xem';
}

function userInitial(username?: string | null) {
  return (username || '?').trim().charAt(0).toUpperCase() || '?';
}

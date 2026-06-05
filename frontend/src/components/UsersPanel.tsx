'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { createUser, deactivateUser, getUserLoginHistory, getUsers, updateUser } from '@/lib/api';
import type { UserAccount, UserLoginEvent } from '@/lib/types';

const ROLE_OPTIONS = [
  { value: 0, label: 'Chỉ xem', hint: 'Theo dõi dữ liệu, không can thiệp vận hành.' },
  { value: 1, label: 'Trực ca', hint: 'Xử lý cảnh báo và theo dõi camera.' },
  { value: 5, label: 'Quản trị', hint: 'Quản lý camera, rule, nhân sự và hệ thống.' },
  { value: 9, label: 'Quyền tối cao', hint: 'Quản trị user và thao tác nhạy cảm.' },
];

type UserModalMode = 'create' | 'edit' | null;

export default function UsersPanel({ token }: { token: string }) {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [selected, setSelected] = useState<UserAccount | null>(null);
  const [roleTarget, setRoleTarget] = useState<UserAccount | null>(null);
  const [activityTarget, setActivityTarget] = useState<UserAccount | null>(null);
  const [activityRows, setActivityRows] = useState<UserLoginEvent[]>([]);
  const [isActivityLoading, setIsActivityLoading] = useState(false);
  const [modalMode, setModalMode] = useState<UserModalMode>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    void loadUsers();
  }, [token]);

  const summary = useMemo(() => ({
    total: users.length,
    active: users.filter((user) => user.is_active).length,
    superAdmins: users.filter((user) => user.role >= 9 && user.is_active).length,
  }), [users]);

  async function loadUsers() {
    setError('');
    try {
      setUsers(await getUsers(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được danh sách user');
    }
  }

  function openCreate() {
    setSelected(null);
    setModalMode('create');
  }

  function openEdit(user: UserAccount) {
    setSelected(user);
    setModalMode('edit');
  }

  async function openActivity(user: UserAccount) {
    setActivityTarget(user);
    setActivityRows([]);
    setIsActivityLoading(true);
    setError('');
    try {
      setActivityRows(await getUserLoginHistory(token, user.username));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được lịch sử đăng nhập');
    } finally {
      setIsActivityLoading(false);
    }
  }

  function closeUserModal() {
    setModalMode(null);
    setSelected(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setMessage('');
    setIsSaving(true);
    const formData = new FormData(event.currentTarget);
    try {
      await createUser(token, {
        username: String(formData.get('username') || '').trim(),
        email: String(formData.get('email') || '').trim() || null,
        password: String(formData.get('password') || ''),
        role: Number(formData.get('role') || 0),
        is_active: formData.get('is_active') === 'on',
      });
      closeUserModal();
      setMessage('Đã tạo user mới.');
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tạo được user');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setError('');
    setMessage('');
    setIsSaving(true);
    const formData = new FormData(event.currentTarget);
    const password = String(formData.get('password') || '');
    try {
      await updateUser(token, selected.username, {
        email: String(formData.get('email') || '').trim() || null,
        role: Number(formData.get('role') || 0),
        is_active: formData.get('is_active') === 'on',
        ...(password ? { password } : {}),
      });
      closeUserModal();
      setMessage('Đã cập nhật user.');
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không cập nhật được user');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRoleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!roleTarget) return;
    setError('');
    setMessage('');
    setIsSaving(true);
    const formData = new FormData(event.currentTarget);
    try {
      await updateUser(token, roleTarget.username, {
        role: Number(formData.get('role') || roleTarget.role),
      });
      setRoleTarget(null);
      setMessage('Đã cập nhật vai trò.');
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không cập nhật được vai trò');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeactivate(user: UserAccount) {
    if (!window.confirm(`Tắt tài khoản ${user.username}?`)) return;
    setError('');
    setMessage('');
    try {
      await deactivateUser(token, user.username);
      setMessage('Đã tắt tài khoản.');
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tắt được tài khoản');
    }
  }

  return (
    <section className="users-page">
      <div className="users-hero">
        <div>
          <span className="eyebrow">Admin Super</span>
          <h2>Bảng quản trị người dùng</h2>
          <p>Quản lý tài khoản, cấp quyền và trạng thái truy cập của hệ thống.</p>
        </div>
        <div className="users-summary">
          <Metric label="Tổng user" value={summary.total} />
          <Metric label="Đang hoạt động" value={summary.active} />
          <Metric label="Super admin" value={summary.superAdmins} />
        </div>
        <button type="button" onClick={openCreate}>Thêm user</button>
      </div>

      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}

      <article className="users-table-card">
        <div className="users-table-title">
          <strong>Người dùng</strong>
          <span>{users.length} tài khoản</span>
        </div>
        <div className="users-table-wrap">
          <table className="users-table">
            <thead>
              <tr>
                <th>Người dùng</th>
                <th>Email</th>
                <th>Vai trò</th>
                <th>Trạng thái</th>
                <th>Hoạt động</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.username}>
                  <td>
                    <div className="user-identity">
                      <span className="user-avatar">{userInitial(user.username)}</span>
                      <div>
                        <strong>{user.username}</strong>
                        <small>ID: {stableUserId(user.username)}</small>
                      </div>
                    </div>
                  </td>
                  <td className="user-email">{user.email || '-'}</td>
                  <td>
                    <button type="button" className="user-role-pill" onClick={() => setRoleTarget(user)}>
                      {roleLabel(user.role)}
                      <span aria-hidden="true">↗</span>
                    </button>
                  </td>
                  <td>
                    <span className={user.is_active ? 'user-status is-active' : 'user-status is-offline'}>
                      <i /> {user.is_active ? 'Đang hoạt động' : 'Đã khóa'}
                    </span>
                  </td>
                  <td>
                    <button type="button" className="user-activity-link" onClick={() => openActivity(user)}>
                      {formatActivity(user.updated_at || user.created_at)}
                    </button>
                  </td>
                  <td>
                    <div className="user-row-actions">
                      <button type="button" className="secondary" onClick={() => openEdit(user)}>Sửa</button>
                      <button type="button" className="danger" onClick={() => handleDeactivate(user)} disabled={!user.is_active}>Khóa</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!users.length ? (
                <tr>
                  <td colSpan={6} className="users-empty">Chưa có user nào.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </article>

      {modalMode ? (
        <UserModal
          title={modalMode === 'create' ? 'Thêm user mới' : `Chỉnh sửa ${selected?.username || ''}`}
          kicker="Tài khoản"
          onClose={closeUserModal}
        >
          <form className="compact-form user-modal-form" onSubmit={modalMode === 'create' ? handleCreate : handleUpdate}>
            {modalMode === 'create' ? (
              <label>Username<input name="username" required minLength={3} autoFocus /></label>
            ) : null}
            <label>Email<input name="email" type="email" defaultValue={selected?.email || ''} /></label>
            <label>{modalMode === 'create' ? 'Mật khẩu tạm' : 'Reset mật khẩu'}<input name="password" type="password" required={modalMode === 'create'} minLength={6} placeholder={modalMode === 'edit' ? 'Bỏ trống nếu không đổi' : undefined} /></label>
            <label>Vai trò<RoleSelect name="role" defaultValue={selected?.role || 0} /></label>
            <label className="inline-check"><input name="is_active" type="checkbox" defaultChecked={modalMode === 'create' ? true : selected?.is_active} /> Tài khoản đang hoạt động</label>
            <div className="modal-actions">
              <button type="submit" disabled={isSaving}>{isSaving ? 'Đang lưu' : modalMode === 'create' ? 'Tạo user' : 'Lưu thay đổi'}</button>
              <button type="button" className="secondary" onClick={closeUserModal}>Hủy</button>
            </div>
          </form>
        </UserModal>
      ) : null}

      {roleTarget ? (
        <UserModal title={`Quản lý vai trò: ${roleTarget.username}`} kicker="Phân quyền" onClose={() => setRoleTarget(null)}>
          <form className="user-role-form" onSubmit={handleRoleUpdate}>
            <p className="user-modal-note">Hệ thống hiện dùng một cấp quyền chính cho mỗi tài khoản. Chọn cấp quyền đúng với trách nhiệm vận hành.</p>
            <div className="role-choice-grid">
              {ROLE_OPTIONS.map((role) => (
                <label className="role-choice" key={role.value}>
                  <input name="role" type="radio" value={role.value} defaultChecked={roleTarget.role === role.value} />
                  <span>
                    <strong>{role.label}</strong>
                    <small>{role.hint}</small>
                  </span>
                </label>
              ))}
            </div>
            <div className="modal-actions">
              <button type="submit" disabled={isSaving}>{isSaving ? 'Đang lưu' : 'Hoàn tất'}</button>
              <button type="button" className="secondary" onClick={() => setRoleTarget(null)}>Đóng</button>
            </div>
          </form>
        </UserModal>
      ) : null}

      {activityTarget ? (
        <UserModal title={`Lịch sử đăng nhập: ${activityTarget.username}`} kicker="Nhật ký truy cập" onClose={() => setActivityTarget(null)} wide>
          <div className="user-activity-modal">
            {isActivityLoading ? <p className="user-modal-note">Đang tải lịch sử đăng nhập...</p> : null}
            {!isActivityLoading && !activityRows.length ? (
              <p className="user-modal-note">Chưa có bản ghi login/logout cho tài khoản này từ lúc bật audit đăng nhập.</p>
            ) : null}
            {activityRows.length ? (
              <div className="login-history-table-wrap">
                <table className="login-history-table">
                  <thead>
                    <tr>
                      <th>Thời gian</th>
                      <th>Hành động</th>
                      <th>IP</th>
                      <th>Vị trí</th>
                      <th>Thiết bị</th>
                      <th>VPN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activityRows.map((row) => (
                      <tr key={`${row.action}-${row.created_at}-${row.ip_address || 'unknown'}`}>
                        <td>{formatDateTime(row.created_at)}</td>
                        <td><span className={row.success ? 'login-action is-success' : 'login-action is-failed'}>{actionLabel(row)}</span></td>
                        <td>{row.ip_address || '-'}</td>
                        <td>{row.location || row.isp || 'Chưa xác định'}</td>
                        <td>{[row.device_os, row.browser].filter(Boolean).join(' / ') || shortUserAgent(row.user_agent)}</td>
                        <td><span className={row.is_vpn ? 'vpn-pill is-vpn' : row.is_vpn === false ? 'vpn-pill' : 'vpn-pill is-unknown'}>{vpnLabel(row.is_vpn)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            <p className="user-modal-note">VPN/IP location chỉ chính xác khi có nguồn enrich log như Nginx/VPN gateway hoặc GeoIP nội bộ. Hiện hệ thống đã lưu trường dữ liệu thật và đánh dấu chưa xác định khi chưa có nguồn xác minh.</p>
          </div>
        </UserModal>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <span><strong>{value}</strong><small>{label}</small></span>;
}

function UserModal({ title, kicker, children, onClose, wide }: { title: string; kicker: string; children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  return (
    <div className="user-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className={wide ? 'user-modal user-modal-wide' : 'user-modal'} role="dialog" aria-modal="true" aria-labelledby="user-modal-title">
        <div className="modal-header">
          <div>
            <span className="modal-kicker">{kicker}</span>
            <h2 id="user-modal-title">{title}</h2>
          </div>
          <button type="button" className="modal-close" aria-label="Đóng" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </section>
    </div>
  );
}

function RoleSelect({ name, defaultValue = 0 }: { name: string; defaultValue?: number }) {
  return (
    <select name={name} defaultValue={defaultValue}>
      {ROLE_OPTIONS.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
    </select>
  );
}

function roleLabel(role: number) {
  return ROLE_OPTIONS.find((item) => item.value === role)?.label || 'Chỉ xem';
}

function userInitial(username: string) {
  return username.trim().charAt(0).toUpperCase() || '?';
}

function stableUserId(username: string) {
  let hash = 0;
  for (const char of username) hash = (hash * 31 + char.charCodeAt(0)) % 997;
  return String(hash).padStart(3, '0');
}

function formatActivity(value: string) {
  if (!value) return 'Chưa có hoạt động';
  return `Cập nhật ${formatDateTime(value)}`;
}

function formatDateTime(value: string) {
  if (!value) return 'Chưa có dữ liệu';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Chưa có dữ liệu';
  return date.toLocaleString('vi-VN');
}

function actionLabel(row: UserLoginEvent) {
  if (!row.success) return 'Thất bại';
  return row.action === 'logout' ? 'Đăng xuất' : 'Đăng nhập';
}

function vpnLabel(value: boolean | null) {
  if (value === true) return 'Có';
  if (value === false) return 'Không';
  return 'N/A';
}

function shortUserAgent(value: string | null) {
  if (!value) return 'Chưa xác định';
  return value.length > 38 ? `${value.slice(0, 38)}...` : value;
}

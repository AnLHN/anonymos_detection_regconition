'use client';

import { useAdminData } from '@/components/AdminShell';
import UsersPanel from '@/components/UsersPanel';
import { hasPermission } from '@/lib/permissions';

export default function UsersPage() {
  const { currentUser, token } = useAdminData();

  if (!hasPermission(currentUser, 'users:read')) {
    return <section className="card"><h2>Không đủ quyền</h2><p>Chỉ tài khoản admin_super được quản lý user.</p></section>;
  }

  return <UsersPanel token={token} />;
}

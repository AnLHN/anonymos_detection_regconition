'use client';

import { useAdminData } from '@/components/AdminShell';
import CamerasPanel from '@/components/CamerasPanel';
import { hasPermission } from '@/lib/permissions';

export default function CamerasPage() {
  const { token, cameras, currentUser, refresh } = useAdminData();

  return (
    <section className="page-grid">
      <CamerasPanel
        token={token}
        cameras={cameras}
        onRefresh={refresh}
        canCreate={hasPermission(currentUser, 'cameras:create')}
        canUpdate={hasPermission(currentUser, 'cameras:update')}
      />
    </section>
  );
}

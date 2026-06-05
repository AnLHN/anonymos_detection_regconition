'use client';

import { useAdminData } from '@/components/AdminShell';
import AlertsPanel from '@/components/AlertsPanel';
import { hasPermission } from '@/lib/permissions';

export default function AlertsPage() {
  const { token, alerts, currentUser, refresh } = useAdminData();

  return (
    <section className="page-grid page-grid-alerts">
      <AlertsPanel token={token} alerts={alerts} onRefresh={refresh} isSuperAdmin={hasPermission(currentUser, 'alerts:delete')} />
    </section>
  );
}

'use client';

import { useAdminData } from '@/components/AdminShell';
import AlertsPanel from '@/components/AlertsPanel';

export default function AlertsPage() {
  const { token, alerts, refresh, markAlertRead } = useAdminData();

  return (
    <section className="page-grid page-grid-alerts">
      <AlertsPanel token={token} alerts={alerts} onRefresh={refresh} onMarkRead={markAlertRead} />
    </section>
  );
}

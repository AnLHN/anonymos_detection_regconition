'use client';

import { useAdminData } from '@/components/AdminShell';
import RulesPanel from '@/components/RulesPanel';
import { hasPermission } from '@/lib/permissions';

export default function RulesPage() {
  const { token, rules, currentUser, refresh } = useAdminData();

  return (
    <section className="page-grid">
      <RulesPanel
        token={token}
        rules={rules}
        onRefresh={refresh}
        canUpdate={hasPermission(currentUser, 'rules:update')}
      />
    </section>
  );
}

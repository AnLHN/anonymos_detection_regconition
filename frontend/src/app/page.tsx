'use client';

import { useAdminData } from '@/components/AdminShell';
import DashboardHome from '@/components/DashboardHome';

export default function Home() {
  const { alerts, cameras, rules, employees } = useAdminData();

  return (
    <>
      <DashboardHome alerts={alerts} cameras={cameras} rules={rules} employees={employees} />
    </>
  );
}

'use client';

import { useAdminData } from '@/components/AdminShell';
import EmployeesList from '@/components/EmployeesList';

export default function EmployeesPage() {
  const { employees } = useAdminData();

  return (
    <section className="page-grid">
      <article className="card">
        <h2>Quản lý nhân viên</h2>
        <EmployeesList employees={employees} />
      </article>
    </section>
  );
}

'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useAdminData } from '@/components/AdminShell';
import { enrollEmployeeFromCamera } from '@/lib/api';
import { hasPermission } from '@/lib/permissions';
import type { Employee } from '@/lib/types';

const PAGE_SIZE_OPTIONS = [6, 12, 24] as const;
type NumericPageSize = (typeof PAGE_SIZE_OPTIONS)[number];
type PageSize = NumericPageSize | 'all';

export default function EmployeesList({ employees }: { employees: Employee[] }) {
  const { token, currentUser, cameras, refresh } = useAdminData();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState<PageSize>(12);
  const [query, setQuery] = useState('');
  const [department, setDepartment] = useState('');
  const [status, setStatus] = useState('');
  const [empCode, setEmpCode] = useState('');
  const [name, setName] = useState('');
  const [newDepartment, setNewDepartment] = useState('');
  const [cameraId, setCameraId] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [formMessage, setFormMessage] = useState('');
  const activeCameras = useMemo(() => cameras.filter((camera) => camera.source_type === 'rtsp' && camera.is_active), [cameras]);
  const canManageEmployees = hasPermission(currentUser, 'employees:create');
  const departments = useMemo(() => [...new Set(employees.map((employee) => employee.department).filter(Boolean))].sort(), [employees]);
  const filteredEmployees = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return employees.filter((employee) => {
      const matchesQuery = !normalizedQuery || employee.name.toLowerCase().includes(normalizedQuery) || employee.emp_code.toLowerCase().includes(normalizedQuery);
      const matchesDepartment = !department || employee.department === department;
      const matchesStatus = !status || (status === 'active' ? employee.is_active : !employee.is_active);
      return matchesQuery && matchesDepartment && matchesStatus;
    });
  }, [department, employees, query, status]);
  const effectivePageSize = pageSize === 'all' ? Math.max(1, filteredEmployees.length) : pageSize;
  const totalPages = pageSize === 'all' ? 1 : Math.max(1, Math.ceil(filteredEmployees.length / effectivePageSize));
  const currentPage = Math.min(page, totalPages - 1);
  const start = pageSize === 'all' ? 0 : currentPage * effectivePageSize;
  const end = pageSize === 'all' ? filteredEmployees.length : Math.min(start + effectivePageSize, filteredEmployees.length);
  const visibleEmployees = useMemo(() => filteredEmployees.slice(start, end), [filteredEmployees, start, end]);

  useEffect(() => {
    setPage(0);
  }, [query, department, pageSize, status]);

  useEffect(() => {
    if (!cameraId && activeCameras[0]) {
      setCameraId(activeCameras[0].camera_id);
    }
  }, [activeCameras, cameraId]);

  async function handleEnroll(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError('');
    setFormMessage('');
    if (!empCode.trim() || !name.trim() || !cameraId) {
      setFormError('Cần nhập mã NV, họ tên và chọn camera.');
      return;
    }
    setSaving(true);
    try {
      await enrollEmployeeFromCamera(token, {
        emp_code: empCode.trim(),
        name: name.trim(),
        department: newDepartment.trim(),
        camera_id: cameraId,
      });
      setEmpCode('');
      setName('');
      setNewDepartment('');
      setFormMessage('Đã chụp khuôn mặt và thêm nhân viên.');
      await refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Không thêm được nhân viên');
    } finally {
      setSaving(false);
    }
  }

  function handlePageSizeChange(value: string) {
    setPageSize(value === 'all' ? 'all' : Number(value) as NumericPageSize);
  }

  return (
    <div className="employee-workspace">
      <div className="filter-bar employee-filter-bar">
        <label>
          Tìm nhân viên
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tên hoặc mã nhân viên" />
        </label>
        <label>
          Phòng ban
          <select value={department} onChange={(event) => setDepartment(event.target.value)}>
            <option value="">Tất cả phòng ban</option>
            {departments.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label>
          Trạng thái
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Tất cả trạng thái</option>
            <option value="active">Đang active</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
      </div>

      <div className={`employee-main-grid ${canManageEmployees ? '' : 'without-enroll'}`}>
        {canManageEmployees ? (
          <form className="compact-form employee-enroll-form employee-enroll-panel" onSubmit={handleEnroll}>
            <div className="rule-editor-heading">
              <strong>Thêm nhân viên bằng camera</strong>
              <span>Cho nhân viên đứng trước camera, chỉ để một khuôn mặt trong khung rồi bấm chụp.</span>
            </div>
            <div className="employee-enroll-fields">
              <label>
                Mã NV
                <input value={empCode} onChange={(event) => setEmpCode(event.target.value)} placeholder="NV001" required />
              </label>
              <label>
                Họ tên
                <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Nguyễn Văn A" required />
              </label>
              <label>
                Phòng ban
                <input value={newDepartment} onChange={(event) => setNewDepartment(event.target.value)} placeholder="IT" />
              </label>
              <label>
                Camera chụp mặt
                <select value={cameraId} onChange={(event) => setCameraId(event.target.value)} required>
                  <option value="">Chọn camera</option>
                  {activeCameras.map((camera) => <option key={camera.camera_id} value={camera.camera_id}>{camera.name || camera.camera_id}</option>)}
                </select>
              </label>
            </div>
            <button type="submit" disabled={saving || !activeCameras.length}>{saving ? 'Đang chụp và enroll...' : 'Chụp và thêm nhân viên'}</button>
            {!activeCameras.length ? <span className="error">Chưa có camera RTSP active để chụp khuôn mặt.</span> : null}
            {formError ? <span className="error">{formError}</span> : null}
            {formMessage ? <span className="success">{formMessage}</span> : null}
          </form>
        ) : null}

        <section className="employee-list-panel">
          <div className="employee-list-summary">
            <span>
              Hiển thị {filteredEmployees.length ? start + 1 : 0}-{end} / {filteredEmployees.length} nhân viên
            </span>
            <label className="employee-page-size">
              Số dòng
              <select value={String(pageSize)} onChange={(event) => handlePageSizeChange(event.target.value)}>
                {PAGE_SIZE_OPTIONS.map((size) => <option key={size} value={size}>{size}</option>)}
                <option value="all">Tất cả</option>
              </select>
            </label>
            <strong>Trang {currentPage + 1}/{totalPages}</strong>
          </div>
          <div className="list employee-list">
            {visibleEmployees.length ? visibleEmployees.map((employee) => (
              <div className="item employee-item" key={employee.id}>
                <strong>{employee.name}</strong>
                <span>Mã NV: {employee.emp_code || 'N/A'}</span>
                <span>Phòng ban: {employee.department || 'Chưa có phòng ban'}</span>
              </div>
            )) : <div className="item"><strong>Không tìm thấy nhân viên</strong><span>Thử đổi từ khóa hoặc bộ lọc.</span></div>}
          </div>
          {totalPages > 1 ? (
            <div className="pagination-controls">
              <button className="secondary" type="button" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={currentPage === 0}>
                Trước
              </button>
              <span>{currentPage + 1} / {totalPages}</span>
              <button className="secondary" type="button" onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))} disabled={currentPage === totalPages - 1}>
                Sau
              </button>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

'use client';

import Image from 'next/image';
import Link from 'next/link';

export default function RegisterPage() {
  return (
    <main className="login-shell">
      <section className="card login-card">
        <div className="login-brand">
          <Image src="/ntc-logo.png" alt="NTC AI" width={120} height={72} priority />
          <div className="login-brand-copy">
            <span>Tài khoản nội bộ</span>
            <h1>NTC Stranger Detect</h1>
            <p>Hệ thống giám sát và nhận diện camera</p>
          </div>
        </div>
        <p className="auth-lead" style={{ margin: '24px 0 16px', textAlign: 'center', fontWeight: 'bold' }}>
          Đăng ký tài khoản hiện không khả dụng công khai.
        </p>
        <p style={{ color: '#607086', fontSize: 14, lineHeight: 1.5, textAlign: 'center', marginBottom: 24 }}>
          Tài khoản truy cập hệ thống chỉ được cấp bởi quản trị viên hệ thống. Vui lòng liên hệ quản trị viên để nhận thông tin đăng nhập.
        </p>
        <Link className="button" href="/login" style={{ width: '100%', display: 'inline-grid', placeItems: 'center' }}>
          Đến trang đăng nhập
        </Link>
      </section>
    </main>
  );
}

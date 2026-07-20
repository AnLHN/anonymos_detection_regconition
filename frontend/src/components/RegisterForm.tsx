'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';
import { ApiError, register } from '@/lib/api';
import { setToken } from '@/lib/auth';

export default function RegisterForm() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const data = await register(username.trim(), email.trim(), password);
      setToken(data.access_token);
      router.replace('/');
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('Username hoặc email đã tồn tại. Hãy đăng nhập hoặc dùng thông tin khác.');
      } else {
        setError(err instanceof Error ? err.message : 'Đăng ký thất bại');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="card login-card">
      <div className="login-brand">
        <Image src="/ntc-logo.png" alt="NTC AI" width={120} height={72} priority />
        <div className="login-brand-copy">
          <span>Tài khoản quản trị</span>
          <h1>NTC Stranger Detect</h1>
          <p>Tạo quyền truy cập dashboard giám sát</p>
        </div>
      </div>
      <p className="auth-lead">Đăng ký tài khoản quản trị để truy cập hệ thống giám sát.</p>
      <form className="login-form" onSubmit={handleSubmit}>
        <label className="auth-field">
          <span>Username</span>
          <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Tối thiểu 3 ký tự" minLength={3} required />
        </label>
        <label className="auth-field">
          <span>Email</span>
          <input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@company.com" required />
        </label>
        <label className="auth-field">
          <span>Password</span>
          <input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Tối thiểu 6 ký tự" minLength={6} required />
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Đang tạo tài khoản...' : 'Đăng ký'}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <p className="auth-switch">
        Đã có tài khoản? <Link href="/login">Đăng nhập</Link>
      </p>
    </section>
  );
}

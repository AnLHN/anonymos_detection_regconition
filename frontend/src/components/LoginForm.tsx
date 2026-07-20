'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';
import { ApiError, login } from '@/lib/api';
import { setToken } from '@/lib/auth';

export default function LoginForm({ onLogin }: { onLogin?: (token: string) => void }) {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const data = await login(username.trim(), password);
      setToken(data.access_token);
      onLogin?.(data.access_token);
      router.replace('/');
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('Sai username hoặc password.');
      } else {
        setError(err instanceof Error ? err.message : 'Đăng nhập thất bại');
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
          <span>Bảng điều hành</span>
          <h1>NTC Stranger Detect</h1>
          <p>Giám sát camera và nhận diện realtime</p>
        </div>
      </div>
      <p className="auth-lead">Đăng nhập để xem dashboard giám sát.</p>
      <form className="login-form" onSubmit={handleSubmit}>
        <label className="auth-field">
          <span>Tên đăng nhập</span>
          <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Nhập tên đăng nhập" required />
        </label>
        <label className="auth-field">
          <span>Mật khẩu</span>
          <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Nhập mật khẩu" required />
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}

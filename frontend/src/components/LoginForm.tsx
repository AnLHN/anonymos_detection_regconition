'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';
import { login } from '@/lib/api';
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
      setError(err instanceof Error ? err.message : 'Đăng nhập thất bại');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="card login-card">
      <div className="login-brand">
        <Image src="/ntc-logo.png" alt="NTC" width={120} height={72} priority />
        <h1>NTC Anonymous Detection & Recognition</h1>
      </div>
      <p>Đăng nhập để xem dashboard giám sát.</p>
      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          Username
          <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </button>
      </form>
      <p className="auth-switch">
        Chưa có tài khoản? <Link href="/register">Đăng ký</Link>
      </p>
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}

'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';
import { register } from '@/lib/api';
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
      setError(err instanceof Error ? err.message : 'Đăng ký thất bại');
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
      <p>Đăng ký tài khoản quản trị để truy cập hệ thống giám sát.</p>
      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          Username
          <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} required />
        </label>
        <label>
          Email
          <input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={6} required />
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Đang tạo tài khoản...' : 'Đăng ký'}
        </button>
      </form>
      <p className="auth-switch">
        Đã có tài khoản? <Link href="/login">Đăng nhập</Link>
      </p>
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}

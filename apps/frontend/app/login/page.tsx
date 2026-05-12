'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { apiFetch, setToken } from '../../lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@rocks.stream');
  const [password, setPassword] = useState('ChangeMe123!');
  const [error, setError] = useState('');

  return (
    <div className="card" style={{ maxWidth: 420, margin: '40px auto' }}>
      <h2>Admin login</h2>
      <div style={{ marginBottom: 12 }}>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      {error ? <p style={{ color: '#fecaca' }}>{error}</p> : null}
      <button
        className="primary"
        onClick={async () => {
          try {
            const result = await apiFetch('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
            setToken(result.access_token);
            router.push('/dashboard');
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed');
          }
        }}
      >
        Login
      </button>
    </div>
  );
}

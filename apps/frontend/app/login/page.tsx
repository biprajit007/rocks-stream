'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { apiFetch, setToken } from '../../lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('rockstreamer');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  return (
    <div className="card" style={{ maxWidth: 420, margin: '40px auto' }}>
      <h2>Admin login</h2>
      <div style={{ marginBottom: 12 }}>
        <label>Username</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
      </div>
      {error ? <p style={{ color: '#fecaca' }}>{error}</p> : null}
      <button
        className="primary"
        onClick={async () => {
          try {
            const result = await apiFetch('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
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

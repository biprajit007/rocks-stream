export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api/v1';

export function getToken() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('rocks_stream_token') || '';
}

export function setToken(token: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('rocks_stream_token', token);
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: 'no-store' });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.text();
}

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api/v1';

export function getToken() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('rocks_stream_token') || '';
}

export function setToken(token: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('rocks_stream_token', token);
  document.cookie = `rocks_stream_token=${token}; Path=/; Max-Age=${60 * 60 * 24 * 7}; SameSite=Lax${location.protocol === 'https:' ? '; Secure' : ''}`;
}

export function clearToken() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('rocks_stream_token');
  document.cookie = 'rocks_stream_token=; Path=/; Max-Age=0; SameSite=Lax';
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: 'no-store' });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;
    try {
      const parsed = JSON.parse(text);
      message = parsed.detail || parsed.message || text;
    } catch {}

    if (response.status === 401 && token && typeof window !== 'undefined' && !path.startsWith('/auth/login')) {
      clearToken();
      window.location.href = '/login';
    }

    throw new Error(message);
  }
  return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.text();
}

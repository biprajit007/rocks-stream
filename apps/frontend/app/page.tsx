import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="card" style={{ maxWidth: 520, margin: '40px auto' }}>
      <h2>Rocks Stream Portal</h2>
      <p className="muted">Authentication required. Sign in to access the streaming control panel.</p>
      <div className="row">
        <Link className="primary" href="/login">Go to login</Link>
      </div>
    </div>
  );
}

import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="grid grid-2">
      <div className="card">
        <h2>Operate live streams cleanly</h2>
        <p className="muted">Manage ingest, outputs, ABR ladders, overlays, previews, and pipeline lifecycle from one admin portal.</p>
        <div className="row">
          <Link className="primary" href="/login">Admin login</Link>
          <Link className="secondary" href="/dashboard">Open dashboard</Link>
        </div>
      </div>
      <div className="card">
        <h3>Built-in protocols</h3>
        <ul>
          <li>SRT ingest/output</li>
          <li>RTMP ingest/output</li>
          <li>HLS ingest/output + ABR master playlist</li>
          <li>Logo overlay positioning</li>
        </ul>
      </div>
    </div>
  );
}

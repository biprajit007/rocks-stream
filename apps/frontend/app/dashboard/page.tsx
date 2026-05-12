'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

type Stream = {
  id: number;
  name: string;
  stream_key: string;
  status: string;
  abr_enabled: boolean;
  playback_urls: { hls?: string | null; master_hls?: string | null; rtmp?: string | null; srt?: string | null };
};

const defaultStream = {
  name: 'Main Channel',
  stream_key: 'main-channel',
  description: 'Primary live stream',
  abr_enabled: true,
  inputs: [{ name: 'Primary RTMP', protocol: 'rtmp', source_url: 'rtmp://example.com/live/source', priority: 1, is_enabled: true }],
  outputs: [{ output_type: 'hls', is_enabled: true }, { output_type: 'rtmp', is_enabled: true }, { output_type: 'srt', is_enabled: true }],
  abr_profiles: []
};

export default function DashboardPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [error, setError] = useState('');

  async function load() {
    try {
      setStreams(await apiFetch('/streams'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load streams');
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="grid">
      <div className="card">
        <div className="row space">
          <div>
            <h2>Dashboard</h2>
            <p className="muted">Create streams, inspect generated URLs, and control pipeline state.</p>
          </div>
          <button className="primary" onClick={async () => { await apiFetch('/streams', { method: 'POST', body: JSON.stringify(defaultStream) }); await load(); }}>Create sample stream</button>
        </div>
        {error ? <p style={{ color: '#fecaca' }}>{error}</p> : null}
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Key</th>
              <th>Status</th>
              <th>Outputs</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {streams.map((stream) => (
              <tr key={stream.id}>
                <td>{stream.name}</td>
                <td><code>{stream.stream_key}</code></td>
                <td><span className={`badge ${stream.status}`}>{stream.status}</span></td>
                <td>
                  <div className="muted">HLS: {stream.playback_urls.hls || '-'}</div>
                  <div className="muted">RTMP: {stream.playback_urls.rtmp || '-'}</div>
                  <div className="muted">SRT: {stream.playback_urls.srt || '-'}</div>
                </td>
                <td>
                  <div className="row">
                    <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/start`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Start</button>
                    <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/stop`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Stop</button>
                    <Link className="secondary" href={`/streams/${stream.id}`}>Open</Link>
                  </div>
                </td>
              </tr>
            ))}
            {!streams.length ? <tr><td colSpan={5} className="muted">No streams yet.</td></tr> : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

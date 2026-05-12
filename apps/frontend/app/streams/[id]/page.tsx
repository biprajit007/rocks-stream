'use client';

import { useEffect, useState } from 'react';
import HlsPlayer from '../../../components/HlsPlayer';
import LogoEditor from '../../../components/LogoEditor';
import { apiFetch } from '../../../lib/api';

export default function StreamDetailPage({ params }: { params: { id: string } }) {
  const [stream, setStream] = useState<any>(null);
  const [error, setError] = useState('');
  const [newInput, setNewInput] = useState({ name: 'Backup Input', protocol: 'srt', source_url: 'srt://backup.example.com:9000?streamid=backup', priority: 2, is_enabled: true });
  const [newOutput, setNewOutput] = useState({ output_type: 'hls', is_enabled: true, port: '' });
  const [newProfile, setNewProfile] = useState({ name: '540p', width: 960, height: 540, bitrate_kbps: 1800, playlist_name: '540p.m3u8', is_enabled: true });

  async function load() {
    try {
      setStream(await apiFetch(`/streams/${params.id}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stream');
    }
  }

  useEffect(() => { load(); }, [params.id]);

  if (!stream) return <div className="card">Loading… {error}</div>;

  const urls = stream.playback_urls || {};

  return (
    <div className="grid grid-2">
      <div className="card">
        <h2>{stream.name}</h2>
        <p className="muted">Key: <code>{stream.stream_key}</code></p>
        {error ? <p style={{ color: '#fecaca' }}>{error}</p> : null}
        <div className="row">
          <span className={`badge ${stream.status}`}>{stream.status}</span>
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/restart`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Restart</button>
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/start`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Start</button>
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/stop`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Stop</button>
        </div>
        <h3>Generated URLs</h3>
        {Object.entries({ HLS: urls.hls, 'Master HLS': urls.master_hls, RTMP: urls.rtmp, SRT: urls.srt }).map(([label, value]) => (
          <div key={label} className="row" style={{ marginBottom: 8 }}>
            <div className="code" style={{ flex: 1 }}>{label}: {value || '-'}</div>
            {value ? <button className="secondary" onClick={() => navigator.clipboard.writeText(String(value))}>Copy</button> : null}
          </div>
        ))}
        <h3>Overlay editor</h3>
        <LogoEditor
          x={stream.logo_x}
          y={stream.logo_y}
          onChange={(x, y) => setStream({ ...stream, logo_x: x, logo_y: y })}
        />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="primary" onClick={async () => {
            await apiFetch(`/streams/${stream.id}`, { method: 'PATCH', body: JSON.stringify({ logo_x: stream.logo_x, logo_y: stream.logo_y, logo_enabled: true, logo_position_mode: 'coordinates' }) });
            await load();
          }}>Save overlay position</button>
          <input type="file" accept="image/*" onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const form = new FormData();
            form.append('file', file);
            await apiFetch(`/streams/${stream.id}/logo`, { method: 'POST', body: form });
            await load();
          }} />
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}`, { method: 'PATCH', body: JSON.stringify({ abr_enabled: !stream.abr_enabled }) }); await load(); }}>
            {stream.abr_enabled ? 'Disable ABR' : 'Enable ABR'}
          </button>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>Preview</h3>
          {urls.hls ? <HlsPlayer src={urls.master_hls || urls.hls} /> : <p className="muted">Enable HLS output to preview here.</p>}
        </div>
        <div className="card">
          <h3>Inputs</h3>
          <table className="table">
            <thead><tr><th>Name</th><th>Protocol</th><th>Priority</th><th>URL</th></tr></thead>
            <tbody>{stream.input_sources.map((item: any) => <tr key={item.id}><td>{item.name}</td><td>{item.protocol}</td><td>{item.priority}</td><td className="muted">{item.source_url}</td></tr>)}</tbody>
          </table>
          <div className="grid" style={{ marginTop: 12 }}>
            <input value={newInput.name} onChange={(e) => setNewInput({ ...newInput, name: e.target.value })} placeholder="Input name" />
            <select value={newInput.protocol} onChange={(e) => setNewInput({ ...newInput, protocol: e.target.value })}><option value="rtmp">RTMP</option><option value="srt">SRT</option><option value="hls">HLS</option></select>
            <input value={newInput.source_url} onChange={(e) => setNewInput({ ...newInput, source_url: e.target.value })} placeholder="Source URL" />
            <input type="number" value={newInput.priority} onChange={(e) => setNewInput({ ...newInput, priority: Number(e.target.value) })} placeholder="Priority" />
            <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/inputs`, { method: 'POST', body: JSON.stringify(newInput) }); await load(); }}>Add input</button>
          </div>
        </div>
        <div className="card">
          <h3>Outputs</h3>
          <table className="table">
            <thead><tr><th>Type</th><th>Enabled</th><th>Port</th></tr></thead>
            <tbody>{stream.output_targets.map((item: any) => <tr key={item.id}><td>{item.output_type}</td><td>{String(item.is_enabled)}</td><td>{item.port || '-'}</td></tr>)}</tbody>
          </table>
          <div className="row" style={{ marginTop: 12 }}>
            <select value={newOutput.output_type} onChange={(e) => setNewOutput({ ...newOutput, output_type: e.target.value })}><option value="hls">HLS</option><option value="rtmp">RTMP</option><option value="srt">SRT</option></select>
            <input value={newOutput.port} onChange={(e) => setNewOutput({ ...newOutput, port: e.target.value })} placeholder="Optional port" />
            <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/outputs`, { method: 'POST', body: JSON.stringify({ ...newOutput, port: newOutput.port ? Number(newOutput.port) : null }) }); await load(); }}>Add output</button>
          </div>
        </div>
        <div className="card">
          <h3>ABR profiles</h3>
          <table className="table">
            <thead><tr><th>Name</th><th>Resolution</th><th>Bitrate</th><th>Enabled</th></tr></thead>
            <tbody>{stream.abr_profiles.map((item: any) => <tr key={item.id}><td>{item.name}</td><td>{item.width}x{item.height}</td><td>{item.bitrate_kbps} kbps</td><td>{String(item.is_enabled)}</td></tr>)}</tbody>
          </table>
          <div className="grid grid-2" style={{ marginTop: 12 }}>
            <input value={newProfile.name} onChange={(e) => setNewProfile({ ...newProfile, name: e.target.value })} placeholder="Profile name" />
            <input value={newProfile.playlist_name} onChange={(e) => setNewProfile({ ...newProfile, playlist_name: e.target.value })} placeholder="Playlist name" />
            <input type="number" value={newProfile.width} onChange={(e) => setNewProfile({ ...newProfile, width: Number(e.target.value) })} placeholder="Width" />
            <input type="number" value={newProfile.height} onChange={(e) => setNewProfile({ ...newProfile, height: Number(e.target.value) })} placeholder="Height" />
            <input type="number" value={newProfile.bitrate_kbps} onChange={(e) => setNewProfile({ ...newProfile, bitrate_kbps: Number(e.target.value) })} placeholder="Bitrate kbps" />
            <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/abr-profiles`, { method: 'POST', body: JSON.stringify(newProfile) }); await load(); }}>Add profile</button>
          </div>
        </div>
        <div className="card">
          <h3>Runtime state</h3>
          <div className="code">{JSON.stringify(stream.runtime_state || {}, null, 2)}</div>
        </div>
      </div>
    </div>
  );
}

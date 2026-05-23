'use client';

import { useEffect, useState } from 'react';
import LogoEditor from '../../../components/LogoEditor';
import { apiFetch } from '../../../lib/api';

export default function StreamDetailPage({ params }: { params: { id: string } }) {
  const [stream, setStream] = useState<any>(null);
  const [adConfig, setAdConfig] = useState<any>(null);
  const [error, setError] = useState('');
  const [adError, setAdError] = useState('');
  const [logoBox, setLogoBox] = useState({ width: 120, height: 48 });

  async function load() {
    try {
      const nextStream = await apiFetch(`/streams/${params.id}`);
      setStream(nextStream);
      try {
        setAdConfig(await apiFetch(`/ads/player-config/${nextStream.stream_key}`));
        setAdError('');
      } catch (adErr) {
        setAdConfig(null);
        setAdError(adErr instanceof Error ? adErr.message : 'Failed to load ad config');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stream');
    }
  }

  useEffect(() => { load(); }, [params.id]);

  useEffect(() => {
    if (stream) {
      setLogoBox({
        width: Number(stream.logo_width) || 120,
        height: Number(stream.logo_height) || 48,
      });
    }
  }, [stream?.id]);

  if (!stream) return <div className="card">Loading… {error}</div>;

  const urls = stream.playback_urls || {};

  return (
    <div className="grid">
      <div className="card">
        <h2>{stream.name}</h2>
        <p className="muted">Key: <code>{stream.stream_key}</code></p>
        <label className="row" style={{ alignItems: 'center', marginBottom: 12 }}>
          <input
            type="checkbox"
            checked={Boolean(stream.playback_auth_enabled)}
            onChange={async (e) => {
              await apiFetch(`/streams/${stream.id}`, { method: 'PATCH', body: JSON.stringify({ playback_auth_enabled: e.target.checked }) });
              await load();
            }}
          />
          <span>Key auth encryption</span>
        </label>
        {error ? <p style={{ color: '#fecaca' }}>{error}</p> : null}
        <div className="row">
          <span className={`badge ${stream.status}`}>{stream.status}</span>
          {stream.is_primary ? <span className="badge running">main live</span> : null}
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/restart`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Restart</button>
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/start`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Start</button>
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}/stop`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Stop</button>
          <button className="primary" onClick={async () => { await apiFetch(`/streams/${stream.id}/go-live`, { method: 'POST', body: JSON.stringify({}) }); await load(); }}>Go live</button>
          <button className="danger" onClick={async () => { if (!confirm(`Delete stream ${stream.name}?`)) return; await apiFetch(`/streams/${stream.id}`, { method: 'DELETE' }); window.location.href = '/dashboard'; }}>Delete</button>
        </div>
        <h3>Generated URLs</h3>
        {Object.entries({ 'Main live HLS': urls.main_hls || 'https://keystream.rockstreamer.com/live/main/index.m3u8', HLS: urls.hls, 'Master HLS': urls.master_hls, RTMP: urls.rtmp, SRT: urls.srt }).map(([label, value]) => (
          <div key={label} className="row" style={{ marginBottom: 8 }}>
            <div className="code" style={{ flex: 1 }}>{label}: {value || '-'}</div>
            {value ? <button className="secondary" onClick={() => navigator.clipboard.writeText(String(value))}>Copy</button> : null}
          </div>
        ))}

        <h3>Player ad config</h3>
        <div className="muted tiny">Endpoint: <code>/api/v1/ads/player-config/{stream.stream_key}</code></div>
        {adError ? <p style={{ color: '#fecaca' }}>{adError}</p> : null}
        <div className="card" style={{ padding: 12, marginTop: 10, background: 'var(--panel-soft)' }}>
          <div className="row space">
            <strong>{adConfig?.enabled ? 'Ads enabled' : 'Ads disabled'}</strong>
            <button className="secondary" onClick={() => navigator.clipboard.writeText(`/api/v1/ads/player-config/${stream.stream_key}`)}>Copy endpoint</button>
          </div>
          <div className="grid grid-2" style={{ marginTop: 10 }}>
            <div className="muted">Provider: <strong>{adConfig?.provider || '—'}</strong></div>
            <div className="muted">Rules: <strong>{adConfig?.mid_roll_rules?.length || 0}</strong></div>
            <div className="muted">Pre-roll: <strong>{adConfig?.pre_roll?.tag_url ? 'set' : 'none'}</strong></div>
            <div className="muted">Mid-roll: <strong>{adConfig?.mid_roll?.tag_url ? 'set' : 'none'}</strong></div>
            <div className="muted">Post-roll: <strong>{adConfig?.post_roll?.tag_url ? 'set' : 'none'}</strong></div>
            <div className="muted">Video ad: <strong>{adConfig?.video_ad?.tag_url ? 'set' : 'none'}</strong></div>
          </div>
          <div className="code" style={{ marginTop: 12, whiteSpace: 'pre-wrap' }}>{JSON.stringify(adConfig || {}, null, 2)}</div>
        </div>

        <h3>Overlay editor</h3>
        <LogoEditor
          x={stream.logo_x}
          y={stream.logo_y}
          width={logoBox.width}
          height={logoBox.height}
          onChange={(x, y) => setStream({ ...stream, logo_x: x, logo_y: y })}
          onSizeChange={(width, height) => setLogoBox({ width, height })}
        />
        <div className="card" style={{ padding: 12, marginTop: 12 }}>
          <div className="row space">
            <strong>Logo status</strong>
            <span className={`badge ${stream.logo_enabled ? 'running' : 'stopped'}`}>{stream.logo_enabled ? 'enabled' : 'disabled'}</span>
          </div>
          <div className="grid grid-2" style={{ marginTop: 10 }}>
            <div className="muted">Uploaded: <strong>{stream.logo_asset_id ? 'yes' : 'no'}</strong></div>
            <div className="muted">Size: <strong>{logoBox.width} × {logoBox.height}</strong></div>
            <div className="muted">Position X: <strong>{stream.logo_x}</strong></div>
            <div className="muted">Position Y: <strong>{stream.logo_y}</strong></div>
          </div>
        </div>
        <div className="card" style={{ padding: 12, marginTop: 12, background: 'var(--panel-soft)' }}>
          <div className="row space">
            <strong>Logo upload</strong>
            <span className="muted tiny">Upload and place inside the editor area</span>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <input type="file" accept="image/*" onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const dimensions = await new Promise<{ width: number; height: number }>((resolve) => {
                const objectUrl = URL.createObjectURL(file);
                const img = new Image();
                img.onload = () => {
                  const maxWidth = Math.min(220, Math.max(80, img.naturalWidth));
                  const scaledHeight = Math.max(24, Math.round((img.naturalHeight / Math.max(1, img.naturalWidth)) * maxWidth));
                  URL.revokeObjectURL(objectUrl);
                  resolve({ width: maxWidth, height: scaledHeight });
                };
                img.onerror = () => {
                  URL.revokeObjectURL(objectUrl);
                  resolve({ width: 120, height: 48 });
                };
                img.src = objectUrl;
              });
              const form = new FormData();
              form.append('file', file);
              await apiFetch(`/streams/${stream.id}/logo`, { method: 'POST', body: form });
              setLogoBox(dimensions);
              await apiFetch(`/streams/${stream.id}`, { method: 'PATCH', body: JSON.stringify({ logo_width: dimensions.width, logo_height: dimensions.height, logo_enabled: true, logo_position_mode: 'coordinates' }) });
              await load();
            }} />
          </div>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="primary" onClick={async () => {
            await apiFetch(`/streams/${stream.id}`, { method: 'PATCH', body: JSON.stringify({ logo_x: stream.logo_x, logo_y: stream.logo_y, logo_width: logoBox.width, logo_height: logoBox.height, logo_enabled: true, logo_position_mode: 'coordinates' }) });
            await load();
          }}>Save logo settings</button>
          <button className="secondary" onClick={async () => {
            await apiFetch(`/streams/${stream.id}`, { method: 'PATCH', body: JSON.stringify({ logo_enabled: !stream.logo_enabled, logo_width: logoBox.width, logo_height: logoBox.height }) });
            await load();
          }}>{stream.logo_enabled ? 'Disable logo' : 'Enable logo'}</button>
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="secondary" onClick={async () => { await apiFetch(`/streams/${stream.id}`, { method: 'PATCH', body: JSON.stringify({ abr_enabled: !stream.abr_enabled }) }); await load(); }}>
            {stream.abr_enabled ? 'Disable ABR' : 'Enable ABR'}
          </button>
        </div>
      </div>

    </div>
  );
}

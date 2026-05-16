'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import HlsPlayer from '../../components/HlsPlayer';
import { apiFetch } from '../../lib/api';
import {
  DEFAULT_ABR_PROFILES,
  OUTPUT_TYPES,
  PROTOCOLS,
  buildInputSourceUrl,
  buildOutputPreview,
  createDefaultInputDraft,
  createDefaultOutputDraft,
} from '../../lib/stream-ui';

type StreamSummary = {
  id: number;
  name: string;
  stream_key: string;
  status: string;
  abr_enabled: boolean;
  is_primary?: boolean;
  is_enabled?: boolean;
  logo_enabled?: boolean;
  description?: string | null;
  input_sources?: Array<any>;
  output_targets?: Array<any>;
  abr_profiles?: Array<any>;
  runtime_state?: any;
  playback_urls: { hls?: string | null; master_hls?: string | null; main_hls?: string | null; rtmp?: string | null; srt?: string | null };
};

type StreamDetail = StreamSummary & {
  description?: string | null;
  is_enabled?: boolean;
  logo_enabled?: boolean;
  logo_x?: number;
  logo_y?: number;
  input_sources?: Array<any>;
  output_targets?: Array<any>;
  abr_profiles?: Array<any>;
  runtime_state?: any;
};

type StreamLog = { id: number; level: string; message: string; created_at: string };

type StreamFormState = {
  name: string;
  stream_key: string;
  description: string;
  is_enabled: boolean;
  abr_enabled: boolean;
  input_protocol: 'hls' | 'rtmp' | 'srt';
  input: ReturnType<typeof createDefaultInputDraft>;
  output_type: 'hls' | 'rtmp' | 'srt';
  output: ReturnType<typeof createDefaultOutputDraft>;
  abr_selected: string[];
};

function slugifyStreamKey(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-');
}

const makeDefaultForm = (index = 1): StreamFormState => ({
  name: `Stream ${index}`,
  stream_key: `stream-${index}`,
  description: '',
  is_enabled: true,
  abr_enabled: false,
  input_protocol: 'srt',
  input: createDefaultInputDraft('srt'),
  output_type: 'hls',
  output: createDefaultOutputDraft('hls'),
  abr_selected: DEFAULT_ABR_PROFILES.map((profile) => profile.name),
});

const tabItems = [
  { key: 'overview', label: 'Overview' },
  { key: 'inputs', label: 'Inputs' },
  { key: 'outputs', label: 'Outputs' },
  { key: 'abr', label: 'ABR' },
  { key: 'runtime', label: 'Runtime' },
  { key: 'logs', label: 'Logs' },
] as const;

type TabKey = (typeof tabItems)[number]['key'];

function statusBadgeClass(status: string) {
  if (status === 'running') return 'running';
  if (status === 'error') return 'error';
  return 'stopped';
}

function streamProtocols(stream: StreamSummary | StreamDetail | null) {
  if (!stream?.input_sources?.length) return '-';
  return stream.input_sources.map((item: any) => String(item.protocol).toUpperCase()).join(', ');
}

function streamOutputs(stream: StreamSummary | StreamDetail | null) {
  if (!stream?.output_targets?.length) return '-';
  return stream.output_targets.filter((item: any) => item.is_enabled).map((item: any) => String(item.output_type).toUpperCase()).join(', ') || '-';
}

function preferredPreviewUrl(stream: StreamSummary | StreamDetail | null) {
  if (!stream) return '';
  return stream.playback_urls.main_hls || stream.playback_urls.master_hls || stream.playback_urls.hls || '';
}

function isBrowserPlayableUrl(url: string) {
  return /^https?:\/\//.test(url) && /\.m3u8($|\?)/.test(url);
}

function inputSourcePlaceholder(protocol: 'hls' | 'rtmp' | 'srt') {
  if (protocol === 'rtmp') return 'rtmp://host:1935/app/stream-key';
  if (protocol === 'srt') return 'srt://host:9000?mode=caller';
  return 'https://origin.example.com/live/index.m3u8';
}

export default function DashboardPage() {
  const [streams, setStreams] = useState<StreamSummary[]>([]);
  const [selectedStreamId, setSelectedStreamId] = useState<number | null>(null);
  const [selectedStream, setSelectedStream] = useState<StreamDetail | null>(null);
  const [selectedLogs, setSelectedLogs] = useState<StreamLog[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'running' | 'stopped' | 'error' | 'degraded'>('all');
  const [form, setForm] = useState<StreamFormState>(makeDefaultForm(1));
  const [submitting, setSubmitting] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [previewStream, setPreviewStream] = useState<StreamSummary | StreamDetail | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewPlayer, setPreviewPlayer] = useState('videojs');
  const [previewNonce, setPreviewNonce] = useState(0);
  const [showPlayerCode, setShowPlayerCode] = useState(false);
  const [inspectorInputDraft, setInspectorInputDraft] = useState(createDefaultInputDraft('hls'));
  const [inspectorOutputDraft, setInspectorOutputDraft] = useState(createDefaultOutputDraft('hls'));
  const [inspectorAbrDraft, setInspectorAbrDraft] = useState({ name: '540p', width: 960, height: 540, bitrate_kbps: 1800, playlist_name: '540p.m3u8', is_enabled: true });

  async function loadStreams() {
    try {
      const list = await apiFetch('/streams');
      setStreams(list);
      setError('');
      if (!selectedStreamId && list.length) {
        setSelectedStreamId(list[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load streams');
    }
  }

  async function loadSelected(id: number) {
    setDetailsLoading(true);
    try {
      const [detail, logs] = await Promise.all([
        apiFetch(`/streams/${id}`),
        apiFetch(`/streams/${id}/logs`),
      ]);
      setSelectedStream(detail);
      setSelectedLogs(logs);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stream details');
    } finally {
      setDetailsLoading(false);
    }
  }

  useEffect(() => {
    loadStreams();
  }, []);

  useEffect(() => {
    if (selectedStreamId) loadSelected(selectedStreamId);
  }, [selectedStreamId]);

  useEffect(() => {
    if (!selectedStreamId) return;
    const timer = setInterval(() => {
      loadSelected(selectedStreamId);
    }, 15000);
    return () => clearInterval(timer);
  }, [selectedStreamId]);

  const inputPreview = useMemo(() => buildInputSourceUrl(form.input), [form.input]);
  const outputPreview = useMemo(() => buildOutputPreview(form.output), [form.output]);

  const filteredStreams = useMemo(() => {
    const q = query.trim().toLowerCase();
    return streams.filter((stream) => {
      const matchesQuery = !q || [stream.name, stream.stream_key, stream.status].some((value) => value?.toLowerCase().includes(q));
      const matchesStatus = statusFilter === 'all' || stream.status === statusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [streams, query, statusFilter]);

  const stats = [
    { label: 'Streams', value: streams.length },
    { label: 'Running', value: streams.filter((s) => s.status === 'running').length },
    { label: 'HLS enabled', value: streams.filter((s) => s.playback_urls.hls).length },
    { label: 'ABR enabled', value: streams.filter((s) => s.abr_enabled).length },
  ];

  async function createStream() {
    setSubmitting(true);
    setError('');
    try {
      const finalName = form.name.trim();
      const finalStreamKey = form.stream_key.trim() || slugifyStreamKey(finalName);
      const finalInputUrl = inputPreview.trim();
      if (!finalName || !finalStreamKey) {
        throw new Error('Stream name and stream key are required');
      }
      if (!finalInputUrl) {
        throw new Error(`${String(form.input_protocol).toUpperCase()} input URL is required`);
      }
      const selectedProfiles = DEFAULT_ABR_PROFILES.filter((profile) => form.abr_selected.includes(profile.name));
      const created = await apiFetch('/streams', {
        method: 'POST',
        body: JSON.stringify({
          name: finalName,
          stream_key: finalStreamKey,
          description: form.description || null,
          is_enabled: form.is_enabled,
          abr_enabled: form.abr_enabled,
          inputs: [{
            name: form.input.name,
            protocol: form.input_protocol,
            source_url: finalInputUrl,
            priority: form.input.priority,
            is_enabled: form.input.is_enabled,
          }],
          outputs: [{
            output_type: form.output_type,
            is_enabled: form.output.is_enabled,
            port: form.output.port ? Number(form.output.port) : null,
            path_suffix: form.output.path_suffix || null,
            latency_ms: form.output.latency_ms ? Number(form.output.latency_ms) : null,
          }],
          abr_profiles: form.abr_enabled ? selectedProfiles.map((profile) => ({ ...profile })) : [],
        }),
      });
      setForm(makeDefaultForm(streams.length + 2));
      setShowCreateForm(false);
      if (created?.id) {
        setSelectedStreamId(created.id);
      }
      await loadStreams();
      if (created?.id) {
        await loadSelected(created.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create stream');
    } finally {
      setSubmitting(false);
    }
  }

  function openPreview(stream: StreamSummary | StreamDetail) {
    const firstUrl = preferredPreviewUrl(stream);
    setPreviewStream(stream);
    setPreviewUrl(firstUrl);
    setPreviewPlayer('videojs');
    setPreviewNonce((value) => value + 1);
    setShowPlayerCode(false);
  }

  async function refreshSelected() {
    if (selectedStreamId) await loadSelected(selectedStreamId);
  }

  const selected = selectedStream || streams.find((s) => s.id === selectedStreamId) || null;
  const urls = selected?.playback_urls || {};
  const mainLiveUrl = selected?.playback_urls.main_hls || 'https://keystream.rockstreamer.com/live/main/index.m3u8';
  const inspectorInputPreview = useMemo(() => buildInputSourceUrl(inspectorInputDraft), [inspectorInputDraft]);
  const inspectorOutputPreview = useMemo(() => buildOutputPreview(inspectorOutputDraft), [inspectorOutputDraft]);

  function patchSelectedInput(inputId: number, patch: Record<string, any>) {
    setSelectedStream((current) => current ? ({
      ...current,
      input_sources: (current.input_sources || []).map((item: any) => item.id === inputId ? { ...item, ...patch } : item),
    }) : current);
  }

  function patchSelectedOutput(outputId: number, patch: Record<string, any>) {
    setSelectedStream((current) => current ? ({
      ...current,
      output_targets: (current.output_targets || []).map((item: any) => item.id === outputId ? { ...item, ...patch } : item),
    }) : current);
  }

  function patchSelectedAbr(profileId: number, patch: Record<string, any>) {
    setSelectedStream((current) => current ? ({
      ...current,
      abr_profiles: (current.abr_profiles || []).map((item: any) => item.id === profileId ? { ...item, ...patch } : item),
    }) : current);
  }

  return (
    <div className="grid" id="dashboard-root">
      <div className="card" id="live-realtime">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">Live realtime data</div>
            <h3 className="panel-title">Overview</h3>
          </div>
          <div className="row">
            <button className="secondary" onClick={loadStreams}>Refresh list</button>
            <button className="secondary" onClick={refreshSelected} disabled={!selectedStreamId}>Refresh selected</button>
          </div>
        </div>
        {error ? <p style={{ color: '#fecaca' }}>{error}</p> : null}
        <div className="stat-grid">
          {stats.map((item) => (
            <div key={item.label} className="stat-card">
              <div className="muted tiny">{item.label}</div>
              <div className="stat-value">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="dashboard-workspace">
        <div className="card table-card" id="monitoring">
          <div className="row space" style={{ marginBottom: 12 }}>
            <div>
              <div className="eyebrow">Library</div>
              <h3 style={{ margin: 0 }}>Streams</h3>
            </div>
            <div className="row">
              <button className="primary" onClick={() => {
                if (!showCreateForm) setForm(makeDefaultForm(streams.length + 1));
                setShowCreateForm((value) => !value);
              }}>{showCreateForm ? 'Hide create form' : 'New stream'}</button>
              <button className="secondary" onClick={loadStreams}>Refresh library</button>
              <button className="secondary" onClick={refreshSelected} disabled={!selectedStreamId}>Refresh inspector</button>
              <button className="secondary" onClick={() => selected?.playback_urls.main_hls && navigator.clipboard.writeText(String(selected.playback_urls.main_hls))} disabled={!selected?.playback_urls.main_hls}>Copy main URL</button>
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search streams" style={{ minWidth: 220 }} />
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)} style={{ minWidth: 150 }}>
                <option value="all">All statuses</option>
                <option value="running">Running</option>
                <option value="stopped">Stopped</option>
                <option value="error">Error</option>
                <option value="degraded">Degraded</option>
              </select>
            </div>
          </div>
          <div className="table-wrap interactive-table-wrap">
            <table className="table interactive-table">
              <thead>
                <tr>
                  <th>Stream</th>
                  <th>Status</th>
                  <th>Main</th>
                  <th>Input</th>
                  <th>Outputs</th>
                  <th>Playback</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredStreams.map((stream) => (
                  <tr key={stream.id} className={selectedStreamId === stream.id ? 'selected-row' : ''} onClick={() => setSelectedStreamId(stream.id)}>
                    <td>
                      <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                        {stream.status === 'running' ? <span className="live-blinker" aria-hidden="true" /> : null}
                        <strong>{stream.name}</strong>
                      </div>
                      <div className="muted tiny"><code>{stream.stream_key}</code></div>
                    </td>
                    <td><span className={`badge ${statusBadgeClass(stream.status)}`}>{stream.status}</span></td>
                    <td>{stream.is_primary ? <span className="badge running">Live</span> : <span className="muted tiny">—</span>}</td>
                    <td className="muted tiny">{streamProtocols(stream)}</td>
                    <td className="muted tiny">{streamOutputs(stream)}</td>
                    <td className="muted tiny">{stream.playback_urls.hls ? 'HLS ready' : '—'}</td>
                    <td>
                      <div className="row table-actions">
                        <button className="secondary" title="Preview stream" onClick={(e) => { e.stopPropagation(); openPreview(stream); }}>?</button>
                        <button className="secondary" onClick={(e) => { e.stopPropagation(); setSelectedStreamId(stream.id); }}>Inspect</button>
                        <button className="primary" onClick={async (e) => { e.stopPropagation(); await apiFetch(`/streams/${stream.id}/go-live`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Go live</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!filteredStreams.length ? <div className="muted" style={{ paddingTop: 12 }}>No streams match the current filter.</div> : null}
          </div>
        </div>

        <div className="card inspector-card" id="live-control">
          <div className="row space" style={{ marginBottom: 14 }}>
            <div>
              <div className="eyebrow">On-air control</div>
              <h3 style={{ margin: '4px 0 0' }}>{selected ? selected.name : 'Select a stream'}</h3>
            </div>
            {selected ? <span className={`badge ${statusBadgeClass(selected.status)}`}>{selected.status}</span> : null}
          </div>
          {!selected ? <p className="muted">Select a stream from the table to inspect it and push it live.</p> : (
            <>
              <div className="inspector-topline">
                <div className="inspector-metric">
                  <span className="muted tiny">Main URL</span>
                  <strong>{selected.is_primary ? 'Active' : 'Standby'}</strong>
                </div>
                <div className="inspector-metric">
                  <span className="muted tiny">Input</span>
                  <strong>{streamProtocols(selected)}</strong>
                </div>
                <div className="inspector-metric">
                  <span className="muted tiny">Outputs</span>
                  <strong>{streamOutputs(selected)}</strong>
                </div>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/start`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Start</button>
                <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/stop`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Stop</button>
                <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/restart`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Restart</button>
                <button className="primary" onClick={async () => { await apiFetch(`/streams/${selected.id}/go-live`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Go live</button>
                <button className="danger" onClick={async () => { if (!confirm(`Delete stream ${selected.name}?`)) return; await apiFetch(`/streams/${selected.id}`, { method: 'DELETE' }); setSelectedStreamId(null); setSelectedStream(null); setSelectedLogs([]); await loadStreams(); }}>Delete</button>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <div className="code" style={{ flex: 1 }}>Main live: {mainLiveUrl}</div>
                <button className="secondary" onClick={() => navigator.clipboard.writeText(String(mainLiveUrl))}>Copy</button>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <div className="code" style={{ flex: 1 }}>Preview: {urls.hls || '-'}</div>
                {urls.hls ? <button className="secondary" onClick={() => navigator.clipboard.writeText(String(urls.hls))}>Copy</button> : null}
              </div>
            </>
          )}
        </div>
      </div>

      {showCreateForm ? (
        <div className="modal-backdrop" onClick={() => setShowCreateForm(false)}>
          <div className="card create-stream-card modal-card" id="live-streams" onClick={(e) => e.stopPropagation()}>
            <div className="row space" style={{ marginBottom: 12 }}>
              <div>
                <div className="eyebrow">Provisioning</div>
                <h3 style={{ margin: 0 }}>Create stream</h3>
              </div>
              <div className="row">
                <button className="primary" disabled={submitting} onClick={createStream}>{submitting ? 'Creating…' : 'Create stream'}</button>
                <button className="secondary" onClick={() => setForm(makeDefaultForm())}>Reset</button>
                <button className="secondary" onClick={() => setShowCreateForm(false)}>Close</button>
              </div>
            </div>
            <div className="grid grid-2">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Stream name" />
            <input value={form.stream_key} onChange={(e) => setForm({ ...form, stream_key: e.target.value })} placeholder="Stream key" />
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description" />
            <label className="row" style={{ alignItems: 'center' }}>
              <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} />
              <span>Enabled</span>
            </label>
            <label className="row" style={{ alignItems: 'center' }}>
              <input type="checkbox" checked={form.abr_enabled} onChange={(e) => setForm({ ...form, abr_enabled: e.target.checked })} />
              <span>Enable ABR</span>
            </label>
          </div>

            <h4 style={{ marginTop: 16 }}>Input source</h4>
            <div className="grid grid-2" id="live-inputs">
            <select value={form.input_protocol} onChange={(e) => {
              const protocol = e.target.value as 'hls' | 'rtmp' | 'srt';
              setForm({ ...form, input_protocol: protocol, input: createDefaultInputDraft(protocol) });
            }}>
              {PROTOCOLS.map((protocol) => <option key={protocol.value} value={protocol.value}>{protocol.label}</option>)}
            </select>
            <input value={form.input.name} onChange={(e) => setForm({ ...form, input: { ...form.input, name: e.target.value } })} placeholder="Input name" />
            <input value={form.input.source_url} onChange={(e) => setForm({ ...form, input: { ...form.input, source_url: e.target.value } })} placeholder={inputSourcePlaceholder(form.input_protocol)} style={{ gridColumn: '1 / -1' }} />
            <input type="number" value={form.input.priority} onChange={(e) => setForm({ ...form, input: { ...form.input, priority: Number(e.target.value) } })} placeholder="Priority" />
            <label className="row" style={{ alignItems: 'center' }}>
              <input type="checkbox" checked={form.input.is_enabled} onChange={(e) => setForm({ ...form, input: { ...form.input, is_enabled: e.target.checked } })} />
              <span>Enabled</span>
            </label>
            </div>
            <div className="muted" style={{ marginTop: 8 }}>Input URL: <code>{inputPreview || '-'}</code></div>

            <h4 style={{ marginTop: 16 }}>Output target</h4>
            <div className="grid grid-2" id="live-outputs">
            <select value={form.output_type} onChange={(e) => {
              const output_type = e.target.value as 'hls' | 'rtmp' | 'srt';
              setForm({ ...form, output_type, output: createDefaultOutputDraft(output_type) });
            }}>
              {OUTPUT_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
            <label className="row" style={{ alignItems: 'center' }}>
              <input type="checkbox" checked={form.output.is_enabled} onChange={(e) => setForm({ ...form, output: { ...form.output, is_enabled: e.target.checked } })} />
              <span>Enabled</span>
            </label>
            {form.output_type === 'hls' ? (
              <div className="muted" style={{ gridColumn: '1 / -1' }}>HLS playback URL is generated automatically after create.</div>
            ) : (
              <>
                <input value={form.output.host} onChange={(e) => setForm({ ...form, output: { ...form.output, host: e.target.value } })} placeholder="IP / host" />
                <input value={form.output.port} onChange={(e) => setForm({ ...form, output: { ...form.output, port: e.target.value } })} placeholder="Port" />
                <input value={form.output.latency_ms} onChange={(e) => setForm({ ...form, output: { ...form.output, latency_ms: e.target.value } })} placeholder="Latency ms" />
                <input value={form.output.path_suffix} onChange={(e) => setForm({ ...form, output: { ...form.output, path_suffix: e.target.value } })} placeholder={form.output_type === 'srt' ? 'Stream ID / suffix' : 'Path suffix'} />
              </>
            )}
            </div>
            <div className="muted" style={{ marginTop: 8 }}>Preview: <code>{outputPreview || '-'}</code></div>

            <details style={{ marginTop: 16 }}>
              <summary><strong>ABR profiles</strong> <span className="muted tiny">optional</span></summary>
              <div className="grid" id="live-abr" style={{ marginTop: 12 }}>
              {DEFAULT_ABR_PROFILES.map((profile) => (
                <label key={profile.name} className="row" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
                  <span><strong>{profile.name}</strong> <span className="muted">{profile.width}x{profile.height} • {profile.bitrate_kbps} kbps</span></span>
                  <input
                    type="checkbox"
                    checked={form.abr_selected.includes(profile.name)}
                    onChange={(e) => {
                      const next = e.target.checked ? [...form.abr_selected, profile.name] : form.abr_selected.filter((name) => name !== profile.name);
                      setForm({ ...form, abr_selected: next });
                    }}
                  />
                </label>
              ))}
              </div>
            </details>

            <div className="row create-stream-actions" style={{ marginTop: 16 }}>
              <button className="primary" disabled={submitting} onClick={createStream}>{submitting ? 'Creating…' : 'Create stream'}</button>
              <button className="secondary" onClick={() => setForm(makeDefaultForm())}>Reset</button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="dashboard-detail-grid">
        <div className="card" id="manage-data-slices">
          <h3>Inspector</h3>
          {!selected ? <p className="muted">Select a stream to inspect.</p> : (
            <>
              <div className="row space">
                <div>
                  <div className="eyebrow">Selected stream</div>
                  <h3 style={{ marginTop: 4 }}>{selected.name}</h3>
                </div>
                <div className="row">
                  <button className="secondary" onClick={refreshSelected} disabled={detailsLoading}>Refresh</button>
                  <Link className="secondary" href={`/streams/${selected.id}`}>Open stream studio</Link>
                </div>
              </div>
              <div className="row">
                <span className={`badge ${statusBadgeClass(selected.status)}`}>{selected.status}</span>
                {selected.is_primary ? <span className="badge running">main live</span> : null}
                <span className="muted">{selected.description || 'No description'}</span>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/start`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Start</button>
                <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/stop`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Stop</button>
                <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/restart`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Restart</button>
                <button className="primary" onClick={async () => { await apiFetch(`/streams/${selected.id}/go-live`, { method: 'POST', body: JSON.stringify({}) }); await loadStreams(); await refreshSelected(); }}>Go live</button>
                <button className="danger" onClick={async () => { if (!confirm(`Delete stream ${selected.name}?`)) return; await apiFetch(`/streams/${selected.id}`, { method: 'DELETE' }); setSelectedStreamId(null); setSelectedStream(null); setSelectedLogs([]); await loadStreams(); }}>Delete</button>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <div className="code" style={{ flex: 1 }}>Main live: {selected.playback_urls.main_hls || 'https://keystream.rockstreamer.com/live/main/index.m3u8'}</div>
                <button className="secondary" onClick={() => navigator.clipboard.writeText(String(selected.playback_urls.main_hls || 'https://keystream.rockstreamer.com/live/main/index.m3u8'))}>Copy</button>
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <div className="code" style={{ flex: 1 }}>HLS: {urls.hls || '-'}</div>
                {urls.hls ? <button className="secondary" onClick={() => navigator.clipboard.writeText(String(urls.hls))}>Copy</button> : null}
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <div className="code" style={{ flex: 1 }}>Master: {urls.master_hls || '-'}</div>
                {urls.master_hls ? <button className="secondary" onClick={() => navigator.clipboard.writeText(String(urls.master_hls))}>Copy</button> : null}
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <div className="code" style={{ flex: 1 }}>RTMP: {urls.rtmp || '-'}</div>
                {urls.rtmp ? <button className="secondary" onClick={() => navigator.clipboard.writeText(String(urls.rtmp))}>Copy</button> : null}
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <div className="code" style={{ flex: 1 }}>SRT: {urls.srt || '-'}</div>
                {urls.srt ? <button className="secondary" onClick={() => navigator.clipboard.writeText(String(urls.srt))}>Copy</button> : null}
              </div>
            </>
          )}
        </div>

        <div className="card" id="manage-playback">
          <div className="row space">
            <h3 style={{ margin: 0 }}>Details</h3>
            <div className="row">
              {tabItems.map((item) => (
                <button key={item.key} className={activeTab === item.key ? 'primary' : 'secondary'} onClick={() => setActiveTab(item.key)}>
                  {item.label}
                </button>
              ))}
            </div>
          </div>
          {!selected ? <p className="muted">Choose a stream first.</p> : (
            <div style={{ marginTop: 16 }}>
              {activeTab === 'overview' ? (
                <div className="grid grid-2">
                  <div className="stat-card"><div className="muted tiny">Enabled</div><div className="stat-value">{String(selected.is_enabled ?? true)}</div></div>
                  <div className="stat-card"><div className="muted tiny">ABR</div><div className="stat-value">{String(selected.abr_enabled)}</div></div>
                  <div className="stat-card"><div className="muted tiny">Logo</div><div className="stat-value">{String(selected.logo_enabled ?? false)}</div></div>
                  <div className="stat-card"><div className="muted tiny">Inputs</div><div className="stat-value">{selected.input_sources?.length || 0}</div></div>
                  <div className="stat-card"><div className="muted tiny">Audio</div><div className="stat-value">AAC</div></div>
                </div>
              ) : null}

              {activeTab === 'inputs' ? (
                <div className="grid">
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Name</th><th>Protocol</th><th>Priority</th><th>Source URL</th><th>Enabled</th><th>Actions</th></tr></thead>
                    <tbody>{(selected.input_sources || []).map((item: any) => (
                      <tr key={item.id}>
                        <td><input value={item.name} onChange={(e) => patchSelectedInput(item.id, { name: e.target.value })} /></td>
                        <td>
                          <select value={item.protocol} onChange={(e) => patchSelectedInput(item.id, { protocol: e.target.value })}>
                            {PROTOCOLS.map((protocol) => <option key={protocol.value} value={protocol.value}>{protocol.label}</option>)}
                          </select>
                        </td>
                        <td><input type="number" value={item.priority} onChange={(e) => patchSelectedInput(item.id, { priority: Number(e.target.value) })} style={{ minWidth: 90 }} /></td>
                        <td><input value={item.source_url} onChange={(e) => patchSelectedInput(item.id, { source_url: e.target.value })} /></td>
                        <td><input type="checkbox" checked={item.is_enabled} onChange={(e) => patchSelectedInput(item.id, { is_enabled: e.target.checked })} /></td>
                        <td>
                          <div className="row table-actions">
                            <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/inputs/${item.id}`, { method: 'PATCH', body: JSON.stringify({ name: item.name, protocol: item.protocol, priority: Number(item.priority), source_url: item.source_url, is_enabled: item.is_enabled }) }); await refreshSelected(); }}>Save</button>
                            <button className="danger" onClick={async () => { if (!confirm(`Delete input ${item.name}?`)) return; await apiFetch(`/streams/${selected.id}/inputs/${item.id}`, { method: 'DELETE' }); await refreshSelected(); }}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
                <div className="card" style={{ padding: 12 }}>
                  <div className="row space"><strong>Add input</strong><span className="muted tiny">Create a new source for this stream</span></div>
                  <div className="grid grid-2" style={{ marginTop: 12 }}>
                    <input value={inspectorInputDraft.name} onChange={(e) => setInspectorInputDraft({ ...inspectorInputDraft, name: e.target.value })} placeholder="Input name" />
                    <select value={inspectorInputDraft.protocol} onChange={(e) => setInspectorInputDraft(createDefaultInputDraft(e.target.value as 'hls' | 'rtmp' | 'srt'))}>
                      {PROTOCOLS.map((protocol) => <option key={protocol.value} value={protocol.value}>{protocol.label}</option>)}
                    </select>
                    <input value={inspectorInputDraft.source_url} onChange={(e) => setInspectorInputDraft({ ...inspectorInputDraft, source_url: e.target.value })} placeholder={inputSourcePlaceholder(inspectorInputDraft.protocol)} style={{ gridColumn: '1 / -1' }} />
                    <input type="number" value={inspectorInputDraft.priority} onChange={(e) => setInspectorInputDraft({ ...inspectorInputDraft, priority: Number(e.target.value) })} placeholder="Priority" />
                    <label className="row" style={{ alignItems: 'center' }}><input type="checkbox" checked={inspectorInputDraft.is_enabled} onChange={(e) => setInspectorInputDraft({ ...inspectorInputDraft, is_enabled: e.target.checked })} /><span>Enabled</span></label>
                  </div>
                  <div className="muted tiny" style={{ marginTop: 10 }}>Input URL: <code>{inspectorInputPreview || '-'}</code></div>
                  <div className="row" style={{ marginTop: 12 }}>
                    <button className="primary" onClick={async () => {
                      if (!inspectorInputPreview.trim()) {
                        setError(`${String(inspectorInputDraft.protocol).toUpperCase()} input URL is required`);
                        return;
                      }
                      await apiFetch(`/streams/${selected.id}/inputs`, { method: 'POST', body: JSON.stringify({ name: inspectorInputDraft.name, protocol: inspectorInputDraft.protocol, source_url: inspectorInputPreview.trim(), priority: inspectorInputDraft.priority, is_enabled: inspectorInputDraft.is_enabled }) });
                      setInspectorInputDraft(createDefaultInputDraft('hls'));
                      await refreshSelected();
                    }}>Add input</button>
                  </div>
                </div>
                </div>
              ) : null}

              {activeTab === 'outputs' ? (
                <div className="grid">
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Type</th><th>Enabled</th><th>Port</th><th>Latency</th><th>Path/Stream ID</th><th>Actions</th></tr></thead>
                    <tbody>{(selected.output_targets || []).map((item: any) => <tr key={item.id}>
                      <td><span className="badge">{String(item.output_type).toUpperCase()}</span></td>
                      <td><input type="checkbox" checked={item.is_enabled} onChange={(e) => patchSelectedOutput(item.id, { is_enabled: e.target.checked })} /></td>
                      <td><input value={item.port ?? ''} onChange={(e) => patchSelectedOutput(item.id, { port: e.target.value })} placeholder="Port" style={{ minWidth: 100 }} /></td>
                      <td><input value={item.latency_ms ?? ''} onChange={(e) => patchSelectedOutput(item.id, { latency_ms: e.target.value })} placeholder="Latency" style={{ minWidth: 110 }} /></td>
                      <td><input value={item.path_suffix ?? ''} onChange={(e) => patchSelectedOutput(item.id, { path_suffix: e.target.value })} placeholder="Suffix / stream ID" /></td>
                      <td><div className="row table-actions"><button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/outputs/${item.id}`, { method: 'PATCH', body: JSON.stringify({ is_enabled: item.is_enabled, port: item.port ? Number(item.port) : null, latency_ms: item.latency_ms ? Number(item.latency_ms) : null, path_suffix: item.path_suffix || null }) }); await refreshSelected(); }}>Save</button><button className="danger" onClick={async () => { if (!confirm(`Delete output ${item.output_type}?`)) return; await apiFetch(`/streams/${selected.id}/outputs/${item.id}`, { method: 'DELETE' }); await refreshSelected(); }}>Delete</button></div></td>
                    </tr>)}</tbody>
                  </table>
                </div>
                <div className="card" style={{ padding: 12 }}>
                  <div className="row space"><strong>Add output</strong><span className="muted tiny">Attach another delivery target</span></div>
                  <div className="grid grid-2" style={{ marginTop: 12 }}>
                    <select value={inspectorOutputDraft.output_type} onChange={(e) => setInspectorOutputDraft(createDefaultOutputDraft(e.target.value as 'hls' | 'rtmp' | 'srt'))}>
                      {OUTPUT_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
                    </select>
                    <label className="row" style={{ alignItems: 'center' }}><input type="checkbox" checked={inspectorOutputDraft.is_enabled} onChange={(e) => setInspectorOutputDraft({ ...inspectorOutputDraft, is_enabled: e.target.checked })} /><span>Enabled</span></label>
                    {inspectorOutputDraft.output_type === 'hls' ? (
                      <div className="muted tiny" style={{ gridColumn: '1 / -1' }}>HLS URL is generated from the stream key automatically.</div>
                    ) : (
                      <>
                        <input value={inspectorOutputDraft.host} onChange={(e) => setInspectorOutputDraft({ ...inspectorOutputDraft, host: e.target.value })} placeholder="IP / host" />
                        <input value={inspectorOutputDraft.port} onChange={(e) => setInspectorOutputDraft({ ...inspectorOutputDraft, port: e.target.value })} placeholder="Port" />
                        <input value={inspectorOutputDraft.latency_ms} onChange={(e) => setInspectorOutputDraft({ ...inspectorOutputDraft, latency_ms: e.target.value })} placeholder="Latency ms" />
                        <input value={inspectorOutputDraft.path_suffix} onChange={(e) => setInspectorOutputDraft({ ...inspectorOutputDraft, path_suffix: e.target.value })} placeholder={inspectorOutputDraft.output_type === 'srt' ? 'Stream ID / suffix' : 'Path suffix'} />
                      </>
                    )}
                  </div>
                  <div className="muted tiny" style={{ marginTop: 10 }}>Preview: <code>{inspectorOutputPreview || '-'}</code></div>
                  <div className="row" style={{ marginTop: 12 }}>
                    <button className="primary" onClick={async () => { await apiFetch(`/streams/${selected.id}/outputs`, { method: 'POST', body: JSON.stringify({ output_type: inspectorOutputDraft.output_type, is_enabled: inspectorOutputDraft.is_enabled, port: inspectorOutputDraft.port ? Number(inspectorOutputDraft.port) : null, latency_ms: inspectorOutputDraft.latency_ms ? Number(inspectorOutputDraft.latency_ms) : null, path_suffix: inspectorOutputDraft.path_suffix || null }) }); setInspectorOutputDraft(createDefaultOutputDraft('hls')); await refreshSelected(); }}>Add output</button>
                  </div>
                </div>
                </div>
              ) : null}

              {activeTab === 'abr' ? (
                <div className="grid">
                  <div className="row" style={{ justifyContent: 'space-between' }}>
                    <div className="muted tiny">Adaptive bitrate profiles for this stream</div>
                    <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}`, { method: 'PATCH', body: JSON.stringify({ abr_enabled: !selected.abr_enabled }) }); await loadStreams(); await refreshSelected(); }}>
                      {selected.abr_enabled ? 'Disable ABR' : 'Enable ABR'}
                    </button>
                  </div>
                  <div className="table-wrap">
                    <table className="table">
                      <thead><tr><th>Name</th><th>Width</th><th>Height</th><th>Bitrate</th><th>Playlist</th><th>Enabled</th><th>Actions</th></tr></thead>
                      <tbody>{(selected.abr_profiles || []).map((item: any) => <tr key={item.id}>
                        <td><input value={item.name} onChange={(e) => patchSelectedAbr(item.id, { name: e.target.value })} /></td>
                        <td><input type="number" value={item.width} onChange={(e) => patchSelectedAbr(item.id, { width: Number(e.target.value) })} style={{ minWidth: 90 }} /></td>
                        <td><input type="number" value={item.height} onChange={(e) => patchSelectedAbr(item.id, { height: Number(e.target.value) })} style={{ minWidth: 90 }} /></td>
                        <td><input type="number" value={item.bitrate_kbps} onChange={(e) => patchSelectedAbr(item.id, { bitrate_kbps: Number(e.target.value) })} style={{ minWidth: 110 }} /></td>
                        <td><input value={item.playlist_name} onChange={(e) => patchSelectedAbr(item.id, { playlist_name: e.target.value })} /></td>
                        <td><input type="checkbox" checked={item.is_enabled} onChange={(e) => patchSelectedAbr(item.id, { is_enabled: e.target.checked })} /></td>
                        <td>
                          <div className="row table-actions">
                            <button className="secondary" onClick={async () => { await apiFetch(`/streams/${selected.id}/abr-profiles/${item.id}`, { method: 'PATCH', body: JSON.stringify({ name: item.name, width: Number(item.width), height: Number(item.height), bitrate_kbps: Number(item.bitrate_kbps), playlist_name: item.playlist_name, is_enabled: item.is_enabled }) }); await refreshSelected(); }}>Save</button>
                            <button className="danger" onClick={async () => { if (!confirm(`Delete ABR profile ${item.name}?`)) return; await apiFetch(`/streams/${selected.id}/abr-profiles/${item.id}`, { method: 'DELETE' }); await refreshSelected(); }}>Delete</button>
                          </div>
                        </td>
                      </tr>)}</tbody>
                    </table>
                  </div>
                  <div className="card" style={{ padding: 12 }}>
                    <div className="row space"><strong>Add ABR profile</strong><span className="muted tiny">Create another output variant</span></div>
                    <div className="grid grid-2" style={{ marginTop: 12 }}>
                      <input value={inspectorAbrDraft.name} onChange={(e) => setInspectorAbrDraft({ ...inspectorAbrDraft, name: e.target.value })} placeholder="Profile name" />
                      <input value={inspectorAbrDraft.playlist_name} onChange={(e) => setInspectorAbrDraft({ ...inspectorAbrDraft, playlist_name: e.target.value })} placeholder="Playlist name" />
                      <input type="number" value={inspectorAbrDraft.width} onChange={(e) => setInspectorAbrDraft({ ...inspectorAbrDraft, width: Number(e.target.value) })} placeholder="Width" />
                      <input type="number" value={inspectorAbrDraft.height} onChange={(e) => setInspectorAbrDraft({ ...inspectorAbrDraft, height: Number(e.target.value) })} placeholder="Height" />
                      <input type="number" value={inspectorAbrDraft.bitrate_kbps} onChange={(e) => setInspectorAbrDraft({ ...inspectorAbrDraft, bitrate_kbps: Number(e.target.value) })} placeholder="Bitrate kbps" />
                      <label className="row" style={{ alignItems: 'center' }}><input type="checkbox" checked={inspectorAbrDraft.is_enabled} onChange={(e) => setInspectorAbrDraft({ ...inspectorAbrDraft, is_enabled: e.target.checked })} /><span>Enabled</span></label>
                    </div>
                    <div className="row" style={{ marginTop: 12 }}>
                      <button className="primary" onClick={async () => { await apiFetch(`/streams/${selected.id}/abr-profiles`, { method: 'POST', body: JSON.stringify(inspectorAbrDraft) }); setInspectorAbrDraft({ name: '540p', width: 960, height: 540, bitrate_kbps: 1800, playlist_name: '540p.m3u8', is_enabled: true }); await refreshSelected(); }}>Add ABR profile</button>
                    </div>
                  </div>
                </div>
              ) : null}

              {activeTab === 'runtime' ? (
                <div className="grid">
                  <div className="card" style={{ padding: 12 }}>
                    <div className="muted tiny">Audio pipeline</div>
                    <div style={{ marginTop: 6 }}>AAC • 128 kbps • 48 kHz stereo</div>
                  </div>
                  <div className="code">{JSON.stringify(selected.runtime_state || {}, null, 2)}</div>
                </div>
              ) : null}

              {activeTab === 'logs' ? (
                <div className="grid">
                  {(selectedLogs || []).slice(0, 8).map((log) => (
                    <div key={log.id} className="card" style={{ padding: 12 }}>
                      <div className="row space">
                        <span className={`badge ${log.level === 'error' ? 'error' : 'stopped'}`}>{log.level}</span>
                        <span className="muted tiny">{new Date(log.created_at).toLocaleString()}</span>
                      </div>
                      <div style={{ marginTop: 8 }}>{log.message}</div>
                    </div>
                  ))}
                  {!selectedLogs.length ? <div className="muted">No logs yet.</div> : null}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {previewStream ? (
        <div className="modal-backdrop" onClick={() => setPreviewStream(null)}>
          <div className="card modal-card player-modal" onClick={(e) => e.stopPropagation()}>
            <div className="row space" style={{ marginBottom: 12 }}>
              <div>
                <h3 style={{ margin: 0 }}>Sample URL for player</h3>
                <div className="muted tiny">{previewStream.name} · <code>{previewStream.stream_key}</code></div>
              </div>
              <button className="secondary" onClick={() => setPreviewStream(null)}>Close</button>
            </div>
            <div className="player-toolbar">
              <label>
                <span className="player-label">Choose URL to play:</span>
                <div className="row player-control-row">
                  <select value={previewUrl} onChange={(e) => setPreviewUrl(e.target.value)}>
                    {[previewStream.playback_urls.main_hls, previewStream.playback_urls.master_hls, previewStream.playback_urls.hls, previewStream.playback_urls.rtmp, previewStream.playback_urls.srt].filter(Boolean).map((url) => (
                      <option key={String(url)} value={String(url)}>{String(url)}</option>
                    ))}
                  </select>
                  <button className="secondary" disabled={!previewUrl} onClick={() => navigator.clipboard.writeText(previewUrl)}>Copy</button>
                </div>
              </label>
              <label>
                <span className="player-label">Available players:</span>
                <div className="row player-control-row">
                  <select value={previewPlayer} onChange={(e) => setPreviewPlayer(e.target.value)}>
                    <option value="videojs">Video.js web player</option>
                    <option value="jwplayer">JW Player</option>
                    <option value="exoplayer">ExoPlayer</option>
                  </select>
                  <button className="secondary" onClick={() => setPreviewNonce((value) => value + 1)}>Restart</button>
                </div>
              </label>
              <button className="primary" onClick={() => setShowPlayerCode((value) => !value)}>{showPlayerCode ? "Hide player's code" : "Show player's code"}</button>
              {showPlayerCode ? (
                <div className="code">
                  {previewUrl ? (
                    previewPlayer === 'exoplayer'
                      ? `MediaItem.fromUri('${previewUrl}')`
                      : previewPlayer === 'jwplayer'
                        ? `jwplayer('player').setup({ file: '${previewUrl}' });`
                        : `player.src({ src: '${previewUrl}', type: 'application/x-mpegURL' });`
                  ) : '-'}
                </div>
              ) : null}
            </div>
            <div className="player-stage" style={{ marginTop: 18 }}>
              {previewUrl ? (
                isBrowserPlayableUrl(previewUrl) ? (
                  <HlsPlayer key={`${previewUrl}-${previewNonce}`} src={previewUrl} />
                ) : (
                  <div className="muted">This URL is available to copy, but browser preview works only for HTTP/HTTPS HLS `.m3u8` URLs.</div>
                )
              ) : (
                <div className="muted">No playable URL is available for this stream yet.</div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

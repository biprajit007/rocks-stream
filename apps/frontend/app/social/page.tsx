'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';

type InputSource = {
  id: number;
  name: string;
  protocol: string;
  source_url: string;
  priority: number;
  is_enabled: boolean;
};

type Stream = {
  id: number;
  name: string;
  stream_key: string;
  status: string;
  is_primary?: boolean;
  input_sources: InputSource[];
  playback_urls: { main_hls?: string | null; hls?: string | null; master_hls?: string | null; rtmp?: string | null; srt?: string | null };
};

type Platform = {
  name: string;
  label: string;
  enabled: boolean;
  color: string;
  ingestUrl: string;
  streamKey: string;
  notes: string;
  resolution: string;
  fps: number;
  videoBitrate: string;
  audioBitrate: string;
  rotateEveryHours: number;
  autoRotation: boolean;
  configEnabled: boolean;
  stopAfterMinutes: number;
  stopAt: string;
  extraArgs: string;
  pid: string;
  started: string;
  restarts: number;
  lastError: string;
};

const platformDefaults: Omit<Platform, 'name' | 'label' | 'color' | 'ingestUrl' | 'streamKey' | 'notes'> = {
  enabled: false,
  resolution: '1920x1080',
  fps: 30,
  videoBitrate: '4000k',
  audioBitrate: '128k',
  rotateEveryHours: 6,
  autoRotation: false,
  configEnabled: true,
  stopAfterMinutes: 0,
  stopAt: '-',
  extraArgs: '',
  pid: '-',
  started: '-',
  restarts: 0,
  lastError: '-',
};

const platformPresets = [
  {
    name: 'YouTube',
    label: 'YouTube Live',
    color: '#6b82ff',
    ingestUrl: 'rtmp://a.rtmp.youtube.com/live2/',
    notes: 'Push-only mode. Paste the YouTube ingest URL and stream key, then manage the outbound stream from the portal.',
    ...platformDefaults,
  },
  {
    name: 'Facebook',
    label: 'Facebook Live',
    color: '#7c5cff',
    ingestUrl: 'rtmps://live-api-s.facebook.com:443/rtmp/',
    notes: 'Push-only mode. Paste the Facebook ingest URL and stream key, then manage the outbound stream from the portal.',
    ...platformDefaults,
  },
  {
    name: 'TikTok',
    label: 'TikTok Live',
    color: '#f472b6',
    ingestUrl: 'rtmps://live.tiktok.com:443/stream/',
    notes: 'Push-only mode. Paste the TikTok ingest URL and stream key, then manage the outbound stream from the portal.',
    ...platformDefaults,
  },
  {
    name: 'Twitch',
    label: 'Twitch',
    color: '#f59e0b',
    ingestUrl: 'rtmp://live.twitch.tv/app/',
    notes: 'Push-only mode. Paste the Twitch ingest URL and stream key, then manage the outbound stream from the portal.',
    ...platformDefaults,
  },
] as const;

function createPlatformFromPreset(
  preset: (typeof platformPresets)[number],
  saved?: Partial<Platform> & Record<string, unknown>
): Platform {
  return {
    name: preset.name,
    label: preset.label,
    color: preset.color,
    ingestUrl: (saved?.ingestUrl as string | undefined) || (saved?.ingest_url as string | undefined) || preset.ingestUrl,
    streamKey: (saved?.streamKey as string | undefined) || (saved?.stream_key as string | undefined) || '',
    notes: (saved?.notes as string | undefined) || preset.notes,
    enabled: Boolean(saved?.enabled ?? preset.enabled),
    resolution: (saved?.resolution as string | undefined) || preset.resolution,
    fps: Number(saved?.fps ?? preset.fps),
    videoBitrate: (saved?.videoBitrate as string | undefined) || (saved?.video_bitrate as string | undefined) || preset.videoBitrate,
    audioBitrate: (saved?.audioBitrate as string | undefined) || (saved?.audio_bitrate as string | undefined) || preset.audioBitrate,
    rotateEveryHours: Number(saved?.rotateEveryHours ?? saved?.rotate_every_hours ?? preset.rotateEveryHours),
    autoRotation: Boolean(saved?.autoRotation ?? saved?.auto_rotation ?? preset.autoRotation),
    configEnabled: Boolean(saved?.configEnabled ?? saved?.config_enabled ?? preset.configEnabled),
    stopAfterMinutes: Number(saved?.stopAfterMinutes ?? saved?.stop_after_minutes ?? preset.stopAfterMinutes),
    stopAt: (saved?.stopAt as string | undefined) || (saved?.stop_at as string | undefined) || preset.stopAt,
    extraArgs: (saved?.extraArgs as string | undefined) || (saved?.extra_args as string | undefined) || preset.extraArgs,
    pid: (saved?.pid as string | undefined) || preset.pid,
    started: (saved?.started as string | undefined) || preset.started,
    restarts: Number(saved?.restarts ?? preset.restarts),
    lastError: (saved?.lastError as string | undefined) || (saved?.last_error as string | undefined) || preset.lastError,
  };
}

export default function SocialStreamPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [selectedStreamId, setSelectedStreamId] = useState<number | null>(null);
  const [selectedInputId, setSelectedInputId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [platforms, setPlatforms] = useState<Platform[]>(
    platformPresets.map((preset) => createPlatformFromPreset(preset))
  );

  useEffect(() => {
    (async () => {
      try {
        const [list, social] = await Promise.all([apiFetch('/streams'), apiFetch('/social')]);
        setStreams(list);
        setSelectedStreamId((current) => current ?? social.source_stream_id ?? list[0]?.id ?? null);
        setSelectedInputId((current) => current ?? social.source_input_id ?? null);
        setPlatforms([
          createPlatformFromPreset(platformPresets[0], social.youtube),
          createPlatformFromPreset(platformPresets[1], social.facebook),
          createPlatformFromPreset(platformPresets[2], social.tiktok),
          createPlatformFromPreset(platformPresets[3], social.twitch),
        ]);
        setMessage('');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load streams');
      }
    })();
  }, []);

  const selectedStream = useMemo(
    () => streams.find((item) => item.id === selectedStreamId) || null,
    [streams, selectedStreamId]
  );

  const availableInputs = useMemo(() => selectedStream?.input_sources?.filter((item) => item.is_enabled) || [], [selectedStream]);

  const selectedInput = useMemo(
    () => availableInputs.find((item) => item.id === selectedInputId) || null,
    [availableInputs, selectedInputId]
  );

  useEffect(() => {
    if (!selectedStream) {
      setSelectedInputId(null);
      return;
    }
    if (selectedInputId && availableInputs.some((item) => item.id === selectedInputId)) {
      return;
    }
    setSelectedInputId(availableInputs[0]?.id ?? null);
  }, [availableInputs, selectedInputId, selectedStream]);

  const sourceUrl = selectedInput?.source_url || selectedStream?.playback_urls.main_hls || selectedStream?.playback_urls.master_hls || selectedStream?.playback_urls.hls || '';

  function patchPlatform(name: Platform['name'], patch: Partial<Platform>) {
    setPlatforms((current) => current.map((platform) => (platform.name === name ? { ...platform, ...patch } : platform)));
  }

  function platformSlug(name: Platform['name']) {
    return name.toLowerCase();
  }

  async function reloadSocial() {
    const [list, social] = await Promise.all([apiFetch('/streams'), apiFetch('/social')]);
    setStreams(list);
    setSelectedStreamId((current) => current ?? social.source_stream_id ?? list[0]?.id ?? null);
    setSelectedInputId((current) => current ?? social.source_input_id ?? null);
    setPlatforms([
      createPlatformFromPreset(platformPresets[0], social.youtube),
      createPlatformFromPreset(platformPresets[1], social.facebook),
      createPlatformFromPreset(platformPresets[2], social.tiktok),
      createPlatformFromPreset(platformPresets[3], social.twitch),
    ]);
  }

  function buildPayload(nextPlatforms = platforms, nextSelectedStreamId = selectedStreamId, nextSelectedInputId = selectedInputId) {
      const toConfig = (platform: Platform) => ({
        enabled: platform.enabled,
        ingest_url: platform.ingestUrl,
        stream_key: platform.streamKey,
        notes: platform.notes,
        resolution: platform.resolution,
      fps: platform.fps,
      video_bitrate: platform.videoBitrate,
      audio_bitrate: platform.audioBitrate,
      rotate_every_hours: platform.rotateEveryHours,
      auto_rotation: platform.autoRotation,
      config_enabled: platform.configEnabled,
      stop_after_minutes: platform.stopAfterMinutes,
      stop_at: platform.stopAt,
      extra_args: platform.extraArgs,
      pid: platform.pid,
      started: platform.started,
      restarts: platform.restarts,
      last_error: platform.lastError,
    });

    return {
      source_stream_id: nextSelectedStreamId,
      source_input_id: nextSelectedInputId,
      youtube: toConfig(nextPlatforms[0]),
      facebook: toConfig(nextPlatforms[1]),
      tiktok: toConfig(nextPlatforms[2]),
      twitch: toConfig(nextPlatforms[3]),
    };
  }

  async function persistSocialSettings(
    nextPlatforms = platforms,
    nextSelectedStreamId = selectedStreamId,
    nextSelectedInputId = selectedInputId,
    successMessage = 'Social restream settings saved'
  ) {
    await apiFetch('/social', {
      method: 'PUT',
      body: JSON.stringify(buildPayload(nextPlatforms, nextSelectedStreamId, nextSelectedInputId)),
    });
    setPlatforms(nextPlatforms);
    setSelectedStreamId(nextSelectedStreamId);
    setSelectedInputId(nextSelectedInputId);
    setMessage(successMessage);
  }

  async function saveSocialSettings() {
    setSaving(true);
    setMessage('');
    try {
      await persistSocialSettings(platforms, selectedStreamId, selectedInputId, 'Social restream settings saved');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to save social settings');
    } finally {
      setSaving(false);
    }
  }

  async function updatePlatform(name: Platform['name'], patch: Partial<Platform>, successMessage: string) {
    const nextPlatforms = platforms.map((item) => (item.name === name ? { ...item, ...patch } : item));
    setSaving(true);
    setMessage('');
    try {
      await persistSocialSettings(nextPlatforms, selectedStreamId, selectedInputId, successMessage);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to save platform settings');
    } finally {
      setSaving(false);
    }
  }

  async function startPlatform(name: Platform['name']) {
    setSaving(true);
    setMessage('');
    try {
      const platform = platforms.find((item) => item.name === name);
      if (!platform?.streamKey.trim() || platform.streamKey.startsWith('paste-')) {
        throw new Error(`${name} stream key is missing. Paste the real platform stream key first.`);
      }
      await apiFetch('/social', {
        method: 'PUT',
        body: JSON.stringify(buildPayload()),
      });
      await apiFetch(`/social/${platformSlug(name)}/start`, { method: 'POST', body: JSON.stringify({}) });
      await reloadSocial();
      setMessage(`${name} started`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to update platform');
    } finally {
      setSaving(false);
    }
  }

  async function stopPlatform(name: Platform['name']) {
    setSaving(true);
    setMessage('');
    try {
      await apiFetch(`/social/${platformSlug(name)}/stop`, { method: 'POST', body: JSON.stringify({}) });
      await reloadSocial();
      setMessage(`${name} stopped`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to update platform');
    } finally {
      setSaving(false);
    }
  }

  async function restartPlatform(name: Platform['name']) {
    setSaving(true);
    setMessage('');
    try {
      await apiFetch('/social', {
        method: 'PUT',
        body: JSON.stringify(buildPayload()),
      });
      await apiFetch(`/social/${platformSlug(name)}/restart`, { method: 'POST', body: JSON.stringify({}) });
      await reloadSocial();
      setMessage(`${name} restarted`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to update platform');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid social-page">
      <div className="card">
        <div className="panel-heading" style={{ marginBottom: 0 }}>
          <div>
            <div className="eyebrow">Social restream</div>
            <h2 className="panel-title">Broadcast one input stream to Facebook, YouTube, TikTok, and Twitch</h2>
          </div>
          <span className="badge running">Live ingest tools</span>
        </div>
        <p className="muted" style={{ marginTop: 12 }}>
          Pick a source stream, then manage each platform as its own box.
        </p>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="primary" onClick={saveSocialSettings} disabled={saving}>{saving ? 'Saving…' : 'Save social setup'}</button>
          {message ? <span className="muted tiny">{message}</span> : null}
        </div>
        {error ? <p style={{ color: '#fecaca' }}>{error}</p> : null}
      </div>

      <div className="grid grid-2 social-slim-grid">
        <div className="card">
          <h3>Source stream</h3>
          <div style={{ marginTop: 12 }}>
            <label>Select stream</label>
            <select
              value={selectedStreamId ?? ''}
              onChange={(e) => {
                const nextStreamId = e.target.value ? Number(e.target.value) : null;
                setSelectedStreamId(nextStreamId);
                const nextStream = streams.find((stream) => stream.id === nextStreamId) || null;
                setSelectedInputId(nextStream?.input_sources?.find((item) => item.is_enabled)?.id ?? null);
              }}
            >
              <option value="">Select an existing stream</option>
              {streams.map((stream) => (
                <option key={stream.id} value={stream.id}>
                  {stream.name} {stream.is_primary ? '(input stream)' : `(${stream.status})`}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginTop: 12 }}>
            <label>Source URL</label>
            <select value={selectedInputId ?? ''} onChange={(e) => setSelectedInputId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Auto-pick source</option>
              {availableInputs.map((input) => (
                <option key={input.id} value={input.id}>
                  {input.name} ({input.protocol})
                </option>
              ))}
            </select>
          </div>
          <div className="card" style={{ marginTop: 12, padding: 12, background: 'var(--panel-soft)' }}>
            <div className="muted tiny">Selected source</div>
            <div style={{ marginTop: 6, fontWeight: 800 }}>{selectedStream?.name || 'No stream selected'}</div>
            <div className="muted tiny" style={{ marginTop: 6 }}>
              Source input: <code>{selectedInput?.name || (availableInputs.length ? 'Auto-pick source' : '-')}</code>
            </div>
            <div className="muted tiny" style={{ marginTop: 6 }}>
              Source URL: <code>{sourceUrl || '-'}</code>
            </div>
            <div className="row" style={{ marginTop: 10 }}>
              {sourceUrl ? <button className="secondary" onClick={() => navigator.clipboard.writeText(sourceUrl)}>Copy source URL</button> : null}
              {selectedStream ? <a className="secondary" href={`/streams/${selectedStream.id}`}>Open stream studio</a> : null}
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Publish presets</h3>
          <div className="grid" style={{ marginTop: 12 }}>
            <div className="stat-card">
              <div className="muted tiny">Recommended settings</div>
              <div className="row" style={{ marginTop: 8 }}>
                <span className="badge">1080p</span>
                <span className="badge">AAC audio</span>
                <span className="badge">2s keyframes</span>
                <span className="badge">RTMP/RTMPS</span>
              </div>
            </div>
            <div className="muted tiny">
              Social platforms usually want a direct RTMP push. Each box below keeps its own target settings and status.
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-2 social-slim-grid">
        {platforms.map((platform) => (
          <div key={platform.name} className="card social-card" style={{ borderTop: `4px solid ${platform.color}` }}>
            <div className="row space social-card-head">
              <div>
                <h3 className="social-card-title">{platform.name}</h3>
                <div className="social-card-copy">{platform.notes}</div>
              </div>
              <div className="row social-badges">
                <span className="social-chip social-chip-target">Manual target</span>
                <span className={`social-chip ${platform.enabled ? 'social-chip-live' : 'social-chip-stopped'}`}>{platform.enabled ? 'Live' : 'Stopped'}</span>
              </div>
            </div>

            <div className="social-grid">
              <div className="social-field">
                <label>Stream URL</label>
                <input
                  value={platform.ingestUrl}
                  onChange={(e) => patchPlatform(platform.name, { ingestUrl: e.target.value })}
                />
              </div>
              <div className="social-field">
                <label>Stream key</label>
                <input
                  placeholder={`Paste ${platform.name} stream key`}
                  value={platform.streamKey}
                  onChange={(e) => patchPlatform(platform.name, { streamKey: e.target.value })}
                />
              </div>
              <div className="social-field">
                <label>Resolution</label>
                <input
                  value={platform.resolution}
                  onChange={(e) => patchPlatform(platform.name, { resolution: e.target.value })}
                />
              </div>
              <div className="social-field">
                <label>FPS</label>
                <input
                  type="number"
                  value={platform.fps}
                  onChange={(e) => patchPlatform(platform.name, { fps: Number(e.target.value) || 0 })}
                />
              </div>
              <div className="social-field">
                <label>Video bitrate</label>
                <input
                  value={platform.videoBitrate}
                  onChange={(e) => patchPlatform(platform.name, { videoBitrate: e.target.value })}
                />
              </div>
              <div className="social-field">
                <label>Audio bitrate</label>
                <input
                  value={platform.audioBitrate}
                  onChange={(e) => patchPlatform(platform.name, { audioBitrate: e.target.value })}
                />
              </div>
              <div className="social-field">
                <label>Rotate every N hours</label>
                <input
                  type="number"
                  value={platform.rotateEveryHours}
                  onChange={(e) => patchPlatform(platform.name, { rotateEveryHours: Number(e.target.value) || 0 })}
                />
              </div>
              <div className="social-field">
                <label>Auto stop after</label>
                <select
                  value={platform.stopAfterMinutes}
                  onChange={(e) => patchPlatform(platform.name, { stopAfterMinutes: Number(e.target.value) || 0, stopAt: '-' })}
                >
                  <option value={0}>Manual stop</option>
                  <option value={10}>10 minutes</option>
                  <option value={30}>30 minutes</option>
                  <option value={60}>60 minutes</option>
                </select>
              </div>
              <div className="social-field social-span-2">
                <label>Extra args</label>
                <textarea
                  rows={3}
                  placeholder="optional extra args"
                  value={platform.extraArgs}
                  onChange={(e) => patchPlatform(platform.name, { extraArgs: e.target.value })}
                />
              </div>
            </div>

            <div className="social-checks">
              <label className="social-check">
                <input
                  type="checkbox"
                  checked={platform.autoRotation}
                  onChange={(e) => patchPlatform(platform.name, { autoRotation: e.target.checked })}
                />
                <span>Enable auto-rotation</span>
              </label>
              <label className="social-check">
                <input
                  type="checkbox"
                  checked={platform.configEnabled}
                  onChange={(e) => patchPlatform(platform.name, { configEnabled: e.target.checked })}
                />
                <span>Config enabled</span>
              </label>
            </div>

            <div className="social-meta-grid">
              <div><span>PID:</span> <strong>{platform.pid || '-'}</strong></div>
              <div className="social-meta-right"><span>Started:</span> <strong>{platform.started || '-'}</strong></div>
              <div><span>Restarts:</span> <strong>{platform.restarts}</strong></div>
              <div className="social-meta-right"><span>Last error:</span> <strong>{platform.lastError || '-'}</strong></div>
              <div><span>Auto stop:</span> <strong>{platform.stopAfterMinutes ? `${platform.stopAfterMinutes} min` : 'Manual'}</strong></div>
              <div className="social-meta-right"><span>Stop at:</span> <strong>{platform.stopAt || '-'}</strong></div>
            </div>

            <div className="row social-actions" style={{ marginTop: 12 }}>
              <button type="button" className="social-pill social-save" onClick={() => updatePlatform(platform.name, {}, `${platform.name} saved`)} disabled={saving}>Save</button>
              <button type="button" className="social-pill social-start" onClick={() => startPlatform(platform.name)} disabled={saving}>Start</button>
              <button type="button" className="social-pill social-stop" onClick={() => stopPlatform(platform.name)} disabled={saving}>Stop</button>
              <button type="button" className="social-pill social-restart" onClick={() => restartPlatform(platform.name)} disabled={saving}>Restart</button>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>How to use</h3>
        <ol className="muted" style={{ lineHeight: 1.8 }}>
          <li>Start or select the source stream.</li>
          <li>Fill the platform box that matches your target.</li>
          <li>Save the card, then use Start / Stop / Restart on that same card.</li>
          <li>Go live on the platform.</li>
        </ol>
      </div>

      <div className="card">
        <h3>Stream matrix</h3>
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table className="table">
            <thead>
              <tr>
                <th>Platform</th>
                <th>Source</th>
                <th>Endpoint</th>
              </tr>
            </thead>
            <tbody>
              {platforms.map((platform) => (
                <tr key={platform.name}>
                  <td><strong>{platform.name}</strong></td>
                  <td className="muted tiny"><code>{sourceUrl || '-'}</code></td>
                  <td className="muted tiny"><code>{platform.ingestUrl}{platform.streamKey}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

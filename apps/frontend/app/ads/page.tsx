'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';

type AdSlot = {
  enabled: boolean;
  tagUrl: string;
  offset: string;
  duration: string;
  skippable: boolean;
};

const defaultTag = 'https://ads.example.com/www/delivery/asyncspc.php?zoneid=1&vast=1';

function makeSlot(offset: string, duration: string): AdSlot {
  return {
    enabled: false,
    tagUrl: defaultTag,
    offset,
    duration,
    skippable: false,
  };
}

export default function AdsPage() {
  const [provider, setProvider] = useState('Revive Adserver (open source)');
  const [enabled, setEnabled] = useState(false);
  const [preRoll, setPreRoll] = useState<AdSlot>(makeSlot('start', '00:00:15'));
  const [midRoll, setMidRoll] = useState<AdSlot>(makeSlot('00:10:00', '00:00:30'));
  const [postRoll, setPostRoll] = useState<AdSlot>(makeSlot('end', '00:00:15'));
  const [videoAd, setVideoAd] = useState<AdSlot>(makeSlot('manual', '00:00:20'));
  const [midRollRulesText, setMidRollRulesText] = useState('00:10:00');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch('/ads');
        setProvider(data.provider || 'Revive Adserver (open source)');
        setEnabled(Boolean(data.enabled));
        setPreRoll({ enabled: !!data.pre_roll?.enabled, tagUrl: data.pre_roll?.tag_url || '', offset: data.pre_roll?.offset || 'start', duration: data.pre_roll?.duration || '00:00:15', skippable: !!data.pre_roll?.skippable });
        setMidRoll({ enabled: !!data.mid_roll?.enabled, tagUrl: data.mid_roll?.tag_url || '', offset: data.mid_roll?.offset || '00:10:00', duration: data.mid_roll?.duration || '00:00:30', skippable: !!data.mid_roll?.skippable });
        setPostRoll({ enabled: !!data.post_roll?.enabled, tagUrl: data.post_roll?.tag_url || '', offset: data.post_roll?.offset || 'end', duration: data.post_roll?.duration || '00:00:15', skippable: !!data.post_roll?.skippable });
        setVideoAd({ enabled: !!data.video_ad?.enabled, tagUrl: data.video_ad?.tag_url || '', offset: data.video_ad?.offset || 'manual', duration: data.video_ad?.duration || '00:00:20', skippable: !!data.video_ad?.skippable });
        setMidRollRulesText((data.mid_roll_rules || ['00:10:00']).join(', '));
      } catch (err) {
        setMessage(err instanceof Error ? err.message : 'Failed to load ad settings');
      }
    })();
  }, []);

  const summary = useMemo(() => {
    const slots = [
      ['Pre-roll', preRoll],
      ['Mid-roll', midRoll],
      ['Post-roll', postRoll],
      ['Video ad', videoAd],
    ] as const;
    return slots.filter(([, slot]) => slot.enabled).map(([name, slot]) => `${name} • ${slot.offset} • ${slot.duration}`).join(' | ') || 'No ad slot enabled yet';
  }, [preRoll, midRoll, postRoll, videoAd]);

  const playerSnippet = useMemo(() => JSON.stringify({
    adsEnabled: enabled,
    provider,
    preRoll: preRoll.enabled ? preRoll : null,
    midRoll: midRoll.enabled ? { ...midRoll, cuePoints: midRollRulesText.split(',').map((item) => item.trim()).filter(Boolean) } : null,
    postRoll: postRoll.enabled ? postRoll : null,
    videoAd: videoAd.enabled ? videoAd : null,
  }, null, 2), [enabled, provider, preRoll, midRoll, postRoll, videoAd, midRollRulesText]);

  const videojsSnippet = `const adConfig = await fetch('/api/v1/ads/player-config/main', {
  headers: { Authorization: 'Bearer <token>' }
}).then((r) => r.json());

player.ima({
  adTagUrl: adConfig.pre_roll?.tag_url || '',
});

const midRollCuePoints = adConfig.mid_roll_rules || [];
// map each cue point into your Video.js / contrib-ads schedule`;

  const jwPlayerSnippet = `const adConfig = await fetch('/api/v1/ads/player-config/main', {
  headers: { Authorization: 'Bearer <token>' }
}).then((r) => r.json());

jwplayer('player').setup({
  file: 'https://keystream.rockstreamer.com/live/main/index.m3u8',
  advertising: {
    client: 'vast',
    schedule: {
      pre: adConfig.pre_roll ? { offset: 'pre', tag: adConfig.pre_roll.tag_url } : undefined,
      mid1: adConfig.mid_roll ? { offset: adConfig.mid_roll_rules?.[0] || '00:10:00', tag: adConfig.mid_roll.tag_url } : undefined,
      post: adConfig.post_roll ? { offset: 'post', tag: adConfig.post_roll.tag_url } : undefined,
    }
  }
});`;

  async function saveSettings() {
    setSaving(true);
    setMessage('');
    try {
      await apiFetch('/ads', {
        method: 'PUT',
        body: JSON.stringify({
          provider,
          enabled,
          pre_roll: { enabled: preRoll.enabled, tag_url: preRoll.tagUrl, offset: preRoll.offset, duration: preRoll.duration, skippable: preRoll.skippable },
          mid_roll: { enabled: midRoll.enabled, tag_url: midRoll.tagUrl, offset: midRoll.offset, duration: midRoll.duration, skippable: midRoll.skippable },
          post_roll: { enabled: postRoll.enabled, tag_url: postRoll.tagUrl, offset: postRoll.offset, duration: postRoll.duration, skippable: postRoll.skippable },
          video_ad: { enabled: videoAd.enabled, tag_url: videoAd.tagUrl, offset: videoAd.offset, duration: videoAd.duration, skippable: videoAd.skippable },
          mid_roll_rules: midRollRulesText.split(',').map((item) => item.trim()).filter(Boolean),
        }),
      });
      setMessage('Ad settings saved');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to save ad settings');
    } finally {
      setSaving(false);
    }
  }

  function renderSlot(title: string, slot: AdSlot, setSlot: (value: AdSlot) => void, hint: string) {
    return (
      <div className="card ad-slot-card">
        <div className="row space">
          <div>
            <h3>{title}</h3>
            <div className="muted tiny">{hint}</div>
          </div>
          <label className="row" style={{ alignItems: 'center' }}>
            <input type="checkbox" checked={slot.enabled} onChange={(e) => setSlot({ ...slot, enabled: e.target.checked })} />
            <span>Enabled</span>
          </label>
        </div>
        <div className="grid grid-2" style={{ marginTop: 12 }}>
          <input value={slot.tagUrl} onChange={(e) => setSlot({ ...slot, tagUrl: e.target.value })} placeholder="VAST tag URL" style={{ gridColumn: '1 / -1' }} />
          <input value={slot.offset} onChange={(e) => setSlot({ ...slot, offset: e.target.value })} placeholder="Offset" />
          <input value={slot.duration} onChange={(e) => setSlot({ ...slot, duration: e.target.value })} placeholder="Duration" />
          <label className="row" style={{ alignItems: 'center' }}>
            <input type="checkbox" checked={slot.skippable} onChange={(e) => setSlot({ ...slot, skippable: e.target.checked })} />
            <span>Skippable</span>
          </label>
        </div>
        <div className="muted tiny" style={{ marginTop: 10 }}>
          Tag preview: <code>{slot.tagUrl || '-'}</code>
        </div>
      </div>
    );
  }

  return (
    <div className="grid">
      <div className="card">
        <div className="panel-heading" style={{ marginBottom: 0 }}>
          <div>
            <div className="eyebrow">Monetization</div>
            <h2 className="panel-title">Ad manager</h2>
          </div>
          <div className="row">
            <label className="row" style={{ alignItems: 'center' }}>
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              <span>Enable ads</span>
            </label>
            <span className="badge running">VAST ready</span>
            <button className="primary" onClick={saveSettings} disabled={saving}>{saving ? 'Saving…' : 'Save ads'}</button>
          </div>
        </div>
        {message ? <div className="muted tiny" style={{ marginTop: 12 }}>{message}</div> : null}
        <div className="grid grid-2" style={{ marginTop: 16 }}>
          <div className="card" style={{ padding: 12 }}>
            <div className="muted tiny">Open-source ad stack</div>
            <h3 style={{ marginTop: 6 }}>{provider}</h3>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option>Revive Adserver (open source)</option>
              <option>Custom VAST endpoint</option>
              <option>Self-hosted VAST XML feed</option>
            </select>
            <div className="muted tiny" style={{ marginTop: 10 }}>
              Recommended open-source path: host your own <strong>Revive Adserver</strong> and use its VAST tag URLs here.
            </div>
          </div>
          <div className="card" style={{ padding: 12 }}>
            <div className="muted tiny">Active setup summary</div>
            <div style={{ marginTop: 8, fontWeight: 700 }}>{summary}</div>
            <div className="muted tiny" style={{ marginTop: 10 }}>
              This page now saves real backend ad settings and exposes player-facing VAST config structure.
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        {renderSlot('Pre-roll', preRoll, setPreRoll, 'Play before the stream starts')}
        {renderSlot('Mid-roll', midRoll, setMidRoll, 'Play during the stream at a timed break')}
        {renderSlot('Post-roll', postRoll, setPostRoll, 'Play after the stream ends')}
        {renderSlot('Video ad', videoAd, setVideoAd, 'Standalone video ad slot for manual trigger or campaign placement')}
      </div>

      <div className="card">
        <h3>Mid-roll rules</h3>
        <input value={midRollRulesText} onChange={(e) => setMidRollRulesText(e.target.value)} placeholder="00:10:00, 00:20:00, 00:30:00" />
        <div className="muted tiny" style={{ marginTop: 8 }}>
          Comma-separated cue points for timed mid-roll insertion.
        </div>
      </div>

      <div className="card">
        <h3>Player ad config hook</h3>
        <div className="muted tiny" style={{ marginBottom: 10 }}>
          Use this saved config in a web player to attach VAST ads to stream playback.
        </div>
        <div className="grid" style={{ marginBottom: 10 }}>
          <div className="code">GET /api/v1/ads/player-config</div>
          <div className="code">GET /api/v1/ads/player-config/{'{stream_key}'}</div>
        </div>
        <div className="code">{playerSnippet}</div>
        <div className="grid grid-2" style={{ marginTop: 12 }}>
          <div>
            <div className="muted tiny" style={{ marginBottom: 8 }}>Video.js / IMA example</div>
            <div className="code">{videojsSnippet}</div>
          </div>
          <div>
            <div className="muted tiny" style={{ marginBottom: 8 }}>JW Player example</div>
            <div className="code">{jwPlayerSnippet}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>VAST tag examples</h3>
        <div className="grid grid-2">
          <div className="code">https://ads.example.com/www/delivery/asyncspc.php?zoneid=1&vast=1</div>
          <div className="code">https://ads.example.com/vast?placement=midroll&stream=main</div>
          <div className="code">https://ads.example.com/vast?placement=postroll&stream=sports</div>
          <div className="code">https://ads.example.com/vast?placement=videoad&campaign=launch</div>
        </div>
      </div>
    </div>
  );
}

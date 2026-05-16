export type ProtocolKind = 'rtmp' | 'srt' | 'hls';
export type OutputKind = 'hls' | 'rtmp' | 'srt';

export const PROTOCOLS: { value: ProtocolKind; label: string }[] = [
  { value: 'hls', label: 'HLS' },
  { value: 'rtmp', label: 'RTMP' },
  { value: 'srt', label: 'SRT' },
];

export const OUTPUT_TYPES: { value: OutputKind; label: string }[] = [
  { value: 'hls', label: 'HLS' },
  { value: 'rtmp', label: 'RTMP' },
  { value: 'srt', label: 'SRT' },
];

export const DEFAULT_ABR_PROFILES = [
  { name: '1080p', width: 1920, height: 1080, bitrate_kbps: 6000, playlist_name: '1080p.m3u8' },
  { name: '720p', width: 1280, height: 720, bitrate_kbps: 3000, playlist_name: '720p.m3u8' },
  { name: '360p', width: 640, height: 360, bitrate_kbps: 900, playlist_name: '360p.m3u8' },
  { name: '280p', width: 480, height: 280, bitrate_kbps: 500, playlist_name: '280p.m3u8' },
  { name: '144p', width: 256, height: 144, bitrate_kbps: 250, playlist_name: '144p.m3u8' },
] as const;

export type InputDraft = {
  name: string;
  protocol: ProtocolKind;
  host: string;
  port: string;
  mode: string;
  source_url: string;
  priority: number;
  is_enabled: boolean;
};

export type OutputDraft = {
  output_type: OutputKind;
  host: string;
  port: string;
  latency_ms: string;
  path_suffix: string;
  is_enabled: boolean;
};

export function createDefaultInputDraft(protocol: ProtocolKind = 'hls'): InputDraft {
  return {
    name: `${protocol.toUpperCase()} Input`,
    protocol,
    host: '',
    port: protocol === 'srt' ? '9000' : protocol === 'rtmp' ? '1935' : '',
    mode: protocol === 'srt' ? 'caller' : protocol === 'rtmp' ? 'live' : '',
    source_url: '',
    priority: 1,
    is_enabled: true,
  };
}

export function createDefaultOutputDraft(output_type: OutputKind = 'hls'): OutputDraft {
  return {
    output_type,
    host: '',
    port: output_type === 'srt' ? '9000' : output_type === 'rtmp' ? '1935' : '',
    latency_ms: output_type === 'hls' ? '' : '2000',
    path_suffix: '',
    is_enabled: true,
  };
}

export function buildInputSourceUrl(draft: InputDraft): string {
  const directUrl = draft.source_url.trim();
  if (directUrl) {
    return directUrl;
  }

  if (draft.protocol === 'hls') {
    return draft.source_url.trim();
  }

  const host = draft.host.trim();
  const port = draft.port.trim();
  const mode = draft.mode.trim();

  if (!host || !port) return '';

  if (draft.protocol === 'srt') {
    const query = mode ? `?mode=${encodeURIComponent(mode)}` : '';
    return `srt://${host}:${port}${query}`;
  }

  const suffix = mode ? `/${encodeURIComponent(mode)}` : '';
  return `rtmp://${host}:${port}${suffix}`;
}

export function buildOutputPreview(draft: OutputDraft): string {
  const host = draft.host.trim();
  const port = draft.port.trim();
  const path = draft.path_suffix.trim();
  const latency = draft.latency_ms.trim();

  if (draft.output_type === 'hls') {
    return 'HLS playback URL is generated from the stream key after create.';
  }

  if (!host || !port) return '';

  if (draft.output_type === 'srt') {
    const query = [latency ? `latency=${encodeURIComponent(latency)}` : '', path ? `streamid=${encodeURIComponent(path)}` : ''].filter(Boolean).join('&');
    return `srt://${host}:${port}${query ? `?${query}` : ''}`;
  }

  const suffix = path ? `/${path.replace(/^\/+/, '')}` : '';
  const query = latency ? `?latency=${encodeURIComponent(latency)}` : '';
  return `rtmp://${host}:${port}${suffix}${query}`;
}

import os
import shlex
from dataclasses import dataclass

from app.config import settings
from app.models import InputSource, LogoAsset, LogoPositionMode, OutputType, Stream


@dataclass
class FfmpegSpec:
    command: str
    active_input_id: int
    preview_url: str | None
    details: dict


def _enabled_inputs(stream: Stream) -> list[InputSource]:
    return sorted([item for item in stream.input_sources if item.is_enabled], key=lambda item: item.priority)


def _enabled_outputs(stream: Stream):
    return [item for item in stream.output_targets if item.is_enabled]


def _input_args(source: InputSource) -> list[str]:
    protocol = source.protocol.value
    args = ["-fflags", "+genpts"]
    if protocol == "hls":
        args.extend([
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_on_network_error", "1",
            "-reconnect_delay_max", "2",
            "-thread_queue_size", "4096",
        ])
    elif protocol in {"rtmp", "srt"}:
        args.extend(["-thread_queue_size", "4096"])
    args.extend(["-i", source.source_url])
    return args


def _logo_xy(stream: Stream) -> tuple[int, int]:
    if stream.logo_position_mode == LogoPositionMode.corner:
        positions = {
            "top-left": (20, 20),
            "top-right": (1700, 20),
            "bottom-left": (20, 980),
            "bottom-right": (1700, 980),
        }
        return positions.get(stream.logo_corner, (20, 20))
    return stream.logo_x, stream.logo_y


def _video_filter(stream: Stream, logo: LogoAsset | None, width: int | None = None, height: int | None = None) -> str:
    filters: list[str] = []
    if stream.logo_enabled and logo:
        logo_path = os.path.join(settings.logos_root, logo.stored_name)
        logo_width = max(1, int(getattr(stream, "logo_width", 0) or 120))
        logo_height = max(1, int(getattr(stream, "logo_height", 0) or 48))
        x, y = _logo_xy(stream)
        overlay = (
            "movie="
            + logo_path.replace("\\", "\\\\").replace(":", "\\:")
            + f",scale={logo_width}:{logo_height}[logo];[in][logo]overlay={x}:{y}[v]"
        )
        if width and height:
            overlay = overlay.removesuffix("[v]") + f",scale={width}:{height}[v]"
        return overlay
    if width and height:
        filters.append(f"scale={width}:{height}:flags=fast_bilinear")
    return ",".join(filters) if filters else "scale=trunc(iw/2)*2:trunc(ih/2)*2"


def _encode_args(stream: Stream, logo: LogoAsset | None, bitrate_kbps: int, width: int | None = None, height: int | None = None) -> list[str]:
    args = [
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-vf", _video_filter(stream, logo, width, height),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-pix_fmt", "yuv420p",
        "-b:v", f"{bitrate_kbps}k",
        "-maxrate", f"{bitrate_kbps}k",
        "-bufsize", f"{max(2, bitrate_kbps * 2)}k",
        "-g", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-ac", "2",
    ]
    return args


def _hls_args(playlist: str, segment_pattern: str) -> list[str]:
    return [
        "-f", "hls",
        "-hls_time", "4",
        "-hls_list_size", "10",
        "-hls_flags", "delete_segments+independent_segments",
        "-hls_segment_filename", segment_pattern,
        playlist,
    ]


def _rtmp_url(stream: Stream, output) -> str:
    suffix = output.path_suffix or stream.stream_key
    return f"rtmp://nginx:1935/live/{suffix}"


def _srt_url(stream: Stream, output) -> str:
    suffix = output.path_suffix or stream.stream_key
    port = output.port or 9000
    return f"srt://0.0.0.0:{port}?mode=listener&streamid={suffix}"


def _quote_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def build_ffmpeg_pipeline(stream: Stream, logo: LogoAsset | None, source: InputSource | None = None) -> FfmpegSpec:
    inputs = _enabled_inputs(stream)
    if source is None and not inputs:
        raise ValueError("No enabled input sources configured")
    if source is None:
        source = inputs[0]
    elif not source.is_enabled:
        raise ValueError(f"Input source {source.id} is disabled")
    outputs = _enabled_outputs(stream)
    if not outputs:
        raise ValueError("No enabled outputs configured")

    stream_dir = os.path.join(settings.hls_root, stream.stream_key)
    os.makedirs(stream_dir, exist_ok=True)

    parts = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-y", *_input_args(source)]
    preview_url = None
    variants = []

    if any(item.output_type == OutputType.hls for item in outputs):
        preview_url = f"{settings.public_scheme}://{settings.public_domain}/live/{stream.stream_key}/index.m3u8"
        base_playlist = os.path.join(stream_dir, "index.m3u8")
        base_segments = os.path.join(stream_dir, "segment_%05d.ts")
        parts.extend([*_encode_args(stream, logo, 2500), *_hls_args(base_playlist, base_segments)])

    if stream.abr_enabled:
        for profile in [item for item in stream.abr_profiles if item.is_enabled]:
            playlist = os.path.join(stream_dir, profile.playlist_name)
            segment_pattern = os.path.join(stream_dir, f"{profile.name}_%05d.ts")
            parts.extend([
                *_encode_args(stream, logo, profile.bitrate_kbps, profile.width, profile.height),
                *_hls_args(playlist, segment_pattern),
            ])
            variants.append({
                "name": profile.name,
                "width": profile.width,
                "height": profile.height,
                "bitrate_kbps": profile.bitrate_kbps,
                "playlist_name": profile.playlist_name,
                "audio_bitrate_kbps": 128,
            })

    for output in outputs:
        if output.output_type == OutputType.rtmp:
            parts.extend([*_encode_args(stream, logo, 2500), "-f", "flv", _rtmp_url(stream, output)])
        elif output.output_type == OutputType.srt:
            parts.extend([*_encode_args(stream, logo, 2500), "-f", "mpegts", _srt_url(stream, output)])

    details = {
        "engine": "ffmpeg",
        "stream_key": stream.stream_key,
        "outputs": [item.output_type.value for item in outputs],
        "output_targets": [
            {"id": item.id, "type": item.output_type.value, "path_suffix": item.path_suffix, "port": item.port}
            for item in outputs
        ],
        "variants": variants,
        "audio": {"codec": "aac", "bitrate_kbps": 128, "channels": 2, "sample_rate_hz": 48000},
    }
    return FfmpegSpec(command=_quote_command(parts), active_input_id=source.id, preview_url=preview_url, details=details)


def write_master_playlist(stream_key: str, variants: list[dict]) -> str:
    stream_dir = os.path.join(settings.hls_root, stream_key)
    master = os.path.join(stream_dir, "master.m3u8")
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for variant in variants:
        bandwidth = (variant["bitrate_kbps"] + variant.get("audio_bitrate_kbps", 128)) * 1000
        resolution = f'{variant["width"]}x{variant["height"]}'
        lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}")
        lines.append(variant["playlist_name"])
    with open(master, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return master

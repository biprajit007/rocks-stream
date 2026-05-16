import os
import shlex
from dataclasses import dataclass

from app.config import settings
from app.models import InputSource, LogoAsset, LogoPositionMode, OutputType, Stream


@dataclass
class PipelineSpec:
    command: str
    active_input_id: int
    preview_url: str | None
    details: dict


def _input_chain(source: InputSource) -> str:
    if source.protocol.value == "rtmp":
        return f'rtmpsrc location={shlex.quote(source.source_url)} ! queue ! flvdemux name=demux demux. ! queue ! decodebin name=dec'
    if source.protocol.value == "srt":
        return f'srtsrc uri={shlex.quote(source.source_url)} ! tsdemux name=demux demux. ! queue ! decodebin name=dec'
    if source.protocol.value == "hls":
        return f'souphttpsrc is-live=true do-timestamp=true location={shlex.quote(source.source_url)} ! queue2 use-buffering=true max-size-time=0 max-size-bytes=0 max-size-buffers=0 ! hlsdemux ! decodebin name=dec'
    return f'uridecodebin uri={shlex.quote(source.source_url)} expose-all-streams=false name=dec'


def _overlay_filter(stream: Stream, logo: LogoAsset | None) -> str:
    if not stream.logo_enabled or not logo:
        return "videoconvert"
    logo_path = os.path.join(settings.logos_root, logo.stored_name)
    if stream.logo_position_mode == LogoPositionMode.corner:
        positions = {
            "top-left": (20, 20),
            "top-right": (1700, 20),
            "bottom-left": (20, 980),
            "bottom-right": (1700, 980),
        }
        x, y = positions.get(stream.logo_corner, (20, 20))
    else:
        x, y = stream.logo_x, stream.logo_y
    width = max(0, int(getattr(stream, "logo_width", 0) or 0))
    height = max(0, int(getattr(stream, "logo_height", 0) or 0))
    size_bits = []
    if width:
        size_bits.append(f"overlay-width={width}")
    if height:
        size_bits.append(f"overlay-height={height}")
    size_clause = (" " + " ".join(size_bits)) if size_bits else ""
    return f'gdkpixbufoverlay location={shlex.quote(logo_path)} offset-x={x} offset-y={y}{size_clause} ! videoconvert'


def build_pipeline(stream: Stream, logo: LogoAsset | None) -> PipelineSpec:
    enabled_inputs = [source for source in stream.input_sources if source.is_enabled]
    if not enabled_inputs:
        raise ValueError("No enabled input sources configured")
    source = sorted(enabled_inputs, key=lambda item: item.priority)[0]
    enabled_outputs = [item for item in stream.output_targets if item.is_enabled]
    output_types = {item.output_type for item in enabled_outputs}
    if not output_types:
        raise ValueError("No enabled outputs configured")

    stream_dir = os.path.join(settings.hls_root, stream.stream_key)
    os.makedirs(stream_dir, exist_ok=True)
    branches: list[str] = []
    preview_url = None
    details = {
        "stream_key": stream.stream_key,
        "outputs": [item.value for item in output_types],
        "audio": {"codec": "aac", "bitrate_kbps": 128, "channels": 2, "sample_rate_hz": 48000},
    }

    if OutputType.hls in output_types:
        preview_url = f"{settings.public_scheme}://{settings.public_domain}/live/{stream.stream_key}/index.m3u8"
        hls_index = os.path.join(stream_dir, "index.m3u8")
        hls_pattern = os.path.join(stream_dir, "segment_%05d.ts")
        branches.extend([
            f'vt. ! queue ! x264enc tune=zerolatency speed-preset=veryfast bitrate=2500 key-int-max=60 ! h264parse ! muxhls.',
            'at. ! queue ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! voaacenc bitrate=128000 ! aacparse ! muxhls.',
            f'mpegtsmux name=muxhls ! hlssink playlist-location={shlex.quote(hls_index)} location={shlex.quote(hls_pattern)} target-duration=4 max-files=10',
        ])

    if stream.abr_enabled:
        variants = []
        for profile in [item for item in stream.abr_profiles if item.is_enabled]:
            mux_name = f'mux_{profile.name.replace("-", "_")}'
            playlist = os.path.join(stream_dir, profile.playlist_name)
            segment_pattern = os.path.join(stream_dir, f"{profile.name}_%05d.ts")
            branches.extend([
                f'vt. ! queue ! videoscale ! video/x-raw,width={profile.width},height={profile.height} ! x264enc tune=zerolatency speed-preset=veryfast bitrate={profile.bitrate_kbps} key-int-max=60 ! h264parse ! {mux_name}.',
                f'at. ! queue ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! voaacenc bitrate=128000 ! aacparse ! {mux_name}.',
                f'mpegtsmux name={mux_name} ! hlssink playlist-location={shlex.quote(playlist)} location={shlex.quote(segment_pattern)} target-duration=4 max-files=10',
            ])
            variants.append({"name": profile.name, "width": profile.width, "height": profile.height, "bitrate_kbps": profile.bitrate_kbps, "playlist_name": profile.playlist_name, "audio_bitrate_kbps": 128})
        details["variants"] = variants

    if OutputType.rtmp in output_types:
        rtmp_target = next((item for item in enabled_outputs if item.output_type == OutputType.rtmp), None)
        path_suffix = rtmp_target.path_suffix or stream.stream_key if rtmp_target else stream.stream_key
        rtmp_url = f"rtmp://nginx:1935/live/{path_suffix}"
        branches.extend([
            'vt. ! queue ! x264enc tune=zerolatency speed-preset=veryfast bitrate=2500 key-int-max=60 ! h264parse ! muxrtmp.video',
            'at. ! queue ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! voaacenc bitrate=128000 ! aacparse ! muxrtmp.audio',
            f'flvmux name=muxrtmp streamable=true ! rtmpsink location={shlex.quote(rtmp_url)}',
        ])

    if OutputType.srt in output_types:
        srt_target = next((item for item in enabled_outputs if item.output_type == OutputType.srt), None)
        stream_id = srt_target.path_suffix or stream.stream_key if srt_target else stream.stream_key
        srt_url = f"srt://0.0.0.0:9000?mode=listener&streamid={stream_id}"
        branches.extend([
            'vt. ! queue ! x264enc tune=zerolatency speed-preset=veryfast bitrate=2500 key-int-max=60 ! h264parse ! muxsrt.',
            'at. ! queue ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! voaacenc bitrate=128000 ! aacparse ! muxsrt.',
            f'mpegtsmux name=muxsrt ! srtsink uri={shlex.quote(srt_url)} sync=false async=false',
        ])

    video_filter = _overlay_filter(stream, logo)
    if source.protocol.value == 'hls':
        command = "gst-launch-1.0 -e " + " ".join([
            f'souphttpsrc is-live=true do-timestamp=true location={shlex.quote(source.source_url)} ! queue2 use-buffering=true max-size-time=0 max-size-bytes=0 max-size-buffers=0 ! hlsdemux ! tsdemux name=demux',
            'demux. ! queue ! h264parse ! avdec_h264 ! videoconvert !',
            video_filter,
            '! tee name=vt',
            'demux. ! queue ! aacparse ! avdec_aac ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! tee name=at',
            *branches,
        ])
    else:
        command = "gst-launch-1.0 -e " + " ".join([
            _input_chain(source),
            'dec. ! queue ! capsfilter caps=video/x-raw ! videoconvert !',
            video_filter,
            '! tee name=vt',
            'dec. ! queue ! capsfilter caps=audio/x-raw ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! tee name=at',
            *branches,
        ])
    return PipelineSpec(command=command, active_input_id=source.id, preview_url=preview_url, details=details)


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

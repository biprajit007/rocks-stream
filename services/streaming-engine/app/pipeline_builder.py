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
        return f'rtmpsrc location={shlex.quote(source.source_url)} ! queue ! flvdemux name=demux demux.video ! queue ! decodebin name=dec'
    if source.protocol.value == "srt":
        return f'srtsrc uri={shlex.quote(source.source_url)} ! tsdemux name=demux demux. ! queue ! decodebin name=dec'
    return f'souphttpsrc location={shlex.quote(source.source_url)} is-live=true ! hlsdemux ! decodebin name=dec'


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
    return f'gdkpixbufoverlay location={shlex.quote(logo_path)} offset-x={x} offset-y={y} ! videoconvert'


def build_pipeline(stream: Stream, logo: LogoAsset | None) -> PipelineSpec:
    enabled_inputs = [source for source in stream.input_sources if source.is_enabled]
    if not enabled_inputs:
        raise ValueError("No enabled input sources configured")
    source = sorted(enabled_inputs, key=lambda item: item.priority)[0]
    output_types = {item.output_type for item in stream.output_targets if item.is_enabled}
    if not output_types:
        raise ValueError("No enabled outputs configured")

    stream_dir = os.path.join(settings.hls_root, stream.stream_key)
    os.makedirs(stream_dir, exist_ok=True)
    hls_branch = ""
    branches: list[str] = []
    preview_url = None
    details = {"stream_key": stream.stream_key, "outputs": [item.value for item in output_types]}

    if OutputType.hls in output_types:
        preview_url = f"{settings.public_scheme}://{settings.public_domain}/live/{stream.stream_key}/index.m3u8"
        hls_index = os.path.join(stream_dir, "index.m3u8")
        hls_pattern = os.path.join(stream_dir, "segment_%05d.ts")
        hls_branch = f't. ! queue ! x264enc tune=zerolatency speed-preset=veryfast bitrate=2500 key-int-max=60 ! h264parse ! mpegtsmux name=muxhls ! hlssink2 playlist-location={shlex.quote(hls_index)} location={shlex.quote(hls_pattern)} target-duration=4 max-files=10'
        branches.append(hls_branch)

    if stream.abr_enabled:
        variants = []
        for profile in [item for item in stream.abr_profiles if item.is_enabled]:
            playlist = os.path.join(stream_dir, profile.playlist_name)
            segment_pattern = os.path.join(stream_dir, f"{profile.name}_%05d.ts")
            branches.append(
                f't. ! queue ! videoscale ! video/x-raw,width={profile.width},height={profile.height} ! x264enc tune=zerolatency speed-preset=veryfast bitrate={profile.bitrate_kbps} key-int-max=60 ! h264parse ! mpegtsmux ! hlssink2 playlist-location={shlex.quote(playlist)} location={shlex.quote(segment_pattern)} target-duration=4 max-files=10'
            )
            variants.append({"name": profile.name, "width": profile.width, "height": profile.height, "bitrate_kbps": profile.bitrate_kbps, "playlist_name": profile.playlist_name})
        details["variants"] = variants

    if OutputType.rtmp in output_types:
        rtmp_url = f"rtmp://nginx:1935/live/{stream.stream_key}"
        branches.append(f't. ! queue ! x264enc tune=zerolatency speed-preset=veryfast bitrate=2500 key-int-max=60 ! voaacenc ! flvmux streamable=true name=muxrtmp ! rtmpsink location={shlex.quote(rtmp_url)}')

    if OutputType.srt in output_types:
        srt_url = f"srt://0.0.0.0:9000?mode=listener&streamid={stream.stream_key}"
        branches.append(f't. ! queue ! x264enc tune=zerolatency speed-preset=veryfast bitrate=2500 key-int-max=60 ! voaacenc ! mpegtsmux ! srtsink uri={shlex.quote(srt_url)} sync=false async=false')

    video_filter = _overlay_filter(stream, logo)
    command = "gst-launch-1.0 -e " + " ".join([
        _input_chain(source),
        "dec. ! queue ! videoconvert !",
        video_filter,
        "! tee name=t",
        *branches,
    ])
    return PipelineSpec(command=command, active_input_id=source.id, preview_url=preview_url, details=details)


def write_master_playlist(stream_key: str, variants: list[dict]) -> str:
    stream_dir = os.path.join(settings.hls_root, stream_key)
    master = os.path.join(stream_dir, "master.m3u8")
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for variant in variants:
        bandwidth = variant["bitrate_kbps"] * 1000
        resolution = f'{variant["width"]}x{variant["height"]}'
        lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}")
        lines.append(variant["playlist_name"])
    with open(master, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return master

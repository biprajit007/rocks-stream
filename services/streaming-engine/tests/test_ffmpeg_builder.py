from types import SimpleNamespace

from app.ffmpeg_builder import build_ffmpeg_pipeline
from app.models import OutputType, Protocol


def test_build_ffmpeg_pipeline_with_hls_abr_and_repeated_outputs():
    stream = SimpleNamespace(
        stream_key="alpha",
        logo_enabled=False,
        input_sources=[
            SimpleNamespace(id=1, protocol=Protocol.hls, source_url="https://origin.example/live/index.m3u8", priority=1, is_enabled=True),
        ],
        output_targets=[
            SimpleNamespace(id=10, output_type=OutputType.hls, is_enabled=True, path_suffix=None, port=None),
            SimpleNamespace(id=11, output_type=OutputType.rtmp, is_enabled=True, path_suffix="youtube/key", port=None),
            SimpleNamespace(id=12, output_type=OutputType.rtmp, is_enabled=True, path_suffix="facebook/key", port=None),
            SimpleNamespace(id=13, output_type=OutputType.srt, is_enabled=True, path_suffix="backup", port=9010),
        ],
        abr_enabled=True,
        abr_profiles=[
            SimpleNamespace(name="720p", width=1280, height=720, bitrate_kbps=3000, playlist_name="720p.m3u8", is_enabled=True),
        ],
    )

    spec = build_ffmpeg_pipeline(stream, logo=None)

    assert spec.active_input_id == 1
    assert spec.details["engine"] == "ffmpeg"
    assert spec.preview_url.endswith("/live/alpha/index.m3u8")
    assert "ffmpeg" in spec.command
    assert "https://origin.example/live/index.m3u8" in spec.command
    assert "/var/lib/rocks-stream/hls/alpha/index.m3u8" in spec.command
    assert "/var/lib/rocks-stream/hls/alpha/720p.m3u8" in spec.command
    assert "rtmp://nginx:1935/live/youtube/key" in spec.command
    assert "rtmp://nginx:1935/live/facebook/key" in spec.command
    assert "srt://0.0.0.0:9010?mode=listener&streamid=backup" in spec.command


def test_ffmpeg_builder_can_use_explicit_input_source():
    hls_source = SimpleNamespace(id=1, protocol=Protocol.hls, source_url="https://origin.example/live/index.m3u8", priority=1, is_enabled=True)
    rtmp_source = SimpleNamespace(id=2, protocol=Protocol.rtmp, source_url="rtmp://backup.example/live/main", priority=2, is_enabled=True)
    stream = SimpleNamespace(
        stream_key="bravo",
        logo_enabled=False,
        input_sources=[hls_source, rtmp_source],
        output_targets=[
            SimpleNamespace(id=20, output_type=OutputType.hls, is_enabled=True, path_suffix=None, port=None),
        ],
        abr_enabled=False,
        abr_profiles=[],
    )

    ffmpeg_spec = build_ffmpeg_pipeline(stream, logo=None, source=rtmp_source)

    assert ffmpeg_spec.active_input_id == 2
    assert "rtmp://backup.example/live/main" in ffmpeg_spec.command
    assert "https://origin.example/live/index.m3u8" not in ffmpeg_spec.command

from types import SimpleNamespace

from app.models import OutputType
from app.services.url_builder import build_playback_urls


def test_build_playback_urls():
    stream = SimpleNamespace(
        stream_key='alpha',
        abr_enabled=True,
        output_targets=[
            SimpleNamespace(output_type=OutputType.hls, is_enabled=True),
            SimpleNamespace(output_type=OutputType.rtmp, is_enabled=True),
            SimpleNamespace(output_type=OutputType.srt, is_enabled=True),
        ],
    )
    urls = build_playback_urls(stream)
    assert urls.hls.endswith('/live/alpha/index.m3u8')
    assert urls.master_hls.endswith('/live/alpha/master.m3u8')
    assert urls.rtmp == 'rtmp://keystream.rockstreamer.com/live/alpha'
    assert urls.srt == 'srt://keystream.rockstreamer.com:9000?streamid=alpha'

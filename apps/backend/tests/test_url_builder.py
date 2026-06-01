from types import SimpleNamespace

from app.models import OutputType
from app.services.url_builder import build_playback_urls


def test_build_playback_urls():
    stream = SimpleNamespace(
        stream_key='alpha',
        abr_enabled=True,
        is_primary=False,
        output_targets=[
            SimpleNamespace(id=1, output_type=OutputType.hls, is_enabled=True, path_suffix=None, port=None),
            SimpleNamespace(id=2, output_type=OutputType.rtmp, is_enabled=True, path_suffix=None, port=None),
            SimpleNamespace(id=3, output_type=OutputType.srt, is_enabled=True, path_suffix=None, port=None),
        ],
    )
    urls = build_playback_urls(stream)
    assert urls.hls.endswith('/live/alpha/index.m3u8')
    assert urls.master_hls.endswith('/live/alpha/master.m3u8')
    assert urls.rtmp == 'rtmp://keystream.rockstreamer.com/live/alpha'
    assert urls.srt == 'srt://keystream.rockstreamer.com:9000?streamid=alpha'
    assert [item.url for item in urls.outputs] == [
        'https://keystream.rockstreamer.com/live/alpha/index.m3u8',
        'rtmp://keystream.rockstreamer.com/live/alpha',
        'srt://keystream.rockstreamer.com:9000?streamid=alpha',
    ]


def test_build_playback_urls_with_repeated_outputs():
    stream = SimpleNamespace(
        stream_key='alpha',
        abr_enabled=False,
        is_primary=True,
        output_targets=[
            SimpleNamespace(id=10, output_type=OutputType.rtmp, is_enabled=True, path_suffix='youtube/key', port=None),
            SimpleNamespace(id=11, output_type=OutputType.rtmp, is_enabled=True, path_suffix='facebook/key', port=None),
            SimpleNamespace(id=12, output_type=OutputType.srt, is_enabled=True, path_suffix='backup', port=9010),
        ],
    )
    urls = build_playback_urls(stream)
    assert urls.rtmp == 'rtmp://keystream.rockstreamer.com/live/alpha'
    assert urls.srt == 'srt://keystream.rockstreamer.com:9000?streamid=alpha'
    assert [item.url for item in urls.outputs] == [
        'rtmp://keystream.rockstreamer.com/live/youtube/key',
        'rtmp://keystream.rockstreamer.com/live/facebook/key',
        'srt://keystream.rockstreamer.com:9010?streamid=backup',
    ]

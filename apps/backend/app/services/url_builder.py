from app.core.config import settings
from app.models import OutputType, Stream
from app.schemas import PlaybackUrls


def build_playback_urls(stream: Stream) -> PlaybackUrls:
    domain = settings.public_domain
    scheme = settings.public_scheme
    key = stream.stream_key
    is_primary = getattr(stream, "is_primary", False)
    available = {output.output_type for output in stream.output_targets if output.is_enabled}
    return PlaybackUrls(
        hls=f"{scheme}://{domain}/live/{key}/index.m3u8" if OutputType.hls in available else None,
        master_hls=f"{scheme}://{domain}/live/{key}/master.m3u8" if stream.abr_enabled and OutputType.hls in available else None,
        main_hls=f"{scheme}://{domain}/live/main/index.m3u8" if is_primary and OutputType.hls in available else None,
        rtmp=f"rtmp://{domain}/live/{key}" if OutputType.rtmp in available else None,
        srt=f"srt://{domain}:9000?streamid={key}" if OutputType.srt in available else None,
    )

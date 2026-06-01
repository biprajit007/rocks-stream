from app.core.config import settings
from app.models import OutputType, Stream
from app.schemas import OutputPlaybackUrl, PlaybackUrls


def _output_url(domain: str, scheme: str, key: str, output) -> str | None:
    suffix = getattr(output, "path_suffix", None) or key
    if output.output_type == OutputType.hls:
        return f"{scheme}://{domain}/live/{suffix}/index.m3u8"
    if output.output_type == OutputType.rtmp:
        return f"rtmp://{domain}/live/{suffix}"
    if output.output_type == OutputType.srt:
        return f"srt://{domain}:{getattr(output, 'port', None) or 9000}?streamid={suffix}"
    return None


def build_playback_urls(stream: Stream) -> PlaybackUrls:
    domain = settings.public_domain
    scheme = settings.public_scheme
    key = stream.stream_key
    is_primary = getattr(stream, "is_primary", False)
    enabled_outputs = [output for output in stream.output_targets if output.is_enabled]
    available = {output.output_type for output in enabled_outputs}
    output_urls = []
    for index, output in enumerate(enabled_outputs, start=1):
        url = _output_url(domain, scheme, key, output)
        if url:
            output_urls.append(
                OutputPlaybackUrl(
                    output_id=getattr(output, "id", index),
                    output_type=output.output_type,
                    url=url,
                    label=f"{output.output_type.value.upper()} {index}",
                )
            )
    return PlaybackUrls(
        hls=f"{scheme}://{domain}/live/{key}/index.m3u8" if OutputType.hls in available else None,
        master_hls=f"{scheme}://{domain}/live/{key}/master.m3u8" if stream.abr_enabled and OutputType.hls in available else None,
        main_hls=f"{scheme}://{domain}/live/main/index.m3u8" if is_primary and OutputType.hls in available else None,
        rtmp=f"rtmp://{domain}/live/{key}" if OutputType.rtmp in available else None,
        srt=f"srt://{domain}:9000?streamid={key}" if OutputType.srt in available else None,
        outputs=output_urls,
    )

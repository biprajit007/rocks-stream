from fastapi import FastAPI, HTTPException

from app.manager import manager

app = FastAPI(title="Rocks Stream Engine")


@app.get('/health')
def health():
    return manager.health()


@app.post('/engine/streams/{stream_id}/start')
def start_stream(stream_id: int, payload: dict):
    try:
        return manager.start(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/engine/streams/{stream_id}/stop')
def stop_stream(stream_id: int, payload: dict):
    try:
        return manager.stop(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/engine/streams/{stream_id}/restart')
def restart_stream(stream_id: int, payload: dict):
    try:
        return manager.restart(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/engine/social/{platform}/start')
def start_social(platform: str, payload: dict):
    try:
        return manager.start_social(
            platform,
            int(payload['source_stream_id']),
            payload['source_url'],
            payload.get('source_protocol'),
            payload['ingest_url'],
            payload['stream_key'],
            payload.get('resolution', '1920x1080'),
            int(payload.get('fps', 30)),
            payload.get('video_bitrate', '4000k'),
            payload.get('audio_bitrate', '128k'),
            payload.get('extra_args', ''),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/engine/social/{platform}/stop')
def stop_social(platform: str, payload: dict):
    try:
        return manager.stop_social(platform, int(payload.get('source_stream_id')) if payload.get('source_stream_id') else None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/engine/social/{platform}/restart')
def restart_social(platform: str, payload: dict):
    try:
        return manager.restart_social(
            platform,
            int(payload['source_stream_id']),
            payload['source_url'],
            payload.get('source_protocol'),
            payload['ingest_url'],
            payload['stream_key'],
            payload.get('resolution', '1920x1080'),
            int(payload.get('fps', 30)),
            payload.get('video_bitrate', '4000k'),
            payload.get('audio_bitrate', '128k'),
            payload.get('extra_args', ''),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

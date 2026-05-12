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

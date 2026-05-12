import os
import signal
import subprocess
from datetime import datetime
from threading import Lock

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import SessionLocal
from app.models import LogoAsset, Stream, StreamLogEntry, StreamRuntimeState, StreamStatus
from app.pipeline_builder import build_pipeline, write_master_playlist


class PipelineManager:
    def __init__(self) -> None:
        self.processes: dict[int, subprocess.Popen] = {}
        self.lock = Lock()

    def _db(self) -> Session:
        return SessionLocal()

    def _load_stream(self, db: Session, stream_id: int) -> Stream | None:
        return db.query(Stream).options(
            joinedload(Stream.input_sources),
            joinedload(Stream.output_targets),
            joinedload(Stream.abr_profiles),
            joinedload(Stream.runtime_state),
        ).filter(Stream.id == stream_id).first()

    def _log(self, db: Session, stream_id: int, level: str, message: str) -> None:
        db.add(StreamLogEntry(stream_id=stream_id, level=level, message=message))

    def _runtime(self, db: Session, stream_id: int) -> StreamRuntimeState:
        runtime = db.query(StreamRuntimeState).filter(StreamRuntimeState.stream_id == stream_id).first()
        if not runtime:
            runtime = StreamRuntimeState(stream_id=stream_id, engine_status="stopped", details={}, updated_at=datetime.utcnow())
            db.add(runtime)
            db.flush()
        return runtime

    def start(self, stream_id: int) -> dict:
        with self.lock:
            db = self._db()
            try:
                stream = self._load_stream(db, stream_id)
                if not stream:
                    raise ValueError("Stream not found")
                if stream_id in self.processes and self.processes[stream_id].poll() is None:
                    runtime = self._runtime(db, stream_id)
                    return {"message": "Stream already running", "engine_status": runtime.engine_status, "stream_status": stream.status.value, "process_id": runtime.process_id, "command": runtime.command, "preview_url": runtime.preview_url, "active_input_id": runtime.active_input_id, "details": runtime.details}

                logo = db.query(LogoAsset).filter(LogoAsset.id == stream.logo_asset_id).first() if stream.logo_asset_id else None
                spec = build_pipeline(stream, logo)
                logfile = os.path.join(settings.logs_root, f"stream-{stream.stream_key}.log")
                os.makedirs(settings.logs_root, exist_ok=True)
                handle = open(logfile, "ab")
                proc = subprocess.Popen(spec.command, shell=True, stdout=handle, stderr=handle, preexec_fn=os.setsid)
                self.processes[stream_id] = proc

                runtime = self._runtime(db, stream_id)
                runtime.engine_status = "running"
                runtime.process_id = proc.pid
                runtime.active_input_id = spec.active_input_id
                runtime.command = spec.command
                runtime.preview_url = spec.preview_url
                runtime.details = {**spec.details, "logfile": logfile}
                runtime.last_heartbeat_at = datetime.utcnow()
                runtime.updated_at = datetime.utcnow()

                stream.status = StreamStatus.running
                stream.active_input_id = spec.active_input_id
                self._log(db, stream_id, "info", f"Pipeline started with PID {proc.pid}")

                variants = spec.details.get("variants", [])
                if variants:
                    write_master_playlist(stream.stream_key, variants)
                    self._log(db, stream_id, "info", "Master playlist generated")

                db.commit()
                return {"message": "Stream started", "engine_status": runtime.engine_status, "stream_status": stream.status.value, "process_id": proc.pid, "command": spec.command, "preview_url": spec.preview_url, "active_input_id": spec.active_input_id, "details": runtime.details}
            except Exception as exc:
                db.rollback()
                stream = self._load_stream(db, stream_id)
                if stream:
                    stream.status = StreamStatus.error
                    runtime = self._runtime(db, stream_id)
                    runtime.engine_status = "error"
                    runtime.details = {"error": str(exc)}
                    runtime.updated_at = datetime.utcnow()
                    self._log(db, stream_id, "error", f"Start failed: {exc}")
                    db.commit()
                raise
            finally:
                db.close()

    def stop(self, stream_id: int) -> dict:
        with self.lock:
            db = self._db()
            try:
                proc = self.processes.get(stream_id)
                if proc and proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=10)
                self.processes.pop(stream_id, None)
                stream = self._load_stream(db, stream_id)
                if not stream:
                    raise ValueError("Stream not found")
                runtime = self._runtime(db, stream_id)
                runtime.engine_status = "stopped"
                runtime.process_id = None
                runtime.updated_at = datetime.utcnow()
                stream.status = StreamStatus.stopped
                self._log(db, stream_id, "info", "Pipeline stopped")
                db.commit()
                return {"message": "Stream stopped", "engine_status": "stopped", "stream_status": stream.status.value, "process_id": None, "command": runtime.command, "preview_url": runtime.preview_url, "active_input_id": runtime.active_input_id, "details": runtime.details}
            finally:
                db.close()

    def restart(self, stream_id: int) -> dict:
        self.stop(stream_id)
        return self.start(stream_id)

    def health(self) -> dict:
        states = {}
        for stream_id, proc in list(self.processes.items()):
            states[stream_id] = {"pid": proc.pid, "running": proc.poll() is None}
        return {"ok": True, "service": "streaming-engine", "streams": states}


manager = PipelineManager()

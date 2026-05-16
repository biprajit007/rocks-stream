import os
import signal
import subprocess
import shlex
from pathlib import Path
from datetime import datetime
from threading import Lock

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import SessionLocal
from app.models import LogoAsset, Stream, StreamLogEntry, StreamRuntimeState, StreamStatus
from app.pipeline_builder import build_pipeline, write_master_playlist


class PipelineManager:
    def __init__(self) -> None:
        self.processes: dict[str, subprocess.Popen] = {}
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

    def _key(self, kind: str, item_id: int | str) -> str:
        return f"{kind}:{item_id}"

    def _parse_bitrate(self, value: str, default: int) -> int:
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        return int(digits or default)

    def _parse_resolution(self, value: str) -> tuple[int, int]:
        try:
            width_s, height_s = str(value).lower().split('x', 1)
            return max(1, int(width_s)), max(1, int(height_s))
        except Exception:
            return 1920, 1080

    def _build_social_pipeline(self, source_url: str, ingest_url: str, stream_key: str, resolution: str, fps: int, video_bitrate: str, audio_bitrate: str, extra_args: str = '') -> str:
        width, height = self._parse_resolution(resolution)
        vbr = self._parse_bitrate(video_bitrate, 4000)
        abr = self._parse_bitrate(audio_bitrate, 128)
        target = f"{ingest_url}{stream_key}"
        extras = f" {extra_args.strip()}" if extra_args.strip() else ''
        uri = shlex.quote(source_url)
        location = shlex.quote(target)
        return (
            "gst-launch-1.0 -e "
            f"uridecodebin uri={uri} name=dec "
            "dec. ! queue ! videoconvert ! videorate ! videoscale ! "
            f"video/x-raw,width={width},height={height} "
            f"! x264enc tune=zerolatency speed-preset=veryfast bitrate={vbr} key-int-max={max(1, int(fps) * 2)} ! h264parse ! mux.video "
            "dec. ! queue ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 "
            f"! voaacenc bitrate={abr * 1000} ! aacparse ! mux.audio "
            f"flvmux name=mux streamable=true ! rtmpsink location={location}{extras}"
        )

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
                proc_key = self._key('stream', stream_id)
                if proc_key in self.processes and self.processes[proc_key].poll() is None:
                    runtime = self._runtime(db, stream_id)
                    return {"message": "Stream already running", "engine_status": runtime.engine_status, "stream_status": stream.status.value, "process_id": runtime.process_id, "command": runtime.command, "preview_url": runtime.preview_url, "active_input_id": runtime.active_input_id, "details": runtime.details}

                logo = db.query(LogoAsset).filter(LogoAsset.id == stream.logo_asset_id).first() if stream.logo_asset_id else None
                spec = build_pipeline(stream, logo)
                logfile = os.path.join(settings.logs_root, f"stream-{stream.stream_key}.log")
                os.makedirs(settings.logs_root, exist_ok=True)
                handle = open(logfile, "ab")
                proc = subprocess.Popen(spec.command, shell=True, stdout=handle, stderr=handle, preexec_fn=os.setsid)
                self.processes[proc_key] = proc

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
                proc_key = self._key('stream', stream_id)
                proc = self.processes.get(proc_key)
                if proc and proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=10)
                self.processes.pop(proc_key, None)
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

    def start_social(self, platform: str, source_stream_id: int, source_url: str, ingest_url: str, stream_key: str, resolution: str, fps: int, video_bitrate: str, audio_bitrate: str, extra_args: str = '') -> dict:
        with self.lock:
            db = self._db()
            proc = None
            try:
                key = self._key('social', platform)
                if key in self.processes and self.processes[key].poll() is None:
                    return {"message": f"{platform} already running", "process_id": self.processes[key].pid}
                cmd = self._build_social_pipeline(source_url, ingest_url, stream_key, resolution, fps, video_bitrate, audio_bitrate, extra_args)
                logfile = os.path.join(settings.logs_root, f"social-{platform}.log")
                os.makedirs(settings.logs_root, exist_ok=True)
                handle = open(logfile, 'ab')
                proc = subprocess.Popen(cmd, shell=True, stdout=handle, stderr=handle, preexec_fn=os.setsid)
                self.processes[key] = proc
                stream = self._load_stream(db, source_stream_id)
                if stream:
                    self._log(db, source_stream_id, 'info', f'Social {platform} started with PID {proc.pid}')
                    db.commit()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    return {"message": f"{platform} started", "process_id": proc.pid, "command": cmd, "logfile": logfile}

                tail = ''
                try:
                    tail = Path(logfile).read_text(errors='ignore')[-4000:]
                except Exception:
                    tail = ''
                self.processes.pop(key, None)
                raise RuntimeError(tail or f"{platform} process exited immediately")
            finally:
                db.close()

    def stop_social(self, platform: str, source_stream_id: int | None = None) -> dict:
        with self.lock:
            db = self._db()
            try:
                key = self._key('social', platform)
                proc = self.processes.get(key)
                if proc and proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=10)
                self.processes.pop(key, None)
                if source_stream_id:
                    self._log(db, source_stream_id, 'info', f'Social {platform} stopped')
                    db.commit()
                return {"message": f"{platform} stopped", "process_id": None}
            finally:
                db.close()

    def restart_social(self, platform: str, source_stream_id: int, source_url: str, ingest_url: str, stream_key: str, resolution: str, fps: int, video_bitrate: str, audio_bitrate: str, extra_args: str = '') -> dict:
        self.stop_social(platform, source_stream_id)
        return self.start_social(platform, source_stream_id, source_url, ingest_url, stream_key, resolution, fps, video_bitrate, audio_bitrate, extra_args)

    def health(self) -> dict:
        states = {}
        for stream_id, proc in list(self.processes.items()):
            states[stream_id] = {"pid": proc.pid, "running": proc.poll() is None}
        return {"ok": True, "service": "streaming-engine", "streams": states}


manager = PipelineManager()

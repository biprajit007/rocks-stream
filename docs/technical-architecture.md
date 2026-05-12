# Rocks Stream Technical Architecture

## 1. Stack
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS + React Query
- **Backend API:** FastAPI + SQLAlchemy + Alembic + Pydantic
- **Database:** PostgreSQL 16
- **Cache/queue:** Redis 7
- **Streaming engine:** Python service controlling GStreamer pipelines via `gst-launch-1.0`
- **Reverse proxy:** Nginx
- **TLS:** Certbot webroot flow
- **Runtime:** Docker Compose

## 2. High-Level Architecture

```text
Browser
  -> Nginx (TLS termination, static HLS, API/frontend routing)
     -> Frontend (Next.js)
     -> Backend API (FastAPI)
     -> HLS files (/var/lib/rocks-stream/hls)

Backend API
  -> PostgreSQL
  -> Redis
  -> Streaming Engine API

Streaming Engine
  -> PostgreSQL (state lookup)
  -> Redis (heartbeat/cache)
  -> GStreamer subprocesses
  -> Shared volumes for HLS output, logs, logos
```

## 3. Service Responsibilities
### 3.1 Frontend
- Admin authentication flow.
- CRUD screens for streams, inputs, outputs, ABR profiles, overlays.
- HLS preview with hls.js.
- Operational actions: start/stop/restart.

### 3.2 Backend
- JWT auth.
- Domain APIs.
- Validation, persistence, URL generation.
- Stream orchestration requests to engine.
- Aggregated status/log read APIs.

### 3.3 Streaming Engine
- Build deterministic GStreamer pipeline specs from DB config.
- Own process lifecycle.
- Monitor child processes.
- Write logs to shared volume.
- Emit runtime status to Redis/Postgres.

### 3.4 Nginx
- Redirect HTTP to HTTPS in production.
- Serve HLS playlists and segments with correct cache headers.
- Proxy `/api` to backend.
- Proxy app routes to frontend.

## 4. Data Model
### tables
- `users`
- `streams`
- `input_sources`
- `output_targets`
- `abr_profiles`
- `logo_assets`
- `stream_log_entries`
- `stream_runtime_state`

### key relationships
- One `stream` has many `input_sources`.
- One `stream` has many `output_targets`.
- One `stream` has many `abr_profiles`.
- One `stream` optionally references one `logo_asset`.
- One `stream` has one current `stream_runtime_state`.

## 5. Pipeline Strategy
### 5.1 Inputs
- **RTMP input:** `rtmpsrc location=... ! flvdemux ! decodebin`
- **SRT input:** `srtsrc uri=... ! tsdemux ! decodebin`
- **HLS input:** `souphttpsrc location=... ! hlsdemux ! decodebin`

### 5.2 Common processing
- Normalize timestamps.
- Decode to raw video/audio.
- Apply logo overlay using `gdkpixbufoverlay` when enabled.
- Split with `tee` for outputs.

### 5.3 ABR outputs
Per enabled profile:
- `videoscale` + `videoconvert`
- `capsfilter` for resolution/framerate
- `x264enc` for H.264 output
- `voaacenc` for AAC audio
- `mpegtsmux` or fragmented MP4/HLS segmenter path
- `hlssink2` per variant playlist

Master playlist generation is handled by the engine after pipeline launch by writing `master.m3u8` from enabled profiles.

### 5.4 Direct outputs
- **RTMP output:** `flvmux streamable=true ! rtmpsink location=...`
- **SRT output:** `mpegtsmux ! srtsink uri=...`
- **HLS output:** `hlssink2 playlist-location=... location=...`

## 6. Failover Design
- Inputs are ordered by priority.
- Engine attempts the highest-priority healthy input first.
- On startup failure or runtime crash, engine retries next input.
- Runtime state records active input and fallback attempts.

## 7. Security
- Secrets only via env vars or deployment-time secret stores.
- JWT signing key required from env.
- Password hashes only, never plaintext.
- Uploaded assets stored on mounted volume with sanitized filenames.
- Nginx limits upload size and locks down hidden files.

## 8. Volumes
- `postgres_data`
- `redis_data`
- `hls_data`
- `logos_data`
- `logs_data`
- `certbot_www`
- `letsencrypt`

## 9. API Surface
- `POST /api/v1/auth/login`
- `GET/POST /api/v1/streams`
- `GET/PATCH/DELETE /api/v1/streams/{id}`
- `POST /api/v1/streams/{id}/start|stop|restart`
- `GET/POST/PATCH/DELETE /api/v1/streams/{id}/inputs`
- `GET/POST/PATCH/DELETE /api/v1/streams/{id}/outputs`
- `GET/POST/PATCH/DELETE /api/v1/streams/{id}/abr-profiles`
- `POST /api/v1/streams/{id}/logo`
- `GET /api/v1/streams/{id}/runtime`
- `GET /api/v1/streams/{id}/logs`
- `GET /api/v1/streams/{id}/playback-urls`

## 10. Deployment Flow
1. Clone repo to host.
2. Copy `.env.example` to `.env` and fill secrets.
3. Point Route53 A record for `keystream.rockstreamer.com` to `206.189.128.172`.
4. Run deployment script.
5. Obtain TLS cert with certbot.
6. Start compose stack.
7. Validate health checks and login.

## 11. Test Strategy
- Backend: pytest for auth, URL generation, stream CRUD, pipeline builder.
- Frontend: lint + type-check.
- Smoke: `docker compose config`, service health endpoints.

## 12. Known Constraints
- GStreamer plugin availability varies by distro; image pins Debian packages.
- HLS ingest support depends on `souphttpsrc` and `hlsdemux` plugins.
- RTMP/SRT output behavior should be validated with live test sources during deployment.

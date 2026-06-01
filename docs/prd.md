# Rocks Stream PRD

## 1. Product Summary
Rocks Stream is a self-hosted web streaming platform for ingesting live sources, transcoding them with FFmpeg, and publishing managed SRT, RTMP, and HLS outputs through a secure admin portal. It is inspired by Nimble Streamer’s operational model but delivered as a modern Docker Compose stack.

## 2. Goals
- Let admins manage live stream inputs, outputs, ABR profiles, overlays, and playback URLs from one web portal.
- Use FFmpeg end-to-end for ingest, processing, packaging, and restreaming.
- Support production deployment behind Nginx with HTTPS and Route53 DNS.
- Provide health, logs, and operational controls for every stream.

## 3. Non-Goals
- Multi-tenant billing.
- DRM, SSAI, or viewer analytics.
- Full CDN orchestration.
- Browser-based live contribution.

## 4. Users
### Primary user
- Streaming operations admin.

### User jobs
- Create a stream with one or more ingest sources.
- Configure failover priority.
- Enable or disable ABR ladders.
- Upload a logo and position it.
- Start, stop, and monitor pipelines.
- Copy output/playback URLs.
- Preview HLS outputs in-browser.

## 5. Core Functional Requirements
### 5.1 Authentication
- Admin login with JWT.
- Initial admin seeded from environment variables.
- Passwords hashed with bcrypt.

### 5.2 Stream Management
- Create, read, update, delete streams.
- Store stream metadata: name, stream key, description, enabled status.
- Multiple input sources per stream with priority ordering.
- Input protocols: SRT, RTMP, HLS.
- Status fields: running, stopped, error, degraded.
- Metrics fields: bitrate, resolution, uptime, last error.

### 5.3 Output Management
- Per stream, enable one or more outputs:
  - HLS
  - RTMP
  - SRT
- Auto-generate canonical URLs.
- Show copyable URLs in the portal.
- Show preview player for HLS output and master playlist.

### 5.4 ABR Transcoding
- Per-stream ABR toggle.
- Default profiles: 1080p, 720p, 360p, 280p, 144p.
- Allow bitrate overrides and enable/disable per profile.
- Generate HLS master and variant playlists when ABR is enabled.

### 5.5 Logo Overlay
- Upload PNG/SVG logo assets.
- Enable/disable overlay per stream.
- Support corner placement and freeform x/y positioning.
- Preview positioning in the UI.
- Pass overlay settings to the FFmpeg pipeline builder.

### 5.6 Streaming Engine
- Start/stop/restart stream pipelines.
- Pipeline generation per stream based on input/output/profile settings.
- Fail over across ordered inputs.
- Persist logs and status snapshots.
- Health endpoint for each running job.

### 5.7 Operations
- Docker Compose starts full platform.
- Nginx serves frontend, proxies API, and serves HLS artifacts.
- Let’s Encrypt SSL supported in production.
- Route53 guidance and automation script without embedded AWS credentials.

## 6. Quality Attributes
- Production-safe defaults.
- No plaintext secrets committed.
- Health checks for all services.
- Clear logs and diagnostics.
- API-first architecture.

## 7. Acceptance Criteria
- `docker compose up -d` starts all services healthy.
- Admin can log in and manage streams.
- Admin can define inputs and outputs.
- HLS preview works using hls.js.
- Enabling ABR exposes `master.m3u8` and variant playlists.
- Overlay config persists and is reflected in pipeline specs.
- README explains local and production deployment.

## 8. Milestones
1. PRD + architecture docs.
2. Backend API + schema + auth.
3. Streaming engine + pipeline manager.
4. Frontend portal.
5. Nginx + Compose + SSL + deployment.
6. Testing, git init, push, deploy.

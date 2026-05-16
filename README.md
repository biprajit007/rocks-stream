# Rocks Stream

Rocks Stream is a Docker Compose based live streaming control plane inspired by Nimble Streamer. It uses **GStreamer** for ingest, transcoding, ABR ladder generation, HLS packaging, logo overlay, and output publishing.

## Stack
- Frontend: Next.js
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL
- Cache: Redis
- Streaming engine: Python service that manages `gst-launch-1.0` pipelines
- Proxy/edge: Nginx RTMP + HTTP + HLS static serving
- TLS: static valid certificate files mounted into nginx

## Repository layout
```text
apps/backend              FastAPI API, auth, models, migrations
apps/frontend             Next.js admin portal
services/streaming-engine GStreamer pipeline manager
infra/nginx               Nginx RTMP + HTTP config
scripts                   Deployment and DNS helpers
docs                      PRD + architecture
samples                   Sample stream payloads
```

## Features
- Admin login with JWT
- Dashboard and stream list
- CRUD-oriented API for streams, inputs, outputs, ABR profiles, and logo config
- SRT / RTMP / HLS output URL generation
- HLS preview player via hls.js
- Per-stream ABR toggle with default ladder: 1080p, 720p, 360p, 280p, 144p
- Logo upload and coordinate/corner positioning
- GStreamer pipeline manager with start/stop/restart endpoints
- Health checks for all services

## Quick start (local)
### 1) Configure environment
```bash
cp .env.example .env
# Edit at minimum:
# - POSTGRES_PASSWORD
# - JWT_SECRET
# - ADMIN_EMAIL
# - ADMIN_PASSWORD
```

### 2) Start the stack
```bash
docker compose up -d --build
```

### 3) Verify health
```bash
docker compose ps
curl -f http://localhost/health
curl -f http://localhost/api/v1/health || true
curl -f http://localhost:8000/health
curl -f http://localhost:8081/health
```

### 4) Log in
- Portal: `http://localhost`
- Default seeded admin comes from `.env`

## Core URLs
Given stream key `main-channel`:
- HLS: `https://keystream.rockstreamer.com/live/main-channel/index.m3u8`
- HLS master: `https://keystream.rockstreamer.com/live/main-channel/master.m3u8`
- RTMP: `rtmp://keystream.rockstreamer.com/live/main-channel`
- SRT: `srt://keystream.rockstreamer.com:9000?streamid=main-channel`

## Sample stream creation
```bash
TOKEN=$(curl -s http://localhost/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"admin@rocks.stream","password":"ChangeMe123!"}' | jq -r .access_token)

curl -s http://localhost/api/v1/streams \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d @samples/sample-stream.json | jq
```

## Backend migrations
The backend container runs:
```bash
alembic -c alembic.ini upgrade head
```

Manual migration command:
```bash
docker compose exec backend alembic -c alembic.ini upgrade head
```

## Production deployment on `206.189.128.172`
### 1) Clone and prepare
```bash
ssh root@206.189.128.172
apt-get update && apt-get install -y git docker.io docker-compose-plugin awscli
git clone https://github.com/biprajit007/rocks-stream.git
cd rocks-stream
cp .env.example .env
nano .env
```

### 2) Route53 DNS
Create or update the A record for `keystream.rockstreamer.com`.

Manual Route53 console target:
- Name: `keystream.rockstreamer.com`
- Type: `A`
- Value: `206.189.128.172`
- TTL: `300`

CLI helper:
```bash
export AWS_ROUTE53_ZONE_ID=YOUR_HOSTED_ZONE_ID
export PUBLIC_DOMAIN=keystream.rockstreamer.com
./scripts/route53-upsert.sh 206.189.128.172
```

No AWS credentials are stored in the repo. Use your normal AWS CLI auth flow.

### 3) Bring the stack up
```bash
./scripts/deploy.sh
```

### 4) Install the valid SSL certificate
Place your existing valid certificate and key on the server at:
```bash
mkdir -p ssl
cp /path/to/fullchain.pem ssl/fullchain.pem
cp /path/to/privkey.pem ssl/privkey.pem
chmod 644 ssl/fullchain.pem
chmod 600 ssl/privkey.pem
```

### 5) Enable TLS
This repo ships HTTP-first nginx to avoid boot failure before cert files exist. After `ssl/fullchain.pem` and `ssl/privkey.pem` are in place:
```bash
./scripts/enable-ssl.sh
docker compose restart nginx
```

## Health checks
```bash
docker compose ps
curl http://localhost/health
curl http://localhost:8000/health
curl http://localhost:8081/health
```

## Notes on GStreamer
- The streaming engine uses `gst-launch-1.0` and Debian GStreamer packages.
- Overlay is applied with `gdkpixbufoverlay`.
- HLS output is written to a shared volume served by Nginx.
- ABR master playlist is written by the engine after profile pipelines are generated.

## What to validate on the server
- RTMP ingress/output on port `1935`
- SRT ingress/output on port `9000`
- HLS playback at `/live/<stream_key>/index.m3u8`
- ABR master playlist at `/live/<stream_key>/master.m3u8`
- Uploaded logos land in shared storage and affect pipeline specs

## Security reminders
- Change every default password and secret.
- Do not commit `.env`.
- Do not store AWS keys in the repo.
- Put the host behind a firewall and only expose required ports: 80, 443, 1935, 9000.

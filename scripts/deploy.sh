#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo ".env is missing. Copy .env.example to .env and fill secrets first."
  exit 1
fi

export $(grep -v '^#' .env | xargs)

docker compose pull --ignore-pull-failures || true
docker compose build --pull
docker compose up -d postgres redis backend streaming-engine frontend nginx

echo "Waiting for core services..."
sleep 10

docker compose ps

echo "Deployment finished. If this host already has valid certs in ./ssl, run ./scripts/enable-ssl.sh to switch nginx to HTTPS mode."

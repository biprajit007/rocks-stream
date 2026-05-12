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
docker compose up -d postgres redis backend streaming-engine frontend nginx certbot

echo "Waiting for core services..."
sleep 10

docker compose ps

echo "If DNS is already pointed at this host, request TLS with:"
echo "docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d ${PUBLIC_DOMAIN} --email ${LETSENCRYPT_EMAIL} --agree-tos --no-eff-email"

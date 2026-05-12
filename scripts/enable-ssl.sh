#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp "$ROOT_DIR/infra/nginx/nginx.ssl.conf" "$ROOT_DIR/infra/nginx/nginx.conf"
docker compose build nginx
docker compose up -d nginx

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
compose=(docker compose --env-file .env --profile production --profile async)

"${compose[@]}" ps
curl --fail --silent --show-error --max-time 8 http://127.0.0.1/api/health/
printf '\n'
curl --fail --silent --show-error --head --max-time 8 http://127.0.0.1/
printf '\n--- memory ---\n'
free -h
printf '\n核心 HTTP、API 健康检查和容器状态通过。\n'

#!/usr/bin/env bash
# 灵溯前端：在 macOS 本机原生启动 Vite（绕过 colima 不稳定的 5173 端口转发）。
# /api 代理指向 docker 后端 http://127.0.0.1:18001（18000 被 colima VM 陈旧转发占用，改用 18001）。
# 用法：./scripts/dev-frontend.sh
set -euo pipefail
cd "$(dirname "$0")/../frontend"
exec env VITE_API_PROXY_TARGET=http://127.0.0.1:18001 npm run dev -- --host 127.0.0.1 --port 5173

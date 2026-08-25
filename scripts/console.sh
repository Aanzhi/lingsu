#!/usr/bin/env bash
# 灵溯项目控制台启动器（宿主机独立进程，不属于 Docker Compose）
# 用法：./scripts/console.sh   （可选 PORT=8800 环境变量指定端口）
set -euo pipefail
cd "$(dirname "$0")/.."
export PORT="${PORT:-8800}"
echo "灵溯项目控制台（宿主机独立进程）→ http://127.0.0.1:${PORT}"
echo "控制台不会随 Docker 自动启动或停止；可在页面内控制 Docker / Colima 和项目服务。"
exec python3 scripts/project-console.py

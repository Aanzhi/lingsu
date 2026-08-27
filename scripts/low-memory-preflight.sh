#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "缺少 .env；请在服务器本地创建，不要从 Git 上传密钥。" >&2
  exit 1
fi

compose=(docker compose --env-file .env --profile production --profile async)
mapfile -t services < <("${compose[@]}" config --services)
expected=(postgres redis backend celery nginx)
for service in "${expected[@]}"; do
  if ! printf '%s\n' "${services[@]}" | grep -qx "$service"; then
    echo "Compose 未包含核心服务：$service" >&2
    exit 1
  fi
done

for optional in clamav gotenberg celery_beat frontend; do
  container_id=$(docker compose --env-file .env --profile scanner --profile documents --profile async-beat --profile dev ps -q "$optional" 2>/dev/null || true)
  if [[ -n "$container_id" ]]; then
    echo "检测到不应运行的可选服务：$optional ($container_id)" >&2
    exit 1
  fi
done

if grep -Eq '^ATTACHMENT_UPLOADS_ENABLED=(1|true|yes|on)$' .env; then
  echo "附件上传已启用，但 2GB 核心方案没有安全扫描服务。" >&2
  exit 1
fi
if grep -Eq '^PDF_EXPORT_ENABLED=(1|true|yes|on)$' .env; then
  echo "PDF 导出已启用，但 2GB 核心方案没有文档转换服务。" >&2
  exit 1
fi

echo "--- memory ---"
free -h
echo "--- swap ---"
swapon --show || true
echo "--- docker ---"
docker version --format '{{.Server.Version}}'
docker compose version
echo "--- core services ---"
printf '%s\n' "${services[@]}"
echo "低内存核心部署预检通过；脚本未修改服务器状态。"

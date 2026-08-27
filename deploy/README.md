# 灵溯 2GB 生产部署

小规格服务器默认只运行网页核心链路：PostgreSQL、Redis、Django/Gunicorn、一个 Celery worker 和 Nginx。

默认关闭以下可选服务：

- ClamAV：关闭附件上传入口，`FILE_SCAN_REQUIRED` 仍保持为 `1`，不会绕过安全扫描。
- Gotenberg：关闭 PDF 转换，只保留 Word 报告导出。
- Celery Beat：核心流程不依赖定时任务，避免常驻进程和额外内存占用。
- Vite 前端开发容器：生产环境使用预构建 Nginx 镜像。

## 生产启动

将服务器上的 `.env` 设置为 `600`，保留真实密钥和数据库密码，只把非敏感部署开关设置为：

```text
ATTACHMENT_UPLOADS_ENABLED=0
CLAMAV_ENABLED=0
CLAMAV_HOST=
DOCUMENT_CONVERTER_ENABLED=0
PDF_EXPORT_ENABLED=0
CELERY_WORKER_ENABLED=1
CELERY_BEAT_ENABLED=0
CELERY_POOL=solo
CELERY_CONCURRENCY=1
GUNICORN_WORKERS=1
GUNICORN_THREADS=2
NGINX_BIND=80
```

镜像发布工作流会为每个 Git 提交发布两个不可变镜像。把镜像标签写入 `.env` 后执行：

```bash
docker compose --env-file .env --profile production --profile async pull backend celery nginx
docker compose --env-file .env --profile production --profile async up -d --no-build postgres redis backend celery nginx
docker compose --env-file .env --profile production --profile async exec -T backend python manage.py seed_ai_agents
```

不要使用 `docker compose down -v`。数据库、Redis 和媒体目录通过命名卷保留。

## 控制台

控制台是独立的宿主机进程，不在 Compose 中。安装仓库里的两个 systemd unit 后，控制台只监听 `127.0.0.1:8800`，通过 SSH 隧道访问：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lingsu.service
sudo systemctl enable --now lingsu-console.service
ssh -N -L 8800:127.0.0.1:8800 ubuntu@SERVER_IP
```

Docker 或项目服务停止时，控制台仍然保持运行，可以查看日志并再次启动核心服务。

## 2GB 机器检查

```bash
bash scripts/low-memory-preflight.sh
bash scripts/low-memory-healthcheck.sh
```

如果机器没有交换空间，先确认 `/swapfile` 不存在，再按运维规范创建 2GB swap；脚本只检查，不自动覆盖已有文件。

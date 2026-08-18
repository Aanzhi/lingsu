# 灵溯 · 青少年科学创新项目工作台

面向学校的科创项目协作平台：学生从立项、材料沉淀到项目报告导出，教师逐项审核；案例库提供可复用的项目路径与思路，AI 只提供可编辑的辅助草稿并保留使用记录。

当前交互问题分析、已实现改进、未完成风险和下一步验收计划见：[灵溯交互问题分析、执行状态与下一步计划](docs/superpowers/plans/2026-08-13-lingsu-interaction-audit.md)。

## 技术与边界

- 前端：Vue 3、Vite、TypeScript、Element Plus、Pinia。
- 后端：Django REST Framework、PostgreSQL、Celery、Redis。
- 所有业务记录关联学校，接口必须按当前用户学校过滤；项目过程及附件仅向成员、指导教师和对应管理员开放。
- 文件限制为 500MB。Django 保存原件并计算 SHA-256，生产环境由官方多架构 `clamav-debian` 扫描后才允许下载；AI 与报告导出通过 Celery 执行。
- Gotenberg 是容器化的 LibreOffice 转换端点；报告任务生成 DOCX 后向它请求 PDF。它不应向公网暴露端口。

## 本地启动

1. 在项目根目录复制环境变量：`cp .env.example .env`，设置 `POSTGRES_PASSWORD`、`DJANGO_SECRET_KEY`，需要 AI 时再设置 `OPENAI_API_KEY`。
2. 开发模式：`docker compose --profile dev up --build`。
   - Vue 开发站点：<http://localhost:5173>
   - Django API：<http://localhost:8000>
3. 首次启动时 `backend` 会执行迁移。创建管理员：`docker compose exec backend python manage.py createsuperuser`。
4. 生产部署：将 `DJANGO_DEBUG=0`，配置 HTTPS 域名、`DJANGO_ALLOWED_HOSTS`、`CSRF_TRUSTED_ORIGINS` 后执行 `docker compose --profile production up --build -d`。Nginx 只代理 `/api/` 与 `/admin/`；私有附件和报告必须通过鉴权下载接口访问。

### 当前集成环境启动

如果本机已经存在灵溯集成数据库卷，请使用项目内的集成配置启动，避免用新的 `.env` 默认数据库名连接到错误的数据卷：

```bash
docker compose --env-file .env.integration --profile dev up --build -d
docker compose --env-file .env.integration exec -T backend python manage.py seed_demo --allow-production
docker compose --env-file .env.integration ps
```

当前集成环境的前端地址仍为 <http://127.0.0.1:5173>，后端直接检查地址为 <http://127.0.0.1:18001/api/health/>（18000 被 colima VM 陈旧端口转发占用，已改用 18001）。`.env.integration` 只用于本机演示，不应作为生产配置。

## 配置说明

| 变量 | 用途 |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django 会话与签名密钥，生产环境必须替换。 |
| `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS` | Django 运行模式与允许访问的域名。 |
| `POSTGRES_*` | 数据库连接与 Compose 初始化参数。 |
| `REDIS_URL` | Celery broker/result backend。 |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | 仅后端及 Celery 使用，绝不发送到浏览器。 |
| `DOCUMENT_CONVERTER_URL` | DOCX/PDF 导出使用的 Gotenberg 服务地址。 |
| `MAX_UPLOAD_SIZE` | 默认 `524288000`（500MB）。 |
| `FILE_SCAN_REQUIRED` / `CLAMAV_HOST` | 生产文件安全扫描开关与 ClamAV 服务地址。生产必须启用。 |

## 部署注意事项

- 生产部署前将 `DJANGO_DEBUG=0`、设置真实域名、HTTPS 终止和持久化卷备份策略；不要使用示例密码。
- 后端使用 Gunicorn，Compose 健康检查会验证数据库与 Django API。生产环境在上游负载均衡器或 Nginx TLS 配置中终止 HTTPS。
- 生产后端与 Celery 直接运行已构建镜像，不挂载宿主机源码；发布新版本必须重新构建镜像。
- 上传文件由 `media_data` 卷持久化。每天备份 PostgreSQL 与该卷；生产可用对象存储替换媒体存储实现，保持权限下载接口不变。
- 病毒扫描与权限下载已由 Django/Celery 实现；分片上传、文档/OCR 解析仍属于后续增强项。
- 大于 8MB 的材料在浏览器中自动切换为可恢复分片上传：服务端保留上传会话、已完成分块与配额预留，重传同一分块是幂等的。所有分块、总文件哈希验证通过后才合并为私有附件并进入 ClamAV 扫描。
- `STORAGE_BACKEND=local` 使用容器的私有媒体卷。设为 `s3` 可接入 AWS S3 或 MinIO；必须设置 `S3_BUCKET_NAME`、访问密钥和（MinIO 时）`S3_ENDPOINT_URL`。对象不开放为公共 URL，下载仍统一经过 Django 权限检查。

## 备份与恢复

- 每日备份：设置 `BACKUP_ROOT` 后执行 `scripts/backup.sh`。脚本同时备份 PostgreSQL、自有媒体卷和环境配置快照，默认保留 30 天。
- 恢复演练：在维护窗口执行 `scripts/restore.sh /backups/<时间戳>`。该操作会覆盖数据库和媒体文件，恢复后重启 Django 与 Celery。
- 至少每月在隔离环境执行一次恢复演练；备份目录必须同步到服务器之外的加密存储。

# 腾讯云 2GB 核心业务部署实施计划

> 执行约束：本计划在当前任务中由主代理执行，不使用子代理。计划阶段不连接远程服务器、不修改远程服务、不写入生产密钥。

## 目标

在腾讯云 2GB 内存主机上稳定运行灵溯的核心业务闭环：

- 公共入口、注册、登录和角色工作台跳转；
- 学生项目创建、项目列表、研究进程和文本材料编辑；
- 教师项目池、项目认领、材料审核和成员管理；
- 灵思 AI 的真实会话、异步生成、失败重试和刷新后恢复；
- Word 研究报告生成与下载；
- PostgreSQL、Redis、Django/Gunicorn、Celery Worker、Nginx；
- 独立项目控制台，继续作为宿主机进程运行在 127.0.0.1:8800。

2GB 主机不作为“一次启动全部能力”的目标。首发版本优先保证页面、文本业务和 AI 核心链路可用；附件安全扫描、PDF 转换和周期任务以明确的降级状态运行，不能通过关闭安全校验来伪造成功。

## 架构结论

### 首发常驻服务

生产 Compose 只运行：

| 服务 | 作用 | 首发策略 |
| --- | --- | --- |
| PostgreSQL | 业务数据、会话、审核、通知和 AI 日志 | 常驻，限制连接数和内存 |
| Redis | Celery broker/result backend | 常驻，限制最大内存 |
| backend | Django/Gunicorn API 和管理端 | 常驻，单 Gunicorn worker |
| celery | AI、报告、异步业务任务 | 常驻，单进程、单并发、solo pool |
| nginx | 预构建前端静态文件和反向代理 | 常驻，公网只暴露 80 |

独立控制台不加入 Compose，不依赖 Docker 容器，不随 docker compose stop 关闭。控制台由 systemd 作为宿主机进程运行，监听 127.0.0.1:8800，通过 SSH 隧道访问。

### 首发关闭服务

以下服务不进入 2GB 首发栈：

- ClamAV：常驻内存约接近 1GB，和业务服务共同运行风险过高；
- Gotenberg：镜像和运行时开销较大，PDF 转换不是首发核心能力；
- Celery Beat：日常核心页面不依赖它，回收站清理可由轻量 systemd timer 或手动任务代替；
- frontend 开发容器：生产使用预构建的 Nginx 镜像，服务器不运行 Node/Vite，不在 2GB 主机上执行前端构建。

### 关键安全边界

首发环境必须保持：

- FILE_SCAN_REQUIRED=1；
- CLAMAV_ENABLED=0；
- ATTACHMENT_UPLOADS_ENABLED=0；
- DOCUMENT_CONVERTER_ENABLED=0；
- PDF_EXPORT_ENABLED=0。

这表示首发版本允许学生保存和审核文本材料、生成 Word 报告，但不接受附件上传，不提供 PDF 导出。不能把 FILE_SCAN_REQUIRED 改为 0 来绕过安全扫描，否则会让未扫描附件进入项目、AI 上下文或报告链路。页面和 API 必须返回明确的“当前部署未启用附件/PDF”状态，而不是出现提交后异步失败。

## 当前证据与资源判断

本地 Docker 运行时已经测得以下空闲或低负载数据：

| 容器 | 观测内存 | 2GB 判断 |
| --- | ---: | --- |
| PostgreSQL | 约 49MiB | 可保留，需限制连接与缓冲 |
| Redis | 约 9MiB | 可保留，设置 64MiB 上限 |
| backend | 约 275MiB | 可保留，限制为 384MiB |
| celery | 约 315MiB | 可保留，但必须改为 solo、单并发 |
| celery beat | 约 90MiB | 首发延后 |
| Gotenberg | 约 195MiB 空闲 | 首发延后 |
| ClamAV | 约 981MiB | 2GB 主机不常驻 |

结论：

1. 2GB 加 2GB swap 可以承载核心栈，但必须采用预构建镜像、单并发异步 worker 和明确的容器上限。
2. 2GB 不适合同时启动 ClamAV、Gotenberg、Beat、开发前端和生产业务服务。
3. swap 只是防止瞬时 OOM 的缓冲，不是把 2GB 当成 4GB 使用；长期 swap 抖动仍然表示需要升级实例。
4. 如果必须同时启用附件扫描和 PDF 转换，应优先升级到至少 4GB，而不是继续压缩业务服务。

## 核心业务与降级业务契约

### 必须在首发通过的功能

- 公共首页、注册、普通登录、平台登录隔离；
- 学生项目创建、项目列表分页、项目生命周期操作；
- 学生研究进程、任务文本填写、实验日志文本保存；
- 教师项目池查看开题字段、认领项目、指导项目列表；
- 教师材料审核、通过、打回和修改意见；
- 学生/教师通知、邀请和成果申请的文本状态流转；
- 灵思 AI 开题、研究、成果表达三种模式；
- Celery 异步任务状态、失败重试和刷新后恢复；
- Word 报告生成和下载；
- Nginx 80 端口、后端健康检查和独立控制台。

### 首发明确降级的功能

| 能力 | 处理方式 | 恢复条件 |
| --- | --- | --- |
| 附件上传 | 前端入口隐藏或禁用；API 创建上传会话前直接返回 4xx 和原因 | 启用独立扫描服务并通过扫描验收 |
| PDF 报告 | 前端只显示 Word；PDF 创建请求在排队前直接返回 4xx | 启用 Gotenberg 并通过转换验收 |
| 30 天回收站清理 | 不启用 Beat；使用 systemd timer 或维护命令 | 需要周期调度时启用轻量 timer |
| AI 真实模型 | 使用单 Celery Worker，限制任务并发 | 升级机器后可扩展并发 |

### 不允许的降级

- 不将 FILE_SCAN_REQUIRED 改为 0；
- 不将 AI、上传或报告任务改为“前端假装完成”；
- 不在每次 backend 重启时执行 seed_ai_agents --reset；
- 不使用 docker compose down -v 清理内存；
- 不把数据库、媒体文件或服务器 .env 放进 GitHub；
- 不在公网暴露 8000、18001、8800、5432 或 6379。

## 实施阶段总览

### 阶段 0：发布前只读检查

确认当前分支、工作区修改、Compose profile、镜像构建方式和服务器资源。保留现有未提交修改，先区分本计划涉及文件与其他 UI/AI 变更，不执行 reset、checkout 或批量格式化。

检查项：

~~~sh
git status --short
git branch --show-current
docker compose config --quiet
rg -n "CELERY_ENABLED|DOCUMENT_CONVERTER_ENABLED|CLAMAV_ENABLED|FILE_SCAN_REQUIRED|GUNICORN_WORKERS" .env.example docker-compose.yml scripts backend frontend
~~~

### 阶段 1：改造低内存配置契约

修改范围：

- .env.example
- docker-compose.yml
- backend/config/settings.py
- scripts/project-console.py
- scripts/test_project_console.py
- 新增或更新后端上传、报告和健康检查测试

#### 1.1 拆分异步 Worker 和 Beat 开关

保留旧变量兼容现有本地环境，但新增明确变量：

~~~env
CELERY_ENABLED=1
CELERY_WORKER_ENABLED=1
CELERY_BEAT_ENABLED=0
CELERY_CONCURRENCY=1
CELERY_POOL=solo
CELERY_LOG_LEVEL=WARNING
~~~

控制台逻辑采用以下兼容规则：

~~~python
CELERY_WORKER_ENABLED = configured_env_flag(
    "CELERY_WORKER_ENABLED",
    configured_env_flag("CELERY_ENABLED", False),
)
CELERY_BEAT_ENABLED = configured_env_flag("CELERY_BEAT_ENABLED", False)
~~~

CELERY_ENABLED=1 仍然可以让旧环境启动 Worker，但不再隐式启动 Beat。只有明确设置 CELERY_BEAT_ENABLED=1 才加入 Beat profile。

2GB 生产模式下，控制台的服务清单应显示：

~~~text
postgres, redis, backend, celery, nginx
~~~

ClamAV、Gotenberg、Celery Beat 不应出现在首发服务状态中。

#### 1.2 删除启动时的 destructive seed

backend 的启动命令保留迁移和静态文件收集，但删除每次启动都执行的：

~~~text
seed_ai_agents --reset
~~~

发布部署时只手动执行一次不带 reset 的幂等初始化：

~~~sh
python manage.py seed_ai_agents
~~~

平台管理员后续在页面中维护的 AI 模板不能因为容器重启被重置。只有明确的模板维护操作才允许使用 reset，并且必须先备份和确认影响范围。

#### 1.3 让异步任务低并发运行

Worker 使用：

~~~sh
celery -A config worker --loglevel=WARNING --pool=solo --concurrency=1
~~~

不使用默认 prefork 多进程，不根据宿主机 CPU 自动增加并发。AI 长任务和报告任务共享一个队列时，前端必须显示处理中状态；后续如出现排队过长，先增加机器内存，再考虑并发。

#### 1.4 低内存 Gunicorn 参数

backend 保持一个 Gunicorn worker，并增加请求回收，避免长时间运行造成内存累积：

~~~sh
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --threads 2 \
  --max-requests 400 \
  --max-requests-jitter 40 \
  --timeout 120
~~~

具体模块路径以仓库当前启动命令为准，不在本阶段改业务接口。

### 阶段 2：给 Compose 加资源边界

修改 docker-compose.yml，只给首发服务加低内存约束；可选服务即使手动启用也要有单独的风险说明，不默认并入核心栈。

建议起始值：

~~~yaml
postgres:
  command: postgres -c shared_buffers=64MB -c work_mem=4MB -c maintenance_work_mem=32MB -c max_connections=30
  mem_limit: 256m
  cpus: 0.40
  pids_limit: 128
  restart: unless-stopped

redis:
  command: redis-server --appendonly yes --maxmemory 64mb --maxmemory-policy noeviction
  mem_limit: 96m
  cpus: 0.20
  pids_limit: 64
  restart: unless-stopped

backend:
  mem_limit: 384m
  cpus: 0.70
  pids_limit: 128
  restart: unless-stopped

celery:
  mem_limit: 384m
  cpus: 0.70
  pids_limit: 128
  restart: unless-stopped

nginx:
  mem_limit: 64m
  cpus: 0.20
  pids_limit: 64
  restart: unless-stopped
~~~

这些值不是性能承诺，而是首发保护线。若数据库出现 OOM，应先检查查询和连接泄漏，不直接无限制放大内存。Redis 使用 noeviction，避免静默淘汰 Celery 任务状态；如果 Redis 达到上限，应报警并处理积压，而不是丢失状态。

验收：

~~~sh
docker compose --profile production --profile async config --quiet
docker compose --profile production --profile async config --services
git diff --check
~~~

### 阶段 3：在 API 层对关闭能力 fail fast

修改范围：

- backend/config/settings.py
- 上传会话 ViewSet 与对应 serializer/view 测试；
- 报告导出 ViewSet 与对应测试；
- 健康检查响应；
- frontend/src/api、StudentTask.vue、StudentProject.vue 或当前实际调用文件；
- 相关前端定向测试。

增加配置：

~~~python
ATTACHMENT_UPLOADS_ENABLED = os.getenv("ATTACHMENT_UPLOADS_ENABLED", "1") == "1"
PDF_EXPORT_ENABLED = os.getenv("PDF_EXPORT_ENABLED", "1") == "1"
~~~

上传会话在创建前检查：

~~~python
if not settings.ATTACHMENT_UPLOADS_ENABLED:
    raise ValidationError(
        "当前核心部署未启用附件上传；请先保存文本材料，或联系管理员启用安全扫描。"
    )
~~~

PDF 报告在入队前检查：

~~~python
if (
    serializer.validated_data["format"] == ReportExport.Format.PDF
    and not settings.PDF_EXPORT_ENABLED
):
    raise ValidationError(
        "当前核心部署未启用 PDF 转换，请导出 Word 文档。"
    )
~~~

健康接口增加能力声明，不泄露密钥：

~~~json
{
  "status": "ok",
  "capabilities": {
    "attachments": false,
    "pdf_export": false
  }
}
~~~

前端启动时读取能力，采用 fail-safe：

- 能力为 false 时隐藏或禁用对应按钮；
- 能力接口失败时按关闭处理，不恢复危险入口；
- 不用普通页面的 loading 文案掩盖功能不可用；
- 文本材料、AI、Word 导出仍可用时不被附件能力阻断。

测试必须证明：附件关闭时不会创建上传会话，PDF 关闭时不会进入异步队列，Word 仍可以创建导出任务。

### 阶段 4：改为 GitHub Actions 构建并发布镜像

#### 4.1 原因

现有生产 Nginx Dockerfile 会在服务器内执行 npm ci 和 npm run build。2GB 主机上执行 Node 构建容易与 Docker、Django、PostgreSQL 同时争抢内存，是部署卡死的高风险来源。

服务器只拉取固定版本镜像，不在生产机上 up build：

- ghcr.io/aanzhi/lingsu-backend:完整 commit SHA；
- ghcr.io/aanzhi/lingsu-web:完整 commit SHA。

镜像仓库保持 private。服务器只保存读取 GHCR 所需的最小权限凭据，不把 token 写入 Git URL、Compose 文件或聊天记录。

#### 4.2 工作流

新增 .github/workflows/publish-images.yml：

~~~yaml
name: Publish deploy images

on:
  push:
    branches:
      - main
      - codex/ui-audit-consistency

permissions:
  contents: read
  packages: write

jobs:
  images:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: GITHUB_ACTOR
          password: GITHUB_TOKEN
      - uses: docker/build-push-action@v6
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: true
          tags: ghcr.io/aanzhi/lingsu-backend:COMMIT_SHA
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ./infra/nginx/Dockerfile
          push: true
          build-args: |
            NPM_REGISTRY=https://registry.npmmirror.com
          tags: ghcr.io/aanzhi/lingsu-web:COMMIT_SHA
~~~

实际实现时应让镜像发布 job 依赖已有的前端单元测试、构建和后端检查 job；测试失败不能发布镜像。镜像 tag 必须包含完整 commit SHA，禁止服务器跟踪 latest。

#### 4.3 Compose 镜像优先

生产服务保留本地 build 作为开发回退，但增加 backend image 和 web image 配置。服务器环境文件填入已经发布的具体 SHA，不使用 shell 未展开的占位字符串。

服务器启动使用 no-build：

~~~sh
docker compose --profile production --profile async pull backend nginx
docker compose --profile production --profile async up -d --no-build postgres redis backend celery nginx
~~~

若镜像拉取失败，不在服务器临时改成 up build，先修复 GHCR 登录、tag 或网络问题，避免低配主机进入不可控构建状态。

### 阶段 5：服务器初始化和 systemd

服务器初始化必须先做只读检查，再决定是否创建 swap 或安装缺失依赖。不要假设主机是空的，也不要删除现有 /home/ubuntu/lingsu 内容。

#### 5.1 只读预检

~~~sh
free -h
df -h / /home
docker --version
docker compose version
git --version
curl --version
ss -ltnp
systemctl is-active docker
~~~

确认：

- 内存约 2GB，磁盘有镜像、数据库卷和媒体文件的余量；
- Docker Engine 和 Compose plugin 可用；
- 80 端口是否被旧服务占用；
- 8800 只被控制台本机监听；
- 没有正在运行的旧生产栈需要保护。

#### 5.2 swap

如果主机没有 swap，创建 2GB swap 文件；如果已有 swap，先记录大小和使用率，不重复创建：

~~~sh
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
~~~

/etc/fstab 追加前必须检查是否已存在同一行，避免重复配置。swap 创建属于主机状态变更，正式执行前确认目标文件不存在且不覆盖现有 swap。

#### 5.3 代码与密钥

代码从私有 GitHub 仓库的固定分支或 commit 获取，服务器不使用工作区临时文件归档。推荐采用 GitHub deploy key 或只读 token；凭据不写入远程 URL，不提交到 .env，不出现在 systemd unit。

目标目录策略：

- 若 /home/ubuntu/lingsu 不存在：创建；
- 若目录为空：创建 /home/ubuntu/lingsu/source；
- 若目录有内容：先停止，列出内容和当前服务，不覆盖、不删除；
- 发布切换使用带 SHA 的 source 目录或 release 目录，保留上一个 release 便于回滚。

服务器 .env 权限必须为 600，只存放服务器本地配置：

~~~env
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=1.15.230.239,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://1.15.230.239
CORS_ALLOWED_ORIGINS=http://1.15.230.239
DJANGO_SECURE_SSL_REDIRECT=0
DJANGO_HSTS_SECONDS=0
DJANGO_SESSION_COOKIE_SECURE=0
DJANGO_CSRF_COOKIE_SECURE=0
BACKEND_BIND=127.0.0.1:18001
NGINX_BIND=80
GUNICORN_WORKERS=1
CELERY_WORKER_ENABLED=1
CELERY_BEAT_ENABLED=0
CELERY_CONCURRENCY=1
CELERY_POOL=solo
CELERY_LOG_LEVEL=WARNING
CLAMAV_ENABLED=0
CLAMAV_HOST=
FILE_SCAN_REQUIRED=1
ATTACHMENT_UPLOADS_ENABLED=0
DOCUMENT_CONVERTER_ENABLED=0
PDF_EXPORT_ENABLED=0
STORAGE_BACKEND=local
BACKEND_IMAGE=ghcr.io/aanzhi/lingsu-backend:COMMIT_SHA
WEB_IMAGE=ghcr.io/aanzhi/lingsu-web:COMMIT_SHA
~~~

DJANGO_SECRET_KEY、POSTGRES_PASSWORD、AI provider key/base URL/model 只在服务器交互式环境中生成或填写。这里不提供真实值，不通过聊天、GitHub、远程 URL 或日志传递。

#### 5.4 启动顺序

只使用已发布镜像：

~~~sh
docker compose --env-file .env --profile production --profile async pull backend nginx
docker compose --env-file .env --profile production --profile async up -d --no-build postgres redis
docker compose --env-file .env --profile production --profile async up -d --no-build backend
docker compose --env-file .env --profile production --profile async exec -T backend python manage.py migrate --noinput
docker compose --env-file .env --profile production --profile async exec -T backend python manage.py collectstatic --noinput
docker compose --env-file .env --profile production --profile async exec -T backend python manage.py seed_ai_agents
docker compose --env-file .env --profile production --profile async up -d --no-build celery nginx
~~~

首次部署再按服务器安全方式创建一个管理员账号；不执行 seed_demo，不生成演示学生、教师或项目。迁移、静态文件收集和 AI 模板初始化应在服务可用后执行，失败时停在当前 release，不删除数据库卷。

#### 5.5 systemd

新增：

- deploy/systemd/lingsu.service
- deploy/systemd/lingsu-console.service
- 可选 deploy/systemd/lingsu-maintenance.service
- 可选 deploy/systemd/lingsu-maintenance.timer

核心服务 unit：

~~~ini
[Unit]
Description=Lingsu core Docker services
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/lingsu/source
ExecStart=/usr/bin/docker compose --env-file /home/ubuntu/lingsu/source/.env --profile production --profile async up -d --no-build postgres redis backend celery nginx
ExecStop=/usr/bin/docker compose --env-file /home/ubuntu/lingsu/source/.env --profile production --profile async stop postgres redis backend celery nginx

[Install]
WantedBy=multi-user.target
~~~

独立控制台 unit：

~~~ini
[Unit]
Description=Lingsu independent project console
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/lingsu/source
Environment=PORT=8800
Environment=COMPOSE_PROFILE=production
Environment=COMPOSE_ENV_FILE=/home/ubuntu/lingsu/source/.env
ExecStart=/usr/bin/python3 /home/ubuntu/lingsu/source/scripts/project-console.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
~~~

安装后：

~~~sh
sudo systemctl daemon-reload
sudo systemctl enable --now lingsu.service
sudo systemctl enable --now lingsu-console.service
sudo systemctl status lingsu.service lingsu-console.service
~~~

控制台只能通过 SSH 隧道访问：

~~~sh
ssh -N -L 8800:127.0.0.1:8800 ubuntu@1.15.230.239
~~~

不开放 8800 云安全组端口，不把控制台放进 Nginx 公网路由。Docker 或项目服务停止时，控制台进程必须仍能打开并显示离线状态。

### 阶段 6：监控、日志和故障处理

#### 6.1 日志轮转

新增 deploy/docker/daemon.json.example，建议：

~~~json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
~~~

应用日志不能无限增长。修改 Docker daemon 配置前记录现有配置，并重启 Docker 前确认 systemd 会自动拉起核心栈。

#### 6.2 健康检查

新增：

- scripts/deploy/preflight-2gb.sh
- scripts/deploy/healthcheck-2gb.sh
- scripts/test_low_memory_deployment.py

健康检查至少验证：

~~~sh
docker compose --env-file .env --profile production --profile async ps
curl -fsS http://127.0.0.1:18001/api/health/
curl -fsSI http://127.0.0.1/
free -h
docker stats --no-stream
~~~

必要时补充内核 OOM 证据：

~~~sh
dmesg -T | grep -i -E 'oom|killed process'
journalctl -k --since '-30 min'
journalctl -u docker --since '-30 min'
~~~

应用层健康为 ok 不代表没有内存压力，必须同时观察 swap、容器上限重启和系统 OOM 记录。

#### 6.3 低内存应急顺序

发现内存持续低于安全线时按顺序处理：

1. 查看 docker stats 和内核 OOM 日志，确认实际占用者；
2. 确认 ClamAV、Gotenberg、Beat、frontend dev 未被误启动；
3. 暂停非核心维护任务和重复 AI 任务；
4. 检查 Worker 是否仍为 solo/单并发；
5. 低峰期重启发生内存增长的单个容器；
6. 仍然频繁 OOM 时升级实例；
7. 不执行 down -v、volume prune、数据库删除或强制回滚。

### 阶段 7：备份与回滚

#### 7.1 备份

- 每日导出 PostgreSQL；
- 每日备份 media_data；
- 备份上传到服务器之外的加密存储；
- 备份成功后保留最近 7 至 14 天；
- 定期做恢复演练；
- 不把生产数据库和媒体目录打包进 GitHub。

#### 7.2 镜像回滚

每个发布目录记录：

- Git commit SHA；
- backend image digest；
- web image digest；
- 迁移状态；
- .env 中的非敏感版本变量；
- 部署时间和健康检查结果。

发布失败时：

1. 保留当前容器日志和数据库卷；
2. 将 BACKEND_IMAGE、WEB_IMAGE 改回上一个已验收 SHA；
3. pull 固定版本并使用 up -d --no-build；
4. 运行 healthcheck 和关键页面冒烟；
5. 查明失败原因后再决定是否重新发布。

禁止强制推送、删除远程历史、git reset --hard、docker compose down -v 和无确认的数据库回滚。

## 灵思 AI 在 2GB 环境的专项策略

AI 不是静态页面功能，必须保留 Celery Worker；否则会出现请求已创建但页面永远等待的假性可用状态。

### 运行配置

- Worker 单实例、solo pool、并发 1；
- AI 任务设置合理超时，前端展示排队/生成/失败状态；
- 失败可以重试，但重试不重复创建用户消息；
- AI 日志保留 Agent、项目、任务、引用来源和实际结果；
- 模型调用失败时页面仍可访问，提供明确重试；
- 不在日志中输出 API key、完整 Authorization header 或 .env 内容。

### 资源争用策略

- AI、报告、其他异步任务共享一个低并发 Worker；
- Word 报告允许排队，但不能阻塞普通 API；
- PDF 关闭时不能进入 Worker；
- 没有扫描服务时不能把附件放入 AI 上下文；
- 如果 AI 任务超过首发响应预算，先提示排队，不盲目增加并发；
- 需要并行 AI 和附件扫描时，优先升级内存或拆到独立服务。

### AI 配置验收

使用真实服务器模型配置做一次最小冒烟：

1. 学生登录；
2. 进入 /student/ai 研究模式；
3. 发送一条短问题；
4. 确认状态从 queued/running 到 completed 或明确 failed；
5. 刷新页面后消息和会话状态一致；
6. 检查日志没有密钥；
7. 不执行自动创建项目、自动提交材料或自动审核。

## 测试策略：增量优先，发布前一次完整验收

本项目后续不需要每次修改都跑全站测试。根据变更文件选择最小测试集。

### 修改 Compose、控制台或部署脚本

~~~sh
python -m unittest scripts/test_project_console.py scripts/test_low_memory_deployment.py
bash -n scripts/deploy/preflight-2gb.sh scripts/deploy/healthcheck-2gb.sh
docker compose --profile production --profile async config --quiet
git diff --check
~~~

### 修改上传、报告或健康接口

~~~sh
docker compose --env-file .env.integration --profile dev exec -T backend python manage.py test apps.core
~~~

同时只运行新增的上传/PDF/health 定向测试；确认附件关闭不会创建会话，PDF 关闭不会入队。

### 修改灵思 AI 前端

~~~sh
npm --prefix frontend test -- --run src/aiCenterUI.test.ts src/aiWorkbenchLayout.test.ts src/studentAICenterEntry.test.ts src/aiResultCard.test.ts
npm --prefix frontend run build
git diff --check
~~~

### 发布提交前完整验收

只在代码和定向测试稳定后执行一次：

~~~sh
npm --prefix frontend test -- --run
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- --workers=1
docker compose --env-file .env.integration --profile dev exec -T backend python manage.py test apps.core
docker compose --env-file .env.integration --profile dev exec -T backend python manage.py makemigrations --check --dry-run
python -m unittest scripts/test_project_console.py scripts/test_low_memory_deployment.py
git diff --check
~~~

### 2GB 服务器验收矩阵

| 类别 | 验收内容 |
| --- | --- |
| 主机 | 内存、swap、磁盘、Docker、80 端口 |
| 核心服务 | postgres、redis、backend、celery、nginx 全部 healthy |
| 可选服务 | ClamAV、Gotenberg、Beat、frontend dev 未启动 |
| 公共端 | /、注册、登录和角色跳转 |
| 学生端 | 项目列表、研究进程、文本任务、AI、Word |
| 教师端 | 项目池、开题预览、认领、审核和通知 |
| AI | 真实模型请求完成/失败可见，刷新后状态一致 |
| 附件 | 明确禁用，不创建上传会话 |
| PDF | 明确禁用，不创建转换任务 |
| 网络 | 80 可访问，8000/18001 仅本机，8800 仅本机 |
| 控制台 | 项目服务停止后控制台仍可访问 |
| 数据 | 迁移成功、备份成功、无 demo seed |
| 安全 | .env 为 600，无密钥进入 GitHub、镜像日志和 URL |

## 发布顺序与停止条件

### 可以继续的条件

- 本地定向测试通过；
- Compose profile 只启动预期服务；
- 镜像已经由 GitHub Actions 构建并可通过固定 SHA 拉取；
- 服务器有 swap 或已确认足够的内存缓冲；
- /home/ubuntu/lingsu 目标目录为空或已明确完成备份；
- .env 由用户在服务器本地准备且权限为 600；
- 80 端口旧服务处理方案已经确认；
- 控制台 systemd unit 不依赖容器启动成功。

### 必须停止并报告的条件

- 远程目录有未知项目或未知数据库，不能覆盖；
- GHCR 仓库有权限或镜像拉取问题；
- 服务器 Docker 不可用；
- 系统已经出现 OOM 或磁盘不足；
- 80 端口由未知服务占用；
- 没有可用的 AI 配置但用户要求真实 AI 冒烟；
- 需要通过关闭 FILE_SCAN_REQUIRED 才能让附件成功；
- 任何操作需要删除卷、强制覆盖远程历史或暴露密钥。

## 后续扩容路径

### 升级到 4GB 后

先在备份和监控稳定的前提下：

1. 单独启用 Gotenberg，恢复 PDF 能力；
2. 在独立服务或足够内存下启用 ClamAV，恢复附件上传；
3. 视队列延迟将 Worker 并发从 1 调到 2；
4. 重新测量容器峰值，而不是只看空闲内存；
5. 最后再考虑 Beat 或更高并发。

### 长期生产化

- 配置域名和 HTTPS；
- 开启 Secure Cookie、SSL redirect 和 HSTS；
- 将媒体存储迁移到对象存储；
- 将扫描、文档转换和异步 Worker 拆分到独立节点；
- 使用外部监控、告警和集中日志；
- 只允许最小化管理端访问控制台。

## 本轮实施边界

本轮先完成方案确认和本地计划文档，不直接执行服务器部署。真正执行时的代码修改顺序应为：

1. 异步开关拆分、启动命令去除 reset、资源边界；
2. 上传/PDF fail-fast 和健康能力声明；
3. GHCR 镜像工作流与 Compose image 配置；
4. 低内存部署脚本、控制台生产配置和 systemd unit；
5. 定向测试；
6. 一次完整质量门；
7. 用户确认服务器目录、凭据和 80 端口策略后再远程部署。

这套方案的核心判断是：2GB 可以稳定承载灵溯的页面、文本业务、AI 和 Word 报告，但不能在同一台机器上无条件承载 ClamAV、PDF 转换、开发构建和高并发异步任务。首发必须让关闭的能力在界面和 API 中明确可见，确保“不可用”不会伪装成“处理中”或“已完成”。

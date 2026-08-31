# 灵溯项目完整交接手册执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于本地最新版与承载真实业务数据的线上环境，产出一份技术基础较弱的接手者也能独立完成接管的综合交接手册。

**Architecture:** 先建立只读安全基线，再分别取得本地静态证据、本地运行证据和线上只读证据，随后完成双环境差异分析。最终把所有结论按证据等级写入单一主文档，并通过敏感信息、命令风险、链接和完整性检查后提交。

**Tech Stack:** Markdown、Git、Vue 3/Vite/TypeScript/Vitest/Playwright、Django/DRF、PostgreSQL、Celery/Redis、Docker Compose、SSH

---

## 文件结构

- Create: `docs/灵溯项目完整交接手册.md` — 唯一正式交接文档，包含产品、开发、测试、部署、运维、风险和资产移交。
- Reference: `docs/superpowers/specs/2026-08-31-lingsu-complete-handover-design.md` — 已确认的范围、安全边界和完成标准。
- Reference: `README.md` — 当前项目概览和基础运行说明。
- Reference: `docs/项目运行说明.md` — 面向非技术人员的既有运行资料，用于核验和纠偏。
- Reference: `docs/项目分析-2026-08-18.md` — 历史分析基线，仅作为待复验资料。

线上审计原始输出不写入仓库。敏感值不写入临时文件或交接文档；只记录配置项名称、用途、存放位置和轮换方式。

### Task 1: 建立安全基线与证据框架

**Files:**
- Create: `docs/灵溯项目完整交接手册.md`
- Reference: `docs/superpowers/specs/2026-08-31-lingsu-complete-handover-design.md`

- [ ] **Step 1: 确认工作区和分支状态**

Run:

```bash
pwd
git status --short
git branch --show-current
git log -5 --oneline
```

Expected: 工作区路径为项目根目录；能够识别已有用户改动且不覆盖；当前分支和最近提交可记录。

- [ ] **Step 2: 创建交接手册骨架**

使用设计稿中确认的 15 个一级章节建立 `docs/灵溯项目完整交接手册.md`。在文档开头加入以下固定说明：

```markdown
> 最后核验日期：2026-08-31
> 证据标记：已实测 / 源码确认 / 文档记录 / 待确认
> 安全说明：本文不保存密码、API Key、私钥或数据库明文凭据。
```

Expected: 15 个章节齐全；尚未取得证据的章节只保留标题，不写推测性结论。

- [ ] **Step 3: 定义命令风险标签**

在手册“接手者第一天”章节定义：

```markdown
- `[只读]`：查询状态，不应改变服务或数据。
- `[变更]`：会改变本地或线上状态，执行前必须理解影响。
- `[高风险]`：涉及生产发布、迁移、恢复、删除或凭据，必须先备份并获得负责人批准。
```

Expected: 后续所有运维命令均使用这三个标签之一。

- [ ] **Step 4: 提交文档骨架**

```bash
git add docs/灵溯项目完整交接手册.md
git commit -m "docs: scaffold complete project handover"
```

Expected: 新提交只包含交接手册骨架。

### Task 2: 完成本地静态架构与产品分析

**Files:**
- Modify: `docs/灵溯项目完整交接手册.md`
- Reference: `backend/apps/core/models.py`
- Reference: `backend/apps/core/urls.py`
- Reference: `backend/apps/core/views.py`
- Reference: `backend/apps/core/serializers.py`
- Reference: `backend/apps/core/workflows/`
- Reference: `frontend/src/router.ts`
- Reference: `frontend/src/pages/`
- Reference: `frontend/src/stores/`
- Reference: `docker-compose.yml`
- Reference: `.github/workflows/`

- [ ] **Step 1: 生成受版本控制的文件地图**

Run:

```bash
git ls-files | sed -n '1,260p'
find backend/apps/core -maxdepth 3 -type f -name '*.py' | sort
find frontend/src -maxdepth 3 -type f \( -name '*.ts' -o -name '*.vue' \) | sort
```

Expected: 能识别源码、测试、迁移、部署脚本和文档的实际位置，不把 `node_modules`、构建产物或媒体文件当成源码。

- [ ] **Step 2: 核对产品入口与角色路由**

Run:

```bash
sed -n '1,280p' frontend/src/router.ts
rg -n "student|teacher|platform|role|requiresAuth" frontend/src/router.ts frontend/src/stores/auth.ts
```

Expected: 手册中的学生、教师、平台管理员入口和导航能力均能追溯到当前路由或权限代码。

- [ ] **Step 3: 核对后端模型、状态机和权限边界**

Run:

```bash
rg -n '^class ' backend/apps/core/models.py backend/apps/core/serializers.py backend/apps/core/views.py backend/apps/core/workflows
rg -n 'status|school|role|permission|leader|teacher|platform' backend/apps/core/models.py backend/apps/core/workflows backend/apps/core/tests
```

Expected: 记录核心模型、状态流转、学校隔离和三角色限制；每个关键规则至少有源码或测试证据。

- [ ] **Step 4: 核对基础设施和异步链路**

Run:

```bash
docker compose config --services
rg -n 'celery|redis|gotenberg|clamav|nginx|volume|healthcheck' docker-compose.yml backend/config backend/apps/core/tasks.py infra
```

Expected: 手册中的服务拓扑、依赖方向、持久化卷和健康检查与当前配置一致。

- [ ] **Step 5: 统计规模和识别维护热点**

Run:

```bash
wc -l backend/apps/core/views.py backend/apps/core/models.py backend/apps/core/serializers.py backend/apps/core/tasks.py
find backend/apps/core/tests -name 'test_*.py' | wc -l
find frontend/src -name '*.test.ts' -o -name '*.spec.ts' | wc -l
find frontend/e2e -name '*.spec.ts' | wc -l
git log --since='2026-08-18' --oneline | wc -l
```

Expected: 用当前数字替换 2026-08-18 旧分析中的过时结论，并明确代码热点和文档漂移。

- [ ] **Step 6: 写入产品、架构、代码地图、数据权限与初步风险**

更新主文档第 3–6、12、15 章。每条事实附“已实测”“源码确认”“文档记录”或“待确认”标记。

Expected: 非技术读者能理解业务闭环；开发者能从功能定位到具体目录和入口；不把历史计划当成已实现事实。

- [ ] **Step 7: 提交静态分析结果**

```bash
git add docs/灵溯项目完整交接手册.md
git commit -m "docs: map handover architecture and business rules"
```

Expected: 提交只包含经源码核验的交接内容。

### Task 3: 验证本地最新版的工程状态

**Files:**
- Modify: `docs/灵溯项目完整交接手册.md`
- Reference: `frontend/package.json`
- Reference: `.github/workflows/mvp.yml`
- Reference: `frontend/playwright.config.ts`
- Reference: `backend/manage.py`

- [ ] **Step 1: 检查本地运行环境和 Compose 状态**

Run:

```bash
docker compose --env-file .env.integration ps
docker compose --env-file .env.integration config --profiles
curl -fsS http://127.0.0.1:18001/api/health/
curl -fsSI http://127.0.0.1:5173/
```

Expected: 若环境正在运行，服务状态和两个健康响应可记录；若未运行，只记录“未启动”，不擅自启动或重建。

- [ ] **Step 2: 执行前端单元测试和生产构建**

Run:

```bash
npm test
npm run build
```

Working directory: `frontend/`

Expected: 分别记录用例数量、通过/失败、耗时和失败摘要；构建必须同时经过 `vue-tsc --noEmit` 与 Vite 构建。

- [ ] **Step 3: 执行后端系统检查、迁移检查和测试**

若集成后端容器健康，Run:

```bash
docker compose --env-file .env.integration exec -T backend python manage.py check
docker compose --env-file .env.integration exec -T backend python manage.py makemigrations --check --dry-run
docker compose --env-file .env.integration exec -T backend python manage.py test apps
```

Expected: 记录系统检查、未生成迁移和测试结果；测试不得使用生产数据库。

- [ ] **Step 4: 核对 E2E 配置并在条件满足时运行**

Run:

```bash
npx playwright test --list
npm run test:e2e
```

Working directory: `frontend/`

Expected: 先记录测试清单；只有配置指向本地/集成环境时才执行。若失败，记录第一个根因和受影响链路，不修改产品代码。

- [ ] **Step 5: 对照 CI 质量门禁**

Run:

```bash
sed -n '1,300p' .github/workflows/mvp.yml
sed -n '1,260p' .github/workflows/publish-images.yml
```

Expected: 手册准确列出自动执行的检查、触发条件、镜像发布方式及未覆盖项。

- [ ] **Step 6: 写入本地运行、测试和质量结论**

更新主文档第 2、7、12、15 章，所有测试结果附执行日期和命令。失败结果原样归类为风险，不宣称通过。

- [ ] **Step 7: 提交本地实测结果**

```bash
git add docs/灵溯项目完整交接手册.md
git commit -m "docs: record verified local handover baseline"
```

Expected: 提交包含可复现的本地核验步骤与结果。

### Task 4: 对生产服务器执行只读审计

**Files:**
- Modify: `docs/灵溯项目完整交接手册.md`

- [ ] **Step 1: 验证 SSH 身份和基础主机信息**

Run:

```bash
ssh ubuntu@1.15.230.239 'set -eu; id; hostname; date -Is; uname -a; uptime; df -h'
```

Expected: 能确认登录身份、主机、时间、内核、负载和磁盘；命令不修改服务器。

- [ ] **Step 2: 发现部署目录和服务管理方式**

Run:

```bash
ssh ubuntu@1.15.230.239 'set -eu; pwd; find /home/ubuntu /opt /srv -maxdepth 3 -type f \( -name docker-compose.yml -o -name compose.yml -o -name compose.yaml \) -print 2>/dev/null; docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"'
```

Expected: 找到实际部署目录并识别容器、镜像、健康状态和端口；不执行 `docker compose up/down/restart`。

- [ ] **Step 3: 核对线上代码或镜像版本**

使用 Compose 文件自动解析并验证明确部署目录，然后执行只读命令：

```bash
ssh ubuntu@1.15.230.239 'set -eu; compose_file=$(find /home/ubuntu /opt /srv -maxdepth 3 -type f \( -name docker-compose.yml -o -name compose.yml -o -name compose.yaml \) -print 2>/dev/null | head -1); test -n "$compose_file"; deploy_dir=${compose_file%/*}; cd "$deploy_dir"; pwd; git rev-parse HEAD; git status --short; git log -5 --oneline'
```

若线上不是 Git 部署，则只记录容器镜像名、镜像 ID、创建时间和标签：

```bash
ssh ubuntu@1.15.230.239 'docker inspect --format "{{.Name}} {{.Image}} {{.Created}}" $(docker ps -q)'
```

Expected: 采用与实际部署方式匹配的一条路径；命令先验证 Compose 文件存在，再进入解析出的明确目录。

- [ ] **Step 4: 核对 Compose 服务、卷和配置项名称**

在自动解析且验证过的部署目录执行：

```bash
ssh ubuntu@1.15.230.239 'set -eu; compose_file=$(find /home/ubuntu /opt /srv -maxdepth 3 -type f \( -name docker-compose.yml -o -name compose.yml -o -name compose.yaml \) -print 2>/dev/null | head -1); test -n "$compose_file"; deploy_dir=${compose_file%/*}; cd "$deploy_dir"; docker compose config --services; docker compose config --volumes; sed -n "s/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p" .env 2>/dev/null | sort -u'
```

Expected: 只输出服务、卷和环境变量名称，不输出任何值。

- [ ] **Step 5: 核对 Django 迁移与服务健康**

从已验证的 Compose 目录通过服务名执行：

```bash
ssh ubuntu@1.15.230.239 'set -eu; compose_file=$(find /home/ubuntu /opt /srv -maxdepth 3 -type f \( -name docker-compose.yml -o -name compose.yml -o -name compose.yaml \) -print 2>/dev/null | head -1); test -n "$compose_file"; deploy_dir=${compose_file%/*}; cd "$deploy_dir"; docker compose exec -T backend python manage.py showmigrations --plan'
ssh ubuntu@1.15.230.239 'docker inspect --format "{{.Name}} {{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}} {{.RestartCount}}" $(docker ps -q)'
```

Expected: 仅查询迁移应用状态、健康状态和重启次数，不运行 `migrate` 或 `check --deploy`。

- [ ] **Step 6: 核对数据库规模而不读取业务内容**

通过 Compose 的 PostgreSQL 服务读取容器自身已有的数据库变量，只查询统计元数据：

```bash
ssh ubuntu@1.15.230.239 'set -eu; compose_file=$(find /home/ubuntu /opt /srv -maxdepth 3 -type f \( -name docker-compose.yml -o -name compose.yml -o -name compose.yaml \) -print 2>/dev/null | head -1); test -n "$compose_file"; deploy_dir=${compose_file%/*}; cd "$deploy_dir"; docker compose exec -T postgres sh -lc '\''psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select pg_size_pretty(pg_database_size(current_database())); select count(*) from django_migrations;"'\'''
```

Expected: 只记录数据库大小和迁移记录数；不查询用户、项目、材料或附件内容。

- [ ] **Step 7: 核对备份机制、磁盘和近期错误**

Run:

```bash
ssh ubuntu@1.15.230.239 'set -eu; systemctl list-timers --all --no-pager; crontab -l 2>/dev/null || true; find /home/ubuntu /opt /srv -maxdepth 4 -type f \( -name "*backup*" -o -name "*restore*" \) -print 2>/dev/null'
ssh ubuntu@1.15.230.239 'docker ps --format "{{.Names}}" | while read name; do echo "[$name]"; docker logs --since 24h --tail 200 "$name" 2>&1 | grep -Ei "error|exception|critical|fatal|out of memory" | tail -20 || true; done'
```

Expected: 确认是否存在定时备份和明显持续错误；日志引用必须脱敏，不复制业务内容或凭据。

- [ ] **Step 8: 写入生产环境现状与风险**

更新主文档第 1、2、8、11–15 章。记录部署事实、健康状态、备份可见性、迁移状态和待确认的资产所有权；禁止写入 `.env` 值和真实数据。

- [ ] **Step 9: 提交脱敏后的生产审计结论**

```bash
git add docs/灵溯项目完整交接手册.md
git diff --cached
git commit -m "docs: record read-only production handover audit"
```

Expected: 提交前人工确认差异中无密码、Token、私钥、Cookie、数据库连接串或用户数据。

### Task 5: 完成线上与本地差异和安全升级建议

**Files:**
- Modify: `docs/灵溯项目完整交接手册.md`
- Reference: `backend/apps/core/migrations/`
- Reference: `docker-compose.yml`
- Reference: `.env.example`
- Reference: `deploy/`

- [ ] **Step 1: 比对 Git 或镜像基线**

若线上有 Git SHA，Run:

```bash
git log --oneline --decorate <线上SHA>..HEAD
git diff --stat <线上SHA>..HEAD
git diff --name-status <线上SHA>..HEAD
```

Expected: 列出线上之后的提交和变化范围；若 SHA 不存在于本地仓库，记录无法直接建立祖先关系，不猜测版本。

- [ ] **Step 2: 比对数据库迁移**

Run:

```bash
find backend/apps/core/migrations -maxdepth 1 -name '[0-9][0-9][0-9][0-9]_*.py' -print | sort
```

Expected: 把本地迁移文件与线上 `showmigrations --plan` 结果对照，列出升级时将新增的迁移及其涉及模型。

- [ ] **Step 3: 比对服务、配置名和功能开关**

Run:

```bash
docker compose config --services
sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' .env.example | sort -u
rg -n 'os\.environ|getenv|env\(' backend docker-compose.yml deploy scripts
```

Expected: 形成配置项“本地存在/线上存在/是否必需/升级动作”的脱敏矩阵。

- [ ] **Step 4: 给出发布前置条件和回滚触发条件**

更新第 9、10、12 章，至少包含：数据库和媒体备份、镜像可回滚标识、迁移可逆性、维护窗口、烟雾测试、回滚触发条件和负责人批准。

Expected: 不给出“直接覆盖线上”的捷径；所有生产变更均标记 `[高风险]`。

- [ ] **Step 5: 提交差异和升级建议**

```bash
git add docs/灵溯项目完整交接手册.md
git commit -m "docs: document environment drift and upgrade safeguards"
```

Expected: 差异结论均可追溯到本地或线上证据。

### Task 6: 完善运维、资产移交和接手验收内容

**Files:**
- Modify: `docs/灵溯项目完整交接手册.md`
- Reference: `scripts/`
- Reference: `deploy/README.md`
- Reference: `README.md`

- [ ] **Step 1: 核对现有运维脚本**

Run:

```bash
find scripts deploy -maxdepth 3 -type f | sort
rg -n 'backup|restore|deploy|health|docker|migrate|rollback' scripts deploy README.md docs/项目运行说明.md
```

Expected: 文档只推荐当前仓库真实存在且已审阅的脚本；恢复类命令不在生产执行。

- [ ] **Step 2: 编写故障诊断决策路径**

为“网页打不开、登录失败、上传失败、AI 不响应、任务不执行、PDF 导出失败、磁盘告警”分别写：第一检查点、只读命令、正常现象、异常分支和升级联系人/待移交责任人。

Expected: 技术基础较弱的接手者可以从症状定位到服务，不需要先理解完整架构。

- [ ] **Step 3: 编写资产与权限移交表**

表格固定列为：

```markdown
| 资产 | 当前入口/位置 | 当前所有者 | 新所有者 | 轮换动作 | 验收证据 | 状态 |
```

必须覆盖服务器、SSH、代码仓库、域名/DNS、HTTPS 证书、数据库、备份、对象/媒体存储、AI 服务、镜像仓库、CI、监控告警和组织账号。

Expected: 未能从系统确认的所有者标记“待确认”，不猜测个人或组织名称。

- [ ] **Step 4: 编写接手验收清单**

至少验证：登录三角色、读取健康状态、本地启动、运行测试、定位日志、确认最近备份、理解发布审批、轮换凭据、确认回滚材料和签收风险。

Expected: 每项包含执行人、日期和结果字段，可直接打印或勾选。

- [ ] **Step 5: 提交运维与验收内容**

```bash
git add docs/灵溯项目完整交接手册.md
git commit -m "docs: add operations and ownership handover checklists"
```

Expected: 主文档已覆盖设计稿规定的全部 15 个章节。

### Task 7: 最终安全、完整性与可用性验证

**Files:**
- Modify: `docs/灵溯项目完整交接手册.md`
- Verify: `docs/灵溯项目完整交接手册.md`

- [ ] **Step 1: 检查章节完整性和占位符**

Run:

```bash
rg -n '^#|^## ' docs/灵溯项目完整交接手册.md
rg -n '本章节将在|稍后补写|后续填写|示例值未替换' docs/灵溯项目完整交接手册.md
```

Expected: 15 个一级业务章节齐全；不存在未解释的占位符。无法自动确认的事项必须改写成带责任人和核验方法的“待确认”。

- [ ] **Step 2: 执行敏感信息扫描**

Run:

```bash
rg -n -i 'password\s*[=:]|api[_-]?key\s*[=:]|secret\s*[=:]|token\s*[=:]|BEGIN (RSA|OPENSSH|PRIVATE) KEY|postgres(ql)?://[^ ]+:[^ ]+@' docs/灵溯项目完整交接手册.md
```

Expected: 无真实敏感值。配置项示例只使用变量名或 `<由新负责人设置>`。

- [ ] **Step 3: 检查危险命令标签**

Run:

```bash
rg -n 'migrate|restart|down|restore|delete|rm |DROP |flush|seed_demo --reset' docs/灵溯项目完整交接手册.md
```

Expected: 所有会改变状态或破坏数据的命令均紧邻 `[变更]` 或 `[高风险]` 标签、前置条件和回滚说明。

- [ ] **Step 4: 检查 Markdown 和仓库差异**

Run:

```bash
git diff --check
git status --short
git diff -- docs/灵溯项目完整交接手册.md
```

Expected: 无空白错误；没有覆盖用户的无关改动；最终差异只包含交接文档的必要修正。

- [ ] **Step 5: 按设计稿逐项自审**

逐项核对设计稿第 8 节的七条完成标准，并在手册末尾加入“文档核验记录”，记录本地实测、线上只读审计、差异复核和敏感信息扫描的日期与结果。

Expected: 每条完成标准均能指向手册中的具体章节；无法满足项明确列为 P0 交接风险。

- [ ] **Step 6: 提交最终交接手册**

```bash
git add docs/灵溯项目完整交接手册.md
git commit -m "docs: finalize complete lingsu project handover"
git status --short
```

Expected: 最终提交完成，工作区不包含本任务产生的未提交改动。

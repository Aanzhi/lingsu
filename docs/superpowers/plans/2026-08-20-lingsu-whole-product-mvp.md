# 灵溯全项目 MVP 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变现有业务规则和权限边界的前提下，完成单校试点可验收的全项目 MVP。

**Architecture:** 复用现有 Vue 3/Pinia 页面、Django REST API、workflow、Celery、Redis、Gotenberg 和私有下载接口。新增或修改仅限配置适配、缺失的页面闭环、状态反馈和测试；不引入新服务、不替换数据模型体系。

**Tech Stack:** Vue 3、TypeScript、Vitest、Django REST Framework、PostgreSQL、Celery、Redis、OpenAI Python SDK、Docker Compose、Gotenberg。

---

## 当前实现基线

已存在并应优先复用的接口：

- AI：`ai-conversations/`、`ai-conversations/:id/messages/`、SSE stream、`ai-logs/:id/save_as_material/`。
- 项目/材料：`projects/`、`project-tasks/`、`materials/`、`material-revisions/`、`material-attachments/`。
- 内容：`public-case-requests/`、`competitions/`、`announcements/`。
- 导出：`report-exports/`，Celery 任务和 Gotenberg 转换已存在。

当前最明显的产品缺口是 AI 真实模型配置与目标材料选择；公开案例、赛事、公告和报告导出已有大部分实现，需要按 MVP 验收链路补齐状态、权限和异常回归，而不是重写。

## Task 1: 固定可重复的环境和迁移基线

**Files:**

- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `backend/config/settings.py`
- Test: `backend/apps/core/tests/test_runtime_configuration.py`
- Test: `backend/apps/core/tests/test_production_contract.py`

- [ ] **Step 1: 锁定 AI 兼容配置的失败测试**

在运行时配置测试中增加以下断言：空 `OPENAI_API_KEY` 返回 demo 状态；有 Key 时，`OPENAI_BASE_URL` 和模型名可被 settings 读取；API 响应不包含 Key。

- [ ] **Step 2: 运行配置测试确认当前缺口**

运行：

```bash
docker compose exec -T backend python manage.py test apps.core.tests.test_runtime_configuration apps.core.tests.test_production_contract -v 2
```

预期：新加的 `OPENAI_BASE_URL` 断言失败，证明测试先锁定行为。

- [ ] **Step 3: 增加非敏感配置项**

在 `.env.example` 增加：

```dotenv
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4.1-mini
```

在 `backend/config/settings.py` 增加：

```python
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
```

不在仓库保存真实 API Key。

- [ ] **Step 4: 用最新迁移重建环境并验证**

运行：

```bash
docker compose up --build -d
docker compose exec -T backend python manage.py migrate --check
docker compose exec -T backend python manage.py showmigrations core
```

预期：迁移检查无待执行项，`0032` 至 `0036` 均为 `[X]`，`/api/health/` 返回 `{"status":"ok"}`。

- [ ] **Step 5: 运行配置测试并提交**

```bash
docker compose exec -T backend python manage.py test apps.core.tests.test_runtime_configuration apps.core.tests.test_production_contract -v 2
git add .env.example docker-compose.yml backend/config/settings.py backend/apps/core/tests/test_runtime_configuration.py backend/apps/core/tests/test_production_contract.py
git commit -m "chore: stabilize MVP runtime configuration"
```

## Task 2: 接入免费 OpenRouter 测试模型，不改业务流程

**Files:**

- Modify: `backend/apps/core/tasks.py`
- Modify: `backend/apps/core/tests/test_ai_service.py`
- Modify: `backend/apps/core/tests/test_agents.py`
- Modify: `.env.example`
- Modify: `docs/项目运行说明.md`

- [ ] **Step 1: 锁定客户端构造行为**

增加测试，断言有 `OPENAI_BASE_URL` 时以该 URL 构造 OpenAI 客户端，调用仍为 `client.responses.create(model=..., instructions=..., input=...)`；无 Key 仍走既有 demo 分支。

- [ ] **Step 2: 运行 AI 测试确认当前失败**

```bash
docker compose exec -T backend python manage.py test apps.core.tests.test_ai_service apps.core.tests.test_agents -v 2
```

- [ ] **Step 3: 只修改客户端初始化**

将 `backend/apps/core/tasks.py` 中的：

```python
client = OpenAI(api_key=api_key)
```

改为：

```python
client_kwargs = {"api_key": api_key}
base_url = getattr(settings, "OPENAI_BASE_URL", "")
if base_url:
    client_kwargs["base_url"] = base_url
client = OpenAI(**client_kwargs)
```

不得修改权限、配额、Agent 模板、审计、Celery 状态或材料保存逻辑。

- [ ] **Step 4: 配置本地测试模型**

在本机 `.env`（不提交）设置：

```dotenv
OPENAI_API_KEY=<由项目所有者创建的测试 Key>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openrouter/free
```

Key 只在后端容器环境变量中出现，前端 `/api/ai-availability/` 只能看到状态和剩余配额。

- [ ] **Step 5: 做一次真实请求和失败请求验证**

分别验证有效 Key、空 Key、无效 Key、429/503 时：生成记录状态正确，前端显示可重试错误，用户输入不丢失，配额规则不被绕过。

- [ ] **Step 6: 运行并提交**

```bash
docker compose exec -T backend python manage.py test apps.core.tests.test_ai_service apps.core.tests.test_agents apps.core.tests.test_ai_conversations -v 2
git add backend/apps/core/tasks.py backend/apps/core/tests/test_ai_service.py backend/apps/core/tests/test_agents.py .env.example docs/项目运行说明.md
git commit -m "feat: support configurable compatible AI provider"
```

## Task 3: 完成学生 AI 草稿保存闭环

**Files:**

- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/api.ts`
- Test: `frontend/src/studentAICenterEntry.test.ts`
- Test: `frontend/src/stores/aiConversationModel.test.ts`
- Test: `backend/apps/core/tests/test_ai_conversations.py`

- [ ] **Step 1: 为目标材料选择写前端状态测试**

测试要求：当前项目材料超过一份时，保存按钮必须要求选择 `material.id`，不能默认取第一份材料；生成失败时输入内容仍保留。

- [ ] **Step 2: 增加材料选择控件**

在 AI 草稿卡片中渲染当前项目材料 `<select>`，保存函数使用所选 ID 调用现有 `saveAIGenerationAsMaterial`，不新增后端写入路径。

- [ ] **Step 3: 补齐重命名入口和上下文显示**

使用现有 `updateAIConversation` 接口增加标题编辑；上下文面板显示当前项目、任务、Agent 和论文类型，并明确提示对话只能绑定一个项目。

- [ ] **Step 4: 运行前端测试和构建**

```bash
cd frontend
npm test
npm run build
```

- [ ] **Step 5: 运行 AI API 回归并提交**

```bash
docker compose exec -T backend python manage.py test apps.core.tests.test_ai_conversations apps.core.tests.test_agents -v 2
git add frontend/src/pages/shared/AICenter.vue frontend/src/api.ts frontend/src/studentAICenterEntry.test.ts frontend/src/stores/aiConversationModel.test.ts backend/apps/core/tests/test_ai_conversations.py
git commit -m "feat: complete MVP AI draft workflow"
```

## Task 4: 验证并补齐 DOCX/PDF 报告导出

**Files:**

- Modify: `frontend/src/pages/student/StudentProject.vue`
- Modify: `frontend/src/stores/reportModel.ts`
- Test: `frontend/src/stores/reportModel.test.ts`
- Test: `backend/apps/core/tests/test_report_exports.py`
- Verify: `backend/apps/core/tasks.py`

- [ ] **Step 1: 锁定导出状态机测试**

覆盖 `queued → processing → completed`、失败状态、重复点击禁用、完成后 DOCX/PDF 下载 URL 鉴权。

- [ ] **Step 2: 核对后端权限和材料快照**

确认 `ReportExportViewSet` 只允许可访问项目，导出记录保存 `project_version` 和 `material_manifest`，未完成记录不返回下载 URL。

- [ ] **Step 3: 补齐前端失败重试和轮询终止**

失败时显示错误并允许重新创建任务；完成或失败后停止轮询；下载按钮只对已完成任务显示。

- [ ] **Step 4: 运行测试并实际打开产物**

```bash
cd frontend && npm test -- src/stores/reportModel.test.ts
docker compose exec -T backend python manage.py test apps.core.tests.test_report_exports -v 2
```

使用演示项目各导出一次 DOCX 和 PDF，确认文件可打开且内容来自通过审核的材料。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/student/StudentProject.vue frontend/src/stores/reportModel.ts frontend/src/stores/reportModel.test.ts backend/apps/core/tests/test_report_exports.py
git commit -m "feat: verify MVP report export workflow"
```

## Task 5: 验证公开案例、赛事和平台公告闭环

**Files:**

- Modify: `frontend/src/pages/platform/PlatformConsole.vue`
- Modify: `frontend/src/pages/platform/PlatformCases.vue`
- Modify: `frontend/src/pages/student/PublicCaseApplication.vue`
- Modify: `frontend/src/pages/shared/ContentLibrary.vue`
- Test: `backend/apps/core/tests/test_public_cases.py`
- Test: `backend/apps/core/tests/test_platform_flow.py`
- Test: `backend/apps/core/tests/test_workflows.py`

- [ ] **Step 1: 先运行已有内容权限测试**

```bash
docker compose exec -T backend python manage.py test apps.core.tests.test_public_cases apps.core.tests.test_platform_flow apps.core.tests.test_workflows -v 2
```

- [ ] **Step 2: 补齐平台案例治理页面**

将 `PlatformConsole.vue` 的案例占位区接入 `getPublicCases`、`setCaseVisibility`，显示待治理案例、当前可见性和下线/发布操作；不改变后端审核状态机。

- [ ] **Step 3: 校验赛事和公告可见性**

平台管理员创建并发布赛事/公告；学生和教师只能看到已发布且属于其可见范围的内容；草稿、撤回内容不可出现在普通用户列表。

- [ ] **Step 4: 补齐失败反馈**

发布、撤回、审核、下线失败时保留表单或当前列表状态，并显示重试入口。

- [ ] **Step 5: 运行前端与后端回归并提交**

```bash
cd frontend && npm test && npm run build
docker compose exec -T backend python manage.py test apps.core.tests.test_public_cases apps.core.tests.test_platform_flow apps.core.tests.test_workflows -v 2
git add frontend/src/pages/platform/PlatformConsole.vue frontend/src/pages/platform/PlatformCases.vue frontend/src/pages/student/PublicCaseApplication.vue frontend/src/pages/shared/ContentLibrary.vue
git commit -m "feat: complete MVP content governance surfaces"
```

## Task 6: MVP 端到端验收

**Files:**

- Create: `frontend/e2e/mvp.spec.ts`
- Create: `frontend/playwright.config.ts`
- Modify: `frontend/package.json`
- Create: `.github/workflows/mvp.yml`

- [ ] **Step 1: 准备稳定演示数据**

使用现有 `seed_demo` 创建一个学校、学生、教师、管理员、项目、任务和材料；E2E 每次运行使用独立数据库或可重复重置的数据集。

- [ ] **Step 2: 写登录和角色路由测试**

验证三类账号登录后只能访问自己的入口，未授权页面被重定向。

- [ ] **Step 3: 写项目审核链路测试**

验证创建项目、材料提交、教师退回、学生重提、教师通过。

- [ ] **Step 4: 写 AI、导出和内容链路测试**

AI 测试使用后端可控的 provider mock，验证生成记录、保存到指定材料、报告任务状态、案例发布、赛事和公告可见性；真实免费 Key 只用于手工 smoke test，不放进 CI。

- [ ] **Step 5: 配置 CI 门禁**

CI 至少执行：

```bash
cd frontend && npm ci && npm test && npm run build
cd ../backend && python manage.py migrate --check && python manage.py test apps.core.tests
```

真实 API Key 不进入 CI secrets 以外的日志、构建产物或前端环境。

- [ ] **Step 6: 按七项手工验收清单签收**

管理员发布赛事和公告；学生创建并提交材料；教师退回和通过；学生调用真实免费 AI 并保存草稿；导出 DOCX/PDF；案例经教师和管理员发布；跨校账号无法读取项目、附件、AI 对话和报告。

- [ ] **Step 7: 完成提交**

```bash
git add frontend/e2e/mvp.spec.ts frontend/playwright.config.ts frontend/package.json .github/workflows/mvp.yml
git commit -m "test: add whole-product MVP acceptance gates"
```

## 最终完成门槛

- [ ] 最新迁移全部应用，前端测试/构建和后端全量测试通过。
- [ ] AI 真实免费 Key 手工请求成功，空 Key 和限流错误可解释、可重试。
- [ ] DOCX/PDF 均生成并可打开。
- [ ] 公开案例、赛事、公告的发布状态和学校权限经过接口与页面验证。
- [ ] 七项手工试点验收全部完成并留存结果。


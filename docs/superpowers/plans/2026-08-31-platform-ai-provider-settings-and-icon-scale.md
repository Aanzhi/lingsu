# 平台 AI 服务参数配置与图标尺寸修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让平台管理员在设置页配置 API Key、模型名称和 Base URL，并让所有真实 AI 调用使用数据库中的生效参数，同时修正 AI 配置标题图标的异常尺寸。

**Architecture:** 在现有单例 `PlatformAIConfiguration` 记录中增加非敏感的 `model` 与 `base_url` 字段；`ai_config.py` 提供统一的运行时配置读取和保存入口，保留环境变量回退，API 只返回安全元数据。前端把三项配置作为一个表单提交，已保存的 API Key 仍只显示掩码；标题图标改用 Element Plus 的 `el-icon` 容器固定 18px。

**Tech Stack:** Django 5.2、Django REST Framework、PostgreSQL、Celery、Vue 3、TypeScript、Element Plus、Vitest。

---

### Task 1: 用失败测试锁定配置契约

**Files:**
- Modify: `backend/apps/core/tests/test_ai_config.py`
- Modify: `backend/apps/core/tests/test_platform_configuration.py`
- Modify: `backend/apps/core/tests/test_ai_service.py`
- Modify: `frontend/src/platformAIConfigUI.test.ts`

- [ ] **Step 1: 扩展后端 API 测试，要求 PUT 保存三项配置。**

在 `test_platform_can_read_masked_ai_configuration_without_plaintext` 中把 PUT 请求改为包含：

```python
{
    "api_key": "sk-live-1234567890-END",
    "model": "deepseek-v4-flash-260425",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
}
```

并断言 PUT 与后续 GET 都返回这两个非敏感字段，同时继续断言响应不包含明文 Key 或 `encrypted_api_key`。新增一个测试：第一次保存后再次 PUT `{ "api_key": "", "model": "new-model", "base_url": "https://example.test/v1" }`，断言掩码不变、数据库解密后的 Key 不变、模型和地址更新。新增一个测试：无数据库记录但有环境变量 Key 时，PUT 空 Key 仍能保存 provider 参数，并把环境 Key 加密迁移到数据库。新增一个测试，提交空模型或非 HTTP(S) Base URL 时返回 400 且错误字段分别为 `model` 或 `base_url`。

- [ ] **Step 2: 扩展服务测试，要求 worker 使用数据库 provider 参数。**

在 `test_ai_service.py` 增加一个平台管理员先通过 `APIClient.put("/api/platform-ai-config/", ...)` 保存 Key、`db-model` 和 `https://db.example/v1`，再调用 `generate_ai_response` 的测试；Mock `apps.core.tasks.OpenAI`，断言构造参数为 `api_key="sk-db-runtime-key"` 与 `base_url="https://db.example/v1"`，并断言 `responses.create` 使用 `model="db-model"`。测试环境变量设置为另一组 model/base URL，证明数据库值优先。

- [ ] **Step 3: 扩展前端契约测试。**

在 `frontend/src/platformAIConfigUI.test.ts` 增加以下可观察契约断言：

```ts
expect(api).toContain('model: string')
expect(api).toContain('base_url: string')
expect(api).toContain('model: string; base_url: string')
expect(settings).toContain('v-model="modelInput"')
expect(settings).toContain('v-model="baseUrlInput"')
expect(settings).toContain('<el-icon :size="18"')
```

- [ ] **Step 4: 运行新增测试，确认在缺少实现时按预期失败。**

运行：

```bash
cd frontend && npm test -- src/platformAIConfigUI.test.ts
cd ../backend && python manage.py test apps.core.tests.test_platform_configuration apps.core.tests.test_ai_service apps.core.tests.test_ai_config --keepdb
```

预期：前端测试因表单和图标契约缺失而失败；后端测试因接口仍返回环境变量参数、worker 仍读取 settings 而失败。若出现导入错误或测试数据库交互式删除提示，先修正运行方式后重跑，不能把实现错误伪装成环境错误。

### Task 2: 扩展数据库模型并实现运行时配置服务

**Files:**
- Modify: `backend/apps/core/models.py:34-53`
- Create: `backend/apps/core/migrations/0042_platform_ai_configuration_provider_fields.py`
- Modify: `backend/apps/core/ai_config.py`

- [ ] **Step 1: 增加可回退的 provider 字段。**

在 `PlatformAIConfiguration` 增加：

```python
model = models.CharField(max_length=128, blank=True)
base_url = models.CharField(max_length=512, blank=True)
```

生成迁移 `0042_platform_ai_configuration_provider_fields`，依赖 `0041_platform_ai_configuration`，两个字段默认空字符串，确保旧单例记录可迁移。

- [ ] **Step 2: 增加字段级校验和有效值回退。**

在 `ai_config.py` 引入 `urlparse`，新增 `AIConfigValidationError(ValueError)`，携带 `field` 属性。新增 `_effective_model(record)` 与 `_effective_base_url(record)`：记录字段非空时使用记录值，否则分别回退 `settings.OPENAI_MODEL` 与 `settings.OPENAI_BASE_URL`。模型名限制为 128 字符且不能为空；Base URL 限制为 512 字符，解析后必须同时具备 `http`/`https` scheme 与 netloc。

- [ ] **Step 3: 提供统一运行时读取函数。**

新增 `get_configured_ai_runtime()`，返回：

```python
{
    "api_key": "仅供服务端内部使用的明文 Key",
    "model": "有效模型名",
    "base_url": "有效 Base URL",
}
```

有数据库记录时仅解密该记录的 Key，并使用记录参数或环境回退；无记录时返回环境变量的 Key、模型和地址。保留 `get_configured_ai_api_key()` 作为兼容包装，只返回上述结果的 `api_key`。`get_ai_configuration_state()` 改为返回 `configured`、`masked_key`、`model`、`base_url`，不读取或返回明文/密文。

- [ ] **Step 4: 实现三项配置事务保存。**

新增 `save_platform_ai_configuration(api_key, model, base_url, actor)`：先校验模型和 URL；没有默认记录且 API Key 为空时，如果环境变量已有 Key 则用它完成加密迁移，否则抛出 `AIConfigValidationError("api_key", ...)`；已有记录且 API Key 为空时保留原加密字段；提供新 Key 时按现有 Fernet 流程加密并更新掩码。使用 `select_for_update()` 在事务中更新模型、地址、Key 和 `updated_by`，保存成功后返回安全状态。

- [ ] **Step 5: 运行服务层测试。**

运行：

```bash
cd backend && python manage.py test apps.core.tests.test_ai_config --keepdb
```

预期：Task 1 的 API/worker 测试仍可能失败，但服务层加密、掩码、回退测试应通过；如果失败，先修正服务层再继续。

### Task 3: 接通 API、AI worker 和 AI 日志模型名

**Files:**
- Modify: `backend/apps/core/views.py:31,508-538,1386,1479,1610`
- Modify: `backend/apps/core/tasks.py:18,262-270,425-446,599-631`
- Modify: `backend/apps/core/tests/test_platform_configuration.py`
- Modify: `backend/apps/core/tests/test_ai_service.py`

- [ ] **Step 1: 更新平台配置 API。**

让 `PlatformAIConfigurationView.get()` 直接返回 `get_ai_configuration_state()`；让 PUT 从 `request.data` 读取 `api_key`、`model`、`base_url` 并调用 `save_platform_ai_configuration`。捕获 `AIConfigValidationError` 后抛出 `{field: [message]}` 的 DRF `ValidationError`，保留现有 `AIConfigError` 的 503 行为和平台管理员权限检查。

- [ ] **Step 2: 统一三条真实 AI 调用路径。**

在 `generate_general_ai_response`、开题/项目 AI 分支和通用研究 AI 分支中调用一次 `get_configured_ai_runtime()`，使用 `runtime["api_key"]` 构造 OpenAI client，非空时使用 `runtime["base_url"]`，Responses API 的 `model` 参数使用 `runtime["model"]`。没有 Key 的演示模式和错误行为保持不变。

- [ ] **Step 3: 让创建的 AI 日志记录实际模型名。**

将 `views.py` 中创建 AI 请求时传入的 `settings.OPENAI_MODEL` 替换为 `get_configured_ai_runtime()["model"]`，确保日志与实际调用的模型一致。

- [ ] **Step 4: 运行后端相关测试。**

运行：

```bash
cd backend && python manage.py test apps.core.tests.test_ai_config apps.core.tests.test_platform_configuration apps.core.tests.test_ai_service --keepdb
```

预期：相关测试全部通过，并确认响应字符串中没有 API Key 明文或密文。

### Task 4: 完成前端配置表单与图标修正

**Files:**
- Modify: `frontend/src/api.ts:68,132`
- Modify: `frontend/src/pages/platform/PlatformSettings.vue`
- Modify: `frontend/src/platformAIConfigUI.test.ts`

- [ ] **Step 1: 更新前端 API 类型和保存请求。**

保持 `PlatformAIConfig` 只含安全返回字段：`configured`、`masked_key`、`model`、`base_url`。将保存函数改为接收 `{ api_key?: string; model: string; base_url: string }`，只在调用时发送输入的 Key，不在响应类型中声明明文 Key。

- [ ] **Step 2: 增加模型和 Base URL 表单状态。**

在 `PlatformSettings.vue` 增加 `modelInput`、`baseUrlInput`，加载成功后用 `config.model` 和 `config.base_url` 填充。保存前校验三项：没有任何已配置 Key 时 API Key 必填；模型和 Base URL 始终非空；已配置时 API Key 为空代表保留旧 Key。保存按钮只要模型/URL有效且满足 Key 条件就可用，保存成功清空 Key 输入并保留模型、URL与掩码。

- [ ] **Step 3: 修正图标渲染尺寸。**

将原始 `<Key :size="18" aria-hidden="true" />` 替换为：

```vue
<el-icon :size="18" aria-hidden="true"><Key /></el-icon>
```

保留 `.section-title-with-icon` 的标题布局，并用 `.section-title-with-icon .el-icon` 固定 `flex: 0 0 18px`，避免全局 `svg { max-width: 100% }` 再次改变尺寸。

- [ ] **Step 4: 运行前端测试和构建。**

运行：

```bash
cd frontend && npm test
npm run build
```

预期：所有 Vitest 测试通过，构建退出码为 0；允许记录当前已存在的 chunk 体积和 PURE 注释警告，但不能新增 TypeScript 或编译错误。

### Task 5: 集成验证、迁移运行与交付

**Files:**
- Modify: `docs/项目运行说明.md`（仅在现有环境变量说明与页面配置行为不一致时更新）
- Modify: `docs/灵溯项目完整交接手册.md`（仅在现有配置说明缺少页面参数时更新）

- [ ] **Step 1: 重建本地后端并执行迁移。**

运行：

```bash
docker compose --profile async --profile async-beat up --build -d backend celery celery_beat
docker compose exec -T backend python manage.py showmigrations core
```

预期：`0042_platform_ai_configuration_provider_fields` 标记为 `[X]`，backend、celery、celery_beat 均正常运行；不使用 `down -v`，不删除现有 PostgreSQL 数据。

- [ ] **Step 2: 验证接口路由与页面行为。**

未认证 curl 访问 `/api/platform-ai-config/` 应返回 401/403 而不是 404。刷新已登录的平台设置页，确认页面显示模型名、Base URL、掩码 Key 和服务健康状态，AI 图标实际尺寸约 18px。使用页面或 API 保存三项测试值后确认刷新仍显示新模型/地址，Key 仍只显示掩码；不在验证日志输出真实 Key。

- [ ] **Step 3: 运行完整回归。**

运行：

```bash
docker compose exec -T backend python manage.py test --keepdb
cd frontend && npm test && npm run build
git diff --check
```

预期：后端 253 个测试全部通过（允许环境条件跳过项），前端测试和构建通过，工作区无未预期改动。

- [ ] **Step 4: 提交并推送。**

```bash
git add backend frontend docs
git commit -m "feat: configure platform AI provider settings"
git push origin codex/ui-audit-consistency
```

推送前确认 `.env` 未被 Git 跟踪、差异中没有真实 API Key；推送后确认本地 HEAD 与 `origin/codex/ui-audit-consistency` 相同。

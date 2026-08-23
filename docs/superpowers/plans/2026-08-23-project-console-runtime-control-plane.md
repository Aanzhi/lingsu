# 灵溯项目控制台运行控制面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将宿主机上的灵溯项目控制台升级为能统一启动、停止、监控、诊断、受控修复并真实验收整个本机项目的运行控制面，彻底阻断前端代理、后端端口和 CSRF 来源漂移导致的重复登录失败。

**Architecture:** 保留 `scripts/project-console.py` 的本机-only 宿主进程架构，新增纯标准库运行契约/诊断模块和本机 JSONL 操作存储。控制台通过白名单动作控制 Colima、Docker Compose、宿主机项目进程和验收脚本；前端控制台页面通过轮询操作资源显示可恢复进度、错误证据和修复结果。真实 `/api/login/` 是唯一登录验收标准，`/api/demo-login/` 不计为通过。

**Tech Stack:** Python 3 标准库、Docker Compose、Colima、Node.js、Playwright、现有 `scripts/console.html`，不新增运行时依赖，不把控制台加入 Docker Compose。

## 实现与测试约定

- 所有 Python 测试使用标准库 `unittest`，从仓库根目录运行；不使用 `pytest`。
- 因为现有控制台文件名包含连字符，测试通过 `importlib.util.spec_from_file_location("project_console", "scripts/project-console.py")` 加载模块，并在每个测试中使用 `unittest.mock.patch` 隔离 Docker、Colima、端口扫描、HTTP 请求和进程终止。
- 测试辅助函数必须在测试文件中显式定义：`load_console_module()`、`read_console_html()`、`start_test_server()`、`get_json(server, path)`、`post_json(server, path, payload, expect_error=False)` 和 `wait_for_operation(console, operation_id, timeout=3)`。`post_json(..., expect_error=True)` 返回 `{status, body}` 以便断言 400；`wait_for_operation` 只轮询 `console.get_operation()`，超过截止时间就用 `self.fail()`，不得使用无限等待。
- 任何会写文件的测试都使用 `tempfile.TemporaryDirectory()`；任何配置修复测试都复制到临时 `.env`，禁止触碰仓库根目录 `.env`、真实 Docker、Colima 或真实端口。
- 异步操作统一返回 `{operation_id, state}`，终态为 `succeeded`、`failed`、`waiting_confirmation` 或 `skipped`；测试先拿 `operation_id`，再通过 `wait_for_operation` 获取最终状态。
- 计划中的测试代码片段仅表达断言意图；实现时必须补齐导入、临时目录、测试服务器生命周期和 mock 清理，不能留下未定义的 fixture、pytest 调用或伪函数。

---

## 设计依据与不可变边界

- 设计文档：[2026-08-23-project-console-control-plane-design.md](../specs/2026-08-23-project-console-control-plane-design.md)
- 控制台只监听 `127.0.0.1:8800`，Docker/Colima 启停不能关闭控制台。
- “一键启动项目”包含 Colima/Docker 检查、Compose 服务启动、前端代理检查、健康检查和真实登录验收。
- “一键停止项目”只停止项目资源，保留控制台和 Docker/Colima；停止 Docker/Colima 是独立确认动作。
- 启动检查与完整测试分离；完整测试不因失败而自动停止运行中的项目。
- 配置修复只允许非敏感白名单字段，修改前备份和展示差异，修复后重启受影响服务并重新验收。
- 错误历史在本机脱敏保存最近 7 天；运行状态和操作日志不进入 Git。
- 保留工作区已有 UI、后端、AI 和控制台改动，不使用破坏性回退命令。

## 文件边界

### 新建

- `scripts/project_runtime.py`：运行契约、端口/进程/来源诊断、错误代码和脱敏函数；保持纯函数优先，便于单元测试。
- `scripts/project_console_store.py`：本机 JSONL 事件、错误历史和操作状态持久化；负责 7 天清理、原子写入和刷新恢复。
- `scripts/test_project_runtime.py`：运行契约和诊断规则测试。
- `scripts/test_project_console_store.py`：事件存储、脱敏、过期清理和操作状态测试。

### 修改

- `scripts/project-console.py`：集成运行契约、诊断、操作状态机、启动/停止流程、修复动作和新 HTTP API；保留现有兼容 API。
- `scripts/lingsu-e2e.mjs`：补充真实登录响应正文、CSRF/Origin 诊断、代理失败证据和明确退出码。
- `scripts/console.html`：增加一键启动/停止/重启、进度时间线、错误中心、日志、修复确认和验收结果 UI。
- `scripts/test_project_console.py`：扩展 API、白名单、操作、兼容性和本机-only 测试。
- `scripts/dev-frontend.sh`：确保宿主机前端启动时显式使用控制台解析出的 canonical backend 代理，不继承旧环境变量。
- `.gitignore`：忽略本机控制台运行数据目录，例如 `var/project-console/`。
- `README.md`、`docs/项目运行说明.md`：统一控制台启动方式、端口契约、诊断和修复说明。

### 不修改

- `backend/apps/core` 业务 API、数据库模型和项目业务逻辑不因本计划改动。
- `frontend/src` 生产业务页面不因本计划改动；控制台 UI 是 `scripts/console.html` 的本机运维页面。
- `docker-compose.yml` 不增加 console service；只在发现运行契约与现有 Compose 端口说明不一致时更新注释/文档，不改变服务协议。

---

## Task 1: 运行契约与诊断规则

**Files:**

- Create: `scripts/test_project_runtime.py`
- Create: `scripts/project_runtime.py`
- Modify: `scripts/project-console.py` only after the helper tests pass

- [ ] **Step 1: 写运行契约和诊断的失败测试**

在 `scripts/test_project_runtime.py` 顶部导入 `json`、`unittest`，并导入待测函数：

```python
from scripts.project_runtime import classify_port_process, diagnose_runtime, redact_text
```

在 `scripts/test_project_runtime.py` 中以 `unittest.TestCase` 覆盖以下纯数据行为（使用 `self.assert*`，不使用 pytest）：

```python
def test_detects_csrf_origin_mismatch_from_runtime_snapshot(self):
    snapshot = {
        "frontend": {"port": 5173, "proxy_target": "http://127.0.0.1:8001"},
        "backend": {"port": 8001},
        "origins": {
            "cors": ["http://127.0.0.1:5175"],
            "csrf": ["http://127.0.0.1:5175"],
        },
    }
    errors = diagnose_runtime(snapshot)
    codes = {item["code"] for item in errors}
    self.assertIn("RUNTIME_CSRF_ORIGIN_MISMATCH", codes)
    self.assertIn("http://127.0.0.1:5173", json.dumps(errors, ensure_ascii=False))

def test_accepts_canonical_docker_frontend_contract(self):
    snapshot = {
        "frontend": {"mode": "docker", "port": 5173, "proxy_target": "http://backend:8000"},
        "backend": {"port": 18001},
        "origins": {
            "cors": ["http://127.0.0.1:5173", "http://localhost:5173"],
            "csrf": ["http://127.0.0.1:5173", "http://localhost:5173"],
        },
    }
    self.assertEqual(diagnose_runtime(snapshot), [])

def test_redacts_credentials_and_tokens_without_destroying_diagnostic_context(self):
    text = "POST /api/login/ Authorization: Bearer abc123 password=secret api_key=hidden"
    safe = redact_text(text)
    self.assertNotIn("secret", safe)
    self.assertNotIn("hidden", safe)
    self.assertIn("POST /api/login/", safe)

def test_marks_unknown_port_process_as_conflict_but_not_owned(self):
    process = {"pid": 77, "cwd": "/Users/other/project", "command": "node vite --port 5173"}
    self.assertEqual(
        classify_port_process(process, project_root="/Users/anzhi/Desktop/雷灵/星辰/lingsu"),
        "foreign_conflict",
    )

def test_marks_project_process_as_safe_to_cleanup_only_when_command_matches(self):
    process = {"pid": 88, "cwd": "/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend", "command": "node vite --host 127.0.0.1 --port 5173"}
    self.assertEqual(
        classify_port_process(process, project_root="/Users/anzhi/Desktop/雷灵/星辰/lingsu"),
        "owned_project_process",
    )
```

- [ ] **Step 2: 运行失败测试，确认失败来自缺少实现**

Run:

```bash
python -m unittest scripts.test_project_runtime -v
```

Expected: FAIL because `scripts.project_runtime` and its diagnostic functions do not exist yet. Fix import/fixture errors until the tests fail for the intended missing behavior rather than syntax errors.

- [ ] **Step 3: 实现最小运行契约模块**

在 `scripts/project_runtime.py` 中实现：

- `CANONICAL_FRONTEND_PORT = 5173`、`LOCAL_FRONTEND_ORIGINS` 和稳定错误代码常量。
- `parse_env_file(path)`：只读取键值，保留逗号分隔列表为字符串，不读取或打印 secrets。
- `expected_origins(frontend_port=5173)`：返回 `localhost` 和 `127.0.0.1` 两个来源。
- `redact_text(value)`：对 `password`、`api_key`、`token`、`secret`、`authorization`、Cookie 值执行大小写不敏感替换，保留键名和请求路径。
- `classify_port_process(process, project_root)`：按 cwd 和命令白名单返回 `owned_project_process`、`foreign_conflict`、`unknown`。
- `diagnose_runtime(snapshot)`：对代理目标、后端端口、CORS/CSRF 来源、前端模式和端口冲突生成稳定错误对象 `{code, severity, title, detail, evidence, remediation}`。
- `build_runtime_snapshot(...)`：只组合调用方传入的实际进程、端口、Compose、环境和健康检查数据，不在纯模块中执行 shell。

- [ ] **Step 4: 运行运行契约测试并提交**

Run:

```bash
python -m unittest scripts.test_project_runtime -v
git diff --check
```

Expected: all runtime tests PASS and no whitespace errors.

Commit:

```bash
git add scripts/project_runtime.py scripts/test_project_runtime.py
git commit -m "feat: add project runtime diagnostics"
```

---

## Task 2: 本机事件、错误历史与可恢复操作状态

**Files:**

- Create: `scripts/test_project_console_store.py`
- Create: `scripts/project_console_store.py`
- Modify: `.gitignore`

- [ ] **Step 1: 写失败测试**

在 `scripts/test_project_console_store.py` 导入 `tempfile`、`unittest`、`datetime`、`timedelta`、`timezone`，并从 `scripts.project_console_store` 导入 `InvalidOperationTransition` 和 `LocalConsoleStore`。每个测试都在自己的 `TemporaryDirectory()` 中运行，覆盖：

```python
def test_appends_and_reads_events_in_time_order(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        store = LocalConsoleStore(temp_dir)
        store.append_event({"source": "backend", "level": "error", "message": "boom"})
        events = store.list_events()
    self.assertEqual(events[0]["source"], "backend")
    self.assertTrue(events[0]["event_id"])
    self.assertTrue(events[0]["created_at"])

def test_persists_operation_steps_after_process_restart(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        first = LocalConsoleStore(temp_dir)
        operation = first.create_operation("start_project", ["docker", "backend", "frontend", "login"])
        first.update_step(operation["operation_id"], "docker", "succeeded", detail="ready")
        second = LocalConsoleStore(temp_dir)
        restored = second.get_operation(operation["operation_id"])
    self.assertEqual(restored["steps"][0]["state"], "succeeded")

def test_prunes_events_older_than_seven_days_and_keeps_recent_failures(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        store = LocalConsoleStore(temp_dir)
        now = datetime.now(timezone.utc)
        old_timestamp = (now - timedelta(days=8)).isoformat()
        recent_timestamp = (now - timedelta(days=1)).isoformat()
        store.append_event({"created_at": old_timestamp, "source": "frontend", "level": "error"})
        store.append_event({"created_at": recent_timestamp, "source": "backend", "level": "error"})
        store.prune(now=now)
        events = store.list_events()
    self.assertEqual(len(events), 1)
    self.assertEqual(events[0]["source"], "backend")

def test_operation_transition_rejects_running_to_succeeded_without_step_completion(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        store = LocalConsoleStore(temp_dir)
        operation = store.create_operation("start_project", ["docker"])
        store.start_step(operation["operation_id"], "docker")
        with self.assertRaises(InvalidOperationTransition):
            store.finish_operation(operation["operation_id"], "succeeded")
```

The implementation must preserve the four assertions above and must not touch the real project runtime directory.

- [ ] **Step 2: 运行失败测试**

Run:

```bash
python -m unittest scripts.test_project_console_store -v
```

Expected: FAIL because the store and transition validation are not implemented.

- [ ] **Step 3: 实现本机 JSONL 存储**

在 `scripts/project_console_store.py` 中实现：

- `LocalConsoleStore(root, retention_days=7)`，默认目录由控制台传入 `ROOT/var/project-console`。
- `append_event(event)`：补齐 `event_id`、`created_at`，执行 `redact_text`，使用临时文件 + `os.replace` 保证单次写入完整。
- `list_events(filters=None, limit=200)`：按时间倒序返回，支持 source、level、code、operation_id 过滤。
- `create_operation(kind, steps)`、`get_operation(id)`、`get_latest_operation()`。
- `start_step`、`update_step`、`confirm_operation`、`retry_from_step`、`finish_operation`，拒绝不合法状态跃迁。
- `prune(now)`：删除 7 天前事件和操作日志；运行目录不存在时自动创建。
- 操作状态固定使用 `pending`、`running`、`succeeded`、`failed`、`waiting_confirmation`、`skipped`。

- [ ] **Step 4: 加入运行目录忽略规则并验证**

在 `.gitignore` 增加：

```gitignore
var/project-console/
```

Run:

```bash
python -m unittest scripts.test_project_console_store -v
git diff --check
```

Expected: all store tests PASS; `git status --short` 不显示运行数据文件。

Commit:

```bash
git add scripts/project_console_store.py scripts/test_project_console_store.py .gitignore
git commit -m "feat: persist console operations and errors"
```

---

## Task 3: 将真实运行状态接入控制台诊断

**Files:**

- Modify: `scripts/project-console.py`
- Modify: `scripts/test_project_console.py`

- [ ] **Step 1: 为诊断 API 写失败测试**

扩展 `scripts/test_project_console.py`。沿用现有的 `importlib` 控制台加载方式，并在测试类中增加 `start_test_server()`、`get_json(server, path)`、`post_json(server, path, payload, expect_error=False)` 辅助方法；使用 patch 替换 Docker、进程和 HTTP 探测，测试：

```python
def test_status_contains_runtime_contract_and_diagnostics(self):
    bad_snapshot = {
        "frontend": {"port": 5173, "proxy_target": "http://127.0.0.1:8001"},
        "backend": {"port": 8001},
        "origins": {"cors": ["http://127.0.0.1:5175"], "csrf": ["http://127.0.0.1:5175"]},
    }
    with patch.object(console, "collect_runtime_snapshot", return_value=bad_snapshot):
        status = console.collect_status()
    self.assertEqual(status["runtime_contract"]["frontend"]["port"], 5173)
    self.assertTrue(any(item["code"] == "RUNTIME_CSRF_ORIGIN_MISMATCH" for item in status["diagnostics"]))

def test_diagnostics_endpoint_is_read_only_and_returns_evidence(self):
    server, thread = start_test_server()
    try:
        response = get_json(server, "/api/diagnostics")
        self.assertTrue(response["ok"])
        self.assertIn("errors", response)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def test_foreign_port_process_is_reported_without_kill(self):
    foreign_process = {"pid": 77, "cwd": "/Users/other/project", "command": "node vite --port 5173"}
    with patch.object(console, "inspect_listeners", side_effect=lambda port: [foreign_process] if port == 5173 else []), \
         patch.object(console, "kill_port") as kill:
        result = console.collect_runtime_snapshot()
    self.assertEqual(result["frontend"]["process_state"], "foreign_conflict")
    kill.assert_not_called()
```

其中三个测试方法属于 `ProjectConsoleTests(unittest.TestCase)`；`start_test_server()` 必须绑定 `("127.0.0.1", 0)`，不能占用 8800，也不能启动后台项目服务。

- [ ] **Step 2: 运行失败测试**

Run:

```bash
python -m unittest scripts.test_project_console -v
```

Expected: new tests fail because the runtime snapshot, diagnostics response and read-only endpoint do not exist.

- [ ] **Step 3: 实现真实快照采集**

在 `scripts/project-console.py` 增加以下职责明确的函数：

- `inspect_listeners(port)`：用 `lsof` 读取监听 PID，再用 `ps` 读取 cwd/command；失败时返回结构化 unknown，不抛出到页面。
- `inspect_host_process(pid)`：返回脱敏的 cwd、command、environment keys 和身份分类；不返回环境变量值中的 secrets。
- `compose_frontend_state()` 和后端端口解析结果统一进入快照，不再只以“HTTP 200”判定服务属于当前项目。
- `collect_runtime_snapshot()`：组装控制台、前端、后端、Compose、Colima、来源配置和健康检查，调用 `project_runtime.diagnose_runtime()`。
- `collect_diagnostics()`：将诊断结果写入事件存储，避免相同 code/evidence 在短时间内无限重复写入。
- `collect_status()` 增加 `runtime_contract`、`diagnostics`、`errors` 和 `operation` 字段，同时保留现有字段。

实现以下本次问题的具体检查：

- Vite 代理目标是否指向当前 canonical backend。
- 实际前端来源是否出现在 CSRF/CORS 白名单。
- 前端监听 PID 是否是当前项目进程或 Compose 容器。
- 8000、8001、18001 等后端端口是否存在多个项目进程。
- Docker backend 的映射端口是否与控制台访问端口一致。

- [ ] **Step 4: 增加诊断相关 HTTP API**

在 `Handler.do_GET` 增加：

- `/api/diagnostics`：返回 `{ok: true, runtime_contract, errors, generated_at}`。
- `/api/errors`：读取 query 的 `source`、`level`、`code`、`operation_id`、`limit`，只返回脱敏事件。
- `/api/operations/latest`：返回最近操作和步骤。
- `/api/operations/<id>`：返回指定操作。

所有 GET 诊断接口只读；非法过滤参数返回 400，不执行命令。`collect_status()` 以 `collect_runtime_snapshot()` 的返回值为输入，避免测试中偷偷读取真实端口；真实采集只在控制台运行时调用。

- [ ] **Step 5: 运行诊断测试并提交**

Run:

```bash
python -m unittest scripts.test_project_runtime scripts.test_project_console -v
git diff --check
```

Expected: all tests PASS; current运行环境能够被识别为“宿主机前端代理与后端可信来源不一致”时，诊断 JSON 必须包含稳定错误代码而不是只返回 HTTP 403。

Commit:

```bash
git add scripts/project-console.py scripts/test_project_console.py
git commit -m "feat: expose runtime diagnostics"
```

---

## Task 4: 一键启停与可恢复进度状态机

**Files:**

- Modify: `scripts/project-console.py`
- Modify: `scripts/test_project_console.py`

- [ ] **Step 1: 为项目生命周期写失败测试**

在测试文件中定义 `patch_start_dependencies(calls, diagnostics=None)`：使用 `contextlib.ExitStack` 依次 patch `ensure_docker`、`start_dependencies`、`start_backend`、`wait_for_backend_health`、`start_frontend`、`check_runtime_contract` 和 `run_real_login`，每个 mock 将自己的步骤名追加到 `calls`；`diagnostics` 参数用于让 `check_runtime_contract` 返回指定错误。再定义 `wait_for_operation`（见“实现与测试约定”）。覆盖以下不执行真实 Docker/Colima 的行为：

```python
def test_start_project_runs_dependencies_before_frontend_and_real_login(self):
    calls = []
    with patch_start_dependencies(calls):
        operation = console.start_project_operation()
        state = wait_for_operation(console, operation["operation_id"])
    self.assertEqual(state["state"], "succeeded")
    self.assertEqual(calls, ["docker", "dependencies", "backend", "health", "frontend", "contract", "real_login"])

def test_start_project_pauses_on_contract_mismatch_before_login(self):
    calls = []
    csrf_error = {"code": "RUNTIME_CSRF_ORIGIN_MISMATCH", "severity": "error"}
    with patch_start_dependencies(calls, diagnostics=[csrf_error]):
        operation = console.start_project_operation()
        state = wait_for_operation(console, operation["operation_id"])
    self.assertEqual(state["state"], "waiting_confirmation")
    self.assertEqual(state["current_step"], "runtime_contract")
    self.assertNotIn("real_login", calls)

def test_stop_project_does_not_call_colima_stop_or_console_kill(self):
    with patch.object(console, "frontend_stop", return_value=True), \
         patch.object(console, "backend_stop", return_value=True), \
         patch.object(console, "dependencies_stop", return_value=True), \
         patch.object(console, "colima_action") as colima, \
         patch.object(console, "kill_port") as kill:
        operation = console.stop_project_operation()
        state = wait_for_operation(console, operation["operation_id"])
    colima.assert_not_called()
    kill.assert_not_called()
    self.assertEqual(state["state"], "succeeded")

def test_stop_colima_requires_explicit_confirmation(self):
    server, thread = start_test_server()
    try:
        response = post_json(server, "/api/operations", {"kind": "stop_colima"}, expect_error=True)
        self.assertEqual(response["status"], 400)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
```

- [ ] **Step 2: 运行失败测试**

Run:

```bash
python -m unittest scripts.test_project_console -v
```

Expected: new lifecycle tests fail because operations are still handled by the old unstructured action worker.

- [ ] **Step 3: 实现操作执行器**

在 `scripts/project-console.py` 实现固定步骤表：

```python
START_STEPS = (
    "runtime",
    "docker",
    "dependencies",
    "backend",
    "health",
    "frontend",
    "runtime_contract",
    "real_login",
)
STOP_STEPS = ("frontend", "backend", "dependencies", "summary")
```

实现：

- `run_operation(operation_id)`：每完成一步更新 store、写事件、刷新 UI 可见状态。
- Docker/Colima 启动只调用 `ensure_docker()`；停止项目不调用 `colima stop`。
- 将生命周期步骤拆成可 patch 的白名单函数：`start_dependencies()`、`start_backend()`、`wait_for_backend_health()`、`start_frontend()`、`check_runtime_contract()`、`run_real_login()`、`frontend_stop()`、`backend_stop()` 和 `dependencies_stop()`；这些函数内部才允许调用已有 `compose`、宿主机进程和 HTTP 探测函数。
- 前端启动前调用 `collect_runtime_snapshot()`；发现陌生占用进程时进入 failed，不自动 kill。
- 健康检查使用固定超时和重试上限；超时写 `SERVICE_HEALTH_TIMEOUT`。
- 运行契约不通过时写 `RUNTIME_*` 错误并进入 `waiting_confirmation`。
- 用户确认修复后从 `runtime_contract` 步骤继续，不能跳过真实登录。
- `run_checks` 独立创建操作，不改变正在运行的服务。
- 单服务操作复用白名单函数，不把操作字符串拼进 shell。

- [ ] **Step 4: 增加操作 API并保留兼容层**

在 `Handler.do_POST` 增加：

- `POST /api/operations`，接受固定 `kind` 和可选 `target`，未知值返回 400。
- `POST /api/operations/<id>/confirm`，只接受 `repair_runtime`、`stop_colima`、`seed_demo` 等待确认状态。
- `POST /api/operations/<id>/retry`，只能从失败/等待确认步骤重试。

旧 `/api/action` 保留，将 `target=all` 映射到 `start_project`/`stop_project`/`restart_project`，保留原有 confirm 规则，避免旧按钮或脚本立即失效。

- [ ] **Step 5: 运行生命周期测试并提交**

Run:

```bash
python -m unittest scripts.test_project_console -v
python -m py_compile scripts/project-console.py scripts/project_runtime.py scripts/project_console_store.py
git diff --check
```

Expected: lifecycle tests PASS，且 `stop_project` 不会停止控制台或 Colima。

Commit:

```bash
git add scripts/project-console.py scripts/test_project_console.py
git commit -m "feat: add resumable project lifecycle operations"
```

---

## Task 5: 修复真实登录验收链路

**Files:**

- Modify: `scripts/lingsu-e2e.mjs`
- Modify: `scripts/project-console.py`
- Modify: `scripts/test_project_console.py`
- Modify: `frontend/e2e/mvp.spec.ts` only to add a real-login scenario without removing existing role coverage

- [ ] **Step 1: 写真实登录失败证据测试**

在 `scripts/test_project_console.py` 中验证控制台新增的 `parse_e2e_output(text)` 保留 JSON 结果：

```python
def test_real_login_result_marks_csrf_origin_failure_as_failed(self):
    result = parse_e2e_output('{"ok":false,"loginStatus":403,"errorText":"CSRF验证失败","csrfTokenSent":true}')
    self.assertFalse(result["ok"])
    self.assertEqual(result["loginStatus"], 403)
    self.assertEqual(result["failure_code"], "AUTH_CSRF_ORIGIN_MISMATCH")
```

在 `frontend/e2e/mvp.spec.ts` 增加真实登录测试：清理 cookies，访问 `/login`，填写 `demo-student` 与 `lingsu-demo-2026`，点击真实登录按钮，断言跳转到 `/student/home`；该测试不调用 `/api/demo-login/`。

- [ ] **Step 2: 运行失败测试**

Run:

```bash
python -m unittest scripts.test_project_console -v
cd frontend && npx playwright test e2e/mvp.spec.ts -g "真实账号密码登录"
```

Expected: 在当前 5173→8001→5175 的错配环境中，真实登录测试失败并报告 CSRF 证据，而不是显示通过。

- [ ] **Step 3: 增强 Playwright 验收脚本**

在 `scripts/lingsu-e2e.mjs`：

- 记录登录请求的 `Origin`、`X-CSRFToken` 是否存在和安全脱敏后的请求地址。
- 记录登录响应正文前 400 个字符并用 `redactText` 脱敏。
- 将 403 CSRF、401/400 账号失败、网络失败和前端表单错误映射成稳定 `failure_code`。
- 失败时保留最终 URL、错误文本、console errors、failed requests 和后端响应摘要。
- 成功条件必须同时满足：登录响应 2xx、最终 URL 包含角色首页、页面无 `.form-error`。

在 `project-console.py` 中实现 `parse_e2e_output(text)`：解析 `scripts/lingsu-e2e.mjs` 的最后一个 JSON 行，解析失败返回 `AUTH_E2E_OUTPUT_INVALID`；根据状态码、响应正文、网络错误和表单错误映射稳定 `failure_code`，并把真实登录结果写入错误事件和操作步骤，不再只显示 `loginStatus` 数字。

- [ ] **Step 4: 让演示账号就绪状态可诊断**

增加只读账号检查，验证 `demo-student` 是否存在、启用且具备可用密码；不在读取接口中输出密码。未就绪时生成 `AUTH_DEMO_ACCOUNT_UNREADY`，页面提供单独的“初始化演示数据”确认动作，调用现有 `seed_demo`，完成后重新执行真实登录。

- [ ] **Step 5: 运行真实登录测试并提交**

Run:

```bash
python -m unittest scripts.test_project_console -v
cd frontend && npx playwright test e2e/mvp.spec.ts -g "真实账号密码登录"
```

Expected: 配置错配时明确失败；完成运行契约修复并初始化演示账号后明确通过。不能把 `/api/demo-login/` 结果作为真实登录结果。

Commit:

```bash
git add scripts/lingsu-e2e.mjs scripts/project-console.py scripts/test_project_console.py frontend/e2e/mvp.spec.ts
git commit -m "test: make real login the console acceptance gate"
```

---

## Task 6: 受控配置修复与残留进程处理

**Files:**

- Modify: `scripts/project-console.py`
- Modify: `scripts/dev-frontend.sh`
- Modify: `scripts/test_project_console.py`

- [ ] **Step 1: 写失败测试**

覆盖以下安全行为：

```python
def test_repair_only_changes_allowlisted_origin_and_proxy_fields(self):
    bad_snapshot = {
        "frontend": {"mode": "host", "proxy_target": "http://127.0.0.1:8001"},
        "backend": {"port": 18001},
        "origins": {"cors": ["http://127.0.0.1:5175"], "csrf": ["http://127.0.0.1:5175"]},
    }
    result = console.plan_runtime_repair(bad_snapshot)
    self.assertTrue(set(result["changes"]) <= {"VITE_API_PROXY_TARGET", "CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"})
    self.assertNotIn("OPENAI_API_KEY", result["changes"])

def test_repair_creates_backup_before_writing_env(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        env_path = os.path.join(temp_dir, ".env")
        with open(env_path, "w", encoding="utf-8") as handle:
            handle.write("VITE_API_PROXY_TARGET=http://127.0.0.1:8001\nOPENAI_API_KEY=secret\n")
        bad_snapshot = {"frontend": {"mode": "host", "proxy_target": "http://127.0.0.1:8001"}, "backend": {"port": 18001}, "origins": {"cors": [], "csrf": []}}
        plan = console.plan_runtime_repair(bad_snapshot, env_path=env_path)
        result = console.apply_runtime_repair(plan, confirm=True)
        self.assertTrue(os.path.exists(result["backup_path"]))
        self.assertNotEqual(result["backup_path"], env_path)
        with open(env_path, encoding="utf-8") as handle:
            repaired = handle.read()
    self.assertIn("OPENAI_API_KEY=secret", repaired)

def test_foreign_process_is_never_terminated_by_repair(self):
    foreign_process = {"pid": 77, "cwd": "/Users/other/project", "command": "node vite --port 5173", "state": "foreign_conflict"}
    with patch.object(console, "kill_pid_tree") as kill:
        console.repair_frontend_conflict(foreign_process, confirm=True)
    kill.assert_not_called()

def test_owned_project_vite_process_can_be_cleaned_after_confirmation(self):
    owned_process = {"pid": 88, "cwd": "/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend", "command": "node vite --host 127.0.0.1 --port 5173", "state": "owned_project_process"}
    with patch.object(console, "kill_pid_tree") as kill:
        console.repair_frontend_conflict(owned_process, confirm=True)
    kill.assert_called_once_with(owned_process["pid"])
```

- [ ] **Step 2: 运行失败测试**

Run:

```bash
python -m unittest scripts.test_project_console -v
```

Expected: repair functions do not exist and tests fail for the intended reason.

- [ ] **Step 3: 实现安全修复计划**

实现 `plan_runtime_repair(snapshot)`：

- 只计算 `VITE_API_PROXY_TARGET`、`CORS_ALLOWED_ORIGINS`、`CSRF_TRUSTED_ORIGINS` 的变化。
- 目标来源固定为 `http://127.0.0.1:5173` 和 `http://localhost:5173`。
- Docker 前端目标固定为 `http://backend:8000`；宿主机前端目标固定为 `http://127.0.0.1:<BACKEND_PORT>`。
- 返回原值、目标值、原因和涉及服务，不直接写文件。

在控制台中定义 `ACTIVE_ENV_FILE = os.path.join(ROOT, ".env")`；`plan_runtime_repair(snapshot, env_path=ACTIVE_ENV_FILE)` 只能接收仓库内的 `.env` 或测试传入的临时 `.env` 文件，拒绝目录、符号链接和仓库外路径。

实现 `plan_runtime_repair(snapshot, env_path=ACTIVE_ENV_FILE)` 和 `apply_runtime_repair(plan, confirm)`：

- `confirm` 不是 true 时只返回计划，不写文件。
- 写入前把 active env 文件复制到 `var/project-console/backups/<timestamp>.env`。
- 只替换 allowlist 键，保留其他行、注释和密钥原文，不把密钥写入事件日志。
- 修复完成后返回脱敏 diff，触发前端/后端重启操作。

`plan_runtime_repair` 的返回值必须包含 `env_path`、`changes`（键到 `{before, after, reason}` 的映射）、`affected_services` 和 `backup_required`；`apply_runtime_repair` 只接受这个计划对象，避免调用方绕过白名单直接传入任意文件或键。

修改 `scripts/dev-frontend.sh`：

- 保留 `--host 127.0.0.1 --port 5173`。
- 由控制台传入已经解析的 `VITE_API_PROXY_TARGET`，脚本不从旧 shell 环境继承冲突值。
- 启动日志只输出目标地址，不输出完整环境。

- [ ] **Step 4: 运行修复安全测试并提交**

Run:

```bash
python -m unittest scripts.test_project_console -v
git diff --check
```

Expected: only allowlisted fields change; foreign process never被终止；backup exists and is ignored by Git.

Commit:

```bash
git add scripts/project-console.py scripts/dev-frontend.sh scripts/test_project_console.py
git commit -m "feat: add safe runtime repair actions"
```

---

## Task 7: 控制台 UI：一键启停、进度、错误与日志

**Files:**

- Modify: `scripts/console.html`
- Modify: `scripts/test_project_console.py` for semantic markup assertions

- [ ] **Step 1: 写 UI 合同失败测试**

在 `scripts/test_project_console.py` 读取 HTML，使用 `self.assertIn` 断言以下结构尚不存在时测试失败：

```python
def test_console_has_project_start_stop_and_full_check_actions(self):
    html = read_console_html()
    self.assertIn('data-operation="start_project"', html)
    self.assertIn('data-operation="stop_project"', html)
    self.assertIn('data-operation="run_checks"', html)

def test_console_has_progress_timeline_error_center_and_runtime_contract_regions(self):
    html = read_console_html()
    for selector in ("operation-progress", "error-center", "runtime-contract", "operation-log"):
        self.assertIn(f'id="{selector}"', html)

def test_console_explains_project_stop_keeps_console_and_docker_alive(self):
    html = read_console_html()
    self.assertIn("停止项目不会关闭控制台", html)
    self.assertIn("停止 Docker", html)
```

- [ ] **Step 2: 运行失败测试**

Run:

```bash
python -m unittest scripts.test_project_console -v
```

Expected: new semantic UI assertions fail before markup is added.

- [ ] **Step 3: 实现控制台信息层级**

在 `scripts/console.html` 保持 B「安静工作台」视觉方向，加入：

- 顶部控制面身份卡：显示“宿主机独立运行”、PID、8800 地址和 Docker 不会关闭控制台说明。
- 项目操作区：一键启动、停止、重启、完整验收；危险动作显示二次确认。
- `#operation-progress`：百分比、当前步骤、步骤列表、等待确认提示、重试次数和耗时。
- `#runtime-contract`：前端端口、代理目标、后端端口、来源白名单和进程身份的声明/实际对照。
- `#error-center`：错误代码、等级、来源、原因、证据、修复按钮和历史筛选。
- 服务监控区：Colima/Docker、Compose 服务、前端、后端、健康检查和真实登录。
- `#operation-log`：只在区域内部滚动的脱敏日志。

所有按钮通过 `data-operation` 映射固定操作，不在浏览器中拼接命令字符串。

- [ ] **Step 4: 实现轮询和操作恢复**

页面脚本实现：

- 空闲时每 3 秒读取 `/api/status`。
- 操作运行时每 500ms 读取 `/api/operations/latest` 和 `/api/status`。
- 页面加载时恢复最新运行操作；如果状态是 `running`，显示“控制台仍在执行”。
- `waiting_confirmation` 显示修复差异和确认按钮；确认后调用 `/confirm`。
- `failed` 显示稳定错误代码和“重试失败步骤”；不把旧结果覆盖成成功。
- 完整验收使用独立进度卡，不改变服务启动状态。

- [ ] **Step 5: 增加响应式和可访问性**

在现有控制台 CSS 中保证：

- 1440px/1280px 使用双栏状态与错误布局。
- 768px 以下切换单列，进度步骤纵向展示。
- 390px 下按钮不遮挡、日志区域局部滚动、页面无横向滚动。
- 每个进度状态同时使用文字和颜色，不只依赖颜色。
- 操作按钮有清晰焦点环，危险动作有可读确认文案。
- `prefers-reduced-motion` 下禁用进度动画。

- [ ] **Step 6: 运行 UI 合同测试并提交**

Run:

```bash
python -m unittest scripts.test_project_console -v
git diff --check
```

Expected: console semantic UI tests PASS；HTML 只发固定 `data-operation` 值，服务端的操作白名单测试负责保证浏览器不能注入任意命令。

Commit:

```bash
git add scripts/console.html scripts/test_project_console.py
git commit -m "feat: add console progress and error center"
```

---

## Task 8: 文档、操作说明和兼容性收口

**Files:**

- Modify: `README.md`
- Modify: `docs/项目运行说明.md`
- Modify: `scripts/console.sh`
- Modify: `scripts/test_project_console.py`

- [ ] **Step 1: 写文档合同测试**

扩展控制台测试，断言文档明确写出：

- 控制台绑定 `127.0.0.1:8800`。
- 一键停止项目不关闭控制台和 Docker/Colima。
- 真实登录验收使用 `/api/login/`，不是 `/api/demo-login/`。
- `5173`、canonical backend 和 CSRF/CORS 来源由控制台检查。
- 完整验收独立于启动操作。

- [ ] **Step 2: 更新文档和启动器**

README 与运行说明统一为：

1. 启动 `scripts/console.sh`。
2. 打开 `http://127.0.0.1:8800`。
3. 使用“启动项目”完成运行链路。
4. 发生问题时查看诊断错误代码和修复按钮。
5. 需要完整验收时单独执行“完整验收”。

`scripts/console.sh` 启动时打印 canonical 前端端口、后端映射端口和控制台地址，但不打印环境变量或密钥。

- [ ] **Step 3: 运行文档和兼容性测试并提交**

Run:

```bash
python -m unittest scripts.test_project_console -v
git diff --check
```

Expected: old `/api/action` compatibility tests and new documentation assertions PASS.

Commit:

```bash
git add README.md docs/项目运行说明.md scripts/console.sh scripts/test_project_console.py
git commit -m "docs: document console diagnostics and recovery"
```

---

## Task 9: 端到端运行验证与回归

**Files:**

- Test: `scripts/test_project_runtime.py`
- Test: `scripts/test_project_console_store.py`
- Test: `scripts/test_project_console.py`
- Test: `frontend/e2e/mvp.spec.ts`
- Review: `git diff --check`

- [ ] **Step 1: 运行不触碰真实 Docker 的单元测试**

Run:

```bash
python -m unittest scripts.test_project_runtime scripts.test_project_console_store scripts.test_project_console -v
python -m py_compile scripts/project-console.py scripts/project_runtime.py scripts/project_console_store.py
```

Expected: all console tests pass; no test stops Colima, kills foreign processes or mutates real `.env`.

- [ ] **Step 2: 启动控制台并检查只读状态**

Run:

```bash
./scripts/console.sh
curl -sS http://127.0.0.1:8800/api/status
curl -sS http://127.0.0.1:8800/api/diagnostics
```

Expected: `console.runtime=host`、`managed_by_docker=false`、运行契约存在、诊断结果可读；控制台启动不创建 Compose 服务。

- [ ] **Step 3: 复现并确认原始故障被识别**

在隔离的测试 fixture 中模拟 `VITE_API_PROXY_TARGET=http://127.0.0.1:8001` 与可信来源 `5175`，运行诊断 API。

Expected: 返回 `RUNTIME_FRONTEND_PROXY_MISMATCH` 或 `RUNTIME_CSRF_ORIGIN_MISMATCH`，包含 5173/8001/5175 证据，不直接显示“运行正常”。

- [ ] **Step 4: 运行真实登录验收**

在演示账号已通过确认动作初始化、canonical 前后端已启动后运行：

```bash
node scripts/lingsu-e2e.mjs
cd frontend && npx playwright test e2e/mvp.spec.ts -g "真实账号密码登录"
```

Expected: `/api/login/` 返回 2xx、最终进入 `/student/home`、无表单错误；错误配置时必须失败并显示稳定错误代码。

- [ ] **Step 5: 运行完整项目验证**

Run:

```bash
cd frontend && npm run test
cd frontend && npm run build
cd frontend && npm run test:e2e
cd backend && python manage.py test apps.core -v 2
git diff --check
```

Expected:

- Vitest、Vite build、Playwright E2E、Django tests 和差异检查通过。
- E2E 报告包含真实登录场景，不只包含 demo-login 场景。
- 构建已有警告必须如实记录，不能写成“无警告”。

- [ ] **Step 6: 进行浏览器视觉和交互检查**

在 `http://127.0.0.1:8800` 检查 1440px、1280px、1024px、768px、390px：

- 启动中、等待确认、失败、修复中、完成五种状态。
- 一键启动/停止/重启和单服务操作。
- 错误证据展开、日志筛选、修复确认、重试失败步骤。
- 浏览器刷新后操作进度恢复。
- 控制台停止项目后仍可访问，停止 Docker/Colima 前出现明确确认。
- 无文档级横向溢出、无隐藏主要操作、键盘焦点清晰。

- [ ] **Step 7: 最终交付检查**

Run:

```bash
git status --short
git log -n 10 --oneline
git diff --check
```

最终报告必须列出：

- 控制台新增的运行契约、诊断、错误中心、进度和修复能力。
- 已验证的真实登录入口和结果。
- 一键启停与 Docker/Colima 的边界。
- 测试命令、通过/失败/阻塞证据。
- 浏览器检查的视口和状态。
- 仍存在的限制，尤其是外部 AI 服务、Docker/Colima 权限和陌生进程冲突。

---

## 完成条件

只有同时满足以下条件才标记完成：

- 控制台保持 `127.0.0.1:8800` 本机-only，且不进入 Docker。
- 一键启动、停止、重启、完整验收和单服务操作均可从页面执行。
- 启动步骤有可恢复进度，失败步骤有日志和稳定错误代码。
- 端口、代理、CSRF/CORS、进程归属和 Docker 状态在真实运行前被检查。
- 已知的 `5173 -> 8001` / `5175` 冲突能够被识别、修复并重新验收。
- 真实 `/api/login/` 通过后才允许显示登录验收通过。
- 错误历史保留 7 天且自动脱敏。
- 外部进程不会被误杀，危险操作有确认。
- 控制台测试、前端测试、构建、E2E、后端测试、浏览器检查和 `git diff --check` 全部如实完成。

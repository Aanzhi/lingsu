# 灵溯独立项目控制台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让项目控制台作为宿主机上的独立控制平面运行，同时能够安全控制整个灵溯项目的 Docker/Colima、Compose 服务、前端、后端和验收流程。

**Status:** Implemented and verified. The console remains a host process and is not a Docker Compose service.

**Architecture:** 控制台继续由 `scripts/console.sh` 启动为宿主机 Python 进程，监听 `127.0.0.1:8800`，不加入 `docker-compose.yml`，也不被任何 Docker 启动命令自动拉起或关闭。控制台后端只通过白名单函数调用 `docker compose`、`colima` 和前端宿主进程，前端页面明确区分“控制台自身”和“项目服务”。全项目停止操作只停止项目资源，永远不停止控制台进程。

**Tech Stack:** Python 3 标准库 `http.server`、Docker Compose、Colima、原生 HTML/CSS/JavaScript、Python `unittest`。

---

## 文件边界

- Modify: `scripts/project-console.py` — 控制台状态模型、Docker/Colima 生命周期、服务白名单和全项目操作。
- Modify: `scripts/console.html` — 独立控制台状态展示、全项目操作按钮、Docker/Colima 操作入口和重复按钮清理。
- Modify: `scripts/console.sh` — 明确宿主机独立启动语义和启动提示。
- Modify: `scripts/test_project_console.py` — 控制台独立性、服务白名单、Docker 操作和安全确认测试。
- Modify: `README.md` — 独立启动、项目服务启动和停止边界。
- Modify: `docs/项目运行说明.md` — 面向用户的双终端启动流程和控制台职责说明。
- Test: `docker-compose.yml` — 只做只读配置断言，确保没有 console service。

## Task 1: 先锁定独立进程和 Compose 边界

- [x] **Step 1: 为控制台进程和 Compose 配置写失败测试**

  在 `scripts/test_project_console.py` 中新增以下断言：

  ```python
  def test_console_is_host_process_and_has_its_own_port(self):
      status = console.console_status()
      self.assertEqual(status["runtime"], "host")
      self.assertFalse(status["managed_by_docker"])
      self.assertEqual(status["port"], console.CONSOLE_PORT)
      self.assertEqual(status["pid"], os.getpid())

  def test_compose_does_not_define_console_service(self):
      with open("docker-compose.yml", encoding="utf-8") as handle:
          content = handle.read()
      self.assertNotRegex(content, r"(?m)^\s{2}console:\s*$")
  ```

  同时补充 `import os`。运行：

  ```bash
  python3 scripts/test_project_console.py
  ```

  预期新增测试因 `console_status` 尚不存在而失败。

- [x] **Step 2: 添加控制台自身状态函数**

  在 `scripts/project-console.py` 的状态采集工具区域新增：

  ```python
  def console_status():
      return {
          "runtime": "host",
          "managed_by_docker": False,
          "pid": os.getpid(),
          "port": CONSOLE_PORT,
          "url": "http://127.0.0.1:%d" % CONSOLE_PORT,
      }
  ```

  在 `collect_status()` 返回值中加入 `"console": console_status()`。不在 `main()`、`ensure_docker()` 或任何 action 中调用 Compose 启动控制台。

- [x] **Step 3: 运行独立性测试并确认 Docker 启动链路没有 console**

  运行：

  ```bash
  python3 scripts/test_project_console.py
  docker compose config --services
  ```

  预期：Python 测试通过；Compose 服务列表只包含项目服务，不包含 `console`。

## Task 2: 扩展为完整项目控制平面

- [x] **Step 1: 为 Colima/Docker 和服务 profile 写失败测试**

  在 `scripts/test_project_console.py` 新增：

  ```python
  def test_colima_stop_and_restart_are_valid_actions(self):
      self.assertTrue(console.is_valid_action("colima", "start"))
      self.assertTrue(console.is_valid_action("colima", "stop"))
      self.assertTrue(console.is_valid_action("colima", "restart"))

  def test_service_profile_is_applied_to_profile_services(self):
      with patch.object(console, "ensure_docker", return_value=True), \
           patch.object(console, "compose", return_value=(0, "ok", "")) as compose:
          self.assertTrue(console.compose_service_action("nginx", "start"))
      compose.assert_called_once_with("--profile", "production", "up", "-d", "nginx", timeout=180)
  ```

  预期：`is_valid_action` 和 profile 映射尚不存在，测试失败。

- [x] **Step 2: 建立服务和 profile 白名单**

  将服务定义拆成：

  ```python
  COMPOSE_SERVICES = ["postgres", "redis", "clamav", "backend", "celery", "celery_beat", "gotenberg"]
  PROFILE_SERVICES = {"frontend": "dev", "nginx": "production"}
  ALL_PROJECT_SERVICES = COMPOSE_SERVICES + list(PROFILE_SERVICES)
  SERVICE_TARGETS = set(ALL_PROJECT_SERVICES + ["all", "colima", "demo"])
  LOG_SERVICES = set(ALL_PROJECT_SERVICES + ["action"])
  ```

  新增：

  ```python
  def compose_service_args(service, *args):
      profile = PROFILE_SERVICES.get(service)
      return (("--profile", profile) if profile else ()) + tuple(args)

  def is_valid_action(target, action):
      if target not in SERVICE_TARGETS:
          return False
      if target == "demo":
          return action == "seed"
      if target == "colima":
          return action in ("start", "stop", "restart")
      return action in ("start", "stop", "restart")
  ```

  `compose_service_action()` 改为使用 `compose(*compose_service_args(service, ...))`，因此 `frontend` 和 `nginx` 分别走 `dev`、`production` profile。`collect_services()`、日志校验和前端状态应识别所有 `ALL_PROJECT_SERVICES`，但不把控制台伪装成 Compose 服务。

- [x] **Step 3: 增加 Colima 生命周期控制并保留安全边界**

  新增：

  ```python
  def colima_action(action):
      colima = shutil.which("colima")
      if not colima:
          _log("未找到 colima 命令")
          return False
      if action == "start":
          return ensure_docker()
      command = [colima, "stop"] if action == "stop" else [colima, "restart"]
      _log("执行：%s" % " ".join(command))
      rc, out, err = run(command, timeout=300)
      _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
      return rc == 0
  ```

  `do_action()` 的 `colima` 分支调用 `colima_action(action)`。前端必须对停止/重启 Docker 显示“会影响本机 Colima 中的其他容器”的确认文本；后端仍只接受白名单目标，不接受任意 shell 命令。

- [x] **Step 4: 让全项目操作明确控制项目而不控制控制台**

  保持 `all` 的语义为项目资源：启动时确保 Docker，然后启动后端 Compose 服务和 `FRONTEND_MODE` 指定的前端；停止/重启时只调用 `frontend_stop()`、`backend_stop()` 和项目服务，不调用 `colima stop`，也不调用 `kill_port(CONSOLE_PORT)`。

  对 `frontend` 使用 `compose_service_args("frontend", "up", "-d", "frontend")`；对 Docker 模式前端的状态和停止逻辑使用相同的 `dev` profile。对 `nginx` 保留独立 production profile 操作，避免开发模式“启动全部”误启动生产 Nginx。

- [x] **Step 5: 运行控制层测试**

  运行：

  ```bash
  python3 scripts/test_project_console.py
  ```

  预期：全部控制台单元测试通过；测试不得真的启动或停止 Docker/Colima。

## Task 3: 重做控制台信息层级和操作入口

- [x] **Step 1: 增加“控制台自身”状态卡**

  在 `scripts/console.html` 顶部增加独立状态说明：

  - “控制台进程：宿主机独立运行”
  - `127.0.0.1:8800`
  - 当前 PID
  - “Docker 启动/停止不会关闭控制台”

  使用 `/api/status.console` 数据渲染，不从服务列表中伪造一个 console 容器。

- [x] **Step 2: 重新命名全局操作并补齐 Docker 操作**

  将全局区域分为两个明确分组：

  1. “项目服务”——启动项目、停止项目、重启项目、初始化演示数据。
  2. “Docker / Colima”——启动 Docker、停止 Docker、重启 Docker。

  对停止/重启 Docker 增加明确的确认文案，禁止把“停止项目”误解为“停止控制台”。

- [x] **Step 3: 清理重复入口和状态文案**

  - 删除后端明细中重复的“启动”按钮。
  - 前端卡片明确显示当前是 Docker 前端还是宿主 Vite。
  - 后端服务明细包含 `nginx` 的 production profile 状态，但不将它计入默认开发后端健康数量，避免开发环境显示“缺一个服务”。
  - 日志选择器补充 `nginx`，仍保持服务名白名单。
  - 页面底部说明“控制台不受 Docker 项目启停影响”。

- [x] **Step 4: 在本机启动控制台做接口冒烟检查**

  运行：

  ```bash
  PORT=8810 python3 scripts/project-console.py
  curl -s http://127.0.0.1:8810/api/status
  curl -s http://127.0.0.1:8810/
  ```

  预期：状态 JSON 包含 `console.runtime=host`、`managed_by_docker=false`；HTML 包含独立控制台说明；终止 8810 进程后不影响 Docker/5173。

## Task 4: 更新启动文档和脚本提示

- [x] **Step 1: 明确双终端启动方式**

  在 `README.md` 和 `docs/项目运行说明.md` 中统一说明：

  ```bash
  # 终端 A：只启动独立控制台，不启动 Docker
  ./scripts/console.sh

  # 浏览器打开控制台
  open http://127.0.0.1:8800

  # 项目 Docker 服务由控制台按钮控制，或单独执行
  docker compose --profile dev up -d
  ```

  说明 `docker compose up/down` 不会启动/停止 8800 控制台；只有显式运行 `scripts/console.sh` 才会启动控制台。

- [x] **Step 2: 更新 shell 启动提示**

  `scripts/console.sh` 启动时打印：

  ```text
  灵溯项目控制台（宿主机独立进程）→ http://127.0.0.1:${PORT}
  控制台不会随 Docker 自动启动或停止；可在页面内控制 Docker/项目服务。
  ```

- [x] **Step 3: 检查文档没有把控制台写成 Docker 服务**

  运行：

  ```bash
  rg -n "console.*service|console.*容器|容器.*console" README.md docs docker-compose.yml
  ```

  预期无结果；控制台只以宿主机脚本方式出现。

## Task 5: 完整验证与交付

- [x] **Step 1: 运行控制台和配置验证**

  ```bash
  python3 scripts/test_project_console.py
  docker compose config --services
  git diff --check
  ```

- [x] **Step 2: 运行前端、后端已有回归测试**

  ```bash
  cd frontend && npm run test
  cd frontend && npm run build
  cd backend && python manage.py test apps.core.tests.test_ai_conversations apps.core.tests.test_ai_service apps.core.tests.test_agents apps.core.tests.test_project_lifecycle -v 1
  ```

  控制台改动不应引入前后端业务回归。

- [x] **Step 3: 记录最终边界**

  最终报告必须说明：

  - 控制台运行在宿主机，不是 Docker 服务。
  - 控制台可控制 Docker/Colima 和项目 Compose 服务。
  - “停止项目”不会关闭控制台；“停止 Docker”可能影响本机其他 Colima 容器，需要确认。
  - 控制台仍只监听 `127.0.0.1`，不接受任意 shell 命令。

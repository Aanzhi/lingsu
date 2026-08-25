#!/usr/bin/env python3
# 灵溯 · 项目控制台（本地开发用）
# 纯标准库实现，无第三方依赖。绑定 127.0.0.1，仅本机可访问。
# 提供：
#   GET  /                      控制台面板（console.html）
#   GET  /api/status            项目实时状态（后端栈容器 + 前端进程 + 健康检查）
#   POST /api/action            {target: service|frontend|all|colima|demo, action: start|stop|restart|seed, confirm?: bool}
#   GET  /api/logs?service=...&lines=N  查看服务日志
#   POST /api/checks            执行前后端完整验收
#   GET  /api/checks/latest      查看最近验收结果
#
# 用法：python3 scripts/project-console.py  （或 scripts/console.sh）
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE_ENV_FILE = os.environ.get("COMPOSE_ENV_FILE", os.path.join(ROOT, ".env"))
COMPOSE = ["docker", "compose"] + (["--env-file", COMPOSE_ENV_FILE] if os.path.isfile(COMPOSE_ENV_FILE) else []) + ["-p", os.environ.get("COMPOSE_PROJECT_NAME", "lingsu")]
FRONTEND_PORT = 5173
FRONTEND_LOG = "/tmp/lingsu-frontend.log"
FRONTEND_PID = "/tmp/lingsu-frontend.pid"
CONSOLE_PORT = int(os.environ.get("PORT", "8800"))
COMPOSE_SERVICES = ["postgres", "redis", "clamav", "backend", "celery", "celery_beat", "gotenberg"]
PROFILE_SERVICES = {"frontend": "dev", "nginx": "production"}
ALL_PROJECT_SERVICES = COMPOSE_SERVICES + list(PROFILE_SERVICES)
SERVICE_TARGETS = set(ALL_PROJECT_SERVICES + ["all", "colima", "demo"])
LOG_SERVICES = set(ALL_PROJECT_SERVICES + ["action"])
FRONTEND_MODE = os.environ.get("FRONTEND_MODE", "docker").lower()

# 从 .env 解析后端宿主端口（BACKEND_BIND=127.0.0.1:18001）
BACKEND_PORT = 18001
try:
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.strip()
            if line.startswith("BACKEND_BIND="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if ":" in val:
                    BACKEND_PORT = int(val.rsplit(":", 1)[1])
                break
except Exception:
    pass

_action_lock = threading.Lock()
_action_state = {
    "running": False,
    "target": None,
    "action": None,
    "started": None,
    "finished": None,
    "log": [],
    "result": None,
}
_checks_lock = threading.Lock()
_checks_state = {
    "running": False,
    "started": None,
    "finished": None,
    "results": [],
    "log": [],
}
_migration_cache = {"at": 0.0, "state": "blocked", "detail": "尚未检查"}
_migration_lock = threading.Lock()


# ---------- 工具函数 ----------
def run(cmd, timeout=180, check=False, cwd=None):
    try:
        p = subprocess.run(
            cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # noqa
        return 1, "", str(e)


def compose(*args, timeout=180):
    """Run a whitelisted docker compose command for this project."""
    return run(COMPOSE + list(args), timeout=timeout)


def compose_service_args(service, *args):
    """Add the profile required by a profile-scoped Compose service."""
    profile = PROFILE_SERVICES.get(service)
    prefix = ("--profile", profile) if profile else ()
    return tuple(prefix) + tuple(args)


def compose_all_profiles_args(*args):
    """Build a read-only Compose command that can see dev and production services."""
    profiles = []
    for profile in PROFILE_SERVICES.values():
        if profile not in profiles:
            profiles.append(profile)
    prefix = tuple(item for profile in profiles for item in ("--profile", profile))
    return prefix + tuple(args)


def is_valid_action(target, action):
    if target not in SERVICE_TARGETS:
        return False
    if target == "demo":
        return action == "seed"
    return action in ("start", "stop", "restart")


def project_python():
    """Pick a local Python that can actually import Django for project checks."""
    candidates = []
    if os.environ.get("PYTHON_BIN"):
        candidates.append(os.environ["PYTHON_BIN"])
    candidates.extend([
        shutil.which("python3.12"),
        "/opt/anaconda3/bin/python3.12",
        sys.executable,
    ])
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen or not os.path.exists(candidate):
            continue
        seen.add(candidate)
        rc, _, _ = run([candidate, "-c", "import django"], timeout=8)
        if rc == 0:
            return candidate
    return candidates[0] if candidates and candidates[0] else sys.executable


def http_ok(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status < 400
    except Exception:
        return False


def http_detail(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {"ok": response.status < 400, "status": response.status}
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def process_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def listener_pid(port):
    """Return the first process listening on a project port, if any."""
    try:
        output = subprocess.run(
            ["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.split()
        return int(output[0]) if output else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def process_command(pid):
    """Read a process command for display-only diagnostics."""
    if not pid:
        return ""
    try:
        return subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def read_pidfile():
    try:
        with open(FRONTEND_PID) as f:
            v = f.read().strip()
            return int(v) if v else None
    except Exception:
        return None


def write_pidfile(pid):
    try:
        with open(FRONTEND_PID, "w") as f:
            f.write(str(pid))
    except Exception:
        pass


def remove_pidfile():
    try:
        os.remove(FRONTEND_PID)
    except Exception:
        pass


def kill_port(port):
    """按端口杀掉监听进程（macOS / Linux）。"""
    try:
        pids = subprocess.run(
            ["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"],
            capture_output=True, text=True,
        ).stdout.split()
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass
        if pids:
            time.sleep(1.5)
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except Exception:
                    pass
    except Exception:
        pass


def kill_pid_tree(pid):
    try:
        pid = int(pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            pass
        time.sleep(1.2)
        if process_alive(pid):
            os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def tail_file(path, n=40):
    try:
        with open(path) as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except Exception:
        return "(无日志)"


def env_value(*names):
    """Read a non-secret environment value from the process or local env files."""
    values = dict(os.environ)
    for filename in (".env", ".env.integration"):
        try:
            with open(os.path.join(ROOT, filename), encoding="utf-8") as handle:
                for raw in handle:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        except OSError:
            continue
    for name in names:
        if values.get(name):
            return values[name]
    return ""


def safe_endpoint(value):
    """Avoid echoing credentials if an endpoint was accidentally configured with a query key."""
    return re.sub(r"([?&](?:api[_-]?key|token|secret)=)[^&]+", r"\1***", value or "", flags=re.IGNORECASE)


def check_item(key, label, state, detail="", **extra):
    item = {"key": key, "label": label, "state": state, "detail": detail}
    item.update(extra)
    return item


def service_health_map(services):
    return {item["service"]: item for item in services}


def console_status():
    """Return the control plane identity; this process is never a Compose service."""
    return {
        "runtime": "host",
        "managed_by_docker": False,
        "pid": os.getpid(),
        "port": CONSOLE_PORT,
        "url": "http://127.0.0.1:%d" % CONSOLE_PORT,
    }


# ---------- 状态采集 ----------
def docker_ready():
    """Docker 守护进程是否可用（colima 已启动且 docker 能连通）。"""
    if not shutil.which("docker"):
        return False
    rc, _, _ = run(["docker", "info"], timeout=8)
    return rc == 0


def frontend_status():
    running = http_ok("http://127.0.0.1:%d/" % FRONTEND_PORT, timeout=2)
    pidfile_pid = read_pidfile()
    listener = listener_pid(FRONTEND_PORT)

    # The pidfile belongs to a process started by this console and can become
    # stale after a terminal/process restart.  A current lsof result is
    # stronger evidence that something is serving 5173, so do not let a stale
    # pidfile hide an unmanaged host Vite process.
    managed_pid = pidfile_pid if pidfile_pid and process_alive(pidfile_pid) else None
    pid = managed_pid or listener
    alive = bool(managed_pid or listener)
    command = process_command(pid)
    is_host_vite = bool(
        listener
        and re.search(r"(?:\bvite\b|npm\s+(?:run\s+)?dev|pnpm\s+dev|yarn\s+dev)", command, re.IGNORECASE)
    )
    compose_state = compose_frontend_state()
    if running:
        state = "running"
    elif alive:
        state = "starting"
    else:
        state = "stopped"
    if compose_state == "running":
        mode = "docker"
        source = "Docker Compose frontend 容器"
    elif managed_pid:
        mode = "host"
        source = "宿主机 Vite（由控制台启动）"
    elif is_host_vite:
        mode = "host"
        source = "宿主机 Vite（未由控制台启动）"
    elif running:
        mode = "unknown"
        source = "5173 端口可访问，但进程来源未识别"
    else:
        mode = "stopped"
        source = "未运行"
    return {
        "running": running,
        "alive": alive,
        "pid": pid,
        "state": state,
        "port": FRONTEND_PORT,
        "log": tail_file(FRONTEND_LOG, 3),
        "mode": mode,
        "source": source,
        "compose_state": compose_state,
        "command": command,
    }


def compose_frontend_state():
    if not docker_ready():
        return "unavailable"
    rc, out, _ = compose(*compose_service_args("frontend", "ps", "--format", "json"), timeout=20)
    if rc != 0:
        return "unavailable"
    for line in out.splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("Service") == "frontend":
            return obj.get("State") or "unknown"
    return "not_created"


def collect_services():
    services = []
    rc, out, err = compose(*compose_all_profiles_args("ps", "--format", "json"), timeout=30)
    parsed = {}
    if rc == 0:
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            svc = obj.get("Service", "")
            if svc in ALL_PROJECT_SERVICES:
                ports = []
                for publisher in obj.get("Publishers") or []:
                    ports.append(
                        "%s:%s->%s/%s"
                        % (publisher.get("URL"), publisher.get("PublishedPort"), publisher.get("TargetPort"), publisher.get("Protocol"))
                    )
                parsed[svc] = {
                    "service": svc,
                    "name": obj.get("Name"),
                    "state": obj.get("State") or "unknown",
                    "health": obj.get("Health") or "",
                    "ports": ports,
                }
    for svc in ALL_PROJECT_SERVICES:
        services.append(parsed.get(svc, {
            "service": svc,
            "name": "%s-%s-1" % (COMPOSE[-1], svc),
            "state": "not_created" if rc == 0 else "unavailable",
            "health": "",
            "ports": [],
            "error": err.strip() if rc != 0 else "",
        }))
    return services


def collect_checks(services=None):
    services = services if services is not None else collect_services()
    service_map = service_health_map(services)
    docker_ok = docker_ready()
    backend_detail = http_detail("http://127.0.0.1:%d/api/health/" % BACKEND_PORT)
    frontend_detail = http_detail("http://127.0.0.1:%d/" % FRONTEND_PORT)
    checks = [
        check_item("docker", "Docker / Colima", "pass" if docker_ok else "fail", "Docker 守护进程可访问" if docker_ok else "Docker 未启动或 docker 命令不可用"),
        check_item("backend_api", "Django API", "pass" if backend_detail["ok"] else "fail", "HTTP %s" % backend_detail.get("status") if backend_detail["ok"] else "API 健康接口不可达", url="http://127.0.0.1:%d/api/health/" % BACKEND_PORT),
        check_item("frontend", "Vue 前端", "pass" if frontend_detail["ok"] else "fail", "HTTP %s" % frontend_detail.get("status") if frontend_detail["ok"] else "前端端口不可达", url="http://127.0.0.1:%d/" % FRONTEND_PORT),
    ]
    if docker_ok and service_map.get("backend", {}).get("state") == "running":
        with _migration_lock:
            fresh = time.time() - _migration_cache["at"] < 30
            migration = dict(_migration_cache)
        if not fresh:
            rc, _, err = compose("exec", "-T", "backend", "python", "manage.py", "migrate", "--check", timeout=25)
            migration = {"at": time.time(), "state": "pass" if rc == 0 else "fail", "detail": "迁移已同步" if rc == 0 else (err.strip() or "存在未应用迁移")}
            with _migration_lock:
                _migration_cache.update(migration)
        checks.append(check_item("migrations", "数据库迁移", migration["state"], migration["detail"]))
    else:
        checks.append(check_item("migrations", "数据库迁移", "blocked", "后端容器未运行，暂无法检查"))
    for svc, label in (("redis", "Redis 缓存"), ("celery", "Celery Worker"), ("celery_beat", "Celery Beat"), ("clamav", "ClamAV 文件扫描"), ("gotenberg", "Gotenberg 文档转换"), ("postgres", "PostgreSQL 数据库")):
        item = service_map.get(svc, {})
        running = item.get("state") == "running"
        healthy = running and (item.get("health") in ("", "healthy") or svc in ("celery", "celery_beat", "gotenberg"))
        checks.append(check_item(svc, label, "pass" if healthy else "fail", "容器运行中" if healthy else "容器未就绪"))
    has_ai_key = bool(env_value("OPENAI_API_KEY", "ARK_API_KEY"))
    ai_mode = "real" if has_ai_key else "demo"
    checks.append(check_item("ai", "AI 服务配置", "pass", "真实模型配置已设置" if has_ai_key else "演示模式：未配置模型密钥", mode=ai_mode, model=env_value("OPENAI_MODEL") or "gpt-4.1-mini", base_url=safe_endpoint(env_value("OPENAI_BASE_URL") or "默认兼容接口")))
    e2e = _e2e_state["last"]
    checks.append(check_item("e2e", "端到端登录", "pass" if e2e and e2e.get("ok") else ("pending" if not e2e else "fail"), "最近一次登录验收通过" if e2e and e2e.get("ok") else ("尚未执行" if not e2e else e2e.get("error") or "登录验收失败")))
    with _checks_lock:
        checks_run = dict(_checks_state)
    return checks, checks_run


def collect_status():
    services = collect_services()
    checks, checks_run = collect_checks(services)
    service_map = service_health_map(services)
    backend_health = any(item["key"] == "backend_api" and item["state"] == "pass" for item in checks)
    with _action_lock:
        action = dict(_action_state)
    e2e = _e2e_state["last"] or {"ok": False, "never_run": True, "error": "尚未跑过端到端验证"}
    running = sum(1 for name in COMPOSE_SERVICES if service_map.get(name, {}).get("state") == "running")
    return {
        "console": console_status(),
        "docker_ready": docker_ready(),
        "backend": {
            "services": services,
            "health": backend_health,
            "port": BACKEND_PORT,
            "count": len(COMPOSE_SERVICES),
            "running": running,
            "project_count": len(services),
        },
        "frontend": frontend_status(),
        "checks": checks,
        "checks_run": checks_run,
        "e2e": e2e,
        "action": action,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------- 操作执行 ----------
def _log(msg):
    with _action_lock:
        _action_state["log"].append("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))
        if len(_action_state["log"]) > 200:
            _action_state["log"] = _action_state["log"][-200:]


# ---------- 端到端验证（playwright 真浏览器登录） ----------
E2E_SCRIPT = os.path.join(ROOT, "scripts", "lingsu-e2e.mjs")
NODE_BIN = "/Users/anzhi/.workbuddy/binaries/node/versions/22.22.2/bin/node"
NODE_PATH_DIR = "/Users/anzhi/.workbuddy/binaries/node/workspace/node_modules"
E2E_RESULT_PATH = "/tmp/lingsu-e2e-result.json"
_e2e_lock = threading.Lock()
_e2e_state = {"running_hosts": set(), "last_run": {}, "last_by_host": {}, "last": None}


def e2e_login_check(force: bool = False, host: str = "127.0.0.1"):
    """用 playwright 真跑浏览器登录流程；30s 内复用上次结果（除非 force=True）。
    host='127.0.0.1' 或 'localhost'，分别验证两种访问路径。
    返回 dict：{ok, finalUrl, errorText, loginStatus, csrfTokenSent, consoleErrors, failedRequests, ts}"""
    with _e2e_lock:
        previous = _e2e_state["last_by_host"].get(host)
        last_run = _e2e_state["last_run"].get(host, 0)
        if not force and previous and (time.time() - last_run) < 30:
            cached = dict(previous)
            cached["cached"] = True
            return cached
        if host in _e2e_state["running_hosts"]:
            cached = dict(previous) if previous else {"ok": False, "error": "验证中…"}
            cached["cached"] = True
            cached["running"] = True
            return cached
        _e2e_state["running_hosts"].add(host)

    def _runner():
        try:
            env = os.environ.copy()
            node_bin = shutil.which("node") or NODE_BIN
            node_path = os.path.join(ROOT, "frontend", "node_modules")
            if os.path.isdir(node_path):
                env["NODE_PATH"] = node_path + (os.pathsep + NODE_PATH_DIR if os.path.isdir(NODE_PATH_DIR) else "")
            env["LS_FRONTEND_URL"] = "http://%s:5173/login" % host
            env["LS_E2E_USER"] = "demo-student"
            env["LS_E2E_PASS"] = "lingsu-demo-2026"
            rc = subprocess.run(
                [node_bin, E2E_SCRIPT],
                env=env,
                timeout=60,
                capture_output=True,
                text=True,
            )
            line = (rc.stdout or "").strip().splitlines()[-1] if rc.stdout else ""
            try:
                result = json.loads(line) if line else {"ok": False, "error": "empty result"}
            except Exception as e:
                result = {"ok": False, "error": "parse failed: %s; raw=%r" % (e, line[:200])}
            result["host"] = host
            result["ran_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with _e2e_lock:
                _e2e_state["last_by_host"][host] = result
                _e2e_state["last_run"][host] = time.time()
                _e2e_state["last"] = result
                _e2e_state["running_hosts"].discard(host)
        except Exception as e:
            with _e2e_lock:
                result = {"ok": False, "error": "subprocess failed: %s" % e, "host": host}
                _e2e_state["last_by_host"][host] = result
                _e2e_state["last_run"][host] = time.time()
                _e2e_state["last"] = result
                _e2e_state["running_hosts"].discard(host)

    threading.Thread(target=_runner, daemon=True).start()
    return {"ok": False, "running": True, "error": "验证进行中，约 5 秒后返回…", "host": host}


def backend_start():
    if not ensure_docker():
        return False
    _log("启动后端服务栈：docker compose up -d postgres redis clamav gotenberg backend celery celery_beat")
    rc, out, err = compose("up", "-d", *COMPOSE_SERVICES, timeout=240)
    _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
    if rc != 0:
        return False
    return wait_for_backend_ready(timeout=240)


def backend_stop():
    _log("停止后端栈：docker compose stop")
    rc, out, err = compose("stop", *COMPOSE_SERVICES, timeout=120)
    _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
    return rc == 0


def compose_service_action(service, action):
    if service not in ALL_PROJECT_SERVICES:
        _log("不支持的服务：%s" % service)
        return False
    if not ensure_docker():
        return False
    if action == "start":
        rc, out, err = compose(*compose_service_args(service, "up", "-d", service), timeout=180)
    elif action == "stop":
        rc, out, err = compose(*compose_service_args(service, "stop", service), timeout=120)
    else:
        rc, out, err = compose(*compose_service_args(service, "restart", service), timeout=120)
    _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
    return rc == 0 and (wait_for_backend_ready(timeout=120) if service == "backend" and action == "start" else True)


def frontend_start():
    if http_ok("http://127.0.0.1:%d/" % FRONTEND_PORT, timeout=2):
        _log("前端已在运行，跳过")
        return True
    if FRONTEND_MODE == "docker":
        if not ensure_docker():
            return False
        _log("启动前端容器：docker compose --profile dev up -d frontend")
        rc, out, err = compose(*compose_service_args("frontend", "up", "-d", "frontend"), timeout=240)
        _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
        if rc != 0:
            return False
        for _ in range(60):
            if http_ok("http://127.0.0.1:%d/" % FRONTEND_PORT, timeout=2):
                _log("Docker 前端已就绪 (5173)")
                return True
            time.sleep(2)
        _log("Docker 前端启动超时，请查看 frontend 日志")
        return False
    script = os.path.join(ROOT, "scripts", "dev-frontend.sh")
    _log("启动前端：bash scripts/dev-frontend.sh")
    with open(FRONTEND_LOG, "a") as lf:
        proc = subprocess.Popen(
            ["bash", script], cwd=ROOT, stdout=lf, stderr=lf, start_new_session=True
        )
    write_pidfile(proc.pid)
    # 轮询直到端口可访问
    for i in range(40):
        time.sleep(1)
        if http_ok("http://127.0.0.1:%d/" % FRONTEND_PORT, timeout=2):
            _log("前端已就绪 (5173)")
            return True
    _log("前端启动超时，请查看日志 /api/logs?service=frontend")
    return False


def frontend_stop():
    if compose_frontend_state() == "running":
        _log("停止前端容器：docker compose --profile dev stop frontend")
        rc, out, err = compose(*compose_service_args("frontend", "stop", "frontend"), timeout=120)
        _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
        return rc == 0
    pid = read_pidfile()
    if pid:
        _log("停止前端进程 pid=%s" % pid)
        kill_pid_tree(pid)
    _log("按端口 5173 清理监听进程")
    kill_port(FRONTEND_PORT)
    remove_pidfile()
    for i in range(10):
        time.sleep(1)
        if not http_ok("http://127.0.0.1:%d/" % FRONTEND_PORT, timeout=2):
            _log("前端已停止")
            return True
    _log("前端停止超时，可能仍有残留进程")
    return False


def ensure_docker():
    if docker_ready():
        return True
    colima = shutil.which("colima")
    if not colima:
        _log("Docker 未就绪，且未找到 colima 命令")
        return False
    _log("Docker 未就绪，启动 Colima：colima start")
    rc, out, err = run([colima, "start"], timeout=240)
    _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
    ready = rc == 0 and docker_ready()
    if not ready:
        _log("Colima 启动后 Docker 仍不可用")
    return ready


def colima_action(action):
    """Control the host Docker runtime without touching the console process."""
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


def wait_for_backend_ready(timeout=240):
    deadline = time.time() + timeout
    logged = 0
    while time.time() < deadline:
        if http_ok("http://127.0.0.1:%d/api/health/" % BACKEND_PORT, timeout=3):
            services = service_health_map(collect_services())
            required = ["postgres", "redis", "clamav", "backend", "celery", "celery_beat", "gotenberg"]
            if all(services.get(name, {}).get("state") == "running" for name in required):
                _log("后端 API 与依赖服务已就绪")
                return True
        if time.time() - logged > 10:
            _log("等待后端健康检查与依赖服务就绪…")
            logged = time.time()
        time.sleep(3)
    _log("后端服务等待超时，请查看服务日志")
    return False


def seed_demo_data():
    if not ensure_docker():
        return False
    if not wait_for_backend_ready(timeout=120):
        return False
    _log("初始化演示数据：seed_demo")
    rc, out, err = compose("exec", "-T", "backend", "python", "manage.py", "seed_demo", timeout=180)
    _log(out.strip() or err.strip() or "done (rc=%d)" % rc)
    return rc == 0


def do_action(target, action):
    with _action_lock:
        if _action_state["running"]:
            return False, "已有操作进行中，请稍候"
        _action_state.update(
            {
                "running": True,
                "target": target,
                "action": action,
                "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "finished": None,
                "log": [],
                "result": None,
            }
        )

    def worker():
        try:
            success = False
            if target == "backend":
                if action == "start":
                    success = backend_start()
                elif action == "stop":
                    success = backend_stop()
                elif action == "restart":
                    first = backend_stop()
                    time.sleep(2)
                    success = backend_start() and first
            elif target == "frontend":
                if action == "start":
                    success = frontend_start()
                elif action == "stop":
                    success = frontend_stop()
                elif action == "restart":
                    first = frontend_stop()
                    time.sleep(2)
                    success = frontend_start() and first
            elif target in ALL_PROJECT_SERVICES:
                success = compose_service_action(target, action)
            elif target == "demo":
                success = action == "seed" and seed_demo_data()
            elif target == "all":
                if action == "start":
                    backend_ok = backend_start()
                    time.sleep(3)
                    success = frontend_start() and backend_ok
                elif action == "stop":
                    success = frontend_stop() and backend_stop()
                elif action == "restart":
                    front_ok = frontend_stop()
                    back_ok = backend_stop()
                    time.sleep(3)
                    backend_started = backend_start()
                    time.sleep(3)
                    success = frontend_start() and front_ok and back_ok and backend_started
            elif target == "colima":
                success = colima_action(action)
            with _action_lock:
                _action_state["result"] = "ok" if success else "error"
        except Exception as e:  # noqa
            _log("ERROR: %s" % e)
            with _action_lock:
                _action_state["result"] = "error: %s" % e
        finally:
            with _action_lock:
                _action_state["running"] = False
                _action_state["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return True, "已接受操作：%s/%s" % (target, action)


def _check_log(message):
    with _checks_lock:
        _checks_state["log"].append("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), message))
        _checks_state["log"] = _checks_state["log"][-200:]


def run_full_checks():
    with _checks_lock:
        if _checks_state["running"]:
            return False, "已有验收正在执行"
        _checks_state.update({"running": True, "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "finished": None, "results": [], "log": []})

    def worker():
        results = []
        commands = [
            ("frontend_build", "前端构建", ["npm", "run", "build"], os.path.join(ROOT, "frontend"), 240),
            ("frontend_tests", "前端测试", ["npm", "run", "test", "--", "--run"], os.path.join(ROOT, "frontend"), 240),
            ("backend_tests", "后端测试", [project_python(), "manage.py", "test", "apps.core"], os.path.join(ROOT, "backend"), 240),
        ]
        for key, label, command, cwd, timeout in commands:
            _check_log("开始：%s" % label)
            started = time.time()
            try:
                rc, out, err = run(command, timeout=timeout, check=False, cwd=cwd)
                combined = (out or "") + ("\n" + err if err else "")
                result = {"key": key, "label": label, "state": "pass" if rc == 0 else "fail", "returncode": rc, "duration": round(time.time() - started, 1), "output": combined[-4000:]}
                _check_log("完成：%s (%s)" % (label, "通过" if rc == 0 else "失败"))
            except Exception as exc:
                result = {"key": key, "label": label, "state": "fail", "returncode": 1, "duration": round(time.time() - started, 1), "output": str(exc)}
                _check_log("失败：%s · %s" % (label, exc))
            results.append(result)
        # 真实浏览器登录验收：两个本机入口并行验证，避免只验证某一个 Host。
        _check_log("开始：真实浏览器登录验收")
        e2e_started = time.time()
        for host in ("127.0.0.1", "localhost"):
            e2e_login_check(force=True, host=host)
        for _ in range(45):
            with _e2e_lock:
                finished = [_e2e_state["last_by_host"].get(host) for host in ("127.0.0.1", "localhost")]
            if all(item and not item.get("running") for item in finished):
                break
            time.sleep(2)
        with _e2e_lock:
            e2e_results = [_e2e_state["last_by_host"].get(host) for host in ("127.0.0.1", "localhost")]
        for host, result in zip(("127.0.0.1", "localhost"), e2e_results):
            passed = bool(result and result.get("ok"))
            results.append({"key": "e2e_%s" % host.replace(".", "_"), "label": "登录验收 %s" % host, "state": "pass" if passed else "fail", "returncode": 0 if passed else 1, "duration": round(time.time() - e2e_started, 1), "output": json.dumps(result or {"error": "no result"}, ensure_ascii=False)})
        _check_log("完成：真实浏览器登录验收 (%s)" % ("通过" if all(item and item.get("ok") for item in e2e_results) else "失败"))
        with _checks_lock:
            _checks_state["results"] = results
            _checks_state["running"] = False
            _checks_state["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    threading.Thread(target=worker, daemon=True).start()
    return True, "完整验收已开始"


# ---------- HTTP 处理 ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静默访问日志
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            try:
                with open(os.path.join(ROOT, "scripts", "console.html"), encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except Exception as e:
                self._send(500, "控制台页面缺失: %s" % e)
            return
        if parsed.path == "/api/status":
            self._send(200, collect_status())
            return
        if parsed.path == "/api/e2e":
            q = parse_qs(parsed.query)
            force = (q.get("force") or ["0"])[0] == "1"
            host = (q.get("host") or ["127.0.0.1"])[0]
            if host not in ("127.0.0.1", "localhost"):
                self._send(400, {"ok": False, "error": "host 不在白名单"})
                return
            self._send(200, e2e_login_check(force=force, host=host))
            return
        if parsed.path == "/api/checks/latest":
            with _checks_lock:
                self._send(200, dict(_checks_state))
            return
        if parsed.path == "/api/logs":
            q = parse_qs(parsed.query)
            service = (q.get("service") or ["backend"])[0]
            try:
                lines = max(1, min(int((q.get("lines") or ["50"])[0]), 200))
            except ValueError:
                lines = 50
            if service not in LOG_SERVICES:
                self._send(400, {"ok": False, "error": "日志服务不在白名单"})
                return
            if service == "frontend":
                if compose_frontend_state() == "running":
                    _, out, err = compose(*compose_service_args(service, "logs", "--tail", str(lines), service), timeout=30)
                    text = out or err or "(无输出)"
                else:
                    text = tail_file(FRONTEND_LOG, lines)
            elif service == "action":
                with _action_lock:
                    text = "\n".join(_action_state["log"][-lines:]) or "(暂无操作记录)"
            else:
                rc, out, err = compose(*compose_service_args(service, "logs", "--tail", str(lines), service), timeout=30)
                text = out or err or "(无输出)"
            self._send(200, text, "text/plain; charset=utf-8")
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/action":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b"{}"
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            target = data.get("target")
            action = data.get("action")
            valid = is_valid_action(target, action)
            if not valid:
                self._send(400, {"ok": False, "msg": "参数不合法"})
                return
            if (action in ("stop", "restart") or target == "demo") and data.get("confirm") is not True:
                if target == "demo":
                    msg = "初始化演示数据需要 confirm=true"
                elif target == "colima":
                    msg = "停止或重启 Docker/Colima 需要 confirm=true"
                else:
                    msg = "停止或重启操作需要 confirm=true"
                self._send(400, {"ok": False, "msg": msg})
                return
            ok, msg = do_action(target, action)
            self._send(200 if ok else 409, {"ok": ok, "msg": msg})
            return
        if parsed.path == "/api/checks":
            ok, msg = run_full_checks()
            self._send(202 if ok else 409, {"ok": ok, "msg": msg})
            return
        self._send(404, {"error": "not found"})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", CONSOLE_PORT), Handler)
    print("灵溯项目控制台已启动（宿主机独立进程）: http://127.0.0.1:%d" % CONSOLE_PORT)
    print("控制台不会随 Docker 自动启动或停止；可在页面内控制 Docker / Colima 和项目服务。")
    print("后端端口 %d · 前端端口 %d" % (BACKEND_PORT, FRONTEND_PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()

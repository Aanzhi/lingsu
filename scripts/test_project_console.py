import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen


SPEC = importlib.util.spec_from_file_location("project_console", "scripts/project-console.py")
console = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(console)


class ProjectConsoleTests(unittest.TestCase):
    def test_console_uses_shared_desktop_workspace_geometry(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn("--brand:#3d6c6a", html)
        self.assertIn("--brand-deep:#285250", html)
        self.assertIn("grid-template-columns:232px minmax(0,1fr)", html)
        self.assertIn('class="console-sidebar"', html)
        self.assertIn('class="console-main"', html)

    def test_console_uses_demo_b_management_primitives(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn('class="console-metric-grid"', html)
        self.assertIn('class="console-two-col"', html)
        self.assertIn('console-card console-control-card', html)
        self.assertIn('查看本机服务状态，按需启停项目资源、执行健康验收和读取日志。', html)
        self.assertNotIn('查看运行状态', html)
        self.assertIn('--brand:#3d6c6a', html)
        self.assertIn('max-height:150px', html)
        self.assertIn('class="startup-flow__step-action ghost" id="e2e-btn"', html)
        self.assertEqual(html.count('id="e2e-btn"'), 1)

    def test_console_does_not_render_role_or_sidebar_tip_labels(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            html = handle.read()
        self.assertNotIn('class="console-role-chip"', html)
        self.assertNotIn('class="console-sidebar-label"', html)
        self.assertNotIn('class="console-sidebar-note"', html)
        self.assertNotIn('项目控制台 · 概览', html)

    def test_console_is_host_process_and_has_its_own_port(self):
        status = console.console_status()
        self.assertEqual(status["runtime"], "host")
        self.assertFalse(status["managed_by_docker"])
        self.assertEqual(status["port"], console.CONSOLE_PORT)
        self.assertEqual(status["pid"], os.getpid())

    def test_compose_does_not_define_console_service(self):
        with open("docker-compose.yml", encoding="utf-8") as handle:
            content = handle.read()
        self.assertNotRegex(content, re.compile(r"^\s{2}console:\s*$", re.MULTILINE))

    def test_clamav_is_optional_and_backend_does_not_wait_for_scanner(self):
        with open("docker-compose.yml", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn('profiles: ["scanner"]', content)
        self.assertIn("FILE_SCAN_REQUIRED: ${FILE_SCAN_REQUIRED:-1}", content)
        self.assertIn("CLAMAV_HOST: ${CLAMAV_HOST-clamav}", content)
        backend_block = content.split("\n  celery:\n", 1)[0]
        self.assertNotIn("      clamav:\n        condition: service_healthy", backend_block)

    def test_heavy_async_and_document_services_are_opt_in_profiles(self):
        with open("docker-compose.yml", encoding="utf-8") as handle:
            content = handle.read()
        self.assertRegex(content, r"(?ms)^  celery:\n.*?profiles: \[\"async\"\]")
        self.assertRegex(content, r"(?ms)^  celery_beat:\n.*?profiles: \[\"async\"\]")
        self.assertRegex(content, r"(?ms)^  gotenberg:\n.*?profiles: \[\"documents\"\]")
        self.assertIn("--workers ${GUNICORN_WORKERS:-1}", content)

    def test_console_core_mode_excludes_scanner_async_and_documents(self):
        probe = (
            "import importlib.util; "
            "spec=importlib.util.spec_from_file_location('console', 'scripts/project-console.py'); "
            "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
            "print(','.join(module.COMPOSE_SERVICES))"
        )
        env = os.environ.copy()
        env.update({
            "CLAMAV_ENABLED": "0",
            "CELERY_ENABLED": "0",
            "DOCUMENT_CONVERTER_ENABLED": "0",
            "COMPOSE_ENV_FILE": "/tmp/lingsu-test-env-does-not-exist",
        })
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "postgres,redis,backend")

    def test_console_adds_profiles_when_starting_optional_services(self):
        with patch.object(console, "COMPOSE_SERVICES", ["postgres", "redis", "backend", "celery", "gotenberg"]), \
             patch.object(console, "PROFILE_SERVICES", {"celery": "async", "gotenberg": "documents"}):
            args = console.compose_enabled_service_args("up", "-d", *console.COMPOSE_SERVICES)
        self.assertEqual(
            args,
            ("--profile", "async", "--profile", "documents", "up", "-d", "postgres", "redis", "backend", "celery", "gotenberg"),
        )

    def test_console_omits_clamav_when_scanner_is_disabled(self):
        probe = (
            "import importlib.util; "
            "spec=importlib.util.spec_from_file_location('console', 'scripts/project-console.py'); "
            "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
            "print(','.join(module.COMPOSE_SERVICES))"
        )
        env = os.environ.copy()
        env["CLAMAV_ENABLED"] = "0"
        env["COMPOSE_ENV_FILE"] = "/tmp/lingsu-test-env-does-not-exist"
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertNotIn("clamav", result.stdout.split(","))

    def test_console_html_has_one_backend_stack_start_button(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            content = handle.read()
        self.assertEqual(content.count('data-target="backend" data-action="start"'), 1)

    def test_console_explains_docker_before_project_services(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("推荐启动顺序", content)
        self.assertIn("1. 启动 Docker / Colima", content)
        self.assertIn("2. 启动项目服务", content)
        self.assertIn("启动项目会自动检测并启动 Docker", content)

    def test_console_mobile_layout_stacks_navigation_and_controls(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn(".console-shell{grid-template-columns:1fr}", content)
        self.assertIn(".console-sidebar{height:auto;position:static", content)
        self.assertIn(".console-two-col{grid-template-columns:1fr}", content)
        self.assertIn(".startup-flow__steps{grid-template-columns:repeat(2,minmax(0,1fr))}", content)

    def test_console_uses_guided_startup_flow_and_unique_primary_actions(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn('class="startup-flow"', content)
        for step in ("flow-step-docker", "flow-step-project", "flow-step-checks", "flow-step-e2e"):
            self.assertIn(f'id="{step}"', content)
        self.assertIn('class="advanced-controls"', content)
        self.assertEqual(content.count('id="checks-btn"'), 1)
        self.assertEqual(content.count('id="e2e-btn"'), 1)
        self.assertEqual(content.count('data-target="all" data-action="start"'), 1)
        self.assertEqual(content.count('data-target="colima" data-action="start"'), 1)

    def test_console_does_not_start_browser_login_until_user_requests_step_four(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            content = handle.read()
        self.assertNotIn("fetchE2E('127.0.0.1');\nfetchE2E('localhost');", content)
        self.assertNotIn("setInterval(() => fetchE2E('127.0.0.1'), 30000)", content)
        self.assertNotIn("setInterval(() => fetchE2E('localhost'), 30000)", content)

    def test_console_html_does_not_render_persistent_bottom_tip(self):
        with open("scripts/console.html", encoding="utf-8") as handle:
            content = handle.read()
        self.assertNotIn("控制台仅绑定 127.0.0.1", content)

    def test_colima_stop_and_restart_are_valid_actions(self):
        self.assertTrue(console.is_valid_action("colima", "start"))
        self.assertTrue(console.is_valid_action("colima", "stop"))
        self.assertTrue(console.is_valid_action("colima", "restart"))

    def test_frontend_status_identifies_unmanaged_host_vite(self):
        with patch.object(console, "http_ok", return_value=True), \
             patch.object(console, "read_pidfile", return_value=None), \
             patch.object(console, "listener_pid", return_value=61425), \
             patch.object(console, "process_command", return_value="node vite"), \
             patch.object(console, "compose_frontend_state", return_value="not_created"):
            status = console.frontend_status()
        self.assertEqual(status["mode"], "host")
        self.assertEqual(status["pid"], 61425)
        self.assertEqual(status["source"], "宿主机 Vite（未由控制台启动）")

    def test_service_profile_is_applied_to_profile_services(self):
        with patch.object(console, "ensure_docker", return_value=True), \
             patch.object(console, "compose", return_value=(0, "ok", "")) as compose:
            self.assertTrue(console.compose_service_action("nginx", "start"))
        compose.assert_called_once_with("--profile", "production", "up", "-d", "nginx", timeout=180)

    def test_production_frontend_start_uses_nginx_and_port_80(self):
        with patch.object(console, "COMPOSE_PROFILE", "production"), \
             patch.object(console, "ACTIVE_FRONTEND_SERVICE", "nginx"), \
             patch.object(console, "FRONTEND_PORT", 80), \
             patch.object(console, "FRONTEND_MODE", "docker"), \
             patch.object(console, "http_ok", side_effect=[False, True]), \
             patch.object(console, "ensure_docker", return_value=True), \
             patch.object(console, "compose", return_value=(0, "ok", "")) as compose, \
             patch.object(console.time, "sleep"):
            self.assertTrue(console.frontend_start())
        compose.assert_called_once_with("--profile", "production", "up", "-d", "nginx", timeout=240)

    def test_production_frontend_stop_does_not_kill_unrelated_port_80_process(self):
        with patch.object(console, "COMPOSE_PROFILE", "production"), \
             patch.object(console, "ACTIVE_FRONTEND_SERVICE", "nginx"), \
             patch.object(console, "compose_frontend_state", return_value="not_created"), \
             patch.object(console, "kill_port") as kill_port:
            self.assertTrue(console.frontend_stop())
        kill_port.assert_not_called()

    def test_collect_services_keeps_expected_services_when_compose_is_empty(self):
        with patch.object(console, "compose", return_value=(0, "", "")):
            services = console.collect_services()
        self.assertEqual([item["service"] for item in services], console.ALL_PROJECT_SERVICES)
        self.assertTrue(all(item["state"] == "not_created" for item in services))

    def test_collect_checks_marks_ai_as_demo_without_secret(self):
        services = [{"service": name, "state": "running", "health": "healthy", "ports": []} for name in console.COMPOSE_SERVICES]
        with patch.object(console, "docker_ready", return_value=True), \
             patch.object(console, "http_detail", return_value={"ok": True, "status": 200}), \
             patch.object(console, "compose", return_value=(0, "", "")), \
             patch.object(console, "env_value", side_effect=lambda *names: "" if "OPENAI_API_KEY" in names or "ARK_API_KEY" in names else ""):
            checks, _ = console.collect_checks(services)
        ai = next(item for item in checks if item["key"] == "ai")
        self.assertEqual(ai["state"], "pass")
        self.assertEqual(ai["mode"], "demo")

    def test_action_endpoint_rejects_stop_without_confirmation(self):
        server = console.ThreadingHTTPServer(("127.0.0.1", 0), console.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(
                "http://127.0.0.1:%d/api/action" % server.server_port,
                data=json.dumps({"target": "all", "action": "stop"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(Exception) as ctx:
                urlopen(request, timeout=3)
            self.assertIn("400", str(ctx.exception))
        finally:
            server.shutdown()
            server.server_close()

    def test_logs_endpoint_rejects_unknown_service(self):
        server = console.ThreadingHTTPServer(("127.0.0.1", 0), console.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(Exception) as ctx:
                urlopen("http://127.0.0.1:%d/api/logs?service=rm+-rf" % server.server_port, timeout=3)
            self.assertIn("400", str(ctx.exception))
        finally:
            server.shutdown()
            server.server_close()

    def test_safe_endpoint_masks_query_credentials(self):
        self.assertEqual(console.safe_endpoint("https://example.test/v1?api_key=secret&x=1"), "https://example.test/v1?api_key=***&x=1")


if __name__ == "__main__":
    unittest.main()

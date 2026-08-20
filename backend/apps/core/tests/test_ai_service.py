from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import AIGenerationLog, Account, Project, School
from apps.core.tasks import generate_ai_response


class AIServiceTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="AI 学校", ai_quota=1)
        self.student = Account.objects.create_user(username="ai-student", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="ai-teacher", school=self.school, role="teacher")
        self.other = Account.objects.create_user(username="ai-other", school=self.school, role="student")
        self.project = Project.objects.create(
            school=self.school, title="雨水研究", problem="如何提升回收效率", plan="测量与对照",
            leader=self.student, primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")

    def client_for(self, user):
        client = APIClient(); client.force_authenticate(user); return client

    @override_settings(OPENAI_API_KEY="")
    def test_school_user_can_read_safe_ai_availability_without_service_secrets(self):
        response = self.client_for(self.student).get("/api/ai-availability/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "demo_mode", "remaining_quota": 1})

    @override_settings(OPENAI_API_KEY="", CELERY_TASK_ALWAYS_EAGER=False)
    @patch("apps.core.views.generate_ai_response.delay")
    def test_ai_request_queues_demo_generation_when_service_key_is_not_configured(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.student).post("/api/ai-logs/", {
                "project": self.project.id, "purpose": "问题梳理", "prompt": "帮我明确变量",
                "context_scope": {"project_basics": True},
            }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "queued")
        self.assertEqual(AIGenerationLog.objects.count(), 1)
        delay.assert_called_once_with(response.data["id"])

    @override_settings(OPENAI_API_KEY="configured", CELERY_TASK_ALWAYS_EAGER=False)
    @patch("apps.core.views.generate_ai_response.delay")
    def test_ai_request_is_audited_and_monthly_school_quota_is_enforced(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.client_for(self.student).post("/api/ai-logs/", {
                "project": self.project.id, "purpose": "问题梳理", "prompt": "帮我明确变量",
                "context_scope": {"project_basics": True},
            }, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["status"], "queued")
        delay.assert_called_once_with(first.data["id"])
        second = self.client_for(self.teacher).post("/api/ai-logs/", {
            "project": self.project.id, "purpose": "审核风险检查", "prompt": "检查证据",
        }, format="json")
        self.assertEqual(second.status_code, 429)

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.tasks.OpenAI")
    def test_worker_saves_model_output_without_changing_project_workflow(self, client_class):
        client_class.return_value.responses.create.return_value.output_text = "建议明确自变量与对照组。"
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, purpose="问题梳理", prompt="帮我明确变量",
            context_scope={"project_basics": True}, status=AIGenerationLog.Status.QUEUED,
        )
        original_status = self.project.status
        result = generate_ai_response(record.id)
        record.refresh_from_db(); self.project.refresh_from_db()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(record.output, "建议明确自变量与对照组。")
        self.assertEqual(record.status, AIGenerationLog.Status.COMPLETED)
        self.assertEqual(record.artifact_payload["draft"], record.output)
        self.assertEqual(record.artifact_payload["content"], record.output)
        self.assertTrue(record.artifact_payload["title"])
        self.assertTrue(record.artifact_payload["next_action"])
        self.assertTrue(record.verification_items)
        self.assertEqual(self.project.status, original_status)

    @override_settings(OPENAI_API_KEY="configured", OPENAI_BASE_URL="https://example.test/v1")
    @patch("apps.core.tasks.OpenAI")
    def test_worker_passes_optional_base_url_to_openai_client(self, client_class):
        client_class.return_value.responses.create.return_value.output_text = "测试回复"
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, purpose="问题梳理", prompt="帮我明确变量",
            context_scope={"project_basics": True}, status=AIGenerationLog.Status.QUEUED,
        )

        generate_ai_response(record.id)

        client_class.assert_called_once_with(api_key="configured", base_url="https://example.test/v1")

    @override_settings(OPENAI_API_KEY="")
    def test_demo_worker_populates_auditable_artifact_fields_without_replacing_raw_output(self):
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, purpose="问题梳理", prompt="帮我明确变量",
            context_scope={"project_basics": True}, status=AIGenerationLog.Status.QUEUED,
        )
        generate_ai_response(record.id)
        record.refresh_from_db()
        self.assertEqual(record.status, AIGenerationLog.Status.COMPLETED)
        self.assertIn("演示模式", record.output)
        self.assertEqual(record.artifact_payload["content"], record.output)
        self.assertTrue(record.verification_items)

    @override_settings(OPENAI_API_KEY="configured")
    def test_non_member_cannot_use_or_read_project_ai_records(self):
        create = self.client_for(self.other).post("/api/ai-logs/", {
            "project": self.project.id, "purpose": "问题梳理", "prompt": "越权读取",
        }, format="json")
        self.assertEqual(create.status_code, 403)
        self.assertEqual(self.client_for(self.other).get("/api/ai-logs/").data, [])

    def test_guiding_teacher_can_read_student_ai_history_for_their_project(self):
        record = AIGenerationLog.objects.create(
            project=self.project,
            actor=self.student,
            purpose="问题梳理",
            prompt="请协助梳理研究变量",
            context_scope={"project_basics": True},
            output="建议增加对照组。",
            status=AIGenerationLog.Status.COMPLETED,
        )

        response = self.client_for(self.teacher).get("/api/ai-logs/", {"project": self.project.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [record.id])
        self.assertEqual(response.data[0]["actor"], self.student.id)

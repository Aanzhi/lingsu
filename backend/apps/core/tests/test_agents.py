from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import Account, AgentTemplate, AIGenerationLog, Project, ProjectTask, Material, MaterialRevision, School
from apps.core.tasks import DEFAULT_AI_INSTRUCTION, generate_ai_response


class AgentTemplateModelTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="学校A")
        self.school_b = School.objects.create(name="学校B")
        self.global_tmpl = AgentTemplate.objects.create(
            key="opening-report", name="开题报告助手", role="student",
            system_instruction="全局开题", prompt_template="题目：{project_title}", is_active=True,
        )
        AgentTemplate.objects.create(
            key="opening-report", name="校本开题", role="student",
            system_instruction="校本开题", prompt_template="题目：{project_title}",
            is_active=True, school=self.school_a,
        )

    def test_unique_constraint_on_key_and_school(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            AgentTemplate.objects.create(
                key="opening-report", name="重复", role="student",
                system_instruction="x", prompt_template="y", school=None,
            )

    def test_resolve_prefers_school_template_then_global(self):
        self.assertEqual(
            AgentTemplate.resolve("opening-report", self.school_a, "student").system_instruction,
            "校本开题",
        )
        # 学校 B 没有校本覆盖，回退全局
        self.assertEqual(
            AgentTemplate.resolve("opening-report", self.school_b, "student").system_instruction,
            "全局开题",
        )

    def test_resolve_filters_by_role_and_inactive(self):
        self.assertIsNone(AgentTemplate.resolve("opening-report", self.school_b, "teacher"))
        self.global_tmpl.is_active = False
        self.global_tmpl.save()
        self.assertIsNone(AgentTemplate.resolve("opening-report", self.school_b, "student"))


class AgentTemplateViewSetTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="模板学校")
        self.student = Account.objects.create_user(username="t-student", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="t-teacher", school=self.school, role="teacher")
        self.admin = Account.objects.create_user(username="t-admin", school=self.school, role="platform_admin")
        self.student_tmpl = AgentTemplate.objects.create(
            key="s1", name="学生模板", role="student", system_instruction="S", prompt_template="s", is_active=True,
        )
        self.teacher_tmpl = AgentTemplate.objects.create(
            key="t1", name="教师模板", role="teacher", system_instruction="T", prompt_template="t", is_active=True,
        )
        self.inactive = AgentTemplate.objects.create(
            key="i1", name="停用模板", role="student", system_instruction="I", prompt_template="i", is_active=False,
        )

    def client_for(self, user):
        client = APIClient(); client.force_authenticate(user); return client

    def test_student_sees_only_active_student_templates(self):
        data = self.client_for(self.student).get("/api/ai-agents/").data
        keys = {item["key"] for item in data}
        self.assertIn("s1", keys)
        self.assertNotIn("t1", keys)
        self.assertNotIn("i1", keys)

    def test_teacher_sees_only_active_teacher_templates(self):
        data = self.client_for(self.teacher).get("/api/ai-agents/").data
        keys = {item["key"] for item in data}
        self.assertIn("t1", keys)
        self.assertNotIn("s1", keys)
        self.assertNotIn("i1", keys)

    def test_admin_sees_all_including_inactive(self):
        data = self.client_for(self.admin).get("/api/ai-agents/").data
        keys = {item["key"] for item in data}
        self.assertIn("s1", keys)
        self.assertIn("t1", keys)
        self.assertIn("i1", keys)

    def test_student_cannot_create_template(self):
        response = self.client_for(self.student).post("/api/ai-agents/", {
            "key": "x", "name": "X", "role": "student",
            "system_instruction": "s", "prompt_template": "p",
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_teacher_creates_school_scoped_non_both_template(self):
        response = self.client_for(self.teacher).post("/api/ai-agents/", {
            "key": "school-t", "name": "校本教师模板", "role": "teacher",
            "system_instruction": "s", "prompt_template": "p",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        obj = AgentTemplate.objects.get(key="school-t")
        self.assertEqual(obj.school_id, self.school.id)
        self.assertEqual(obj.role, "teacher")

    def test_teacher_cannot_create_both_template(self):
        response = self.client_for(self.teacher).post("/api/ai-agents/", {
            "key": "both-t", "name": "B", "role": "both",
            "system_instruction": "s", "prompt_template": "p",
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_admin_creates_global_template(self):
        response = self.client_for(self.admin).post("/api/ai-agents/", {
            "key": "global-t", "name": "全局", "role": "student",
            "system_instruction": "s", "prompt_template": "p",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        obj = AgentTemplate.objects.get(key="global-t")
        self.assertIsNone(obj.school)

    def test_teacher_cannot_edit_global_template(self):
        # teacher_tmpl 角色为 teacher 且 school=None，教师可见但归属为空，应被拒编辑
        response = self.client_for(self.teacher).patch(f"/api/ai-agents/{self.teacher_tmpl.id}/", {
            "name": "被改",
        }, format="json")
        self.assertEqual(response.status_code, 403)


class AIGenerationAgentInstructionTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="指令学校", ai_quota=10)
        self.student = Account.objects.create_user(username="g-student", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="g-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            school=self.school, title="雨水研究", problem="如何提升回收效率", plan="测量与对照",
            leader=self.student, primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        self.agent = AgentTemplate.objects.create(
            key="opening-report", name="开题报告助手", role="student",
            system_instruction="【专属开题教练】只给建议。", prompt_template="题目：{project_title}", is_active=True,
        )

    def client_for(self, user):
        from rest_framework.test import APIClient
        client = APIClient(); client.force_authenticate(user); return client

    @override_settings(OPENAI_API_KEY="configured")
    def test_agent_system_instruction_is_used(self):
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, purpose="", agent_key="opening-report",
            prompt="题目：校园雨水", context_scope={"project_basics": True}, status=AIGenerationLog.Status.QUEUED,
        )
        with patch("apps.core.tasks.OpenAI") as client_class:
            client_class.return_value.responses.create.return_value.output_text = "ok"
            generate_ai_response(record.id)
            kwargs = client_class.return_value.responses.create.call_args.kwargs
        self.assertEqual(kwargs["instructions"], "【专属开题教练】只给建议。")

    @override_settings(OPENAI_API_KEY="configured")
    def test_fallback_to_default_instruction_without_agent_key(self):
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, purpose="问题梳理",
            prompt="帮我明确变量", context_scope={"project_basics": True}, status=AIGenerationLog.Status.QUEUED,
        )
        with patch("apps.core.tasks.OpenAI") as client_class:
            client_class.return_value.responses.create.return_value.output_text = "ok"
            generate_ai_response(record.id)
            kwargs = client_class.return_value.responses.create.call_args.kwargs
        self.assertEqual(kwargs["instructions"], DEFAULT_AI_INSTRUCTION)

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.views.generate_ai_response.delay")
    def test_create_with_agent_key_sets_purpose_and_persists(self, delay):
        # purpose 由序列化器在创建时按模板名注入；agent_key 持久化到记录
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.student).post("/api/ai-logs/", {
                "project": self.project.id, "agent_key": "opening-report",
                "prompt": "题目：校园雨水", "context_scope": {"project_basics": True},
            }, format="json")
        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()
        record = AIGenerationLog.objects.get(id=response.data["id"])
        self.assertEqual(record.agent_key, "opening-report")
        self.assertEqual(record.purpose, "开题报告助手")

    @override_settings(OPENAI_API_KEY="configured")
    def test_create_with_unknown_agent_key_is_rejected(self):
        response = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id, "agent_key": "does-not-exist",
            "prompt": "x", "context_scope": {"project_basics": True},
        }, format="json")
        self.assertEqual(response.status_code, 400)


class SeedAIAgentsCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command("seed_ai_agents")
        first = AgentTemplate.objects.filter(school=None).count()
        self.assertEqual(first, 16)
        call_command("seed_ai_agents")
        self.assertEqual(AgentTemplate.objects.filter(school=None).count(), first)

    def test_reset_updates_existing_fields(self):
        call_command("seed_ai_agents")
        AgentTemplate.objects.filter(key="opening-report", school=None).update(name="旧名")
        call_command("seed_ai_agents", "--reset")
        self.assertEqual(
            AgentTemplate.objects.get(key="opening-report", school=None).name, "开题报告助手"
        )


class AIGenerationContextAssemblyTests(TestCase):
    """验证 AIGenerationLog 的 task/material 外键与 context_scope 的 current_*/consistency 拼装。"""

    def setUp(self):
        self.school = School.objects.create(name="装配学校")
        self.student = Account.objects.create_user(username="asm-student", school=self.school, role="student")
        self.project = Project.objects.create(
            title="校园雨水回收", problem="如何回收雨水", plan="建回收系统", school=self.school,
            leader=self.student, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        self.task = ProjectTask.objects.create(
            project=self.project, stage_name="方案设计", title="设计回收装置",
            description="请说明装置的结构与原理", order=1,
        )
        self.material = Material.objects.create(
            project=self.project, task=self.task, title="装置设计说明",
            guidance_override="请说明结构、材料与原理", status=Material.Status.DRAFT,
        )
        MaterialRevision.objects.create(
            material=self.material, author=self.student,
            content="我的装置由管道和滤网组成，可过滤杂质。", status=MaterialRevision.Status.DRAFT,
        )
        self.agent = AgentTemplate.objects.create(
            key="research-report", name="研究报告起草", role="student",
            system_instruction="教练", prompt_template="写报告", is_active=True,
        )

    def _run(self, record):
        with patch("apps.core.tasks.OpenAI") as client_class:
            client_class.return_value.responses.create.return_value.output_text = "ok"
            generate_ai_response(record.id)
            return client_class.return_value.responses.create.call_args.kwargs["input"]

    @override_settings(OPENAI_API_KEY="configured")
    def test_current_context_assembled(self):
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, agent_key="research-report",
            task=self.task, material=self.material, prompt="帮我写",
            context_scope={"project_basics": True, "current_task": True,
                           "current_material_draft": True, "current_guidance": True},
            status=AIGenerationLog.Status.QUEUED,
        )
        inp = self._run(record)
        self.assertIn("设计回收装置", inp)                                  # 当前步骤标题
        self.assertIn("请说明装置的结构与原理", inp)                         # 步骤说明
        self.assertIn("我的装置由管道和滤网组成", inp)                       # 已写草稿
        self.assertIn("请说明结构、材料与原理", inp)                         # 材料指引

    @override_settings(OPENAI_API_KEY="configured")
    def test_consistency_scope_includes_all_materials(self):
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, agent_key="cross-consistency",
            prompt="体检", context_scope={"project_basics": True, "consistency": True},
            status=AIGenerationLog.Status.QUEUED,
        )
        inp = self._run(record)
        self.assertIn("装置设计说明", inp)                                  # 材料标题
        self.assertIn("我的装置由管道和滤网组成", inp)                       # 材料内容


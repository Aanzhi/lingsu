from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import Account, AgentTemplate, AIGenerationLog, AuditEvent, Project, ProjectTask, Material, MaterialAttachment, MaterialRevision, School
from apps.core.ai_agents import parse_research_question_output
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

    def test_teacher_cannot_create_school_template(self):
        response = self.client_for(self.teacher).post("/api/ai-agents/", {
            "key": "school-t", "name": "校本教师模板", "role": "teacher",
            "system_instruction": "s", "prompt_template": "p",
        }, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AgentTemplate.objects.filter(key="school-t").exists())

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

    def test_teacher_cannot_delete_template(self):
        response = self.client_for(self.teacher).delete(f"/api/ai-agents/{self.teacher_tmpl.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AgentTemplate.objects.filter(pk=self.teacher_tmpl.id).exists())


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
    def test_agent_prompt_is_rendered_from_validated_inputs_and_paper_type(self):
        self.agent.prompt_template = "题目：{topic}\n项目类型：{project_type}\n论文类型：{paper_type}\n观察：{observations}"
        self.agent.input_schema = [
            {"key": "topic", "required": True, "type": "text"},
            {"key": "observations", "required": False, "type": "textarea"},
        ]
        self.agent.save(update_fields=["prompt_template", "input_schema"])
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, agent_key="opening-report",
            prompt="兼容的自由文本", paper_type="empirical",
            context_scope={"agent_inputs": {"topic": "校园雨水"}},
            status=AIGenerationLog.Status.QUEUED,
        )
        with patch("apps.core.tasks.OpenAI") as client_class:
            client_class.return_value.responses.create.return_value.output_text = "ok"
            generate_ai_response(record.id)
            request_input = client_class.return_value.responses.create.call_args.kwargs["input"]
        self.assertIn("题目：校园雨水", request_input)
        self.assertIn("项目类型：research", request_input)
        self.assertIn("论文类型：empirical", request_input)
        self.assertIn("观察：", request_input)
        self.assertNotIn("{topic}", request_input)

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.views.generate_ai_response.delay")
    def test_agent_request_rejects_missing_required_input(self, delay):
        self.agent.input_schema = [{"key": "topic", "label": "项目主题", "required": True, "type": "text"}]
        self.agent.save(update_fields=["input_schema"])
        response = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id, "agent_key": "opening-report", "prompt": "校园雨水",
            "input_values": {},
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("input_values", response.data)
        delay.assert_not_called()

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.views.generate_ai_response.delay")
    def test_legacy_agent_request_uses_prompt_as_required_input_fallback(self, delay):
        self.agent.input_schema = [{"key": "topic", "label": "项目主题", "required": True, "type": "text"}]
        self.agent.prompt_template = "主题：{topic}"
        self.agent.save(update_fields=["input_schema", "prompt_template"])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.student).post("/api/ai-logs/", {
                "project": self.project.id, "agent_key": "opening-report", "prompt": "校园雨水",
            }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AIGenerationLog.objects.get(pk=response.data["id"]).context_scope["agent_inputs"], {"topic": "校园雨水"})
        delay.assert_called_once()

    @override_settings(OPENAI_API_KEY="")
    def test_demo_generation_keeps_rendered_agent_context_auditable(self):
        self.agent.prompt_template = "主题：{topic}\n论文类型：{paper_type}"
        self.agent.input_schema = [{"key": "topic", "required": True, "type": "text"}]
        self.agent.save(update_fields=["prompt_template", "input_schema"])
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, agent_key="opening-report", prompt="校园雨水",
            paper_type="case", context_scope={"agent_inputs": {"topic": "校园雨水"}},
        )
        generate_ai_response(record.id)
        record.refresh_from_db()
        self.assertIn("论文类型：case", record.output)

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

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.views.generate_ai_response.delay")
    def test_agent_request_uses_template_context_without_client_boolean_override(self, delay):
        self.agent.context_scope_default = {
            "project_basics": True,
            "approved_materials": False,
            "consistency": True,
        }
        self.agent.save(update_fields=["context_scope_default"])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.student).post("/api/ai-logs/", {
                "project": self.project.id,
                "agent_key": "opening-report",
                "prompt": "校园雨水",
                "context_scope": {
                    "project_basics": False,
                    "approved_materials": True,
                    "consistency": False,
                },
            }, format="json")
        self.assertEqual(response.status_code, 201)
        scope = AIGenerationLog.objects.get(pk=response.data["id"]).context_scope
        self.assertTrue(scope["project_basics"])
        self.assertFalse(scope["approved_materials"])
        self.assertTrue(scope["consistency"])
        delay.assert_called_once()

    @override_settings(OPENAI_API_KEY="configured")
    def test_agent_request_rejects_unpermitted_context_selection(self):
        response = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id,
            "agent_key": "opening-report",
            "prompt": "校园雨水",
            "context_scope": {"selected_materials": [123]},
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("context_scope", response.data)

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.views.generate_ai_response.delay")
    def test_agent_request_accepts_selection_explicitly_permitted_by_template(self, delay):
        self.agent.context_scope_default = {"allowed_selections": ["related_tasks"]}
        self.agent.save(update_fields=["context_scope_default"])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.student).post("/api/ai-logs/", {
                "project": self.project.id,
                "agent_key": "opening-report",
                "prompt": "校园雨水",
                "context_scope": {"related_tasks": [42]},
            }, format="json")
        self.assertEqual(response.status_code, 201)
        scope = AIGenerationLog.objects.get(pk=response.data["id"]).context_scope
        self.assertEqual(scope["related_tasks"], [42])
        delay.assert_called_once()

    @override_settings(OPENAI_API_KEY="configured")
    def test_agent_request_rejects_cross_project_or_unscanned_selected_materials(self):
        self.agent.context_scope_default = {"allowed_selections": ["selected_materials"]}
        self.agent.save(update_fields=["context_scope_default"])
        other = Project.objects.create(school=self.school, leader=self.student, title="另一项目")
        foreign_material = Material.objects.create(project=other, title="外部材料")
        cross_project = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id, "agent_key": "opening-report", "prompt": "校园雨水",
            "context_scope": {"selected_materials": [foreign_material.id]},
        }, format="json")
        self.assertEqual(cross_project.status_code, 400)
        selected_material = Material.objects.create(project=self.project, title="待扫描材料")
        revision = MaterialRevision.objects.create(material=selected_material, author=self.student, content="待扫描附件")
        MaterialAttachment.objects.create(revision=revision, original_name="pending.pdf", scan_status=MaterialAttachment.ScanStatus.PENDING)
        unsafe = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id, "agent_key": "opening-report", "prompt": "校园雨水",
            "context_scope": {"selected_materials": [selected_material.id]},
        }, format="json")
        self.assertEqual(unsafe.status_code, 400)

    @override_settings(OPENAI_API_KEY="configured")
    def test_agent_request_rejects_incompatible_project_type(self):
        self.agent.project_types = ["engineering"]
        self.agent.save(update_fields=["project_types"])
        response = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id,
            "agent_key": "opening-report",
            "prompt": "校园雨水",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("agent_key", response.data)


class SeedAIAgentsCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command("seed_ai_agents")
        first = AgentTemplate.objects.filter(school=None).count()
        self.assertEqual(first, 11)
        call_command("seed_ai_agents")
        self.assertEqual(AgentTemplate.objects.filter(school=None).count(), first)

    def test_reset_updates_existing_fields(self):
        call_command("seed_ai_agents")
        AgentTemplate.objects.filter(key="proposal-topic", school=None).update(name="旧名")
        call_command("seed_ai_agents", "--reset")
        self.assertEqual(
            AgentTemplate.objects.get(key="proposal-topic", school=None).name, "研究问题助手"
        )

    def test_seeded_student_agents_include_workflow_metadata_and_safety_guardrails(self):
        call_command("seed_ai_agents")
        agents = AgentTemplate.objects.filter(school=None, role=AgentTemplate.Role.STUDENT)
        self.assertEqual(agents.count(), 11)
        for agent in agents:
            self.assertTrue(agent.workflow)
            self.assertTrue(agent.applicable_stages)
            self.assertTrue(agent.quick_tasks)
            self.assertTrue(agent.project_types)
            self.assertTrue(agent.output_contract)
            self.assertIn("不虚构", agent.system_instruction)
        self.assertEqual(agents.filter(workflow__startswith="proposal_").count(), 5)
        self.assertEqual(agents.filter(workflow__startswith="paper_").count(), 6)
        self.assertSetEqual(
            set(agents.values_list("key", flat=True)),
            {
                "proposal-topic", "proposal-background", "proposal-objectives", "proposal-plan", "proposal-consistency",
                "paper-title-abstract", "paper-framework", "paper-expand-polish", "paper-reference-format",
                "paper-result-interpret", "paper-reviewer-response",
            },
        )
        consistency = agents.get(key="proposal-consistency")
        self.assertTrue(consistency.context_scope_default["consistency"])
        self.assertTrue(consistency.context_scope_default["teacher_feedback"])
        self.assertEqual(
            agents.get(key="paper-expand-polish").context_scope_default["allowed_selections"],
            ["selected_materials"],
        )
        self.assertNotIn("allowed_selections", agents.get(key="proposal-topic").context_scope_default)
        self.assertFalse(
            agents.exclude(key="proposal-consistency").filter(
                context_scope_default__approved_materials=True
            ).exists()
        )
        reference_agent = agents.get(key="paper-reference-format")
        self.assertEqual(
            reference_agent.output_contract["sections"],
            ["检索式", "筛选标准", "待核验候选来源"],
        )
        self.assertIn("不生成任何可直接引用的文献条目", reference_agent.system_instruction)

    def test_seed_disables_legacy_global_student_templates_but_preserves_teacher_and_school_templates(self):
        school = School.objects.create(name="校本模板学校")
        legacy = AgentTemplate.objects.create(key="legacy-student", name="旧学生助手", role="student", system_instruction="x", prompt_template="x")
        teacher = AgentTemplate.objects.create(key="legacy-teacher", name="旧教师助手", role="teacher", system_instruction="x", prompt_template="x")
        local = AgentTemplate.objects.create(key="legacy-local", name="校本学生助手", role="student", school=school, system_instruction="x", prompt_template="x")
        call_command("seed_ai_agents")
        legacy.refresh_from_db(); teacher.refresh_from_db(); local.refresh_from_db()
        self.assertFalse(legacy.is_active)
        self.assertTrue(teacher.is_active)
        self.assertTrue(local.is_active)


class PaperTypeAgentContractTests(TestCase):
    def setUp(self):
        call_command("seed_ai_agents")
        self.school = School.objects.create(name="论文类型学校", ai_quota=30)
        self.student = Account.objects.create_user(username="paper-type-student", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="paper-type-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            school=self.school, title="校园雨水", problem="研究问题", plan="研究方案",
            leader=self.student, primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")

    def client_for(self, user):
        client = APIClient(); client.force_authenticate(user); return client

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.views.generate_ai_response.delay")
    def test_paper_agents_require_one_of_the_four_paper_types(self, delay):
        response = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id,
            "agent_key": "paper-title-abstract",
            "prompt": "校园雨水",
            "paper_type": "unsupported",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("paper_type", response.data)

        response = self.client_for(self.student).post("/api/ai-logs/", {
            "project": self.project.id,
            "agent_key": "paper-title-abstract",
            "prompt": "校园雨水",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("paper_type", response.data)
        delay.assert_not_called()

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.views.generate_ai_response.delay")
    def test_paper_agents_accept_each_supported_paper_type(self, delay):
        for paper_type in ("empirical", "case", "literature-review", "theoretical"):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client_for(self.student).post("/api/ai-logs/", {
                    "project": self.project.id,
                    "agent_key": "paper-title-abstract",
                    "prompt": "校园雨水",
                    "paper_type": paper_type,
                }, format="json")
            self.assertEqual(response.status_code, 201, paper_type)
            self.assertEqual(response.data["paper_type"], paper_type)
        self.assertEqual(delay.call_count, 4)

    @override_settings(OPENAI_API_KEY="configured")
    def test_every_paper_agent_receives_selected_type_even_without_template_placeholder(self):
        paper_agents = AgentTemplate.objects.filter(school=None, key__startswith="paper-").order_by("key")
        self.assertEqual(paper_agents.count(), 6)
        with patch("apps.core.tasks.OpenAI") as client_class:
            client_class.return_value.responses.create.return_value.output_text = "ok"
            for agent in paper_agents:
                agent.prompt_template = "固定模板，不含论文类型占位符。"
                agent.save(update_fields=["prompt_template"])
                inputs = {
                    field["key"]: "真实项目输入"
                    for field in agent.input_schema if field.get("required")
                }
                record = AIGenerationLog.objects.create(
                    project=self.project, actor=self.student, agent_key=agent.key,
                    prompt="论文写作", paper_type="theoretical",
                    context_scope={"agent_inputs": inputs}, status=AIGenerationLog.Status.QUEUED,
                )
                generate_ai_response(record.id)
                request_input = client_class.return_value.responses.create.call_args.kwargs["input"]
                self.assertIn("论文类型：theoretical", request_input, agent.key)

class SaveAIOutputAsMaterialTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="保存学校")
        self.student = Account.objects.create_user(username="save-student", school=self.school, role="student")
        self.peer = Account.objects.create_user(username="save-peer", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="save-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            title="水质观察", problem="水样差异", plan="采样分析", school=self.school,
            leader=self.student, primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        self.other_project = Project.objects.create(
            title="另一项目", problem="问题", plan="方案", school=self.school,
            leader=self.peer, primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.other_project.members.create(account=self.peer, role="leader")
        self.material = Material.objects.create(project=self.project, title="研究设计", status=Material.Status.DRAFT)
        self.other_material = Material.objects.create(project=self.other_project, title="他人材料", status=Material.Status.DRAFT)
        self.log = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, purpose="研究设计建议", prompt="请设计",
            output="可编辑的研究设计草稿", artifact_payload={"content": "结构化草稿", "title": "研究设计"},
            verification_items=[{"item": "样本量", "status": "needs_verification"}],
            paper_type="empirical", status=AIGenerationLog.Status.COMPLETED,
        )

    def client_for(self, user):
        client = APIClient(); client.force_authenticate(user); return client

    def test_completed_log_creates_auditable_material_draft(self):
        response = self.client_for(self.student).post(
            f"/api/ai-logs/{self.log.id}/save_as_material/", {"material": self.material.id, "content": "学生已编辑的草稿", "revision_note": "保留实验原始记录"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        revision = MaterialRevision.objects.get(pk=response.data["id"])
        self.assertEqual(revision.material, self.material)
        self.assertEqual(revision.author, self.student)
        self.assertEqual(revision.content, "学生已编辑的草稿")
        self.assertEqual(revision.revision_note, "保留实验原始记录")
        self.log.refresh_from_db()
        self.assertEqual(self.log.saved_material_revision, revision)
        self.assertEqual(response.data["source_summary"]["ai_log_id"], self.log.id)
        self.assertEqual(response.data["verification_summary"]["total"], 1)
        self.assertTrue(AuditEvent.objects.filter(
            action=AuditEvent.Action.AI_OUTPUT_SAVED_AS_MATERIAL,
            actor=self.student,
            changes__ai_log_id=self.log.id,
            changes__revision_id=revision.id,
        ).exists())

    def test_cannot_save_to_material_from_another_project(self):
        response = self.client_for(self.student).post(
            f"/api/ai-logs/{self.log.id}/save_as_material/", {"material": self.other_material.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MaterialRevision.objects.count(), 0)

    def test_save_without_edits_defaults_to_structured_artifact_content(self):
        response = self.client_for(self.student).post(
            f"/api/ai-logs/{self.log.id}/save_as_material/", {"material": self.material.id}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(MaterialRevision.objects.get(pk=response.data["id"]).content, "结构化草稿")

    def test_cannot_save_same_log_twice(self):
        client = self.client_for(self.student)
        self.assertEqual(client.post(
            f"/api/ai-logs/{self.log.id}/save_as_material/", {"material": self.material.id}, format="json"
        ).status_code, 201)
        self.assertEqual(client.post(
            f"/api/ai-logs/{self.log.id}/save_as_material/", {"material": self.material.id}, format="json"
        ).status_code, 400)

    def test_only_completed_student_owned_log_can_be_saved(self):
        self.log.status = AIGenerationLog.Status.PROCESSING
        self.log.save(update_fields=["status"])
        response = self.client_for(self.student).post(
            f"/api/ai-logs/{self.log.id}/save_as_material/", {"material": self.material.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)


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

    @override_settings(OPENAI_API_KEY="configured")
    def test_history_and_teacher_feedback_are_limited_to_the_current_project(self):
        teacher = Account.objects.create_user(username="context-teacher", school=self.school, role="teacher")
        MaterialRevision.objects.create(
            material=self.material, author=self.student, content="待修改",
            status=MaterialRevision.Status.REVISION_REQUIRED,
            reviewer=teacher,
            review_comment="请补充滤网孔径的实测数据。",
        )
        AIGenerationLog.objects.create(
            project=self.project, actor=self.student, agent_key="research-report",
            purpose="先前大纲", output="同项目的既有 AI 草稿", status=AIGenerationLog.Status.COMPLETED,
        )
        other_student = Account.objects.create_user(username="other-context", school=self.school, role="student")
        other_project = Project.objects.create(
            title="不相关项目", problem="不相关问题", plan="不相关方案", school=self.school,
            leader=other_student, status=Project.Status.ACTIVE,
        )
        AIGenerationLog.objects.create(
            project=other_project, actor=other_student, agent_key="research-report",
            output="绝不能泄露的其他项目 AI 草稿", status=AIGenerationLog.Status.COMPLETED,
        )
        record = AIGenerationLog.objects.create(
            project=self.project, actor=self.student, agent_key="research-report", prompt="继续写",
            context_scope={"ai_history": True, "teacher_feedback": True},
            status=AIGenerationLog.Status.QUEUED,
        )
        inp = self._run(record)
        self.assertIn("同项目的既有 AI 草稿", inp)
        self.assertIn("请补充滤网孔径的实测数据", inp)
        self.assertNotIn("绝不能泄露", inp)


class ResearchQuestionOutputTests(TestCase):
    def test_research_question_output_accepts_fenced_json_and_limits_scores(self):
        payload = parse_research_question_output('```json\n{"project_title":"校园积水观察","project_type":"engineering","project_plan":"连续记录积水变化并比较排水条件。","candidates": [\n'
            '{"question":"问题一","scope":"校园","why":"价值","evidence_plan":"观察","limitations":"时间","scores":{"researchability":9,"clarity":0,"verifiability":4,"resource_fit":3}},'
            '{"question":"问题二","scores":{"researchability":3,"clarity":4,"verifiability":5,"resource_fit":2}},'
            '{"question":"问题三","scores":{"researchability":1,"clarity":2,"verifiability":3,"resource_fit":4}}],"recommended_index":1}\n```')
        self.assertEqual(len(payload["candidates"]), 3)
        self.assertEqual(payload["candidates"][0]["scores"], {"researchability": 5, "clarity": 1, "verifiability": 4, "resource_fit": 3})

    def test_research_question_output_returns_none_for_non_structured_text(self):
        self.assertIsNone(parse_research_question_output("先聊聊你的兴趣，再逐步缩小范围。"))

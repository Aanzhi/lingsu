from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import AIConversation, AIConversationMessage, Account, AIGenerationLog, AgentTemplate, Project, School
from apps.core.tasks import generate_general_ai_response


class AIConversationAPITests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="会话学校", ai_quota=20)
        self.student = Account.objects.create_user(username="conversation-student", school=self.school, role="student")
        self.other = Account.objects.create_user(username="conversation-other", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="conversation-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            school=self.school, title="对话项目", problem="问题", plan="方案", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")

    def api_client(self, user):
        c = APIClient(); c.force_authenticate(user); return c

    def test_student_can_create_private_project_and_general_conversations(self):
        response = self.api_client(self.student).post("/api/ai-conversations/", {"project": self.project.id, "title": "项目讨论"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["project"], self.project.id)
        general = self.api_client(self.student).post("/api/ai-conversations/", {"title": "通用问题"}, format="json")
        self.assertEqual(general.status_code, 201)
        self.assertIsNone(general.data["project"])
        unselected_agent = self.api_client(self.student).post(
            "/api/ai-conversations/", {"title": "未选择 Agent", "current_agent": None}, format="json",
        )
        self.assertEqual(unselected_agent.status_code, 201)
        self.assertEqual(unselected_agent.data["current_agent"], "")

    def test_opening_conversation_accepts_null_optional_paper_type(self):
        response = self.api_client(self.student).post(
            "/api/ai-conversations/",
            {"workspace_mode": "opening", "paper_type": None},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["paper_type"], "")

    def test_teacher_and_other_student_cannot_read_conversation(self):
        conversation = AIConversation.objects.create(owner=self.student, project=self.project)
        self.assertEqual(self.api_client(self.other).get(f"/api/ai-conversations/{conversation.id}/").status_code, 404)
        self.assertEqual(self.api_client(self.teacher).get("/api/ai-conversations/").data, [])

    @patch("apps.core.views.generate_ai_response.delay")
    def test_project_message_creates_user_assistant_and_linked_log(self, delay):
        conversation = AIConversation.objects.create(owner=self.student, project=self.project, current_agent="proposal-topic")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client(self.student).post(
                f"/api/ai-conversations/{conversation.id}/messages/", {"content": "帮我梳理研究问题"}, format="json"
            )
        self.assertEqual(response.status_code, 201)
        assistant = AIConversationMessage.objects.get(pk=response.data["id"])
        self.assertEqual(assistant.role, "assistant")
        self.assertEqual(assistant.status, "queued")
        log = AIGenerationLog.objects.get(pk=assistant.generation_log_id)
        self.assertEqual(log.conversation_message.id, assistant.id)
        self.assertEqual(log.conversation_id, conversation.id)
        self.assertEqual(log.message_id, assistant.id)
        delay.assert_called_once_with(log.id)
        self.assertEqual(conversation.messages.count(), 2)

    @override_settings(OPENAI_API_KEY="")
    def test_general_message_is_available_without_project_log(self):
        conversation = AIConversation.objects.create(owner=self.student)
        response = self.api_client(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/", {"content": "什么是研究变量？"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "completed")
        self.assertFalse(AIGenerationLog.objects.exists())

    @override_settings(OPENAI_API_KEY="")
    def test_first_user_message_names_conversation_and_exposes_preview(self):
        conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening")
        response = self.api_client(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/",
            {"content": "  我想研究校园积水的持续时间和排水条件  "},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        conversation.refresh_from_db()
        self.assertEqual(conversation.title, "我想研究校园积水的持续时间和排水条件")
        listed = self.api_client(self.student).get("/api/ai-conversations/")
        item = next(item for item in listed.data if item["id"] == conversation.id)
        self.assertEqual(item["preview"], "我想研究校园积水的持续时间和排水条件")

    @override_settings(OPENAI_API_KEY="")
    def test_explicit_conversation_title_is_preserved_after_first_message(self):
        conversation = AIConversation.objects.create(owner=self.student, title="我的研究记录")
        response = self.api_client(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/",
            {"content": "补充一条研究观察"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        conversation.refresh_from_db()
        self.assertEqual(conversation.title, "我的研究记录")

    def test_legacy_generic_conversation_uses_first_user_message_as_history_title(self):
        conversation = AIConversation.objects.create(owner=self.student, title="新对话")
        AIConversationMessage.objects.create(
            conversation=conversation, role=AIConversationMessage.Role.USER, content="旧会话的第一句研究问题",
        )

        response = self.api_client(self.student).get("/api/ai-conversations/")

        self.assertEqual(response.status_code, 200)
        item = next(item for item in response.data if item["id"] == conversation.id)
        self.assertEqual(item["title"], "旧会话的第一句研究问题")
        self.assertEqual(item["preview"], "旧会话的第一句研究问题")

    def test_legacy_unnamed_placeholder_uses_first_user_message_as_history_title(self):
        conversation = AIConversation.objects.create(owner=self.student, title="未命名对话")
        AIConversationMessage.objects.create(
            conversation=conversation, role=AIConversationMessage.Role.USER, content="截图中显示为未命名的旧问题",
        )

        response = self.api_client(self.student).get("/api/ai-conversations/")

        self.assertEqual(response.status_code, 200)
        item = next(item for item in response.data if item["id"] == conversation.id)
        self.assertEqual(item["title"], "截图中显示为未命名的旧问题")

    @override_settings(OPENAI_API_KEY="configured", CELERY_TASK_ALWAYS_EAGER=False)
    @patch("apps.core.views.generate_general_ai_response.delay")
    def test_configured_general_message_queues_real_generation_without_project_log(self, delay):
        conversation = AIConversation.objects.create(owner=self.student)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client(self.student).post(
                f"/api/ai-conversations/{conversation.id}/messages/", {"content": "什么是研究变量？"}, format="json"
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "queued")
        self.assertFalse(AIGenerationLog.objects.exists())
        delay.assert_called_once_with(response.data["id"])

    @override_settings(OPENAI_API_KEY="")
    def test_project_free_research_question_assistant_requires_real_ai_service(self):
        conversation = AIConversation.objects.create(owner=self.student, current_agent="proposal-topic")
        response = self.api_client(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/",
            {"content": "请帮我从校园积水开始找研究问题", "agent_key": "proposal-topic"},
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("研究问题助手需要配置真实 AI 服务", response.data["detail"])
        self.assertEqual(conversation.messages.count(), 0)

    @override_settings(OPENAI_API_KEY="configured", CELERY_TASK_ALWAYS_EAGER=False)
    @patch("apps.core.views.generate_general_ai_response.delay")
    def test_project_free_research_question_assistant_keeps_agent_and_queues_generation(self, delay):
        conversation = AIConversation.objects.create(owner=self.student, current_agent="proposal-topic")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client(self.student).post(
                f"/api/ai-conversations/{conversation.id}/messages/",
                {
                    "content": "请从校园积水中生成候选研究问题",
                    "agent_key": "proposal-topic",
                    "input_values": {"topic": "校园积水", "observations": "雨后操场东侧积水"},
                },
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "queued")
        conversation.refresh_from_db()
        self.assertEqual(conversation.current_agent, "proposal-topic")
        delay.assert_called_once_with(response.data["id"])

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.tasks.OpenAI")
    def test_project_free_research_question_task_persists_editable_project_draft(self, client_class):
        conversation = AIConversation.objects.create(owner=self.student, current_agent="proposal-topic")
        AIConversationMessage.objects.create(
            conversation=conversation, role="user", content="雨后操场东侧积水很久，想研究排水条件。",
        )
        assistant = AIConversationMessage.objects.create(
            conversation=conversation, role="assistant", content="", status="queued",
        )
        client_class.return_value.responses.create.return_value.output_text = (
            '{"project_title":"校园积水观察","project_type":"engineering",'
            '"project_plan":"记录积水位置并比较排水条件。","candidates":['
            '{"question":"问题一","scope":"校园操场","why":"有价值","evidence_plan":"观察记录",'
            '"limitations":"周期有限","scores":{"researchability":4,"clarity":4,"verifiability":4,"resource_fit":4}},'
            '{"question":"问题二","scores":{"researchability":3,"clarity":4,"verifiability":4,"resource_fit":3}},'
            '{"question":"问题三","scores":{"researchability":4,"clarity":3,"verifiability":4,"resource_fit":4}}],'
            '"recommended_index":0,"missing_information":[]}'
        )

        generate_general_ai_response.run(assistant.id)

        assistant.refresh_from_db()
        self.assertEqual(assistant.status, "completed")
        self.assertEqual(assistant.artifact_payload["project_title"], "校园积水观察")
        self.assertEqual(assistant.artifact_payload["project_type"], "engineering")
        self.assertEqual(assistant.artifact_payload["project_plan"], "记录积水位置并比较排水条件。")
        self.assertEqual(len(assistant.artifact_payload["candidates"]), 3)
        self.assertIn("雨后操场东侧积水很久", client_class.return_value.responses.create.call_args.kwargs["input"])

    @override_settings(OPENAI_API_KEY="configured")
    @patch("apps.core.tasks.OpenAI")
    def test_project_free_message_uses_the_selected_skill_template(self, client_class):
        AgentTemplate.objects.create(
            key="proposal-background", name="研究背景 Skill", role="student", category="开题",
            system_instruction="SKILL_SYSTEM_INSTRUCTION",
            prompt_template="SKILL_PROMPT {user_prompt}", is_active=True,
        )
        conversation = AIConversation.objects.create(
            owner=self.student, workspace_mode="opening", current_agent="proposal-background",
        )
        AIConversationMessage.objects.create(
            conversation=conversation, role="user", content="请梳理校园积水的研究背景",
        )
        assistant = AIConversationMessage.objects.create(
            conversation=conversation, role="assistant", content="", status="queued",
        )
        client_class.return_value.responses.create.return_value.output_text = "普通文本回复"

        generate_general_ai_response.run(assistant.id)

        kwargs = client_class.return_value.responses.create.call_args.kwargs
        self.assertEqual(kwargs["instructions"], "SKILL_SYSTEM_INSTRUCTION")
        self.assertIn("SKILL_PROMPT 请梳理校园积水的研究背景", kwargs["input"])

    def test_student_can_read_conversation_messages(self):
        conversation = AIConversation.objects.create(owner=self.student)
        AIConversationMessage.objects.create(
            conversation=conversation, role="assistant", content="已有回复", status="completed",
        )

        response = self.api_client(self.student).get(
            f"/api/ai-conversations/{conversation.id}/messages/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["content"], "已有回复")

    def test_conversation_cannot_change_project_and_can_archive(self):
        conversation = AIConversation.objects.create(owner=self.student, project=self.project)
        changed = self.api_client(self.student).patch(f"/api/ai-conversations/{conversation.id}/", {"project": None}, format="json")
        self.assertEqual(changed.status_code, 400)
        archived = self.api_client(self.student).post(f"/api/ai-conversations/{conversation.id}/archive/")
        self.assertEqual(archived.status_code, 200)
        self.assertTrue(archived.data["is_archived"])

    def test_student_can_permanently_delete_conversation_and_detach_audit_log(self):
        conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening", is_archived=True)
        other_conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening")
        self.assertEqual(
            self.api_client(self.other).delete(f"/api/ai-conversations/{other_conversation.id}/").status_code,
            404,
        )
        log = AIGenerationLog.objects.create(
            actor=self.student,
            conversation=conversation,
            project=None,
            purpose="开题对话",
            prompt="删除测试",
        )
        message = AIConversationMessage.objects.create(
            conversation=conversation,
            role=AIConversationMessage.Role.USER,
            content="待删除的问题",
            generation_log=log,
        )
        log.message = message
        log.save(update_fields=["message"])

        response = self.api_client(self.student).delete(f"/api/ai-conversations/{conversation.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(AIConversation.objects.filter(pk=conversation.id).exists())
        self.assertFalse(AIConversationMessage.objects.filter(pk=message.id).exists())
        log.refresh_from_db()
        self.assertIsNone(log.conversation_id)
        self.assertIsNone(log.message_id)

    @override_settings(OPENAI_API_KEY="configured", CELERY_TASK_ALWAYS_EAGER=False)
    @patch("apps.core.views.generate_general_ai_response.delay")
    def test_failed_general_message_can_retry_without_duplicate_user_message(self, delay):
        conversation = AIConversation.objects.create(owner=self.student)
        user_message = AIConversationMessage.objects.create(conversation=conversation, role="user", content="请重试")
        assistant = AIConversationMessage.objects.create(
            conversation=conversation, role="assistant", content="", status="failed", error_message="临时失败",
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client(self.student).post(
                f"/api/ai-conversations/{conversation.id}/messages/{assistant.id}/retry/"
            )
        self.assertEqual(response.status_code, 200)
        assistant.refresh_from_db()
        self.assertEqual(response.data["id"], assistant.id)
        self.assertEqual(assistant.status, "queued")
        self.assertEqual(assistant.error_message, "")
        self.assertEqual(conversation.messages.filter(role="user").count(), 1)
        self.assertEqual(conversation.messages.get(role="user").id, user_message.id)
        delay.assert_called_once_with(assistant.id)

    @patch("apps.core.views.generate_ai_response.delay")
    def test_failed_project_message_retry_creates_new_log_and_preserves_old_audit_record(self, delay):
        conversation = AIConversation.objects.create(owner=self.student, project=self.project, current_agent="proposal-topic")
        user_message = AIConversationMessage.objects.create(conversation=conversation, role="user", content="原问题")
        old_log = AIGenerationLog.objects.create(
            project=self.project, conversation=conversation, actor=self.student, purpose="对话咨询",
            agent_key="proposal-topic", prompt="原问题", status="failed", error_message="临时失败",
        )
        assistant = AIConversationMessage.objects.create(
            conversation=conversation, role="assistant", content="", status="failed", error_message="临时失败",
            generation_log=old_log,
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api_client(self.student).post(
                f"/api/ai-conversations/{conversation.id}/messages/{assistant.id}/retry/"
            )
        self.assertEqual(response.status_code, 200)
        assistant.refresh_from_db()
        self.assertEqual(assistant.status, "queued")
        self.assertIsNotNone(assistant.generation_log_id)
        self.assertNotEqual(assistant.generation_log_id, old_log.id)
        self.assertTrue(AIGenerationLog.objects.filter(pk=old_log.id, status="failed").exists())
        delay.assert_called_once_with(assistant.generation_log_id)
        self.assertEqual(conversation.messages.filter(role="user").count(), 1)

    def test_retry_rejects_completed_messages_and_other_owners(self):
        conversation = AIConversation.objects.create(owner=self.student)
        completed = AIConversationMessage.objects.create(conversation=conversation, role="assistant", content="完成", status="completed")
        self.assertEqual(
            self.api_client(self.student).post(f"/api/ai-conversations/{conversation.id}/messages/{completed.id}/retry/").status_code,
            400,
        )
        failed = AIConversationMessage.objects.create(conversation=conversation, role="assistant", content="", status="failed")
        self.assertEqual(
            self.api_client(self.other).post(f"/api/ai-conversations/{conversation.id}/messages/{failed.id}/retry/").status_code,
            404,
        )

    @override_settings(OPENAI_API_KEY="")
    def test_failed_general_message_retry_keeps_demo_fallback_without_queueing(self):
        conversation = AIConversation.objects.create(owner=self.student)
        AIConversationMessage.objects.create(conversation=conversation, role="user", content="什么是变量？")
        assistant = AIConversationMessage.objects.create(conversation=conversation, role="assistant", content="", status="failed")
        response = self.api_client(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/{assistant.id}/retry/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "completed")
        self.assertIn("这是通用咨询", response.data["content"])

    @override_settings(OPENAI_API_KEY="")
    def test_failed_no_project_topic_retry_keeps_real_ai_blocking_message(self):
        conversation = AIConversation.objects.create(owner=self.student, current_agent="proposal-topic")
        AIConversationMessage.objects.create(conversation=conversation, role="user", content="我想研究校园积水")
        assistant = AIConversationMessage.objects.create(conversation=conversation, role="assistant", content="", status="failed")
        response = self.api_client(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/{assistant.id}/retry/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "completed")
        self.assertIn("研究问题助手需要配置真实 AI 服务", response.data["content"])

    @patch("apps.core.views.redis.Redis.from_url")
    def test_stream_replays_last_event_id_and_ends_on_completed(self, from_url):
        conversation = AIConversation.objects.create(owner=self.student, project=self.project)
        message = AIConversationMessage.objects.create(conversation=conversation, role="assistant", content="完成", status="completed")
        from_url.return_value.xread.return_value = []
        response = self.api_client(self.student).get(
            f"/api/ai-conversations/{conversation.id}/messages/{message.id}/stream/?last_event_id=12-0"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("message.done", b"".join(response.streaming_content).decode())
        from_url.return_value.xread.assert_called()

    @patch("apps.core.views.redis.Redis.from_url")
    def test_stream_accepts_browser_event_stream_requests(self, from_url):
        conversation = AIConversation.objects.create(owner=self.student, project=self.project)
        message = AIConversationMessage.objects.create(conversation=conversation, role="assistant", content="完成", status="completed")
        from_url.return_value.xread.return_value = []
        response = self.api_client(self.student).get(
            f"/api/ai-conversations/{conversation.id}/messages/{message.id}/stream/",
            HTTP_ACCEPT="text/event-stream",
        )
        self.assertEqual(response.status_code, 200)

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import AIConversation, AIConversationMessage, Account, AIGenerationLog, Project, School


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

    def test_general_message_is_available_without_project_log(self):
        conversation = AIConversation.objects.create(owner=self.student)
        response = self.api_client(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/", {"content": "什么是研究变量？"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "completed")
        self.assertFalse(AIGenerationLog.objects.exists())

    def test_conversation_cannot_change_project_and_can_archive(self):
        conversation = AIConversation.objects.create(owner=self.student, project=self.project)
        changed = self.api_client(self.student).patch(f"/api/ai-conversations/{conversation.id}/", {"project": None}, format="json")
        self.assertEqual(changed.status_code, 400)
        archived = self.api_client(self.student).post(f"/api/ai-conversations/{conversation.id}/archive/")
        self.assertEqual(archived.status_code, 200)
        self.assertTrue(archived.data["is_archived"])

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

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import AIConversation, AIConversationMessage, Account, Project, School


class AIWorkspaceContractTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="AI 工作台学校", ai_quota=20)
        self.student = Account.objects.create_user(username="ai-workspace-student", school=self.school, role=Account.Role.STUDENT)
        self.teacher = Account.objects.create_user(username="ai-workspace-teacher", school=self.school, role=Account.Role.TEACHER)
        self.other_teacher = Account.objects.create_user(username="ai-workspace-other", school=self.school, role=Account.Role.TEACHER)
        self.project = Project.objects.create(
            school=self.school,
            title="当前科创项目",
            problem="校园环境观察",
            plan="完成观察与记录",
            leader=self.student,
            primary_teacher=self.teacher,
            status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_research_and_defense_messages_require_the_current_project(self):
        research = AIConversation.objects.create(owner=self.student, workspace_mode="research")
        defense = AIConversation.objects.create(owner=self.student, workspace_mode="defense")
        for conversation, mode in ((research, "research"), (defense, "defense")):
            response = self.client_for(self.student).post(
                f"/api/ai-conversations/{conversation.id}/messages/",
                {"content": "请结合项目继续完善", "workspace_mode": mode},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("当前项目", str(response.data))
            self.assertEqual(conversation.messages.count(), 0)

    @override_settings(OPENAI_API_KEY="")
    def test_opening_conversation_stays_project_free_and_never_creates_generation_log(self):
        conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening")
        response = self.client_for(self.student).post(
            f"/api/ai-conversations/{conversation.id}/messages/",
            {"content": "我想研究校园积水", "workspace_mode": "opening"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data.get("generation_log"))
        self.assertIsNone(conversation.project_id)

    def test_teacher_ai_cannot_read_a_project_guided_by_another_teacher(self):
        response = self.client_for(self.other_teacher).post(
            "/api/ai-logs/",
            {"project": self.project.id, "prompt": "读取这个项目的所有材料"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_opening_draft_requires_explicit_confirmation_before_creating_project(self):
        conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening")
        assistant = AIConversationMessage.objects.create(
            conversation=conversation,
            role=AIConversationMessage.Role.ASSISTANT,
            status=AIConversationMessage.Status.COMPLETED,
            content="结构化开题草稿",
            artifact_payload={
                "project_title": "校园积水观察",
                "project_type": "research",
                "project_plan": "记录积水位置并比较排水条件。",
                "candidates": [{"question": "排水条件是否影响积水时长？"}],
                "recommended_index": 0,
            },
        )
        endpoint = f"/api/ai-conversations/{conversation.id}/create_from_opening/"
        blocked = self.client_for(self.student).post(endpoint, {"confirm": False}, format="json")
        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(Project.objects.filter(title="校园积水观察").count(), 0)

        created = self.client_for(self.student).post(endpoint, {"confirm": True}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["title"], "校园积水观察")
        self.assertEqual(created.data["leader"], self.student.id)
        assistant.refresh_from_db()
        conversation.refresh_from_db()
        self.assertEqual(conversation.opening_project_id, created.data["id"])

        repeated = self.client_for(self.student).post(endpoint, {"confirm": True}, format="json")
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.data["id"], created.data["id"])

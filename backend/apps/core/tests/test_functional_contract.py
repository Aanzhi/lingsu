from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    AIConversation,
    AIGenerationLog,
    Material,
    MaterialRevision,
    Project,
    ProjectTask,
    PublicCaseRequest,
    School,
)


class FunctionalContractTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="功能契约学校")
        self.student = Account.objects.create_user(username="contract-student", school=self.school, role=Account.Role.STUDENT)
        self.teacher = Account.objects.create_user(username="contract-teacher", school=self.school, role=Account.Role.TEACHER)
        self.other_teacher = Account.objects.create_user(username="contract-other-teacher", school=self.school, role=Account.Role.TEACHER)
        self.platform = Account.objects.create_user(username="contract-platform", role=Account.Role.PLATFORM_ADMIN)
        self.project = Project.objects.create(
            school=self.school,
            title="功能契约项目",
            problem="如何降低校园用水浪费？",
            leader=self.student,
            primary_teacher=self.teacher,
            status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        self.task = ProjectTask.objects.create(
            project=self.project,
            stage_name="实验验证",
            title="完成实验与记录",
            order=1,
            status=ProjectTask.Status.PENDING_REVIEW,
        )
        self.material = Material.objects.create(
            project=self.project,
            task=self.task,
            title="实验结论",
            kind="standard",
            status=Material.Status.DRAFT,
            required=True,
        )
        self.experiment_log = Material.objects.create(
            project=self.project,
            task=self.task,
            title="实验日志",
            kind="experiment_log",
            status=Material.Status.DRAFT,
            required=True,
        )
        self.revision = MaterialRevision.objects.create(
            material=self.material,
            author=self.student,
            content="已完成实验结论",
            truth_confirmed=True,
            status=MaterialRevision.Status.DRAFT,
        )

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def make_teacher_public_case(self, student_consent_at=None):
        self.project.status = Project.Status.COMPLETED
        self.project.save(update_fields=["status"])
        self.material.status = Material.Status.APPROVED
        self.material.save(update_fields=["status"])
        approved = MaterialRevision.objects.create(
            material=self.material,
            author=self.student,
            content="可公开的实验结论",
            status=MaterialRevision.Status.APPROVED,
        )
        case = PublicCaseRequest.objects.create(
            project=self.project,
            applicant=self.teacher,
            request_type=PublicCaseRequest.RequestType.TEACHER_PLATFORM,
            visibility_scope=PublicCaseRequest.VisibilityScope.PLATFORM,
            public_summary="教师邀请公开的项目摘要",
            student_consent_at=student_consent_at,
        )
        case.selected_materials.add(self.material)
        return case

    def test_experiment_log_is_required_before_task_submit(self):
        response = self.client_for(self.student).post(
            f"/api/material-revisions/{self.revision.id}/submit/",
            {"truth_confirmed": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("实验日志", str(response.data))
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, MaterialRevision.Status.DRAFT)

    def test_teacher_cannot_review_a_project_guided_by_another_teacher(self):
        response = self.client_for(self.other_teacher).post(
            f"/api/material-revisions/{self.revision.id}/review/",
            {"outcome": "approved", "comment": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_student_case_requires_student_consent_before_platform_publication(self):
        case = self.make_teacher_public_case(student_consent_at=None)
        response = self.client_for(self.platform).post(
            f"/api/public-case-requests/{case.id}/set_visibility/",
            {"visible": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_ai_workspace_mode_and_project_free_generation_log_are_explicit(self):
        conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening")
        self.assertEqual(self.client_for(self.student).get(f"/api/ai-conversations/{conversation.id}/").data["workspace_mode"], "opening")
        log = AIGenerationLog.objects.create(
            project=None,
            actor=self.student,
            purpose="开题",
            prompt="帮助我找到研究问题",
        )
        self.assertIsNone(log.project_id)

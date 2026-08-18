from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Account, AuditEvent, Material, Project, ProjectTask, PublicCaseRequest, School


class WorkflowAuditTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="工作流审计学校")
        self.student = Account.objects.create_user(username="audit-student", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="audit-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            school=self.school, title="可追溯项目", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        task = ProjectTask.objects.create(
            project=self.project, stage_name="立项", title="问题定义", order=1,
            status=ProjectTask.Status.AVAILABLE,
        )
        self.material = Material.objects.create(project=self.project, task=task, title="问题定义")

    def client_for(self, user):
        client = APIClient(); client.force_authenticate(user)
        return client

    def test_submission_and_review_create_non_sensitive_audit_events(self):
        revision = self.client_for(self.student).post(
            "/api/material-revisions/", {"material": self.material.id, "content": "真实研究记录"}, format="json",
        )
        self.assertEqual(revision.status_code, 201)
        self.assertEqual(self.client_for(self.student).post(
            f"/api/material-revisions/{revision.data['id']}/submit/", {"truth_confirmed": True}, format="json",
        ).status_code, 200)
        self.assertEqual(self.client_for(self.teacher).post(
            f"/api/material-revisions/{revision.data['id']}/review/", {"outcome": "approved", "comment": "通过"}, format="json",
        ).status_code, 200)

        events = list(AuditEvent.objects.filter(school=self.school).order_by("created_at", "id"))
        self.assertEqual([event.action for event in events], [
            AuditEvent.Action.MATERIAL_SUBMITTED,
            AuditEvent.Action.MATERIAL_REVIEWED,
        ])
        self.assertNotIn("真实研究记录", str([event.changes for event in events]))

    def test_teacher_case_decision_audits_outcome_without_review_comment(self):
        self.project.status = Project.Status.COMPLETED
        self.project.save(update_fields=["status"])
        self.material.status = "approved"
        self.material.save(update_fields=["status"])
        case = PublicCaseRequest.objects.create(
            project=self.project, applicant=self.student, public_summary="公开研究结论",
        )
        case.selected_materials.add(self.material)

        response = self.client_for(self.teacher).post(
            f"/api/public-case-requests/{case.id}/teacher_reject/",
            {"comment": "请移除个人信息。"}, format="json",
        )

        self.assertEqual(response.status_code, 200)
        event = AuditEvent.objects.get(action=AuditEvent.Action.CASE_REVIEWED)
        self.assertEqual(event.changes["outcome"], "rejected")
        self.assertNotIn("请移除个人信息", str(event.changes))

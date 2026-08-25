from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Account, Material, MaterialRevision, Notification, Project, PublicCaseRequest, School


class CaseConsentFlowTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="成果链学校")
        self.student = Account.objects.create_user(username="case-flow-student", school=self.school, role=Account.Role.STUDENT)
        self.teacher = Account.objects.create_user(username="case-flow-teacher", school=self.school, role=Account.Role.TEACHER)
        self.platform = Account.objects.create_user(username="case-flow-platform", role=Account.Role.PLATFORM_ADMIN)
        self.project = Project.objects.create(
            school=self.school,
            title="校园观察成果",
            leader=self.student,
            primary_teacher=self.teacher,
            status=Project.Status.COMPLETED,
        )
        self.project.members.create(account=self.student, role="leader")
        self.material = Material.objects.create(project=self.project, title="结论", status=Material.Status.APPROVED)
        MaterialRevision.objects.create(
            material=self.material,
            author=self.student,
            content="真实且已审核的结论",
            status=MaterialRevision.Status.APPROVED,
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_teacher_platform_invite_waits_for_student_then_platform(self):
        teacher = self.client_for(self.teacher)
        created = teacher.post(
            "/api/public-case-requests/",
            {
                "project": self.project.id,
                "request_type": PublicCaseRequest.RequestType.TEACHER_PLATFORM,
                "visibility_scope": PublicCaseRequest.VisibilityScope.PLATFORM,
                "public_summary": "邀请公开的成果摘要",
                "selected_materials": [self.material.id],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        case_id = created.data["id"]
        self.assertEqual(created.data["status"], PublicCaseRequest.Status.WAITING_STUDENT)

        bypass = self.client_for(self.platform).post(
            f"/api/public-case-requests/{case_id}/set_visibility/", {"visible": True}, format="json",
        )
        self.assertEqual(bypass.status_code, 400)

        consent = self.client_for(self.student).post(
            f"/api/public-case-requests/{case_id}/student_consent/", {}, format="json",
        )
        self.assertEqual(consent.status_code, 200)
        self.assertEqual(consent.data["status"], PublicCaseRequest.Status.PENDING_PLATFORM)
        self.assertTrue(Notification.objects.filter(recipient=self.teacher, kind=Notification.Kind.CASE_PENDING_PLATFORM).exists())

        reviewed = self.client_for(self.platform).post(
            f"/api/public-case-requests/{case_id}/platform_review/", {"approved": True}, format="json",
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.data["status"], PublicCaseRequest.Status.PUBLISHED)

    def test_student_school_application_stays_school_scoped(self):
        created = self.client_for(self.student).post(
            "/api/public-case-requests/",
            {
                "project": self.project.id,
                "request_type": PublicCaseRequest.RequestType.STUDENT_SCHOOL,
                "visibility_scope": PublicCaseRequest.VisibilityScope.SCHOOL,
                "public_summary": "校内展示摘要",
                "selected_materials": [self.material.id],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        approved = self.client_for(self.teacher).post(
            f"/api/public-case-requests/{created.data['id']}/teacher_approve/",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["visibility_scope"], PublicCaseRequest.VisibilityScope.SCHOOL)

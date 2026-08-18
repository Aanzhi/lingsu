from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    AuditEvent,
    MemberInvitation,
    Project,
    ProjectMember,
    School,
)
from apps.core.workflows.memberships import assign_member


class TeacherAssignMemberTests(TestCase):
    """教师一步直接把本校学生加入自己指导的项目（无需学生二次确认）。"""

    def setUp(self):
        self.school = School.objects.create(name="组队测试学校")
        self.other_school = School.objects.create(name="外校")
        self.leader = Account.objects.create_user(username="tm-leader", school=self.school, role=Account.Role.STUDENT)
        self.teacher = Account.objects.create_user(username="tm-teacher", school=self.school, role=Account.Role.TEACHER)
        self.other_teacher = Account.objects.create_user(username="tm-other-teacher", school=self.school, role=Account.Role.TEACHER)
        self.outsider = Account.objects.create_user(username="tm-outsider", school=self.other_school, role=Account.Role.STUDENT)
        self.outsider_teacher = Account.objects.create_user(username="tm-outsider-teacher", school=self.other_school, role=Account.Role.TEACHER)
        self.candidate = Account.objects.create_user(username="tm-candidate", school=self.school, role=Account.Role.STUDENT)

        self.project = Project.objects.create(
            school=self.school, title="组队项目", leader=self.leader,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.leader, role="leader")

        self.unclaimed = Project.objects.create(
            school=self.school, title="未认领项目", leader=self.leader, status=Project.Status.UNCLAIMED,
        )
        self.unclaimed.members.create(account=self.leader, role="leader")

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def _url(self, project_id):
        return f"/api/projects/{project_id}/add_member/"

    def test_teacher_assigns_member_directly(self):
        response = self.client_for(self.teacher).post(
            self._url(self.project.id), {"invitee": self.candidate.id}, format="json",
        )
        self.assertEqual(response.status_code, 201)
        member = ProjectMember.objects.get(project=self.project, account=self.candidate)
        self.assertEqual(member.role, "member")
        invitation = MemberInvitation.objects.get(project=self.project, invitee=self.candidate)
        self.assertEqual(invitation.status, MemberInvitation.Status.APPROVED)
        self.assertEqual(invitation.inviter_id, self.teacher.id)
        self.assertTrue(AuditEvent.objects.filter(
            action=AuditEvent.Action.MEMBER_ASSIGNED, actor=self.teacher, school=self.school,
        ).exists())

    def test_unauthorized_school_teacher_rejected(self):
        self.school.license_expires_at = timezone.localdate() - timedelta(days=1)
        self.school.save(update_fields=["license_expires_at"])
        response = self.client_for(self.teacher).post(
            self._url(self.project.id), {"invitee": self.candidate.id}, format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ProjectMember.objects.filter(project=self.project, account=self.candidate).exists())

    def test_unclaimed_project_rejected(self):
        parked = Project.objects.create(
            school=self.school, title="有教师未启动", leader=self.leader,
            primary_teacher=self.teacher, status=Project.Status.UNCLAIMED,
        )
        with self.assertRaises(ValidationError):
            assign_member(parked, self.teacher, self.candidate)

    def test_non_primary_teacher_rejected(self):
        with self.assertRaises(PermissionDenied):
            assign_member(self.project, self.other_teacher, self.candidate)

    def test_out_of_school_student_rejected(self):
        response = self.client_for(self.teacher).post(
            self._url(self.project.id), {"invitee": self.outsider.id}, format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ProjectMember.objects.filter(project=self.project, account=self.outsider).exists())

    def test_non_student_invitee_rejected(self):
        response = self.client_for(self.teacher).post(
            self._url(self.project.id), {"invitee": self.outsider_teacher.id}, format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_assign_idempotent_for_same_student(self):
        first = self.client_for(self.teacher).post(
            self._url(self.project.id), {"invitee": self.candidate.id}, format="json",
        )
        self.assertEqual(first.status_code, 201)
        second = self.client_for(self.teacher).post(
            self._url(self.project.id), {"invitee": self.candidate.id}, format="json",
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(ProjectMember.objects.filter(project=self.project, account=self.candidate).count(), 1)
        self.assertEqual(MemberInvitation.objects.filter(project=self.project, invitee=self.candidate).count(), 1)

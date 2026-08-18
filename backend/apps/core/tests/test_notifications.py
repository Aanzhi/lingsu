from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    Material,
    MaterialRevision,
    MemberInvitation,
    Notification,
    Project,
    ProjectTask,
    School,
)
from apps.core.notifiers import notify
from apps.core.workflows.materials import review_material_revision
from apps.core.workflows.memberships import respond_to_invitation


class NotificationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="通知学校", invite_code="NOTIF")
        self.teacher = Account.objects.create_user(username="notif-teacher", school=self.school, role=Account.Role.TEACHER)
        self.leader = Account.objects.create_user(username="notif-leader", school=self.school, role=Account.Role.STUDENT)
        self.invitee = Account.objects.create_user(username="notif-invitee", school=self.school, role=Account.Role.STUDENT)
        self.project = Project.objects.create(
            school=self.school, title="通知项目", leader=self.leader,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.leader, role="leader")

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_notify_creates_row_for_recipient(self):
        note = notify(
            self.leader, kind=Notification.Kind.MEMBER_ASSIGNED, title="你被加入项目",
            actor=self.teacher, project=self.project,
        )
        self.assertIsNotNone(note)
        self.assertEqual(Notification.objects.filter(recipient=self.leader).count(), 1)
        self.assertEqual(note.kind, Notification.Kind.MEMBER_ASSIGNED)

    def test_invitation_accept_notifies_leader(self):
        invitation = MemberInvitation.objects.create(
            project=self.project, invitee=self.invitee, inviter=self.leader,
            status=MemberInvitation.Status.PENDING_STUDENT,
        )
        respond_to_invitation(invitation, self.invitee, accept=True)
        note = Notification.objects.filter(
            recipient=self.leader, kind=Notification.Kind.INVITATION_ACCEPTED,
        ).first()
        self.assertIsNotNone(note)
        self.assertIn(self.invitee.username, note.title)

    def test_material_approval_notifies_leader(self):
        task = ProjectTask.objects.create(
            project=self.project, stage_name="阶段", title="任务", order=1,
            status=ProjectTask.Status.AVAILABLE,
        )
        material = Material.objects.create(
            project=self.project, task=task, title="材料A", status=Material.Status.DRAFT,
        )
        revision = MaterialRevision.objects.create(
            material=material, author=self.leader, content="正文",
            status=MaterialRevision.Status.SUBMITTED, truth_confirmed=True,
        )
        review_material_revision(revision, self.teacher, "approved", "")
        note = Notification.objects.filter(
            recipient=self.leader, kind=Notification.Kind.MATERIAL_APPROVED,
        ).first()
        self.assertIsNotNone(note)
        self.assertIn("材料A", note.title)

    def test_teacher_recipient_gets_teacher_route_link(self):
        # 收件人是教师时，/student/... 链接应改写为 /teacher/...，避免点击后 SPA 内 404
        note = notify(
            self.teacher, kind=Notification.Kind.MEMBER_ASSIGNED,
            title="你被加入项目", link="/student/projects/7",
            actor=self.leader, project=self.project,
        )
        self.assertIsNotNone(note)
        self.assertEqual(note.link, "/teacher/projects/7")
        # 学生收件人保持原样
        student_note = notify(
            self.leader, kind=Notification.Kind.MEMBER_ASSIGNED,
            title="你被加入项目", link="/student/projects/7",
            actor=self.teacher, project=self.project,
        )
        self.assertEqual(student_note.link, "/student/projects/7")

    def test_notification_endpoint_scoped_and_mark_read(self):
        notify(self.leader, kind=Notification.Kind.MEMBER_ASSIGNED, title="给leader")
        notify(self.invitee, kind=Notification.Kind.MEMBER_ASSIGNED, title="给invitee")

        leader_client = self._client(self.leader)
        data = leader_client.get("/api/notifications/").data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "给leader")

        note_id = data[0]["id"]
        resp = leader_client.post(f"/api/notifications/{note_id}/mark_read/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["is_read"])

        invitee_client = self._client(self.invitee)
        self.assertEqual(len(invitee_client.get("/api/notifications/").data), 1)
        invitee_client.post("/api/notifications/mark_all_read/")
        self.assertEqual(Notification.objects.filter(recipient=self.invitee, is_read=False).count(), 0)

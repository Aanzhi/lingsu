from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.core.models import Account, AuditEvent, Project, School
from apps.core.tasks import purge_trashed_project_records


class TrashedProjectPurgeTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="回收站学校")
        self.student = Account.objects.create_user(username="purge-student", school=self.school, role=Account.Role.STUDENT)
        self.project = Project.objects.create(
            school=self.school, title="到期回收项目", leader=self.student,
            status=Project.Status.ACTIVE,
            deleted_at=timezone.now() - timedelta(days=31),
            trashed_at=timezone.now() - timedelta(days=31),
        )
        self.project.members.create(account=self.student, role="leader")

    def test_dry_run_does_not_delete_or_audit(self):
        result = purge_trashed_project_records(retention_days=30, dry_run=True)
        self.assertEqual(result["purged"], 1)
        self.assertTrue(Project.all_objects.filter(pk=self.project.id).exists())
        self.assertFalse(AuditEvent.objects.filter(action=AuditEvent.Action.PROJECT_PURGED).exists())

    def test_expired_project_is_deleted_and_keeps_audit_summary(self):
        result = purge_trashed_project_records(retention_days=30)
        self.assertEqual(result["purged"], 1)
        self.assertFalse(Project.all_objects.filter(pk=self.project.id).exists())
        event = AuditEvent.objects.get(action=AuditEvent.Action.PROJECT_PURGED)
        self.assertEqual(event.changes["project_id"], self.project.id)
        self.assertEqual(event.changes["title"], "到期回收项目")

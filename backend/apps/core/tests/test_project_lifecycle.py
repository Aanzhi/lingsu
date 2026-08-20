from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Account, AuditEvent, Project, School
from apps.core.tasks import purge_trashed_projects


class ProjectLifecycleTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="生命周期学校")
        self.teacher = Account.objects.create_user(username="guide-life", school=self.school, role=Account.Role.TEACHER)
        self.student = Account.objects.create_user(username="student-life", school=self.school, role=Account.Role.STUDENT)
        self.other_student = Account.objects.create_user(username="other-life", school=self.school, role=Account.Role.STUDENT)
        self.project = Project.objects.create(
            school=self.school,
            title="我的项目",
            leader=self.student,
            primary_teacher=self.teacher,
        )
        self.project.members.create(account=self.student, role="leader")

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_default_listing_excludes_archived_and_trashed_projects(self):
        completed = Project.objects.create(school=self.school, title="已完成", leader=self.student, primary_teacher=self.teacher, status=Project.Status.COMPLETED)
        completed.is_archived = True
        completed.archived_at = timezone.now()
        completed.save(update_fields=["is_archived", "archived_at"])
        trashed = Project.objects.create(school=self.school, title="回收站", leader=self.student, primary_teacher=self.teacher)
        trashed.deleted_at = timezone.now()
        trashed.trashed_at = timezone.now()
        trashed.save(update_fields=["deleted_at", "trashed_at"])

        client = self._client(self.student)
        data = client.get("/api/projects/").data
        self.assertEqual([p["title"] for p in data], ["我的项目"])

        data = client.get("/api/projects/?include_archived=1").data
        titles = sorted(p["title"] for p in data)
        self.assertEqual(titles, sorted(["我的项目", "已完成"]))

        data = client.get("/api/projects/?only_archived=1").data
        self.assertEqual([p["title"] for p in data], ["已完成"])

        trashed_data = client.get("/api/projects/trashed/").data
        self.assertEqual([p["title"] for p in trashed_data], ["回收站"])

    def test_student_can_soft_delete_and_restore_their_own_project(self):
        client = self._client(self.student)
        self.assertEqual(client.post(f"/api/projects/{self.project.id}/trash/").status_code, 200)
        self.project.refresh_from_db()
        self.assertIsNotNone(self.project.deleted_at)

        self.assertEqual(client.get("/api/projects/").data, [])
        self.assertEqual(client.get("/api/projects/trashed/").data[0]["id"], self.project.id)

        self.assertEqual(client.post(f"/api/projects/{self.project.id}/restore/").status_code, 200)
        self.project.refresh_from_db()
        self.assertIsNone(self.project.deleted_at)

    def test_archived_project_can_only_be_restored_by_owner(self):
        self.project.status = Project.Status.COMPLETED
        self.project.save(update_fields=["status"])
        client = self._client(self.student)

        self.assertEqual(client.post(f"/api/projects/{self.project.id}/archive/").status_code, 200)
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_archived)
        self.assertIsNotNone(self.project.archived_at)

        client = client = self._client(self.student)
        data = client.get("/api/projects/?include_archived=1").data
        self.assertEqual([p["id"] for p in data], [self.project.id])

        other_client = self._client(self.other_student)
        # Non-members receive 404 since the project is not in their accessible queryset.
        self.assertIn(other_client.post(f"/api/projects/{self.project.id}/unarchive/").status_code, (403, 404))

        owner_client = self._client(self.student)
        self.assertEqual(owner_client.post(f"/api/projects/{self.project.id}/unarchive/").status_code, 200)
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_archived)

    def test_set_primary_marks_only_one_project_per_student(self):
        extra = Project.objects.create(school=self.school, title="第二项目", leader=self.student, primary_teacher=self.teacher)
        extra.members.create(account=self.student, role="member")
        client = self._client(self.student)

        self.assertEqual(client.post(f"/api/projects/{self.project.id}/set_primary/").status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.primary_project_id, self.project.id)
        self.assertTrue(client.get("/api/projects/").data[0]["is_primary"])

        self.assertEqual(client.post(f"/api/projects/{extra.id}/set_primary/").status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.primary_project_id, extra.id)

    def test_purge_trashed_projects_removes_only_expired_records(self):
        old = Project.objects.create(school=self.school, title="已过期", leader=self.student, primary_teacher=self.teacher)
        old.deleted_at = timezone.now() - timedelta(days=31)
        old.trashed_at = timezone.now() - timedelta(days=31)
        old.save(update_fields=["deleted_at", "trashed_at"])
        fresh = Project.objects.create(school=self.school, title="新近删除", leader=self.student, primary_teacher=self.teacher)
        fresh.deleted_at = timezone.now() - timedelta(days=2)
        fresh.trashed_at = timezone.now() - timedelta(days=2)
        fresh.save(update_fields=["deleted_at", "trashed_at"])

        result = purge_trashed_projects(retention_days=30)
        self.assertEqual(result["purged"], 1)
        self.assertIn(old.id, result["ids"])
        self.assertFalse(Project.all_objects.filter(pk=old.id).exists())
        self.assertTrue(Project.all_objects.filter(pk=fresh.id).exists())

    def test_me_endpoint_exposes_primary_project_and_school(self):
        self.student.primary_project = self.project
        self.student.save(update_fields=["primary_project"])
        client = self._client(self.student)
        data = client.get("/api/me/").data
        self.assertEqual(data["school_name"], "生命周期学校")
        self.assertEqual(data["primary_project"], self.project.id)
        self.assertEqual(data["primary_project_title"], self.project.title)

    def test_leader_can_update_basics_and_audit_is_written(self):
        client = self._client(self.student)
        resp = client.post(
            f"/api/projects/{self.project.id}/update_basics/",
            {"title": "新标题", "problem": "新问题", "plan": "新方案", "summary": "新总结"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "新标题")
        self.assertEqual(self.project.problem, "新问题")
        self.assertEqual(self.project.plan, "新方案")
        self.assertEqual(self.project.summary, "新总结")
        event = AuditEvent.objects.get(action=AuditEvent.Action.PROJECT_UPDATED)
        self.assertIn("title", event.changes["fields"])

    def test_non_leader_cannot_update_basics(self):
        client = self._client(self.other_student)
        resp = client.post(
            f"/api/projects/{self.project.id}/update_basics/",
            {"title": "越权标题"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "我的项目")

    def test_update_basics_rejects_empty_title(self):
        client = self._client(self.student)
        resp = client.post(
            f"/api/projects/{self.project.id}/update_basics/",
            {"title": "   "}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

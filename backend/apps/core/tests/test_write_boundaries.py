from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    Announcement,
    Material,
    Project,
    ProjectTask,
    School,
    Template,
)


class WriteBoundaryTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="写入边界学校")
        self.student = Account.objects.create_user(
            username="boundary-student", school=self.school, role=Account.Role.STUDENT,
        )
        self.teacher = Account.objects.create_user(
            username="boundary-teacher", school=self.school, role=Account.Role.TEACHER,
        )
        self.project = Project.objects.create(
            school=self.school,
            title="任务状态边界",
            leader=self.student,
            primary_teacher=self.teacher,
            status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def expire_school(self):
        self.school.license_expires_at = timezone.localdate() - timedelta(days=1)
        self.school.save(update_fields=["license_expires_at"])

    def test_expired_school_teacher_cannot_create_or_update_templates(self):
        template = Template.objects.create(
            school=self.school, owner=self.teacher, name="原模板", is_published=True,
        )
        self.expire_school()
        client = self.client_for(self.teacher)

        created = client.post("/api/templates/", {"name": "不应创建"}, format="json")
        updated = client.patch(
            f"/api/templates/{template.id}/", {"name": "不应修改"}, format="json",
        )

        self.assertEqual(created.status_code, 403)
        self.assertEqual(updated.status_code, 403)
        template.refresh_from_db()
        self.assertEqual(template.name, "原模板")

    def test_expired_school_teacher_cannot_update_or_delete_announcement(self):
        announcement = Announcement.objects.create(
            school=self.school,
            author=self.teacher,
            title="原公告",
            body="原内容",
            audience=Announcement.Audience.STUDENTS,
            status=Announcement.Status.PUBLISHED,
        )
        self.expire_school()
        client = self.client_for(self.teacher)

        updated = client.patch(
            f"/api/announcements/{announcement.id}/", {"title": "不应修改"}, format="json",
        )
        deleted = client.delete(f"/api/announcements/{announcement.id}/")

        self.assertEqual(updated.status_code, 403)
        self.assertEqual(deleted.status_code, 403)
        self.assertTrue(Announcement.objects.filter(pk=announcement.id, title="原公告").exists())

    def test_student_cannot_create_revision_before_project_is_claimed(self):
        unclaimed = Project.objects.create(
            school=self.school, title="尚未认领", leader=self.student,
            status=Project.Status.UNCLAIMED,
        )
        unclaimed.members.create(account=self.student, role="leader")
        material = Material.objects.create(project=unclaimed, title="异常材料")

        response = self.client_for(self.student).post(
            "/api/material-revisions/",
            {"material": material.id, "content": "不应进入正式材料流程"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("尚未由教师认领并启动", str(response.data))

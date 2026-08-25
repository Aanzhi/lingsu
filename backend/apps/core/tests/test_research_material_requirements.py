from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Account, Material, MaterialRevision, Project, ProjectTask, School


class ResearchMaterialRequirementTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="实验日志学校")
        self.student = Account.objects.create_user(username="log-student", school=self.school, role=Account.Role.STUDENT)
        self.teacher = Account.objects.create_user(username="log-teacher", school=self.school, role=Account.Role.TEACHER)
        self.project = Project.objects.create(
            school=self.school, title="日志项目", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        self.task = ProjectTask.objects.create(
            project=self.project, stage_name="实验", title="完成实验记录", order=1,
            status=ProjectTask.Status.AVAILABLE,
        )
        self.result = Material.objects.create(project=self.project, task=self.task, title="实验结论", kind="standard")
        self.log = Material.objects.create(project=self.project, task=self.task, title="实验日志", kind="experiment_log")

    def test_filled_experiment_log_unblocks_submission(self):
        result_revision = MaterialRevision.objects.create(
            material=self.result, author=self.student, content="结果正文", status=MaterialRevision.Status.DRAFT,
        )
        MaterialRevision.objects.create(
            material=self.log, author=self.student, content="日期：2026-08-25；观察：积水减少。", status=MaterialRevision.Status.DRAFT,
        )
        client = APIClient(); client.force_authenticate(self.student)
        response = client.post(
            f"/api/material-revisions/{result_revision.id}/submit/", {"truth_confirmed": True}, format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_missing_experiment_log_keeps_revision_draft(self):
        revision = MaterialRevision.objects.create(
            material=self.result, author=self.student, content="结果正文", status=MaterialRevision.Status.DRAFT,
        )
        client = APIClient(); client.force_authenticate(self.student)
        response = client.post(
            f"/api/material-revisions/{revision.id}/submit/", {"truth_confirmed": True}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("实验日志", str(response.data))
        revision.refresh_from_db()
        self.assertEqual(revision.status, MaterialRevision.Status.DRAFT)

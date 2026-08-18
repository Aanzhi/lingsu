from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Account, Material, MaterialRevision, Project, ProjectGrowth, ProjectTask, School


class GrowthSemanticsTests(TestCase):
    def setUp(self):
        school = School.objects.create(name="成长语义学校")
        self.student = Account.objects.create_user(username="growth-student", school=school, role="student")
        self.teacher = Account.objects.create_user(username="growth-teacher", school=school, role="teacher")
        self.project = Project.objects.create(school=school, title="成长项目", leader=self.student, primary_teacher=self.teacher, status="active")
        self.project.members.create(account=self.student, role="leader")
        self.client = APIClient(); self.client.force_authenticate(self.teacher)

    def _revision(self, order):
        task = ProjectTask.objects.create(project=self.project, stage_name="阶段", title=f"任务 {order}", order=order, status="pending_review", xp_reward=100)
        material = Material.objects.create(project=self.project, task=task, title=f"材料 {order}", status="submitted", required=True)
        return MaterialRevision.objects.create(material=material, author=self.student, content="真实证据", truth_confirmed=True, status="submitted")

    def test_same_day_approvals_only_count_one_streak_activity(self):
        first = self._revision(1)
        second = self._revision(2)
        self.assertEqual(self.client.post(f"/api/material-revisions/{first.id}/review/", {"outcome": "approved", "comment": "通过"}, format="json").status_code, 200)
        self.assertEqual(self.client.post(f"/api/material-revisions/{second.id}/review/", {"outcome": "approved", "comment": "通过"}, format="json").status_code, 200)
        growth = ProjectGrowth.objects.get(project=self.project)
        self.assertEqual(growth.experience, 100)
        self.assertEqual(growth.streak_days, 1)
        self.assertEqual(growth.last_activity_date, date.today())

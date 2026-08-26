import os
from unittest.mock import patch

from django.core import management
from django.test import TestCase, override_settings

from apps.core.models import Account, Material, Project, ProjectTask, School, Template


class CoreE2ESeedCommandTests(TestCase):
    @override_settings(DEBUG=False)
    @patch.dict(os.environ, {"LINGSU_E2E_SEED": "1"})
    def test_seed_creates_an_isolated_core_flow_fixture(self):
        management.call_command(
            "seed_core_e2e",
            "--reset",
            "--password",
            "core-e2e-pass-2026",
            verbosity=0,
        )

        school = School.objects.get(name="灵溯核心闭环测试学校")
        student = Account.objects.get(username="core-e2e-student")
        member = Account.objects.get(username="core-e2e-member")
        direct = Account.objects.get(username="core-e2e-direct")
        teacher = Account.objects.get(username="core-e2e-teacher")
        platform = Account.objects.get(username="core-e2e-platform")
        project = Project.objects.get(title="核心闭环验收项目")
        public_project = Project.objects.get(title="核心公域验收项目")

        self.assertEqual(student.school_id, school.id)
        self.assertEqual(member.school_id, school.id)
        self.assertEqual(direct.school_id, school.id)
        self.assertEqual(teacher.school_id, school.id)
        self.assertIsNone(platform.school_id)
        self.assertTrue(student.check_password("core-e2e-pass-2026"))
        self.assertEqual(project.school_id, school.id)
        self.assertEqual(project.leader_id, student.id)
        self.assertIsNone(project.primary_teacher_id)
        self.assertEqual(project.status, Project.Status.UNCLAIMED)
        self.assertEqual(project.members.get(account=student).role, "leader")
        self.assertEqual(public_project.status, Project.Status.COMPLETED)
        self.assertEqual(Material.objects.filter(project=public_project, status="approved").count(), 1)

        pool_projects = Project.objects.filter(
            school=school, title__startswith="核心项目池验收 ", status=Project.Status.UNCLAIMED,
        ).order_by("title")
        guided_projects = Project.objects.filter(
            school=school, title__startswith="核心指导项目验收 ",
            status=Project.Status.ACTIVE, primary_teacher=teacher,
        ).order_by("title")
        self.assertEqual(pool_projects.count(), 4)
        self.assertEqual(guided_projects.count(), 4)
        self.assertEqual(pool_projects.first().problem, "如何验证校园观察问题 1 的关键变量？")
        self.assertEqual(guided_projects.first().summary, "指导项目确定性样本 1，用于验证教师工作台的完整列表。")
        self.assertTrue(all(project.members.filter(account=student).exists() for project in pool_projects))
        self.assertTrue(all(project.members.filter(account=student).exists() for project in guided_projects))

        template = Template.objects.get(school=school, name="核心闭环验收模板")
        self.assertTrue(template.is_published)
        tasks = list(ProjectTask.objects.filter(project=project).order_by("order"))
        self.assertEqual(tasks, [])
        self.assertEqual(template.stages.count(), 22)
        self.assertEqual(Template.objects.get(pk=template.id).stages.filter(tasks__isnull=False).count(), 2)

        management.call_command(
            "seed_core_e2e",
            "--password",
            "core-e2e-pass-2026",
            verbosity=0,
        )
        self.assertEqual(School.objects.filter(name="灵溯核心闭环测试学校").count(), 1)
        self.assertEqual(Account.objects.filter(username__startswith="core-e2e-").count(), 5)

    @override_settings(DEBUG=False)
    def test_seed_refuses_to_run_without_explicit_e2e_environment_flag(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(management.CommandError):
                management.call_command("seed_core_e2e", verbosity=0)

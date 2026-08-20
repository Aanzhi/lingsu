from datetime import date, timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    Competition,
    Material,
    MaterialAttachment,
    Project,
    ProjectTask,
    School,
    Template,
    TemplateMaterial,
    TemplateStage,
    TemplateTask,
)
from apps.core.services import DEFAULT_TEMPLATE_BLUEPRINTS


class ProductionContractTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="灵川中学",
            invite_code="LINGCHUAN",
            license_expires_at=date.today() + timedelta(days=365),
        )
        self.student = Account.objects.create_user(
            username="student-a", password="correct-pass-123", school=self.school,
            role=Account.Role.STUDENT, must_change_password=False,
        )
        self.other_student = Account.objects.create_user(
            username="student-b", password="correct-pass-123", school=self.school,
            role=Account.Role.STUDENT, must_change_password=False,
        )
        self.teacher = Account.objects.create_user(
            username="teacher-a", password="correct-pass-123", school=self.school,
            role=Account.Role.TEACHER, must_change_password=False,
        )
        self.platform = Account.objects.create_user(
            username="platform-a", password="correct-pass-123",
            role=Account.Role.PLATFORM_ADMIN, must_change_password=False,
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_compose_backend_startup_resets_global_ai_agent_templates_after_migrations(self):
        compose = (
            Path(__file__).resolve().parents[4] / "docker-compose.yml"
        ).read_text(encoding="utf-8")

        migrate_index = compose.index("python manage.py migrate --noinput")
        seed_index = compose.index("python manage.py seed_ai_agents --reset")
        self.assertLess(migrate_index, seed_index)

    def test_real_session_login_and_logout(self):
        client = APIClient()
        response = client.post(
            "/api/login/",
            {"username": "student-a", "password": "correct-pass-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "student")
        self.assertEqual(client.get("/api/me/").status_code, 200)
        self.assertEqual(client.post("/api/logout/").status_code, 204)
        self.assertEqual(client.get("/api/me/").status_code, 403)

    def test_restored_session_receives_csrf_cookie_and_can_logout(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="student-a", password="correct-pass-123"))
        restored = client.get("/api/me/")
        self.assertEqual(restored.status_code, 200)
        self.assertIn("csrftoken", restored.cookies)
        token = restored.cookies["csrftoken"].value
        self.assertEqual(client.post("/api/logout/", HTTP_X_CSRFTOKEN=token).status_code, 204)

    def test_platform_cannot_enter_school_project_or_material_data(self):
        project = Project.objects.create(
            school=self.school, title="校内项目", leader=self.student,
            status=Project.Status.ACTIVE,
        )
        Material.objects.create(project=project, title="内部材料")
        client = self.client_for(self.platform)
        self.assertEqual(client.get("/api/projects/").status_code, 403)
        self.assertEqual(client.get("/api/materials/").status_code, 403)
        self.assertEqual(client.get("/api/material-revisions/").status_code, 403)
        self.assertEqual(client.get("/api/member-invitations/").status_code, 403)
        self.assertEqual(client.get("/api/proposals/").status_code, 404)

    def test_legacy_proposal_endpoint_is_no_longer_exposed(self):
        response = self.client_for(self.student).get("/api/proposals/")

        self.assertEqual(response.status_code, 404)

    def test_generic_mutations_cannot_bypass_project_workflows(self):
        project = Project.objects.create(
            school=self.school, title="不可绕过流程", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        project.members.create(account=self.student, role="leader")
        material = Material.objects.create(project=project, title="模板生成材料")

        student_client = self.client_for(self.student)
        self.assertEqual(
            student_client.patch(f"/api/projects/{project.id}/", {"title": "绕过"}, format="json").status_code,
            403,
        )
        self.assertEqual(student_client.delete(f"/api/projects/{project.id}/").status_code, 403)
        self.assertEqual(
            student_client.post("/api/materials/", {"project": project.id, "title": "任意材料"}, format="json").status_code,
            405,
        )

        teacher_client = self.client_for(self.teacher)
        self.assertEqual(
            teacher_client.post("/api/material-revisions/", {"material": material.id, "content": "冒充学生"}, format="json").status_code,
            403,
        )

    def test_claim_and_review_actions_are_idempotent_at_workflow_boundary(self):
        project = Project.objects.create(school=self.school, title="唯一认领", leader=self.student)
        project.members.create(account=self.student, role="leader")
        teacher_client = self.client_for(self.teacher)
        first = teacher_client.post(f"/api/projects/{project.id}/claim/")
        second = teacher_client.post(f"/api/projects/{project.id}/claim/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        # The default "research" blueprint expands to its configured stage count
        # (10 stages -> 10 tasks). Derive from the blueprint so the assertion
        # stays correct if the blueprint is revised.
        expected_tasks = len(DEFAULT_TEMPLATE_BLUEPRINTS["research"][1])
        self.assertEqual(ProjectTask.objects.filter(project=project).count(), expected_tasks)

    def test_project_is_completed_when_the_final_required_task_is_approved(self):
        project = Project.objects.create(
            school=self.school, title="完成状态", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        project.members.create(account=self.student, role="leader")
        task = ProjectTask.objects.create(
            project=project, stage_name="答辩与展示", title="最终任务",
            order=1, status=ProjectTask.Status.PENDING_REVIEW,
        )
        material = Material.objects.create(
            project=project, task=task, title="最终材料", status="submitted", required=True,
        )
        from apps.core.models import MaterialRevision
        revision = MaterialRevision.objects.create(
            material=material, author=self.student, content="最终成果", truth_confirmed=True, status="submitted",
        )

        response = self.client_for(self.teacher).post(
            f"/api/material-revisions/{revision.id}/review/",
            {"outcome": "approved", "comment": "完成"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.COMPLETED)

    def test_same_school_non_member_cannot_read_project_materials(self):
        project = Project.objects.create(
            school=self.school, title="私有项目", leader=self.student,
            status=Project.Status.ACTIVE,
        )
        material = Material.objects.create(project=project, title="私有材料")
        client = self.client_for(self.other_student)
        self.assertEqual(client.get("/api/materials/").data, [])
        self.assertEqual(client.get(f"/api/materials/{material.id}/").status_code, 404)

    def test_teacher_claim_instantiates_project_tasks_and_materials_from_template(self):
        template = Template.objects.create(
            school=self.school, name="研究型", category="research",
            is_published=True, owner=self.teacher,
        )
        stage = TemplateStage.objects.create(template=template, name="发现与立项", order=1)
        task = TemplateTask.objects.create(
            stage=stage, name="问题定义", order=1, description="形成可研究的问题",
        )
        TemplateMaterial.objects.create(
            task=task, title="问题定义材料", required=True,
            report_section="研究问题", order=1,
        )
        student_client = self.client_for(self.student)
        created = student_client.post(
            "/api/projects/",
            {
                "title": "校园积水研究",
                "problem": "雨后哪些位置最容易积水？",
                "plan": "连续观察并记录降雨量与消退时间。",
                "project_type": "research",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "unclaimed")
        self.assertEqual(created.data["problem"], "雨后哪些位置最容易积水？")
        self.assertEqual(created.data["plan"], "连续观察并记录降雨量与消退时间。")

        teacher_client = self.client_for(self.teacher)
        claimed = teacher_client.post(
            f"/api/projects/{created.data['id']}/claim/",
            {"template": template.id},
            format="json",
        )
        self.assertEqual(claimed.status_code, 200)
        project_task = ProjectTask.objects.get(project_id=created.data["id"])
        self.assertEqual(project_task.status, ProjectTask.Status.AVAILABLE)
        self.assertEqual(project_task.stage_name, "发现与立项")
        self.assertTrue(Material.objects.filter(project_id=created.data["id"], task=project_task).exists())

    def test_platform_publishes_global_competition_and_students_can_only_read_it(self):
        platform_client = self.client_for(self.platform)
        created = platform_client.post(
            "/api/competitions/",
            {"title": "全国青少年创新赛", "status": "published", "audience": "all"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertIsNone(Competition.objects.get(pk=created.data["id"]).school_id)

        student_client = self.client_for(self.student)
        self.assertEqual(student_client.get("/api/competitions/").data[0]["title"], "全国青少年创新赛")
        self.assertEqual(
            student_client.patch(f"/api/competitions/{created.data['id']}/", {"title": "篡改"}, format="json").status_code,
            403,
        )

    def test_material_revision_supports_multiple_private_attachment_records(self):
        project = Project.objects.create(
            school=self.school, title="上传测试", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        material = Material.objects.create(project=project, title="观察记录")
        client = self.client_for(self.student)
        response = client.post(
            "/api/material-revisions/",
            {
                "material": material.id,
                "content": "真实观察内容",
                "uploaded_files": [
                    SimpleUploadedFile("记录.txt", b"record", content_type="text/plain"),
                    SimpleUploadedFile("数据.csv", b"x,y\n1,2", content_type="text/csv"),
                ],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(MaterialAttachment.objects.filter(revision_id=response.data["id"]).count(), 2)
        self.assertEqual(len(response.data["attachments"]), 2)

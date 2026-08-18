"""Tests for material reference templates (guidance + reference file)."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    Material,
    Project,
    School,
    Template,
    TemplateMaterial,
    TemplateStage,
    TemplateTask,
)
from apps.core.services import DEFAULT_TEMPLATE_BLUEPRINTS, get_or_create_default_template


class MaterialReferenceTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="ref-school", is_active=True)
        self.student = Account.objects.create_user(
            username="ref-student", password="test-pass-123", school=self.school, role=Account.Role.STUDENT,
        )
        self.teacher = Account.objects.create_user(
            username="ref-teacher", password="test-pass-123", school=self.school, role=Account.Role.TEACHER,
        )
        self.other_teacher = Account.objects.create_user(
            username="ref-teacher2", password="test-pass-123", school=self.school, role=Account.Role.TEACHER,
        )
        self.admin = Account.objects.create_user(
            username="ref-admin", password="test-pass-123", school=self.school, role=Account.Role.PLATFORM_ADMIN,
        )
        self.project = Project.objects.create(
            school=self.school, title="参考模板测试项目", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        template = Template.objects.create(school=self.school, category="research", name="t", is_published=False)
        stage = TemplateStage.objects.create(template=template, name="s", order=1)
        task = TemplateTask.objects.create(stage=stage, name="task", order=1)
        self.tmpl = TemplateMaterial.objects.create(task=task, title="材料", required=True, guidance="默认系统指引")
        self.material = Material.objects.create(
            project=self.project, task=None, template_material=self.tmpl, title="材料", report_order=1,
        )

    # --- effective guidance fallback ---
    def test_effective_guidance_falls_back_to_template(self):
        self.assertEqual(self.material.effective_guidance, "默认系统指引")
        self.material.guidance_override = "教师覆盖指引"
        self.material.save()
        self.assertEqual(self.material.effective_guidance, "教师覆盖指引")

    def test_effective_reference_none_without_files(self):
        file_field, name = self.material.effective_reference
        self.assertIsNone(file_field)
        self.assertIsNone(name)

    # --- reference GET action ---
    def test_reference_action_returns_guidance(self):
        client = APIClient()
        client.force_authenticate(self.teacher)
        resp = client.get(f"/api/materials/{self.material.id}/reference/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["guidance"], "默认系统指引")
        self.assertTrue(resp.json()["reference"]["url"].endswith("/reference/download/"))

    # --- set_reference permission boundaries ---
    def test_set_reference_by_primary_teacher_succeeds(self):
        client = APIClient()
        client.force_authenticate(self.teacher)
        resp = client.put(
            f"/api/materials/{self.material.id}/set_reference/",
            data={"guidance": "覆盖指引"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.material.refresh_from_db()
        self.assertEqual(self.material.guidance_override, "覆盖指引")

    def test_set_reference_student_forbidden(self):
        client = APIClient()
        client.force_authenticate(self.student)
        resp = client.put(
            f"/api/materials/{self.material.id}/set_reference/",
            data={"guidance": "x"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_set_reference_other_teacher_forbidden(self):
        # A teacher who does not advise this project cannot even locate it
        # (accessible_projects restricts teachers to their own projects), so the
        # platform returns 404 rather than leaking existence.
        client = APIClient()
        client.force_authenticate(self.other_teacher)
        resp = client.put(
            f"/api/materials/{self.material.id}/set_reference/",
            data={"guidance": "x"}, format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_set_reference_platform_admin_forbidden(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        resp = client.put(
            f"/api/materials/{self.material.id}/set_reference/",
            data={"guidance": "x"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_set_reference_extension_whitelist(self):
        client = APIClient()
        client.force_authenticate(self.teacher)
        bad = SimpleUploadedFile("virus.exe", b"x", content_type="application/octet-stream")
        resp = client.put(
            f"/api/materials/{self.material.id}/set_reference/",
            data={"reference_file": bad}, format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_set_reference_upload_file(self):
        client = APIClient()
        client.force_authenticate(self.teacher)
        good = SimpleUploadedFile(
            "blank.docx", b"docx-bytes",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        resp = client.put(
            f"/api/materials/{self.material.id}/set_reference/",
            data={"reference_file": good}, format="multipart",
        )
        self.assertEqual(resp.status_code, 200)
        self.material.refresh_from_db()
        self.assertTrue(self.material.reference_file_override)

    # --- reset_reference ---
    def test_reset_reference_falls_back(self):
        client = APIClient()
        client.force_authenticate(self.teacher)
        client.put(
            f"/api/materials/{self.material.id}/set_reference/",
            data={"guidance": "覆盖"}, format="json",
        )
        resp = client.delete(f"/api/materials/{self.material.id}/reset_reference/")
        self.assertEqual(resp.status_code, 200)
        self.material.refresh_from_db()
        self.assertEqual(self.material.guidance_override, "")
        self.assertEqual(self.material.effective_guidance, "默认系统指引")

    # --- reference_download ---
    def test_reference_download_generates_when_no_file(self):
        client = APIClient()
        client.force_authenticate(self.teacher)
        resp = client.get(f"/api/materials/{self.material.id}/reference/download/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Content-Disposition", resp)

    def test_reference_download_404_without_guidance(self):
        self.tmpl.guidance = ""
        self.tmpl.save()
        client = APIClient()
        client.force_authenticate(self.teacher)
        resp = client.get(f"/api/materials/{self.material.id}/reference/download/")
        self.assertEqual(resp.status_code, 404)

    # --- blueprint seeds guidance ---
    def test_blueprint_writes_guidance_for_all_categories(self):
        for category in ("research", "engineering", "invention"):
            template = get_or_create_default_template(
                school=self.school, owner=self.teacher, category=category,
            )
            materials = TemplateMaterial.objects.filter(task__stage__template=template)
            self.assertEqual(materials.count(), len(DEFAULT_TEMPLATE_BLUEPRINTS[category][1]))
            self.assertTrue(all(m.guidance for m in materials))

from io import BytesIO
from unittest.mock import Mock, patch

from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from docx import Document
from rest_framework.test import APIClient

from apps.core.models import Account, AuditEvent, Material, MaterialRevision, Project, ReportExport, School
from apps.core.tasks import generate_report_export


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ReportExportTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="报告学校")
        self.leader = Account.objects.create_user(username="report-leader", school=self.school, role="student")
        self.member = Account.objects.create_user(username="report-member", school=self.school, role="student")
        self.outsider = Account.objects.create_user(username="report-outsider", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="report-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            school=self.school, title="雨水回收研究", problem="如何提升回收效率", plan="对照实验",
            leader=self.leader, primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.leader, role="leader")
        self.project.members.create(account=self.member, role="member")

    def client_for(self, user):
        client = APIClient(); client.force_authenticate(user); return client

    def test_only_project_leader_can_queue_report_export(self):
        denied = self.client_for(self.member).post(
            "/api/report-exports/", {"project": self.project.id, "format": "docx"}, format="json",
        )
        self.assertEqual(denied.status_code, 403)
        queued = self.client_for(self.leader).post(
            "/api/report-exports/", {"project": self.project.id, "format": "docx"}, format="json",
        )
        self.assertEqual(queued.status_code, 201)
        self.assertEqual(queued.data["status"], "queued")

    @override_settings(PDF_EXPORT_ENABLED=False)
    def test_core_deployment_rejects_pdf_before_queueing(self):
        response = self.client_for(self.leader).post(
            "/api/report-exports/", {"project": self.project.id, "format": "pdf"}, format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("未启用 PDF", str(response.data))
        self.assertFalse(ReportExport.objects.filter(project=self.project, format="pdf").exists())

    def test_queueing_report_export_records_a_non_sensitive_audit_event(self):
        response = self.client_for(self.leader).post(
            "/api/report-exports/", {"project": self.project.id, "format": "docx"}, format="json",
        )

        event = AuditEvent.objects.get(action="report_export_requested")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(event.school_id, self.school.id)
        self.assertEqual(event.actor_id, self.leader.id)
        self.assertEqual(event.changes, {
            "project_id": self.project.id,
            "export_id": response.data["id"],
            "format": "docx",
        })

    def test_docx_contains_only_latest_approved_material_versions(self):
        approved = Material.objects.create(
            project=self.project, title="问题定义", status="approved", report_section="研究问题", report_order=1,
        )
        MaterialRevision.objects.create(material=approved, author=self.leader, content="旧的已通过文字", status="approved")
        MaterialRevision.objects.create(material=approved, author=self.leader, content="最新已通过文字", status="approved")
        ignored = Material.objects.create(
            project=self.project, title="实验过程", status="revision_required", report_section="实验", report_order=2,
        )
        MaterialRevision.objects.create(material=ignored, author=self.leader, content="不应进入报告", status="revision_required")
        export = ReportExport.objects.create(project=self.project, requested_by=self.leader, format="docx")

        result = generate_report_export(export.id)

        export.refresh_from_db()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(export.status, ReportExport.Status.COMPLETED)
        with default_storage.open(export.file.name, "rb") as handle:
            document = Document(BytesIO(handle.read()))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("最新已通过文字", text)
        self.assertNotIn("旧的已通过文字", text)
        self.assertNotIn("不应进入报告", text)

    @override_settings(DOCUMENT_CONVERTER_URL="http://gotenberg.test")
    @patch("apps.core.tasks.requests.post")
    def test_pdf_export_converts_docx_and_persists_pdf(self, post):
        post.return_value = Mock(content=b"%PDF-1.7 test", raise_for_status=Mock())
        export = ReportExport.objects.create(project=self.project, requested_by=self.leader, format="pdf")

        result = generate_report_export(export.id)

        export.refresh_from_db()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(export.status, ReportExport.Status.COMPLETED)
        self.assertTrue(export.file.name.endswith(".pdf"))
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], "http://gotenberg.test/forms/libreoffice/convert")
        self.assertEqual(default_storage.open(export.file.name, "rb").read(), b"%PDF-1.7 test")

    @override_settings(DOCUMENT_CONVERTER_URL="http://gotenberg.test")
    @patch("apps.core.tasks.requests.post", side_effect=RuntimeError("converter unavailable"))
    def test_pdf_export_failure_is_persisted_as_retryable_failed_state(self, _post):
        export = ReportExport.objects.create(project=self.project, requested_by=self.leader, format="pdf")

        with self.assertRaises(RuntimeError):
            generate_report_export(export.id)

        export.refresh_from_db()
        self.assertEqual(export.status, ReportExport.Status.FAILED)
        self.assertIn("converter unavailable", export.error_message)

    def test_export_file_download_respects_project_membership(self):
        export = ReportExport.objects.create(
            project=self.project, requested_by=self.leader, format="docx", status=ReportExport.Status.COMPLETED,
        )
        export.file.save("report.docx", BytesIO(b"private report"), save=True)
        self.assertEqual(self.client_for(self.member).get(f"/api/report-exports/{export.id}/download/").status_code, 200)
        self.assertEqual(self.client_for(self.teacher).get(f"/api/report-exports/{export.id}/download/").status_code, 200)
        self.assertEqual(self.client_for(self.outsider).get(f"/api/report-exports/{export.id}/download/").status_code, 404)

    def test_completed_export_uses_same_origin_relative_download_url(self):
        export = ReportExport.objects.create(
            project=self.project, requested_by=self.leader, format="docx", status=ReportExport.Status.COMPLETED,
        )
        export.file.save("relative.docx", BytesIO(b"private report"), save=True)

        response = self.client_for(self.leader).get("/api/report-exports/")

        self.assertEqual(response.data[0]["download_url"], f"/api/report-exports/{export.id}/download/")

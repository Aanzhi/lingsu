from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from unittest.mock import patch
from rest_framework.test import APIClient

from apps.core.models import Account, Material, MaterialAttachment, MaterialRevision, Project, School
from apps.core.tasks import process_uploaded_material


class UploadPolicyTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="上传学校", storage_quota_mb=1)
        self.student = Account.objects.create_user(username="upload-student", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="upload-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            school=self.school, title="上传项目", leader=self.student,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        self.material = Material.objects.create(project=self.project, title="证据")
        self.client = APIClient(); self.client.force_authenticate(self.student)

    @override_settings(MAX_UPLOAD_SIZE=5)
    def test_rejects_single_file_over_limit(self):
        response = self.client.post("/api/material-revisions/", {
            "material": self.material.id, "uploaded_files": [SimpleUploadedFile("large.txt", b"123456", content_type="text/plain")],
        }, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("大小", str(response.data))

    def test_rejects_executable_file_types(self):
        response = self.client.post("/api/material-revisions/", {
            "material": self.material.id, "uploaded_files": [SimpleUploadedFile("payload.exe", b"MZ", content_type="application/octet-stream")],
        }, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("文件类型", str(response.data))

    @override_settings(MAX_UPLOAD_SIZE=2 * 1024 * 1024)
    def test_rejects_upload_when_school_storage_quota_would_be_exceeded(self):
        response = self.client.post("/api/material-revisions/", {
            "material": self.material.id, "uploaded_files": [SimpleUploadedFile("full.zip", b"x" * (1024 * 1024 + 1), content_type="application/zip")],
        }, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("存储配额", str(response.data))

    @override_settings(ATTACHMENT_UPLOADS_ENABLED=False)
    def test_core_deployment_rejects_regular_attachment_upload_before_creation(self):
        response = self.client.post("/api/material-revisions/", {
            "material": self.material.id,
            "uploaded_files": [SimpleUploadedFile("evidence.txt", b"real evidence", content_type="text/plain")],
        }, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("未启用附件上传", str(response.data))
        self.assertFalse(MaterialRevision.objects.filter(material=self.material).exists())

    @patch("apps.core.serializers.process_uploaded_material.delay")
    def test_accepted_upload_is_queued_for_security_processing(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/material-revisions/", {
                "material": self.material.id,
                "uploaded_files": [SimpleUploadedFile("evidence.txt", b"real evidence", content_type="text/plain")],
            }, format="multipart")

        self.assertEqual(response.status_code, 201)
        attachment = MaterialAttachment.objects.get(revision_id=response.data["id"])
        self.assertEqual(attachment.scan_status, MaterialAttachment.ScanStatus.PENDING)
        self.assertEqual(attachment.sha256, "")
        delay.assert_called_once_with(response.data["id"])

    @override_settings(FILE_SCAN_REQUIRED=False, CLAMAV_HOST="")
    def test_security_processing_calculates_hash_and_marks_clean_in_development(self):
        response = self.client.post("/api/material-revisions/", {
            "material": self.material.id,
            "uploaded_files": [SimpleUploadedFile("evidence.txt", b"real evidence", content_type="text/plain")],
        }, format="multipart")
        revision_id = response.data["id"]

        result = process_uploaded_material(revision_id)

        attachment = MaterialAttachment.objects.get(revision_id=revision_id)
        self.assertEqual(result["status"], "clean")
        self.assertEqual(attachment.scan_status, MaterialAttachment.ScanStatus.CLEAN)
        self.assertEqual(len(attachment.sha256), 64)

    @override_settings(FILE_SCAN_REQUIRED=True, CLAMAV_HOST="")
    def test_download_is_blocked_until_required_security_scan_completes(self):
        with patch("apps.core.serializers.process_uploaded_material.delay"):
            response = self.client.post("/api/material-revisions/", {
                "material": self.material.id,
                "uploaded_files": [SimpleUploadedFile("evidence.txt", b"real evidence", content_type="text/plain")],
            }, format="multipart")
        attachment_id = response.data["attachments"][0]["id"]

        download = self.client.get(f"/api/material-attachments/{attachment_id}/download/")

        self.assertEqual(download.status_code, 423)

    def test_revision_cannot_be_submitted_while_attachment_scan_is_pending(self):
        revision = MaterialRevision.objects.create(
            material=self.material, author=self.student, content="待检查证据",
        )
        MaterialAttachment.objects.create(
            revision=revision,
            file=SimpleUploadedFile("evidence.txt", b"real evidence", content_type="text/plain"),
            original_name="evidence.txt",
            size=13,
            scan_status=MaterialAttachment.ScanStatus.PENDING,
        )

        response = self.client.post(
            f"/api/material-revisions/{revision.id}/submit/",
            {"truth_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("安全检查", str(response.data))
        revision.refresh_from_db()
        self.assertEqual(revision.status, "draft")

    def test_revision_cannot_be_submitted_when_attachment_is_infected(self):
        revision = MaterialRevision.objects.create(
            material=self.material, author=self.student, content="风险证据",
        )
        MaterialAttachment.objects.create(
            revision=revision,
            file=SimpleUploadedFile("risk.txt", b"risk", content_type="text/plain"),
            original_name="risk.txt",
            size=4,
            scan_status=MaterialAttachment.ScanStatus.INFECTED,
        )

        response = self.client.post(
            f"/api/material-revisions/{revision.id}/submit/",
            {"truth_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("未通过", str(response.data))

    def test_revision_can_be_submitted_after_all_attachments_are_clean(self):
        revision = MaterialRevision.objects.create(
            material=self.material, author=self.student, content="安全证据",
        )
        MaterialAttachment.objects.create(
            revision=revision,
            file=SimpleUploadedFile("safe.txt", b"safe", content_type="text/plain"),
            original_name="safe.txt",
            size=4,
            scan_status=MaterialAttachment.ScanStatus.CLEAN,
        )

        response = self.client.post(
            f"/api/material-revisions/{revision.id}/submit/",
            {"truth_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "submitted")

    @patch("apps.core.serializers.process_uploaded_material.delay")
    def test_attachment_download_url_is_same_origin_relative_path(self, _delay):
        response = self.client.post("/api/material-revisions/", {
            "material": self.material.id,
            "uploaded_files": [SimpleUploadedFile("evidence.txt", b"evidence", content_type="text/plain")],
        }, format="multipart")

        self.assertEqual(
            response.data["attachments"][0]["download_url"],
            f"/api/material-attachments/{response.data['attachments'][0]['id']}/download/",
        )

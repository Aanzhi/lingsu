import hashlib
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    Material,
    MaterialAttachment,
    MaterialRevision,
    Project,
    School,
    UploadPart,
    UploadSession,
)


@override_settings(
    MAX_UPLOAD_SIZE=1024,
    UPLOAD_CHUNK_MIN_SIZE=1,
    UPLOAD_CHUNK_MAX_SIZE=8,
    UPLOAD_SESSION_TTL_HOURS=24,
)
class ChunkedUploadTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="分片上传学校", storage_quota_mb=10)
        self.student = Account.objects.create_user(username="chunk-student", school=self.school, role="student")
        self.outsider = Account.objects.create_user(username="chunk-outsider", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="chunk-teacher", school=self.school, role="teacher")
        self.project = Project.objects.create(
            school=self.school,
            title="分片上传项目",
            leader=self.student,
            primary_teacher=self.teacher,
            status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.student, role="leader")
        self.material = Material.objects.create(project=self.project, title="大文件证据")
        self.revision = MaterialRevision.objects.create(material=self.material, author=self.student, content="大文件证据")
        self.client = APIClient(); self.client.force_authenticate(self.student)

    def create_session(self, content=b"abcdefghij", chunk_size=4):
        response = self.client.post("/api/upload-sessions/", {
            "revision": self.revision.id,
            "original_name": "evidence.bin",
            "content_type": "application/octet-stream",
            "total_size": len(content),
            "chunk_size": chunk_size,
            "expected_sha256": hashlib.sha256(content).hexdigest(),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def put_part(self, session_id, index, content, digest=None):
        digest = digest or hashlib.sha256(content).hexdigest()
        return self.client.put(
            f"/api/upload-sessions/{session_id}/parts/{index}/",
            {"chunk": SimpleUploadedFile(f"part-{index}", content)},
            format="multipart",
            HTTP_X_CHUNK_SHA256=digest,
        )

    def test_session_reports_uploaded_parts_for_resume(self):
        session = self.create_session().data
        uploaded = self.put_part(session["id"], 0, b"abcd")
        detail = self.client.get(f"/api/upload-sessions/{session['id']}/")

        self.assertEqual(uploaded.status_code, 201)
        self.assertEqual(detail.data["uploaded_parts"], [0])
        self.assertEqual(detail.data["part_count"], 3)

    @override_settings(ATTACHMENT_UPLOADS_ENABLED=False)
    def test_core_deployment_rejects_chunked_attachment_session(self):
        response = self.client.post("/api/upload-sessions/", {
            "revision": self.revision.id,
            "original_name": "evidence.bin",
            "content_type": "application/octet-stream",
            "total_size": 10,
            "chunk_size": 4,
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("未启用附件上传", str(response.data))
        self.assertFalse(UploadSession.objects.exists())

    def test_same_part_is_idempotent_but_conflicting_reupload_is_rejected(self):
        session = self.create_session().data
        first = self.put_part(session["id"], 0, b"abcd")
        duplicate = self.put_part(session["id"], 0, b"abcd")
        conflict = self.put_part(session["id"], 0, b"WXYZ")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(UploadPart.objects.filter(session_id=session["id"]).count(), 1)

    def test_chunk_hash_and_exact_chunk_size_are_enforced(self):
        session = self.create_session().data
        wrong_hash = self.put_part(session["id"], 0, b"abcd", digest="0" * 64)
        wrong_size = self.put_part(session["id"], 0, b"abc")

        self.assertEqual(wrong_hash.status_code, 400)
        self.assertIn("哈希", str(wrong_hash.data))
        self.assertEqual(wrong_size.status_code, 400)
        self.assertIn("大小", str(wrong_size.data))

    @patch("apps.core.views.process_uploaded_material.delay")
    def test_complete_merges_parts_creates_attachment_and_queues_scan(self, scan):
        content = b"abcdefghij"
        session = self.create_session(content).data
        for index, chunk in enumerate((b"abcd", b"efgh", b"ij")):
            self.assertIn(self.put_part(session["id"], index, chunk).status_code, (200, 201))

        with self.captureOnCommitCallbacks(execute=True):
            completed = self.client.post(f"/api/upload-sessions/{session['id']}/complete/")

        self.assertEqual(completed.status_code, 200, completed.data)
        attachment = MaterialAttachment.objects.get(pk=completed.data["attachment_id"])
        with attachment.file.open("rb") as source:
            self.assertEqual(source.read(), content)
        self.assertEqual(attachment.sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(attachment.scan_status, MaterialAttachment.ScanStatus.PENDING)
        self.assertFalse(UploadPart.objects.filter(session_id=session["id"]).exists())
        scan.assert_called_once_with(self.revision.id)

    @patch("apps.core.views.process_uploaded_material.delay")
    def test_completed_session_can_be_retried_without_duplicate_attachment(self, scan):
        session = self.create_session(b"abcd", chunk_size=4).data
        self.put_part(session["id"], 0, b"abcd")
        with self.captureOnCommitCallbacks(execute=True):
            first = self.client.post(f"/api/upload-sessions/{session['id']}/complete/")
        second = self.client.post(f"/api/upload-sessions/{session['id']}/complete/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["attachment_id"], first.data["attachment_id"])
        self.assertEqual(MaterialAttachment.objects.filter(revision=self.revision).count(), 1)
        scan.assert_called_once_with(self.revision.id)

    def test_complete_requires_every_part_and_matching_whole_file_hash(self):
        session = self.create_session().data
        self.put_part(session["id"], 0, b"abcd")
        incomplete = self.client.post(f"/api/upload-sessions/{session['id']}/complete/")

        for index, chunk in ((1, b"efgh"), (2, b"XX")):
            self.put_part(session["id"], index, chunk)
        mismatched = self.client.post(f"/api/upload-sessions/{session['id']}/complete/")

        self.assertEqual(incomplete.status_code, 409)
        self.assertEqual(mismatched.status_code, 400)
        self.assertIn("整体哈希", str(mismatched.data))
        self.assertEqual(UploadSession.objects.get(pk=session["id"]).status, UploadSession.Status.ACTIVE)

    @override_settings(MAX_UPLOAD_SIZE=2 * 1024 * 1024)
    def test_session_creation_reserves_quota_and_rejects_unsafe_extension(self):
        self.school.storage_quota_mb = 1
        self.school.save(update_fields=["storage_quota_mb"])
        MaterialAttachment.objects.create(
            revision=self.revision,
            file=SimpleUploadedFile("existing.txt", b"x"),
            original_name="existing.txt",
            size=900_000,
            scan_status=MaterialAttachment.ScanStatus.CLEAN,
        )
        quota = self.client.post("/api/upload-sessions/", {
            "revision": self.revision.id, "original_name": "large.zip",
            "total_size": 200_000, "chunk_size": 4,
        }, format="json")
        unsafe = self.client.post("/api/upload-sessions/", {
            "revision": self.revision.id, "original_name": "payload.exe",
            "total_size": 10, "chunk_size": 4,
        }, format="json")

        self.assertEqual(quota.status_code, 400)
        self.assertIn("配额", str(quota.data))
        self.assertEqual(unsafe.status_code, 400)
        self.assertIn("文件类型", str(unsafe.data))

    @override_settings(MAX_UPLOAD_SIZE=2 * 1024 * 1024)
    def test_regular_upload_counts_active_chunk_reservations_against_storage_quota(self):
        self.school.storage_quota_mb = 1
        self.school.save(update_fields=["storage_quota_mb"])
        active = self.client.post("/api/upload-sessions/", {
            "revision": self.revision.id, "original_name": "reserved.zip",
            "total_size": 200_000, "chunk_size": 4,
        }, format="json")
        self.assertEqual(active.status_code, 201, active.data)

        direct = self.client.post("/api/material-revisions/", {
            "material": self.material.id,
            "content": "混合上传不能绕过学校存储额度",
            "uploaded_files": [SimpleUploadedFile("too-large.txt", b"x" * 900_000)],
        }, format="multipart")

        self.assertEqual(direct.status_code, 400)
        self.assertIn("配额", str(direct.data))

    def test_only_revision_author_can_access_session_and_expired_session_is_closed(self):
        session = self.create_session().data
        outsider = APIClient(); outsider.force_authenticate(self.outsider)
        hidden = outsider.get(f"/api/upload-sessions/{session['id']}/")
        UploadSession.objects.filter(pk=session["id"]).update(expires_at=timezone.now() - timedelta(seconds=1))
        expired = self.put_part(session["id"], 0, b"abcd")

        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(expired.status_code, 410)

    def test_abort_removes_parts_and_releases_reserved_quota(self):
        session = self.create_session().data
        self.put_part(session["id"], 0, b"abcd")
        part_name = UploadPart.objects.get(session_id=session["id"], index=0).file.name
        aborted = self.client.post(f"/api/upload-sessions/{session['id']}/abort/")

        self.assertEqual(aborted.status_code, 200)
        self.assertEqual(aborted.data["status"], UploadSession.Status.ABORTED)
        self.assertFalse(UploadPart.objects.filter(session_id=session["id"]).exists())
        self.assertFalse(default_storage.exists(part_name))

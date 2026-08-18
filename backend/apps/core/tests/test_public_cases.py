from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Account, Material, MaterialRevision, Project, PublicCaseRequest, School


class PublicCaseTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="案例学校")
        self.other_school = School.objects.create(name="外校")
        self.leader = Account.objects.create_user(username="case-leader", school=self.school, role="student")
        self.teacher = Account.objects.create_user(username="case-teacher", school=self.school, role="teacher")
        self.other_student = Account.objects.create_user(username="case-reader", school=self.other_school, role="student")
        self.platform = Account.objects.create_user(username="case-platform", role="platform_admin")
        self.project = Project.objects.create(
            school=self.school, title="校园节水装置", problem="如何减少浪费", plan="制作与测试",
            leader=self.leader, primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.leader, role="leader")
        self.public_material = Material.objects.create(project=self.project, title="结论", status="approved", report_section="结论")
        MaterialRevision.objects.create(material=self.public_material, author=self.leader, content="节水率提升 18%", status="approved")
        self.private_material = Material.objects.create(project=self.project, title="源代码", status="approved")
        MaterialRevision.objects.create(material=self.private_material, author=self.leader, content="PRIVATE-SOURCE", status="approved")

    def client_for(self, user):
        client = APIClient(); client.force_authenticate(user); return client

    def test_leader_selects_only_approved_project_materials_for_publication(self):
        draft = Material.objects.create(project=self.project, title="未通过材料", status="draft")
        denied = self.client_for(self.leader).post("/api/public-case-requests/", {
            "project": self.project.id, "public_summary": "公开摘要", "selected_materials": [draft.id],
        }, format="json")
        self.assertEqual(denied.status_code, 400)

        self.project.status = Project.Status.COMPLETED
        self.project.save(update_fields=["status"])

        created = self.client_for(self.leader).post("/api/public-case-requests/", {
            "project": self.project.id, "public_summary": "公开摘要", "tags": ["节水", "工程"],
            "discipline": "工程技术", "application_scene": "校园", "outcome_form": "实物装置",
            "selected_materials": [self.public_material.id],
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "pending_teacher")

    def test_active_project_cannot_apply_for_publication(self):
        response = self.client_for(self.leader).post("/api/public-case-requests/", {
            "project": self.project.id,
            "public_summary": "尚未结项的项目不应公开",
            "selected_materials": [self.public_material.id],
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("完成", str(response.data))

    def test_teacher_publish_exposes_only_selected_material_summary_to_other_school(self):
        case = PublicCaseRequest.objects.create(project=self.project, applicant=self.leader, public_summary="公开摘要")
        case.selected_materials.add(self.public_material)
        approved = self.client_for(self.teacher).post(f"/api/public-case-requests/{case.id}/teacher_approve/")
        self.assertEqual(approved.status_code, 200)
        reader = self.client_for(self.other_student).get("/api/public-case-requests/")
        self.assertEqual(reader.status_code, 200)
        self.assertEqual(len(reader.data), 1)
        payload = str(reader.data[0])
        self.assertIn("节水率提升 18%", payload)
        self.assertNotIn("PRIVATE-SOURCE", payload)

    def test_platform_can_hide_and_restore_but_cannot_edit_school_case(self):
        case = PublicCaseRequest.objects.create(
            project=self.project, applicant=self.leader, public_summary="公开摘要", status="published",
        )
        platform = self.client_for(self.platform)
        self.assertEqual(platform.patch(f"/api/public-case-requests/{case.id}/", {"public_summary": "篡改"}, format="json").status_code, 405)
        hidden = platform.post(f"/api/public-case-requests/{case.id}/set_visibility/", {"visible": False}, format="json")
        self.assertEqual(hidden.data["status"], "offline")
        self.assertEqual(self.client_for(self.other_student).get("/api/public-case-requests/").data, [])
        restored = platform.post(f"/api/public-case-requests/{case.id}/set_visibility/", {"visible": True}, format="json")
        self.assertEqual(restored.data["status"], "published")

    def test_platform_visibility_action_rejects_string_boolean_values(self):
        case = PublicCaseRequest.objects.create(
            project=self.project, applicant=self.leader, public_summary="公开摘要", status="published",
        )

        response = self.client_for(self.platform).post(
            f"/api/public-case-requests/{case.id}/set_visibility/", {"visible": "false"}, format="json",
        )

        self.assertEqual(response.status_code, 400)
        case.refresh_from_db()
        self.assertEqual(case.status, PublicCaseRequest.Status.PUBLISHED)

    def test_teacher_rejection_requires_a_reason_and_is_auditable(self):
        case = PublicCaseRequest.objects.create(
            project=self.project, applicant=self.leader, public_summary="公开摘要",
        )
        teacher = self.client_for(self.teacher)

        missing = teacher.post(f"/api/public-case-requests/{case.id}/teacher_reject/", {"comment": ""}, format="json")
        rejected = teacher.post(
            f"/api/public-case-requests/{case.id}/teacher_reject/",
            {"comment": "请先移除包含个人信息的过程照片。"},
            format="json",
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.data["status"], "rejected")
        self.assertEqual(rejected.data["review_comment"], "请先移除包含个人信息的过程照片。")
        case.refresh_from_db()
        self.assertEqual(case.teacher_reviewer, self.teacher)

    def test_teacher_cannot_reapprove_or_reject_an_already_processed_case(self):
        case = PublicCaseRequest.objects.create(
            project=self.project, applicant=self.leader, public_summary="公开摘要", status="published",
        )
        client = self.client_for(self.teacher)

        approved_again = client.post(f"/api/public-case-requests/{case.id}/teacher_approve/")
        rejected_after_publish = client.post(
            f"/api/public-case-requests/{case.id}/teacher_reject/", {"comment": "晚了"}, format="json",
        )

        self.assertEqual(approved_again.status_code, 400)
        self.assertEqual(rejected_after_publish.status_code, 400)

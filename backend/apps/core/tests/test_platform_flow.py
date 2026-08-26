from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Account, MemberInvitation, Project, School


class PlatformFlowTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="灵溯试点学校", invite_code="LINGSUO-001")
        self.platform = Account.objects.create_user(username="platform", role="platform_admin")
        self.teacher = Account.objects.create_user(username="teacher", school=self.school, role="teacher")
        self.leader = Account.objects.create_user(username="leader", school=self.school, role="student")
        self.member = Account.objects.create_user(username="member", school=self.school, role="student")

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_student_project_is_claimed_by_teacher_before_material_work(self):
        client = APIClient(); client.force_authenticate(self.leader)
        created = client.post("/api/projects/", {"title": "节水侦测器", "summary": "发现漏水", "project_type": "engineering"}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "unclaimed")
        teacher_client = APIClient(); teacher_client.force_authenticate(self.teacher)
        self.assertEqual([p["id"] for p in teacher_client.get("/api/projects/pool/").data], [created.data["id"]])
        claimed = teacher_client.post(f"/api/projects/{created.data['id']}/claim/")
        self.assertEqual(claimed.data["status"], "active")
        self.assertEqual(claimed.data["primary_teacher"], self.teacher.id)

    def test_teacher_pool_exposes_opening_fields_before_claim(self):
        project = Project.objects.create(
            school=self.school,
            title="开题预览项目",
            leader=self.leader,
            status=Project.Status.UNCLAIMED,
            problem="如何减少校园雨后积水？",
            plan="记录不同位置的积水变化并比较排水条件。",
            summary="通过连续观察形成可复核的研究证据。",
        )
        project.members.create(account=self.leader, role="leader")
        teacher_client = self.client_for(self.teacher)

        response = teacher_client.get("/api/projects/pool/")

        self.assertEqual(response.status_code, 200)
        item = next(value for value in response.data if value["id"] == project.id)
        self.assertEqual(item["title"], "开题预览项目")
        self.assertEqual(item["problem"], "如何减少校园雨后积水？")
        self.assertEqual(item["plan"], "记录不同位置的积水变化并比较排水条件。")
        self.assertEqual(item["summary"], "通过连续观察形成可复核的研究证据。")
        self.assertEqual(item["status"], Project.Status.UNCLAIMED)
        self.assertIsNone(item["primary_teacher"])
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.UNCLAIMED)
        self.assertIsNone(project.primary_teacher_id)

    def test_project_payload_includes_supervising_teacher_display_name(self):
        self.teacher.first_name = "林老师"
        self.teacher.save(update_fields=["first_name"])
        project = Project.objects.create(
            school=self.school,
            title="教师名称展示",
            leader=self.leader,
            primary_teacher=self.teacher,
            status=Project.Status.ACTIVE,
        )

        response = self.client_for(self.leader).get("/api/projects/")

        self.assertEqual(response.status_code, 200)
        item = next(value for value in response.data if value["id"] == project.id)
        self.assertEqual(item["primary_teacher_name"], "林老师")

    def test_member_invitation_requires_student_then_teacher_confirmation(self):
        project = Project.objects.create(school=self.school, title="项目", leader=self.leader, primary_teacher=self.teacher, status="active")
        project.members.create(account=self.leader, role="leader")
        leader_client = APIClient(); leader_client.force_authenticate(self.leader)
        invited = leader_client.post("/api/member-invitations/", {"project": project.id, "invitee": self.member.id}, format="json")
        self.assertEqual(invited.status_code, 201)
        member_client = APIClient(); member_client.force_authenticate(self.member)
        self.assertEqual(member_client.post(f"/api/member-invitations/{invited.data['id']}/accept/").data["status"], "pending_teacher")
        teacher_client = APIClient(); teacher_client.force_authenticate(self.teacher)
        self.assertEqual(teacher_client.post(f"/api/member-invitations/{invited.data['id']}/decide/", {"approved": True}, format="json").data["status"], "approved")
        self.assertTrue(project.members.filter(account=self.member).exists())

    def test_teacher_member_decision_rejects_string_boolean_values(self):
        project = Project.objects.create(
            school=self.school, title="布尔值邀请", leader=self.leader,
            primary_teacher=self.teacher, status=Project.Status.ACTIVE,
        )
        project.members.create(account=self.leader, role="leader")
        invited = self.client_for(self.leader).post(
            "/api/member-invitations/", {"project": project.id, "invitee": self.member.id}, format="json",
        )
        self.assertEqual(self.client_for(self.member).post(
            f"/api/member-invitations/{invited.data['id']}/accept/",
        ).status_code, 200)

        response = self.client_for(self.teacher).post(
            f"/api/member-invitations/{invited.data['id']}/decide/", {"approved": "false"}, format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(project.members.filter(account=self.member).exists())

    def test_member_invitation_cannot_skip_or_repeat_state_transitions(self):
        project = Project.objects.create(
            school=self.school, title="成员状态机", leader=self.leader,
            primary_teacher=self.teacher, status="active",
        )
        project.members.create(account=self.leader, role="leader")
        leader_client = APIClient(); leader_client.force_authenticate(self.leader)
        invited = leader_client.post(
            "/api/member-invitations/", {"project": project.id, "invitee": self.member.id}, format="json",
        )
        teacher_client = APIClient(); teacher_client.force_authenticate(self.teacher)
        skipped = teacher_client.post(
            f"/api/member-invitations/{invited.data['id']}/decide/", {"approved": True}, format="json",
        )
        self.assertEqual(skipped.status_code, 400)

        member_client = APIClient(); member_client.force_authenticate(self.member)
        first_accept = member_client.post(f"/api/member-invitations/{invited.data['id']}/accept/")
        repeated_accept = member_client.post(f"/api/member-invitations/{invited.data['id']}/accept/")
        self.assertEqual(first_accept.status_code, 200)
        self.assertEqual(repeated_accept.status_code, 400)

    def test_duplicate_active_member_invitation_is_rejected(self):
        project = Project.objects.create(
            school=self.school, title="邀请去重", leader=self.leader,
            primary_teacher=self.teacher, status="active",
        )
        project.members.create(account=self.leader, role="leader")
        client = APIClient(); client.force_authenticate(self.leader)
        payload = {"project": project.id, "invitee": self.member.id}

        self.assertEqual(client.post("/api/member-invitations/", payload, format="json").status_code, 201)
        duplicate = client.post("/api/member-invitations/", payload, format="json")

        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("邀请", str(duplicate.data))

    def test_student_can_search_same_school_students_without_exposing_other_roles_or_schools(self):
        other_school = School.objects.create(name="外校成员搜索")
        Account.objects.create_user(username="outside-member", school=other_school, role="student")
        client = APIClient(); client.force_authenticate(self.leader)

        response = client.get("/api/accounts/students/", {"q": "mem"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["username"] for item in response.data], ["member"])
        self.assertNotIn("school", response.data[0])

    def test_guiding_teacher_can_search_same_school_students_for_direct_assignment(self):
        client = APIClient(); client.force_authenticate(self.teacher)

        response = client.get("/api/accounts/students/", {"q": "mem"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["username"] for item in response.data], ["member"])

    def test_invited_student_can_list_pending_invitations_and_reject_one(self):
        project = Project.objects.create(
            school=self.school, title="邀请响应", leader=self.leader,
            primary_teacher=self.teacher, status="active",
        )
        project.members.create(account=self.leader, role="leader")
        leader_client = APIClient(); leader_client.force_authenticate(self.leader)
        invited = leader_client.post(
            "/api/member-invitations/", {"project": project.id, "invitee": self.member.id}, format="json",
        )
        member_client = APIClient(); member_client.force_authenticate(self.member)

        pending = member_client.get("/api/member-invitations/pending_student/")
        rejected = member_client.post(f"/api/member-invitations/{invited.data['id']}/reject/")

        self.assertEqual([item["id"] for item in pending.data], [invited.data["id"]])
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.data["status"], "rejected")

    def test_expired_school_can_read_but_cannot_create_project(self):
        self.school.license_expires_at = timezone.localdate().replace(year=timezone.localdate().year - 1); self.school.save()
        client = APIClient(); client.force_authenticate(self.leader)
        self.assertEqual(client.get("/api/projects/").status_code, 200)
        self.assertEqual(client.post("/api/projects/", {"title": "不可创建"}, format="json").status_code, 403)

    def test_platform_admin_manages_school_spaces(self):
        client = APIClient(); client.force_authenticate(self.platform)
        result = client.post("/api/schools/", {"name": "第二学校", "is_active": True}, format="json")
        self.assertEqual(result.status_code, 201)
        self.assertTrue(result.data["invite_code"])
        self.assertEqual(client.post(f"/api/schools/{result.data['id']}/reset_invite_code/").status_code, 200)

    def test_student_cannot_list_materials_belonging_to_other_school_projects(self):
        from apps.core.models import Material

        other_school = School.objects.create(name="隔离学校")
        other_student = Account.objects.create_user(username="isolated-student", school=other_school, role="student")
        other_project = Project.objects.create(school=other_school, title="隔离项目", leader=other_student)
        Material.objects.create(project=other_project, title="不应可见材料")
        client = APIClient(); client.force_authenticate(self.leader)

        response = client.get("/api/materials/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

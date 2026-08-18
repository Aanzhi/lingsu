from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class TenantWorkflowTests(TestCase):
    @override_settings(DEBUG=True)
    def test_debug_demo_login_creates_a_student_session_and_guide(self):
        client = APIClient()

        response = client.post("/api/demo-login/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "student")
        self.assertTrue(response.data["teacher_id"])
        self.assertIn("csrftoken", response.cookies)
        self.assertEqual(client.get("/api/me/").status_code, 200)

    @override_settings(DEBUG=True)
    def test_debug_demo_login_can_create_a_teacher_session(self):
        client = APIClient()

        response = client.post("/api/demo-login/", {"role": "teacher"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "teacher")
        self.assertEqual(client.get("/api/me/").data["role"], "teacher")
    def test_student_project_scope_me_and_direct_project_creation(self):
        from apps.core.models import Account, Project, School

        school = School.objects.create(name="学生流程学校")
        teacher = Account.objects.create_user(username="guide", school=school, role=Account.Role.TEACHER)
        student = Account.objects.create_user(username="student-flow", school=school, role=Account.Role.STUDENT)
        other_student = Account.objects.create_user(username="other-flow", school=school, role=Account.Role.STUDENT)
        own = Project.objects.create(school=school, title="我的项目", leader=student, primary_teacher=teacher)
        own.members.create(account=student, role="leader")
        Project.objects.create(school=school, title="别人的项目", leader=other_student, primary_teacher=teacher)
        client = APIClient(); client.force_authenticate(student)

        self.assertEqual(client.get("/api/me/").data["role"], "student")
        self.assertEqual([p["title"] for p in client.get("/api/projects/").data], ["我的项目"])
        response = client.post("/api/projects/", {
            "title": "节水", "problem": "浪费", "plan": "测试方案", "project_type": "research",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "unclaimed")

    def test_student_sees_only_published_school_competitions_and_audience_announcements(self):
        from apps.core.models import Account, Announcement, Competition, School

        school = School.objects.create(name="星辰学校")
        other = School.objects.create(name="其他学校")
        student = Account.objects.create_user(username="student-viewer", school=school, role=Account.Role.STUDENT)
        Competition.objects.create(school=school, title="校内赛", status="published")
        Competition.objects.create(school=school, title="草稿赛", status="draft")
        Competition.objects.create(school=other, title="外校赛", status="published")
        Announcement.objects.create(school=school, title="学生通知", body="请报名", audience="students", status="published", author=student)
        Announcement.objects.create(school=school, title="教师通知", body="请审核", audience="teachers", status="published", author=student)
        Announcement.objects.create(school=other, title="外校通知", body="不可见", audience="all", status="published", author=student)
        client = APIClient(); client.force_authenticate(student)

        self.assertEqual([item["title"] for item in client.get("/api/competitions/").data], ["校内赛"])
        self.assertEqual([item["title"] for item in client.get("/api/announcements/").data], ["学生通知"])

    def test_teacher_can_create_student_announcement_and_marking_read_is_idempotent(self):
        from apps.core.models import Account, AnnouncementRead, School

        school = School.objects.create(name="教师学校")
        teacher = Account.objects.create_user(username="teacher-announcement", school=school, role=Account.Role.TEACHER)
        client = APIClient(); client.force_authenticate(teacher)
        response = client.post("/api/announcements/", {"title": "学生提醒", "body": "完善日志", "audience": "students", "status": "published"}, format="json")

        self.assertEqual(response.status_code, 201)
        item_id = response.data["id"]
        self.assertEqual(client.post(f"/api/announcements/{item_id}/mark_read/").status_code, 200)
        self.assertEqual(client.post(f"/api/announcements/{item_id}/mark_read/").status_code, 200)
        self.assertEqual(AnnouncementRead.objects.filter(announcement_id=item_id, account=teacher).count(), 1)

    def test_teacher_cannot_publish_schoolwide_competition_or_announcement(self):
        from apps.core.models import Account, School

        school = School.objects.create(name="权限学校")
        teacher = Account.objects.create_user(username="teacher-permission", school=school, role=Account.Role.TEACHER)
        client = APIClient(); client.force_authenticate(teacher)

        self.assertEqual(client.post("/api/competitions/", {"title": "校赛", "status": "published"}, format="json").status_code, 403)
        self.assertEqual(client.post("/api/announcements/", {"title": "全校公告", "body": "内容", "audience": "all", "status": "published"}, format="json").status_code, 403)
    def test_student_cannot_read_a_project_from_another_school(self):
        from apps.core.models import Account, Project, School

        first = School.objects.create(name="第一学校")
        second = School.objects.create(name="第二学校")
        student = Account.objects.create_user(
            username="student", password="secret", school=first, role=Account.Role.STUDENT
        )
        foreign_project = Project.objects.create(school=second, title="不应可见", leader=student)
        client = APIClient()
        client.force_authenticate(student)

        response = client.get(f"/api/projects/{foreign_project.id}/")

        self.assertEqual(response.status_code, 404)

    def test_teacher_can_claim_student_project_from_school_pool(self):
        from apps.core.models import Account, Project, School

        school = School.objects.create(name="第一学校")
        teacher = Account.objects.create_user(
            username="teacher", password="secret", school=school, role=Account.Role.TEACHER
        )
        student = Account.objects.create_user(
            username="student", password="secret", school=school, role=Account.Role.STUDENT
        )
        project = Project.objects.create(school=school, leader=student, title="节水装置", problem="浪费水")
        project.members.create(account=student, role="leader")
        client = APIClient()
        client.force_authenticate(teacher)

        response = client.post(f"/api/projects/{project.id}/claim/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(response.data["primary_teacher"], teacher.id)

    def test_teacher_cannot_claim_project_from_another_school(self):
        from apps.core.models import Account, Project, School

        school = School.objects.create(name="指定教师学校")
        other_school = School.objects.create(name="外校项目")
        other_teacher = Account.objects.create_user(username="other-guide", school=other_school, role=Account.Role.TEACHER)
        student = Account.objects.create_user(username="approval-student", school=school, role=Account.Role.STUDENT)
        project = Project.objects.create(school=school, leader=student, title="题目", problem="问题")
        project.members.create(account=student, role="leader")
        client = APIClient(); client.force_authenticate(other_teacher)

        self.assertEqual(client.post(f"/api/projects/{project.id}/claim/").status_code, 404)

    def test_material_revision_requires_truth_confirmation_before_submit(self):
        from apps.core.models import Account, Material, MaterialRevision, Project, School

        school = School.objects.create(name="第一学校")
        student = Account.objects.create_user(
            username="student", password="secret", school=school, role=Account.Role.STUDENT
        )
        project = Project.objects.create(school=school, title="节水", leader=student)
        project.members.create(account=student, role="leader")
        material = Material.objects.create(project=project, title="开题报告")
        revision = MaterialRevision.objects.create(material=material, author=student, content="草稿")
        client = APIClient()
        client.force_authenticate(student)

        response = client.post(f"/api/material-revisions/{revision.id}/submit/", {"truth_confirmed": False}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "提交前须确认内容已按真实项目核对。")

    def test_guiding_teacher_can_list_and_return_only_own_pending_materials(self):
        from apps.core.models import Account, Material, MaterialRevision, Project, School

        school = School.objects.create(name="审核工作台学校")
        guide = Account.objects.create_user(username="review-guide", school=school, role=Account.Role.TEACHER)
        other_guide = Account.objects.create_user(username="other-review-guide", school=school, role=Account.Role.TEACHER)
        student = Account.objects.create_user(username="review-student", school=school, role=Account.Role.STUDENT)
        own_project = Project.objects.create(school=school, title="我的指导项目", leader=student, primary_teacher=guide)
        other_project = Project.objects.create(school=school, title="别人的指导项目", leader=student, primary_teacher=other_guide)
        own_revision = MaterialRevision.objects.create(material=Material.objects.create(project=own_project, title="开题报告"), author=student, content="真实内容", status="submitted")
        Material.objects.filter(pk=own_revision.material_id).update(status="submitted")
        other_revision = MaterialRevision.objects.create(material=Material.objects.create(project=other_project, title="项目日志"), author=student, content="别的内容", status="submitted")
        Material.objects.filter(pk=other_revision.material_id).update(status="submitted")
        client = APIClient(); client.force_authenticate(guide)

        queue = client.get("/api/material-revisions/pending_reviews/")
        returned = client.post(f"/api/material-revisions/{own_revision.id}/review/", {"outcome": "revision_required", "comment": "请补充测试数据。"}, format="json")

        self.assertEqual(queue.status_code, 200)
        self.assertEqual([item["id"] for item in queue.data], [own_revision.id])
        self.assertEqual(returned.status_code, 200)
        self.assertEqual(returned.data["status"], "revision_required")
        self.assertEqual(returned.data["review_comment"], "请补充测试数据。")
        self.assertEqual(returned.data["material_title"], "开题报告")
        self.assertEqual(returned.data["project_title"], "我的指导项目")
        self.assertEqual(returned.data["author_name"], "review-student")
        self.assertEqual(Material.objects.get(pk=own_revision.material_id).status, "revision_required")

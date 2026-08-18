from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    Material,
    MaterialRevision,
    Project,
    ProjectTask,
    PublicCaseRequest,
    School,
)


class BusinessRuleTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="业务规则学校")
        self.teacher = Account.objects.create_user(
            username="business-teacher", school=self.school, role=Account.Role.TEACHER,
        )
        self.leader = Account.objects.create_user(
            username="business-leader", school=self.school, role=Account.Role.STUDENT,
        )
        self.member = Account.objects.create_user(
            username="business-member", school=self.school, role=Account.Role.STUDENT,
        )
        self.project = Project.objects.create(
            school=self.school,
            title="业务规则项目",
            leader=self.leader,
            primary_teacher=self.teacher,
            status=Project.Status.ACTIVE,
        )
        self.project.members.create(account=self.leader, role="leader")
        self.project.members.create(account=self.member, role="member")
        self.task = ProjectTask.objects.create(
            project=self.project,
            stage_name="立项与开题",
            title="问题定义",
            order=1,
            status=ProjectTask.Status.AVAILABLE,
        )
        self.material = Material.objects.create(
            project=self.project,
            task=self.task,
            title="问题定义材料",
            status="draft",
        )

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_member_can_create_draft_but_only_leader_can_submit_it(self):
        created = self.client_for(self.member).post(
            "/api/material-revisions/",
            {"material": self.material.id, "content": "组员的观察记录"},
            format="json",
        )
        denied = self.client_for(self.member).post(
            f"/api/material-revisions/{created.data['id']}/submit/",
            {"truth_confirmed": True},
            format="json",
        )
        accepted = self.client_for(self.leader).post(
            f"/api/material-revisions/{created.data['id']}/submit/",
            {"truth_confirmed": True},
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(accepted.status_code, 200)

    def test_material_submission_rejects_string_truth_confirmation(self):
        revision = MaterialRevision.objects.create(
            material=self.material,
            author=self.leader,
            content="真实的观察记录",
            status=MaterialRevision.Status.DRAFT,
        )

        response = self.client_for(self.leader).post(
            f"/api/material-revisions/{revision.id}/submit/", {"truth_confirmed": "false"}, format="json",
        )

        self.assertEqual(response.status_code, 400)
        revision.refresh_from_db()
        self.assertEqual(revision.status, MaterialRevision.Status.DRAFT)

    def test_approved_material_cannot_create_an_implicit_replacement_revision(self):
        self.material.status = "approved"
        self.material.save(update_fields=["status"])

        response = self.client_for(self.leader).post(
            "/api/material-revisions/",
            {"material": self.material.id, "content": "试图修改已通过证据"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_task_stays_available_until_every_required_material_is_approved(self):
        second = Material.objects.create(
            project=self.project,
            task=self.task,
            title="第二份证据",
            status="draft",
            required=True,
        )
        revision = MaterialRevision.objects.create(
            material=self.material,
            author=self.leader,
            content="第一份已提交证据",
            truth_confirmed=True,
            status="submitted",
        )
        self.material.status = "submitted"
        self.material.save(update_fields=["status"])
        self.task.status = ProjectTask.Status.PENDING_REVIEW
        self.task.save(update_fields=["status"])

        response = self.client_for(self.teacher).post(
            f"/api/material-revisions/{revision.id}/review/",
            {"outcome": "approved", "comment": "通过"},
            format="json",
        )

        self.task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.task.status, ProjectTask.Status.AVAILABLE)
        self.assertEqual(second.status, "draft")

    def test_leader_cannot_invite_members_before_teacher_claims_project(self):
        unclaimed = Project.objects.create(
            school=self.school,
            title="尚未认领项目",
            leader=self.leader,
            status=Project.Status.UNCLAIMED,
        )
        unclaimed.members.create(account=self.leader, role="leader")

        response = self.client_for(self.leader).post(
            "/api/member-invitations/",
            {"project": unclaimed.id, "invitee": self.member.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejected_completed_project_case_can_be_resubmitted(self):
        self.project.status = Project.Status.COMPLETED
        self.project.save(update_fields=["status"])
        self.material.status = "approved"
        self.material.save(update_fields=["status"])
        MaterialRevision.objects.create(
            material=self.material,
            author=self.leader,
            content="可以公开的研究结论",
            status="approved",
        )
        case = PublicCaseRequest.objects.create(
            project=self.project,
            applicant=self.leader,
            public_summary="旧版摘要",
            status=PublicCaseRequest.Status.REJECTED,
            review_comment="请删除个人信息。",
            teacher_reviewer=self.teacher,
        )
        case.selected_materials.add(self.material)

        response = self.client_for(self.leader).post(
            f"/api/public-case-requests/{case.id}/resubmit/",
            {
                "public_summary": "已去除个人信息的公开摘要",
                "selected_materials": [self.material.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "pending_teacher")
        self.assertEqual(response.data["review_comment"], "")

"""Create the isolated data set used by the cross-role core-flow E2E test.

This command is intentionally unavailable unless the caller explicitly sets
``LINGSU_E2E_SEED=1``. It is safe to run with ``--reset`` only against the
named test school; it must never be used as a production data fixture.
"""

import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import (
    Account,
    AIGenerationLog,
    AIConversation,
    AgentTemplate,
    Announcement,
    AuditEvent,
    Competition,
    Material,
    MaterialRevision,
    Project,
    ProjectTask,
    PublicCaseRequest,
    School,
    Template,
    TemplateMaterial,
    TemplateStage,
    TemplateTask,
)


DEFAULT_SCHOOL = "灵溯核心闭环测试学校"
DEFAULT_PASSWORD = "core-e2e-pass-2026"
ACCOUNT_NAMES = (
    "core-e2e-student",
    "core-e2e-member",
    "core-e2e-direct",
    "core-e2e-teacher",
    "core-e2e-platform",
)


class Command(BaseCommand):
    help = "创建核心项目闭环的隔离 E2E 测试数据（必须显式开启 LINGSU_E2E_SEED）。"

    def add_arguments(self, parser):
        parser.add_argument("--school", default=DEFAULT_SCHOOL)
        parser.add_argument("--password", default=DEFAULT_PASSWORD)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="删除并重新创建指定测试学校及其测试数据。",
        )

    def handle(self, *args, **options):
        if os.getenv("LINGSU_E2E_SEED") != "1":
            raise CommandError(
                "拒绝执行：仅在显式设置 LINGSU_E2E_SEED=1 的集成/E2E 环境运行。"
            )

        school_name = options["school"]
        password = options["password"]
        if len(password) < 10:
            raise CommandError("E2E 测试密码至少需要 10 个字符。")

        with transaction.atomic():
            if options["reset"]:
                fixture_accounts = Account.objects.filter(username__in=ACCOUNT_NAMES)
                # Keep the fixed accounts so protected audit/auth references do
                # not make a repeated browser suite depend on deletion order.
                AuditEvent.objects.filter(actor__in=fixture_accounts).delete()
                Announcement.objects.filter(author__in=fixture_accounts).delete()
                AIGenerationLog.objects.filter(actor__in=fixture_accounts).delete()
                AIConversation.objects.filter(owner__in=fixture_accounts).delete()
                MaterialRevision.objects.filter(author__in=fixture_accounts).delete()
                PublicCaseRequest.objects.filter(applicant__in=fixture_accounts).delete()
                # The platform CRUD E2E creates global records outside the
                # fixture school; remove only its deterministic test prefix.
                Announcement.objects.filter(title__startswith="E2E 管理公告 ").delete()
                Competition.objects.filter(title__startswith="E2E 管理赛事 ").delete()
                AgentTemplate.objects.filter(key__startswith="e2e-management-").delete()
                School.objects.filter(name__startswith="E2E 管理学校 ").delete()
                School.objects.filter(name=school_name).delete()

            school, _ = School.objects.get_or_create(
                name=school_name,
                defaults={"is_active": True, "invite_code": "CORE-E2E"},
            )
            school.is_active = True
            school.save(update_fields=["is_active"])

            student = self._account(
                "core-e2e-student", Account.Role.STUDENT, school, password, "闭环学生"
            )
            self._account(
                "core-e2e-member", Account.Role.STUDENT, school, password, "协作学生"
            )
            self._account(
                "core-e2e-direct", Account.Role.STUDENT, school, password, "教师分配学生"
            )
            teacher = self._account(
                "core-e2e-teacher", Account.Role.TEACHER, school, password, "闭环教师"
            )
            platform = self._account(
                "core-e2e-platform",
                Account.Role.PLATFORM_ADMIN,
                None,
                password,
                "闭环平台管理员",
                is_staff=True,
                is_superuser=True,
            )

            template = self._template(school, teacher)
            project, _ = Project.objects.get_or_create(
                school=school,
                title="核心闭环验收项目",
                defaults={
                    "leader": student,
                    "status": Project.Status.UNCLAIMED,
                    "project_type": "research",
                    "problem": "如何通过连续观察改善校园雨后积水？",
                    "plan": "记录不同位置的积水变化，整理证据并提出改进建议。",
                },
            )
            if project.leader_id != student.id:
                project.leader = student
                project.save(update_fields=["leader"])
            student.primary_project = project
            student.save(update_fields=["primary_project"])
            project.members.get_or_create(account=student, defaults={"role": "leader"})
            self._completed_project(school, student, teacher)

        self.stdout.write(
            self.style.SUCCESS(
                f"核心闭环 E2E 数据已就绪：学校={school.name}，学生={student.username}，"
                f"教师={teacher.username}，平台={platform.username}，项目={project.title}，"
                f"模板={template.name}。"
            )
        )

    @staticmethod
    def _account(username, role, school, password, display_name, **flags):
        account, _ = Account.objects.get_or_create(
            username=username,
            defaults={
                "school": school,
                "role": role,
                "must_change_password": False,
                "first_name": display_name,
                **flags,
            },
        )
        account.school = school
        account.role = role
        account.must_change_password = False
        account.first_name = display_name
        for field, value in flags.items():
            setattr(account, field, value)
        account.set_password(password)
        account.save()
        return account

    @staticmethod
    def _template(school, teacher):
        template, _ = Template.objects.get_or_create(
            school=school,
            name="核心闭环验收模板",
            defaults={"category": "research", "is_published": True, "owner": teacher},
        )
        template.category = "research"
        template.is_published = True
        template.owner = teacher
        template.save(update_fields=["category", "is_published", "owner"])
        if template.stages.exists():
            return template

        stages = [
            (
                "记录与观察",
                1,
                "填写实验日志",
                "记录真实观察过程、时间和现象。",
                TemplateMaterial.Kind.EXPERIMENT_LOG,
                "实验日志",
                "按日期记录观察、操作、现象和待核实数据。",
            ),
            (
                "分析与表达",
                2,
                "整理研究记录",
                "根据已完成观察整理研究证据。",
                TemplateMaterial.Kind.STANDARD,
                "研究记录",
                "整理观察证据、初步分析和下一步改进建议。",
            ),
        ]
        stages.extend(
            (
                f"核心闭环预留章节 {stage_order}",
                stage_order,
                None,
                "",
                None,
                "",
                "",
            )
            for stage_order in range(len(stages) + 1, 23)
        )
        for stage_name, stage_order, task_name, task_description, kind, material_title, guidance in stages:
            stage = TemplateStage.objects.create(
                template=template, name=stage_name, order=stage_order
            )
            if task_name is None:
                continue
            task = TemplateTask.objects.create(
                stage=stage,
                name=task_name,
                order=1,
                description=task_description,
            )
            TemplateMaterial.objects.create(
                task=task,
                title=material_title,
                kind=kind,
                required=True,
                order=1,
                report_section=stage_name,
                guidance=guidance,
            )
        return template

    @staticmethod
    def _completed_project(school, student, teacher):
        """Provide a finished, case-free project for the public-case E2E branch."""
        project, _ = Project.objects.get_or_create(
            school=school,
            title="核心公域验收项目",
            defaults={
                "leader": student,
                "primary_teacher": teacher,
                "status": Project.Status.COMPLETED,
                "project_type": "research",
                "problem": "如何通过记录优化校园公共空间？",
                "plan": "整理已完成的观察证据并向校内外展示研究过程。",
            },
        )
        project.leader = student
        project.primary_teacher = teacher
        project.status = Project.Status.COMPLETED
        project.save(update_fields=["leader", "primary_teacher", "status"])
        project.members.get_or_create(account=student, defaults={"role": "leader"})
        task, _ = ProjectTask.objects.get_or_create(
            project=project,
            order=1,
            defaults={
                "stage_name": "成果整理",
                "stage_order": 1,
                "title": "整理公开结论",
                "description": "整理已完成研究的公开结论。",
                "status": ProjectTask.Status.COMPLETED,
            },
        )
        task.status = ProjectTask.Status.COMPLETED
        task.save(update_fields=["status"])
        material, _ = Material.objects.get_or_create(
            project=project,
            task=task,
            title="公开结论",
            defaults={
                "status": Material.Status.APPROVED,
                "required": True,
                "report_section": "成果结论",
                "report_order": 1,
            },
        )
        material.status = Material.Status.APPROVED
        material.save(update_fields=["status"])
        MaterialRevision.objects.get_or_create(
            material=material,
            author=student,
            status=MaterialRevision.Status.APPROVED,
            defaults={
                "content": "这是可以对外展示的真实研究结论。",
                "truth_confirmed": True,
            },
        )
        return project

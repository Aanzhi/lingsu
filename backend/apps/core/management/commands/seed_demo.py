"""Seed demo accounts for the three role-specific portals.

Usage:
    docker compose exec backend python manage.py seed_demo
    docker compose exec backend python manage.py seed_demo --reset --password=lips1234
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

from apps.core.models import Account, Material, Project, ProjectTask, School, Template
from apps.core.services import get_or_create_default_template, DEFAULT_TEMPLATE_BLUEPRINTS


DEMO_PASSWORD = "lingsu-demo-2026"

ACCOUNTS = [
    # username, role, is_staff, is_superuser, display_name
    ("demo-student", Account.Role.STUDENT, False, False, "林同学"),
    ("demo-teacher", Account.Role.TEACHER, False, False, "王老师"),
    ("demo-platform", Account.Role.PLATFORM_ADMIN, True, True, "平台管理员"),
]


def rebuild_project_to_template(project, template):
    """按最新蓝图模板重建项目的任务链（22 步 + 22 带指引材料），并去除门禁。"""
    Material.objects.filter(project=project).delete()
    project.tasks.all().delete()
    for stage in template.stages.prefetch_related("tasks__materials").all():
        for source_task in stage.tasks.all():
            order = project.tasks.count() + 1
            task = ProjectTask.objects.create(
                project=project, template_task=source_task, stage_name=stage.name,
                stage_order=stage.order, title=source_task.name,
                description=source_task.description, order=order,
                status=ProjectTask.Status.AVAILABLE,
            )
            for source_material in source_task.materials.all():
                Material.objects.create(
                    project=project, task=task, template_material=source_material,
                    title=source_material.title, required=source_material.required,
                    report_section=source_material.report_section, report_order=source_material.order,
                )
    project.template_snapshot = [
        {"stage": t.stage_name, "title": t.title, "order": t.order}
        for t in project.tasks.all()
    ]
    project.save(update_fields=["template_snapshot"])


class Command(BaseCommand):
    help = "为学生/教师/平台三端创建（或重置）演示账号与示例数据。"

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEMO_PASSWORD, help="统一密码，默认 lingsu-demo-2026")
        parser.add_argument("--school", default="灵溯演示学校", help="学校名称")
        parser.add_argument("--reset", action="store_true", help="删除已存在的同名账号后重建")
        parser.add_argument(
            "--allow-production",
            action="store_true",
            help="允许在 DJANGO_DEBUG=0 时执行（默认会在生产模式拒绝）",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_production"]:
            self.stderr.write(self.style.ERROR("生产环境拒绝执行；如确需运行请加 --allow-production。"))
            return

        password = options["password"]
        school_name = options["school"]
        reset = options["reset"]

        with transaction.atomic():
            school, _ = School.objects.get_or_create(
                name=school_name,
                defaults={"invite_code": "LINGSUO-DEMO", "is_active": True},
            )
            self.stdout.write(self.style.SUCCESS(f"学校就绪：{school.name} (id={school.id})"))

            for username, role, is_staff, is_superuser, display_name in ACCOUNTS:
                if reset and Account.objects.filter(username=username).exists():
                    Account.objects.filter(username=username).delete()
                    self.stdout.write(f"  - 已删除旧账号：{username}")

                user, created = Account.objects.get_or_create(
                    username=username,
                    defaults={
                        "school": None if role == Account.Role.PLATFORM_ADMIN else school,
                        "role": role,
                        "is_staff": is_staff,
                        "is_superuser": is_superuser,
                        "must_change_password": False,
                        "first_name": display_name,
                    },
                )
                # 始终刷新密码、display_name、role，便于 reset 之外的幂等更新
                user.set_password(password)
                user.school = None if role == Account.Role.PLATFORM_ADMIN else school
                user.role = role
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.must_change_password = False
                user.first_name = display_name
                user.save()

                tag = "新建" if created else "更新"
                self.stdout.write(self.style.SUCCESS(f"  - {tag}账号：{username} ({role})"))

            student = Account.objects.get(username="demo-student")
            teacher = Account.objects.get(username="demo-teacher")

            # 确保演示学校每分类都有一个「最新蓝图」的默认模板（22 步、材料带 guidance）；
            # 先清理该学校下陈腐（阶段数不符）的默认模板，避免旧的 5 阶段 / 0 指引模板残留。
            for cat in DEFAULT_TEMPLATE_BLUEPRINTS:
                expected = len(DEFAULT_TEMPLATE_BLUEPRINTS[cat])
                stale = (Template.objects
                         .filter(school=school, category=cat, is_published=True)
                         .annotate(nstages=Count("stages"))
                         .exclude(nstages=expected))
                if stale.exists():
                    n = stale.count()
                    stale.delete()
                    self.stdout.write(f"  - 清理陈腐默认模板({cat})：{n} 个")

            templates = {
                cat: get_or_create_default_template(school=school, owner=teacher, category=cat)
                for cat in DEFAULT_TEMPLATE_BLUEPRINTS
            }

            # 给学生配一个主示例项目（research），方便三端联动演示
            project, proj_created = Project.objects.get_or_create(
                school=school,
                title="校园雨水花园观察",
                defaults={
                    "leader": student,
                    "primary_teacher": teacher,
                    "template_snapshot": {},
                    "project_type": "research",
                    "status": Project.Status.ACTIVE,
                    "problem": "校园绿地雨后积水，能否用本地植物组合降低径流？",
                    "plan": "选取三处样方，记录雨后 24h 土壤含水量与植物存活率。",
                },
            )
            if proj_created:
                project.members.get_or_create(account=student, defaults={"role": "leader"})
                project.members.get_or_create(account=teacher, defaults={"role": "teacher"})
                self.stdout.write(self.style.SUCCESS(f"  - 新建示例项目：{project.title} (id={project.id})"))
            else:
                self.stdout.write(f"  - 示例项目已存在：{project.title}")

            # 规范化 demo-student 名下所有项目：按各自分类的最新蓝图重建任务链（含 guidance）。
            # 阶段数不符、或材料指引缺失的项目会被重建；已正确的项目（如主示例）保持不变，不误删进度。
            CATEGORY_BY_TYPE = {"research": "research", "engineering": "engineering", "invention": "invention"}
            for proj in Project.objects.filter(leader=student):
                cat = CATEGORY_BY_TYPE.get(proj.project_type, "research")
                tmpl = templates[cat]
                need_rebuild = (not proj.tasks.exists()) or (proj.tasks.count() != tmpl.stages.count())
                if not need_rebuild:
                    lacking = (Material.objects
                               .filter(project=proj)
                               .filter(Q(template_material__isnull=True) | Q(template_material__guidance=""))
                               .exists())
                    need_rebuild = lacking
                if need_rebuild:
                    rebuild_project_to_template(proj, tmpl)
                    self.stdout.write(self.style.SUCCESS(
                        f"  - 重建项目任务链：{proj.title} ({tmpl.stages.count()} 步)"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== 演示账号清单 ==="))
        self.stdout.write(f"  学校邀请码：{school.invite_code}")
        self.stdout.write(f"  统一密码  ：{password}")
        self.stdout.write("  ┌──────────────┬──────────────────┬──────────────┐")
        self.stdout.write("  │ 账号         │ 角色             │ 入口         │")
        self.stdout.write("  ├──────────────┼──────────────────┼──────────────┤")
        self.stdout.write("  │ demo-student │ student          │ /student     │")
        self.stdout.write("  │ demo-teacher │ teacher          │ /teacher     │")
        self.stdout.write("  │ demo-platform│ platform_admin   │ /platform    │")
        self.stdout.write("  └──────────────┴──────────────────┴──────────────┘")
        self.stdout.write("")
        self.stdout.write("登录页：POST /api/login/  body={\"username\":\"...\",\"password\":\"...\"}")
        self.stdout.write("开发模式快捷：POST /api/demo-login/  body={\"role\":\"platform_admin\"}")

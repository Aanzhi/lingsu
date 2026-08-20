from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import secrets


def make_invite_code():
    return secrets.token_urlsafe(8)


class School(models.Model):
    name = models.CharField(max_length=120, unique=True)
    invite_code = models.CharField(max_length=20, unique=True, null=True, blank=True, default=make_invite_code)
    is_active = models.BooleanField(default=True)
    license_expires_at = models.DateField(null=True, blank=True)
    ai_quota = models.PositiveIntegerField(default=100)
    storage_quota_mb = models.PositiveIntegerField(default=10240)

    def __str__(self): return self.name

    @property
    def is_authorized(self):
        return self.is_active and (not self.license_expires_at or self.license_expires_at >= timezone.localdate())


class AuditEvent(models.Model):
    """Minimal, non-sensitive audit trail for platform governance actions."""

    class Action(models.TextChoices):
        SCHOOL_UPDATED = "school_updated", "学校配置已更新"
        INVITE_CODE_RESET = "invite_code_reset", "邀请码已重置"
        PROJECT_CLAIMED = "project_claimed", "项目已认领"
        PROJECT_ARCHIVED = "project_archived", "项目已归档"
        PROJECT_TRASHED = "project_trashed", "项目已移入回收站"
        PROJECT_RESTORED = "project_restored", "项目已恢复"
        PROJECT_UPDATED = "project_updated", "项目信息已更新"
        MEMBER_INVITATION_DECIDED = "member_invitation_decided", "成员邀请已处理"
        MEMBER_ASSIGNED = "member_assigned", "成员已分配"
        MATERIAL_SUBMITTED = "material_submitted", "材料已提交审核"
        MATERIAL_REVIEWED = "material_reviewed", "材料审核已完成"
        CASE_SUBMITTED = "case_submitted", "公开申请已提交"
        CASE_REVIEWED = "case_reviewed", "公开案例已审核"
        CASE_VISIBILITY_CHANGED = "case_visibility_changed", "公开案例可见性已变更"
        REPORT_EXPORT_REQUESTED = "report_export_requested", "报告导出已请求"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="audit_events")
    action = models.CharField(max_length=40, choices=Action.choices)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Notification(models.Model):
    """In-app notification for the recipient; driven by notifiers module."""

    class Kind(models.TextChoices):
        INVITATION_ACCEPTED = "invitation_accepted", "成员接受邀请"
        INVITATION_REJECTED = "invitation_rejected", "成员拒绝邀请"
        MEMBER_ASSIGNED = "member_assigned", "被加入项目"
        MATERIAL_APPROVED = "material_approved", "材料已通过"
        MATERIAL_REVISION_REQUIRED = "material_revision_required", "材料需修订"
        CASE_PUBLISHED = "case_published", "案例已发布"
        CASE_REJECTED = "case_rejected", "案例被驳回"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="notifications")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="triggered_notifications",
    )
    kind = models.CharField(max_length=40, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    project = models.ForeignKey("Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Account(AbstractUser):
    class Role(models.TextChoices):
        PLATFORM_ADMIN = "platform_admin", "平台管理员"
        TEACHER = "teacher", "教师"
        STUDENT = "student", "学生"
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL, related_name="accounts")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    must_change_password = models.BooleanField(default=True)
    primary_project = models.ForeignKey(
        "Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="primary_for_accounts",
    )

    class Meta:
        indexes = [models.Index(fields=["primary_project"], name="account_primary_proj_idx")]


class ProjectManager(models.Manager):
    """Default manager that hides soft-deleted (trashed) projects from list views."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllProjectsManager(models.Manager):
    """Manager that returns every project, including trashed ones for admin flows."""


class SchoolBound(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    class Meta: abstract = True


class Template(SchoolBound):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=30, default="research")
    is_published = models.BooleanField(default=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)


class Competition(SchoolBound):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"

    class Audience(models.TextChoices):
        ALL = "all", "全校"
        STUDENTS = "students", "学生"
        TEACHERS = "teachers", "教师"

    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.CASCADE, related_name="competitions")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    audience = models.CharField(max_length=16, choices=Audience.choices, default=Audience.ALL)
    template = models.ForeignKey(Template, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)


class Announcement(SchoolBound):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"

    class Audience(models.TextChoices):
        ALL = "all", "全校"
        STUDENTS = "students", "学生"
        TEACHERS = "teachers", "教师"

    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=160)
    body = models.TextField()
    audience = models.CharField(max_length=16, choices=Audience.choices, default=Audience.ALL)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="reads")
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["announcement", "account"], name="unique_announcement_read")]


class TemplateStage(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)

    class Meta: ordering = ["order"]


class TemplateTask(models.Model):
    stage = models.ForeignKey(TemplateStage, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)


class TemplateMaterial(models.Model):
    task = models.ForeignKey(TemplateTask, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=120)
    required = models.BooleanField(default=True)
    submission_type = models.CharField(max_length=20, default="rich_text")
    report_section = models.CharField(max_length=120, blank=True)
    order = models.PositiveIntegerField(default=0)
    guidance = models.TextField(blank=True, help_text="系统默认的内嵌填写指引/章节大纲")
    reference_file = models.FileField(upload_to="material-references/%Y/%m/", null=True, blank=True)


class Project(SchoolBound):
    class Status(models.TextChoices):
        UNCLAIMED = "unclaimed", "待认领"
        ACTIVE = "active", "进行中"
        COMPLETED = "completed", "已完成"
    title = models.CharField(max_length=200)
    problem = models.TextField(blank=True)
    plan = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="led_projects")
    primary_teacher = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="guided_projects")
    template_snapshot = models.JSONField(default=dict, blank=True)
    project_type = models.CharField(max_length=30, default="research")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNCLAIMED)
    created_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    trashed_at = models.DateTimeField(null=True, blank=True)

    objects = ProjectManager()
    all_objects = AllProjectsManager()

    class Meta:
        indexes = [
            models.Index(fields=["school", "deleted_at"], name="project_school_trash_idx"),
            models.Index(fields=["school", "is_archived", "status"], name="project_school_arch_idx"),
        ]


class ProjectTask(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "可开始"
        PENDING_REVIEW = "pending_review", "待审核"
        REVISION_REQUIRED = "revision_required", "需修订"
        APPROVED = "approved", "已通过"
        COMPLETED = "completed", "已完成"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    template_task = models.ForeignKey(TemplateTask, null=True, blank=True, on_delete=models.SET_NULL)
    stage_name = models.CharField(max_length=120)
    stage_order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    evidence_requirements = models.JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.AVAILABLE)
    xp_reward = models.PositiveIntegerField(default=100)
    due_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["project", "order"], name="unique_project_task_order")]


class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, default="member")
    class Meta: unique_together = [("project", "account")]


class MemberInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING_STUDENT = "pending_student", "等待学生确认"
        PENDING_TEACHER = "pending_teacher", "等待教师确认"
        APPROVED = "approved", "已加入"
        REJECTED = "rejected", "已拒绝"
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="invitations")
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations")
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_invitations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_STUDENT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = [("project", "invitee")]


class ProjectGrowth(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="growth")
    experience = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    streak_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    achievements = models.JSONField(default=list, blank=True)
    title = models.CharField(max_length=60, default="探索新手")


class Material(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        SUBMITTED = "submitted", "待审核"
        REVISION_REQUIRED = "revision_required", "需修订"
        APPROVED = "approved", "已通过"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="materials")
    task = models.ForeignKey(ProjectTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="materials")
    template_material = models.ForeignKey(TemplateMaterial, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=120)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    required = models.BooleanField(default=True)
    report_section = models.CharField(max_length=120, blank=True)
    report_order = models.PositiveIntegerField(default=0)
    guidance_override = models.TextField(blank=True, help_text="教师针对本项目覆盖的系统默认指引")
    reference_file_override = models.FileField(upload_to="material-references/%Y/%m/", null=True, blank=True)

    @property
    def effective_guidance(self):
        if self.guidance_override:
            return self.guidance_override
        return self.template_material.guidance if self.template_material else ""

    @property
    def effective_reference(self):
        """Return (file_field, original_name) for the effective reference, teacher override wins."""
        override = self.reference_file_override
        if override:
            return override, override.name.rsplit("/", 1)[-1]
        if self.template_material and self.template_material.reference_file:
            tmpl = self.template_material.reference_file
            return tmpl, tmpl.name.rsplit("/", 1)[-1]
        return None, None


class MaterialRevision(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        SUBMITTED = "submitted", "待审核"
        REVISION_REQUIRED = "revision_required", "需修订"
        APPROVED = "approved", "已通过"

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="revisions")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to="materials/%Y/%m/", blank=True)
    truth_confirmed = models.BooleanField(default=False)
    revision_note = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_revisions")
    review_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MaterialAttachment(models.Model):
    class ScanStatus(models.TextChoices):
        PENDING = "pending", "等待安全检查"
        PROCESSING = "processing", "检查中"
        CLEAN = "clean", "安全"
        INFECTED = "infected", "发现威胁"
        FAILED = "failed", "检查失败"

    revision = models.ForeignKey(MaterialRevision, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="materials/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    scan_status = models.CharField(max_length=16, choices=ScanStatus.choices, default=ScanStatus.PENDING)
    scan_detail = models.CharField(max_length=500, blank=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class ExtractStatus(models.TextChoices):
        PENDING = "pending", "待抽取"
        PROCESSING = "processing", "抽取中"
        DONE = "done", "已抽取"
        UNSUPPORTED = "unsupported", "暂不支持的文件类型"
        FAILED = "failed", "抽取失败"

    extracted_text = models.TextField(blank=True, help_text="上传文件抽取的可读文本（PDF/Word/图片OCR），供 AI 上下文使用")
    extract_status = models.CharField(max_length=16, choices=ExtractStatus.choices, default=ExtractStatus.PENDING)
    extract_detail = models.CharField(max_length=500, blank=True)
    extracted_at = models.DateTimeField(null=True, blank=True)


class UploadSession(models.Model):
    """A private, resumable upload owned by one immutable material revision."""
    class Status(models.TextChoices):
        ACTIVE = "active", "上传中"
        COMPLETED = "completed", "已完成"
        ABORTED = "aborted", "已取消"
        EXPIRED = "expired", "已过期"

    revision = models.ForeignKey(MaterialRevision, on_delete=models.CASCADE, related_name="upload_sessions")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    total_size = models.PositiveBigIntegerField()
    chunk_size = models.PositiveIntegerField()
    expected_sha256 = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    attachment = models.OneToOneField(MaterialAttachment, null=True, blank=True, on_delete=models.SET_NULL, related_name="upload_session")

    @property
    def part_count(self):
        return (self.total_size + self.chunk_size - 1) // self.chunk_size


class UploadPart(models.Model):
    session = models.ForeignKey(UploadSession, on_delete=models.CASCADE, related_name="parts")
    index = models.PositiveIntegerField()
    file = models.FileField(upload_to="upload-parts/%Y/%m/")
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "index"], name="unique_upload_session_part")]


class PublicCaseRequest(models.Model):
    class Status(models.TextChoices): PENDING_TEACHER = "pending_teacher", "教师审核"; PUBLISHED = "published", "已公开"; OFFLINE = "offline", "已下架"; REJECTED = "rejected", "已拒绝"
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="public_request")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    public_summary = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    discipline = models.CharField(max_length=80, blank=True)
    application_scene = models.CharField(max_length=120, blank=True)
    outcome_form = models.CharField(max_length=80, blank=True)
    cover = models.ImageField(upload_to="cases/%Y/%m/", blank=True)
    selected_materials = models.ManyToManyField(Material, blank=True, related_name="public_case_selections")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_TEACHER)
    teacher_reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="teacher_public_reviews")
    review_comment = models.TextField(blank=True)
    admin_reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="admin_public_reviews")


class AIGenerationLog(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "排队中"
        PROCESSING = "processing", "生成中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="ai_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    purpose = models.CharField(max_length=80, default="", blank=True)  # 可由 agent 模板名注入；自由用途也可留空
    agent_key = models.CharField(max_length=80, null=True, blank=True)  # 关联 AgentTemplate.key；历史/自由用途记录为 NULL
    task = models.ForeignKey(ProjectTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_logs")  # 审计：本次针对哪一步
    material = models.ForeignKey(Material, null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_logs")  # 审计：本次针对哪份材料
    prompt = models.TextField(default="")
    context_scope = models.JSONField(default=dict)
    referenced_sources = models.JSONField(default=list, blank=True, help_text="本次生成实际读取的来源清单（步骤/材料/文件），供前端溯源展示")
    output = models.TextField(blank=True)
    artifact_payload = models.JSONField(default=dict, blank=True, help_text="结构化生成物；保留可写入材料的正文、标题及分段信息")
    verification_items = models.JSONField(default=list, blank=True, help_text="生成物中需要学生核验的文献、数据、事实清单")
    paper_type = models.CharField(max_length=40, blank=True, default="", help_text="论文类型，如 empirical、review、case")
    saved_material_revision = models.OneToOneField(
        MaterialRevision, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="source_ai_log", help_text="由本次 AI 生成保存而成的不可变材料草稿",
    )
    model_name = models.CharField(max_length=100, default="configured-model")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class AgentTemplate(models.Model):
    """可配置的 AI Agent 模板：每个模板拥有独立的 system 指令、提示词模板与输入变量。"""

    class Role(models.TextChoices):
        STUDENT = "student", "学生"
        TEACHER = "teacher", "教师"
        BOTH = "both", "师生通用"

    key = models.CharField(max_length=80)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    category = models.CharField(max_length=40, blank=True, default="")  # 分组：开题/实验/写作/答辩/教师审核
    system_instruction = models.TextField()  # 含护栏的 system prompt
    prompt_template = models.TextField()  # 含 {变量} 占位
    input_schema = models.JSONField(default=list, blank=True)  # [{key,label,placeholder,required,type,options?}]
    context_scope_default = models.JSONField(default=dict, blank=True)  # {project_basics, approved_materials}
    workflow = models.CharField(max_length=40, blank=True, default="", help_text="工作流标识，如 proposal 或 paper")
    applicable_stages = models.JSONField(default=list, blank=True, help_text="适用研究阶段")
    quick_tasks = models.JSONField(default=list, blank=True, help_text="可触发该助手的快捷任务")
    project_types = models.JSONField(default=list, blank=True, help_text="适用项目类型")
    output_contract = models.JSONField(default=dict, blank=True, help_text="结构化输出约定")
    is_active = models.BooleanField(default=True)
    school = models.ForeignKey(
        School, null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_agents"
    )  # null = 平台全局模板；非 null = 某校校本模板
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            # 全局模板（school 为 NULL）每 key 仅一条；校本模板每 (key, school) 仅一条。
            # 注意：Postgres 的 UNIQUE(key, school) 对 NULL 不生效，必须用部分唯一约束区分。
            models.UniqueConstraint(fields=["key"], name="uniq_global_agent_key", condition=models.Q(school=None)),
            models.UniqueConstraint(fields=["key", "school"], name="uniq_school_agent_key", condition=models.Q(school__isnull=False)),
        ]
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["school", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.key})"

    @classmethod
    def resolve(cls, agent_key, school, role):
        """校本优先：先找该校同名 key 的活动模板，否则找全局；按角色（含 both）过滤。"""
        if not agent_key:
            return None
        cand = cls.objects.filter(key=agent_key, is_active=True)
        school_match = cand.filter(school=school).filter(role__in=[role, cls.Role.BOTH]).first()
        if school_match:
            return school_match
        return cand.filter(school=None).filter(role__in=[role, cls.Role.BOTH]).first()


class ReportExport(models.Model):
    class Format(models.TextChoices):
        DOCX = "docx", "Word"
        PDF = "pdf", "PDF"

    class Status(models.TextChoices):
        QUEUED = "queued", "排队中"
        PROCESSING = "processing", "生成中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "生成失败"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="report_exports")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    format = models.CharField(max_length=8, choices=Format.choices, default=Format.DOCX)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    file = models.FileField(upload_to="reports/%Y/%m/", blank=True)
    project_version = models.CharField(max_length=60, blank=True)
    material_manifest = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

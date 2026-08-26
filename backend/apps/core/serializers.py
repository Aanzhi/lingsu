from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import serializers
from .models import AIGenerationLog, AIConversation, AIConversationMessage, Account, AgentTemplate, Announcement, AuditEvent, Competition, Material, MaterialAttachment, MaterialRevision, MemberInvitation, Notification, Project, ProjectGrowth, ProjectMember, ProjectTask, PublicCaseRequest, ReportExport, School, Template, TemplateMaterial, UploadSession
from .ai_agents import PAPER_AGENT_KEYS, PAPER_TYPES, normalize_workspace_mode, validate_agent_inputs
from .tasks import process_uploaded_material


class ProjectMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="account.username", read_only=True)
    class Meta: model = ProjectMember; fields = ["id", "account", "username", "role"]

class ProjectSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(many=True, read_only=True)
    growth = serializers.SerializerMethodField()
    school_name = serializers.CharField(source="school.name", read_only=True)
    primary_teacher_name = serializers.SerializerMethodField()
    is_primary = serializers.SerializerMethodField()
    days_until_purge = serializers.SerializerMethodField()
    class Meta: model = Project; fields = ["id", "school", "school_name", "title", "problem", "plan", "summary", "leader", "primary_teacher", "primary_teacher_name", "template_snapshot", "project_type", "status", "members", "growth", "is_archived", "archived_at", "deleted_at", "trashed_at", "days_until_purge", "is_primary", "created_at"]; read_only_fields = ["school", "leader", "template_snapshot", "primary_teacher", "primary_teacher_name", "status", "is_archived", "archived_at", "deleted_at", "trashed_at", "days_until_purge"]
    def get_primary_teacher_name(self, obj):
        if not obj.primary_teacher:
            return None
        return obj.primary_teacher.get_full_name() or obj.primary_teacher.username
    def get_growth(self, obj):
        growth, _ = ProjectGrowth.objects.get_or_create(project=obj)
        return {"experience": growth.experience, "level": growth.level, "streak_days": growth.streak_days, "achievements": growth.achievements, "title": growth.title}

    def get_is_primary(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return getattr(request.user, "primary_project_id", None) == obj.id

    def get_days_until_purge(self, obj):
        if not obj.trashed_at:
            return None
        delta = (obj.trashed_at + timedelta(days=30)) - timezone.now()
        return max(0, delta.days)


class ProjectTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTask
        fields = ["id", "project", "stage_name", "stage_order", "title", "description", "evidence_requirements", "order", "status", "xp_reward", "due_at"]
        read_only_fields = fields

class SchoolSerializer(serializers.ModelSerializer):
    is_authorized = serializers.BooleanField(read_only=True)
    student_count = serializers.SerializerMethodField()
    teacher_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    class Meta: model = School; fields = ["id", "name", "invite_code", "is_active", "license_expires_at", "is_authorized", "ai_quota", "storage_quota_mb", "student_count", "teacher_count", "project_count"]

    def validate_is_active(self, value):
        if not isinstance(self.initial_data.get("is_active"), bool):
            raise serializers.ValidationError("请提供 true 或 false 布尔值。")
        return value

    def get_student_count(self, obj): return obj.accounts.filter(role=Account.Role.STUDENT).count()
    def get_teacher_count(self, obj): return obj.accounts.filter(role=Account.Role.TEACHER).count()
    def get_project_count(self, obj): return Project.objects.filter(school=obj).count()


class AuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "school", "actor", "actor_name", "action", "changes", "created_at"]
        read_only_fields = fields

class MemberInvitationSerializer(serializers.ModelSerializer):
    invitee_name = serializers.CharField(source="invitee.username", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)
    class Meta:
        model = MemberInvitation
        fields = ["id", "project", "project_title", "inviter", "invitee", "invitee_name", "status", "created_at"]
        read_only_fields = ["inviter", "status"]
        validators = []

    def validate(self, attrs):
        project = attrs.get("project")
        invitee = attrs.get("invitee")
        if project and invitee and MemberInvitation.objects.filter(project=project, invitee=invitee).exists():
            raise serializers.ValidationError("该学生已有邀请记录，不能重复邀请。")
        if project and invitee and project.members.filter(account=invitee).exists():
            raise serializers.ValidationError("该学生已经是项目成员。")
        return attrs

class MaterialAttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MaterialAttachment
        fields = ["id", "original_name", "content_type", "size", "sha256", "scan_status", "scan_detail", "extract_status", "extract_detail", "download_url", "created_at"]

    def get_download_url(self, obj):
        if not self.context.get("request"):
            return None
        return f"/api/material-attachments/{obj.pk}/download/"


class UploadSessionSerializer(serializers.ModelSerializer):
    uploaded_parts = serializers.SerializerMethodField()
    part_count = serializers.IntegerField(read_only=True)
    attachment_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = UploadSession
        fields = [
            "id", "revision", "original_name", "content_type", "total_size", "chunk_size",
            "expected_sha256", "status", "expires_at", "created_at", "completed_at",
            "part_count", "uploaded_parts", "attachment_id",
        ]
        read_only_fields = ["status", "expires_at", "created_at", "completed_at", "part_count", "uploaded_parts", "attachment_id"]

    def get_uploaded_parts(self, obj):
        return list(obj.parts.order_by("index").values_list("index", flat=True))

    def validate_original_name(self, value):
        suffix = Path(value).suffix.lower()
        if suffix in {".exe", ".com", ".bat", ".cmd", ".msi", ".dll", ".scr", ".ps1", ".sh"}:
            raise serializers.ValidationError(f"不允许上传该文件类型：{suffix}")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        revision = attrs["revision"]
        total_size = attrs["total_size"]
        chunk_size = attrs["chunk_size"]
        if total_size < 1 or total_size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError({"total_size": "文件大小不在允许范围内。"})
        if not settings.UPLOAD_CHUNK_MIN_SIZE <= chunk_size <= settings.UPLOAD_CHUNK_MAX_SIZE:
            raise serializers.ValidationError({"chunk_size": "分块大小不在允许范围内。"})
        if revision.author_id != request.user.id:
            raise serializers.ValidationError({"revision": "只能为自己的材料版本创建上传会话。"})
        project = revision.material.project
        used = MaterialAttachment.objects.filter(revision__material__project__school=project.school).aggregate(total=Sum("size"))["total"] or 0
        reserved = UploadSession.objects.filter(
            revision__material__project__school=project.school,
            status=UploadSession.Status.ACTIVE,
        ).aggregate(total=Sum("total_size"))["total"] or 0
        if used + reserved + total_size > project.school.storage_quota_mb * 1024 * 1024:
            raise serializers.ValidationError("学校存储配额不足，请联系平台管理员扩容。")
        return attrs


class MaterialRevisionSerializer(serializers.ModelSerializer):
    material_title = serializers.CharField(source="material.title", read_only=True)
    project_title = serializers.CharField(source="material.project.title", read_only=True)
    author_name = serializers.CharField(source="author.username", read_only=True)
    primary_teacher_id = serializers.IntegerField(source="material.project.primary_teacher_id", read_only=True, allow_null=True)
    attachments = MaterialAttachmentSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    source_summary = serializers.SerializerMethodField()
    verification_summary = serializers.SerializerMethodField()

    class Meta:
        model = MaterialRevision
        fields = ["id", "material", "material_title", "project_title", "author", "author_name", "primary_teacher_id", "content", "truth_confirmed", "revision_note", "status", "reviewer", "review_comment", "created_at", "attachments", "uploaded_files", "source_summary", "verification_summary"]
        read_only_fields = ["author", "status", "reviewer", "review_comment", "truth_confirmed"]

    def validate_uploaded_files(self, uploads):
        request = self.context["request"]
        max_size = getattr(settings, "MAX_UPLOAD_SIZE", 500 * 1024 * 1024)
        denied_extensions = {".exe", ".com", ".bat", ".cmd", ".msi", ".dll", ".scr", ".ps1", ".sh"}
        for upload in uploads:
            if upload.size > max_size:
                raise serializers.ValidationError(f"文件 {upload.name} 大小超过允许上限。")
            suffix = Path(upload.name).suffix.lower()
            if suffix in denied_extensions:
                raise serializers.ValidationError(f"不允许上传该文件类型：{suffix}")
        material_id = self.initial_data.get("material")
        material = Material.objects.filter(pk=material_id).select_related("project__school").first()
        if material and request.user.school_id == material.project.school_id:
            used = MaterialAttachment.objects.filter(revision__material__project__school=material.project.school).aggregate(total=Sum("size"))["total"] or 0
            reserved = UploadSession.objects.filter(
                revision__material__project__school=material.project.school,
                status=UploadSession.Status.ACTIVE,
                expires_at__gt=timezone.now(),
            ).aggregate(total=Sum("total_size"))["total"] or 0
            if used + reserved + sum(upload.size for upload in uploads) > material.project.school.storage_quota_mb * 1024 * 1024:
                raise serializers.ValidationError("学校存储配额不足，请联系平台管理员扩容。")
        return uploads

    def create(self, validated_data):
        uploads = validated_data.pop("uploaded_files", [])
        revision = super().create(validated_data)
        for upload in uploads:
            MaterialAttachment.objects.create(
                revision=revision,
                file=upload,
                original_name=upload.name,
                content_type=getattr(upload, "content_type", "") or "",
                size=upload.size,
            )
        if uploads:
            transaction.on_commit(lambda: process_uploaded_material.delay(revision.id))
        return revision

    def get_source_summary(self, obj):
        log = getattr(obj, "source_ai_log", None)
        if not log:
            return None
        return {
            "ai_log_id": log.id,
            "agent_key": log.agent_key,
            "purpose": log.purpose,
            "paper_type": log.paper_type,
            "created_at": log.created_at,
        }

    def get_verification_summary(self, obj):
        log = getattr(obj, "source_ai_log", None)
        if not log:
            return None
        items = log.verification_items or []
        return {"total": len(items), "items": items}

class MaterialSerializer(serializers.ModelSerializer):
    revisions = MaterialRevisionSerializer(many=True, read_only=True)
    guidance = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()

    class Meta: model = Material; fields = ["id", "project", "task", "template_material", "title", "kind", "status", "required", "report_section", "report_order", "revisions", "guidance", "reference"]

    def get_guidance(self, obj):
        return obj.effective_guidance

    def get_reference(self, obj):
        file_field, original_name = obj.effective_reference
        if file_field:
            return {"url": f"/api/materials/{obj.pk}/reference/download/", "original_name": original_name}
        if obj.effective_guidance:
            safe = (obj.title or "参考范本").replace("/", "_")
            return {"url": f"/api/materials/{obj.pk}/reference/download/", "original_name": f"{safe}_参考范本.docx"}
        return None


class TemplateMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateMaterial
        fields = ["id", "task", "title", "kind", "required", "submission_type", "report_section", "order", "guidance", "reference_file"]

class TemplateSerializer(serializers.ModelSerializer):
    class Meta: model = Template; fields = "__all__"; read_only_fields = ["school", "owner"]

class PublicCaseRequestSerializer(serializers.ModelSerializer):
    selected_material_summaries = serializers.SerializerMethodField()
    project_title = serializers.CharField(source="project.title", read_only=True)
    school_name = serializers.CharField(source="project.school.name", read_only=True)
    class Meta:
        model = PublicCaseRequest
        fields = ["id", "project", "project_title", "school_name", "applicant", "request_type", "visibility_scope", "public_summary", "tags", "discipline", "application_scene", "outcome_form", "cover", "selected_materials", "selected_material_summaries", "status", "teacher_reviewer", "review_comment", "admin_reviewer", "student_consent_at", "student_consent_by", "platform_reviewer"]
        read_only_fields = ["applicant", "teacher_reviewer", "review_comment", "admin_reviewer", "student_consent_at", "student_consent_by", "platform_reviewer", "status", "selected_material_summaries"]

    def validate_selected_materials(self, materials):
        project = self.initial_data.get("project") or (self.instance.project_id if self.instance else None)
        invalid = [item.id for item in materials if str(item.project_id) != str(project) or item.status != Material.Status.APPROVED]
        if invalid:
            raise serializers.ValidationError("只能选择本项目已通过的材料公开。")
        return materials

    def get_selected_material_summaries(self, obj):
        result = []
        for material in obj.selected_materials.filter(status=Material.Status.APPROVED).order_by("report_order", "id"):
            revision = material.revisions.filter(status=MaterialRevision.Status.APPROVED).order_by("-created_at", "-id").first()
            if revision:
                result.append({"material_id": material.id, "title": material.title, "report_section": material.report_section, "content": revision.content})
        return result

class AIGenerationLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)
    input_values = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = AIGenerationLog
        fields = ["id", "project", "workspace_mode", "conversation", "message", "actor", "actor_name", "purpose", "agent_key", "task", "material", "prompt", "input_values", "context_scope", "referenced_sources", "output", "artifact_payload", "verification_items", "paper_type", "saved_material_revision", "model_name", "status", "error_message", "created_at", "completed_at"]
        read_only_fields = ["actor", "conversation", "message", "output", "artifact_payload", "verification_items", "saved_material_revision", "model_name", "status", "error_message", "completed_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project") or getattr(self.instance, "project", None)
        workspace_mode = normalize_workspace_mode(attrs.get("workspace_mode") or getattr(self.instance, "workspace_mode", "research"))
        attrs["workspace_mode"] = workspace_mode
        if project is None and workspace_mode != "opening" and attrs.get("agent_key"):
            raise serializers.ValidationError({"project": "研究或答辩 AI 必须绑定当前项目。"})
        if project is not None and workspace_mode == "opening" and "workspace_mode" in self.initial_data:
            raise serializers.ValidationError({"project": "开题 AI 不读取项目上下文。"})
        task = attrs.get("task")
        material = attrs.get("material")
        if task and project and task.project_id != project.id:
            raise serializers.ValidationError({"task": "所选步骤不属于该项目。"})
        if material and project and material.project_id != project.id:
            raise serializers.ValidationError({"material": "所选材料不属于该项目。"})
        if material and task and material.task_id and material.task_id != task.id:
            raise serializers.ValidationError({"material": "所选材料不属于该步骤。"})
        agent_key = attrs.get("agent_key")
        paper_type = attrs.get("paper_type") or getattr(self.instance, "paper_type", "")
        if paper_type and paper_type not in PAPER_TYPES:
            raise serializers.ValidationError({
                "paper_type": "论文类型仅支持 empirical、case、literature-review 或 theoretical。"
            })
        if agent_key:
            user = self.context["request"].user
            tmpl = AgentTemplate.resolve(agent_key, user.school, user.role)
            if not tmpl:
                raise serializers.ValidationError({"agent_key": "指定的 AI 模板不存在或无权限使用。"})
            if agent_key in PAPER_AGENT_KEYS and not paper_type:
                raise serializers.ValidationError({
                    "paper_type": "论文写作工具必须选择论文类型：empirical、case、literature-review 或 theoretical。"
                })
            submitted_inputs = attrs.pop("input_values", None)
            if submitted_inputs is None:
                # Older clients submit one free-form prompt. Keep that request
                # shape working while giving every required field a non-empty
                # value until the client renders the template input form.
                submitted_inputs = {
                    field.get("key"): attrs.get("prompt", "")
                    for field in (tmpl.input_schema or [])
                    if isinstance(field, dict) and field.get("key") and field.get("required")
                }
            try:
                validated_inputs = validate_agent_inputs(tmpl, submitted_inputs)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"input_values": exc.detail})
            if tmpl.project_types and project and project.project_type not in tmpl.project_types:
                raise serializers.ValidationError({
                    "agent_key": f"该 AI 模板不适用于“{project.project_type}”类型项目。"
                })
            context_scope = self._template_context_scope(tmpl, attrs.get("context_scope"))
            self._validate_selected_context(project, workspace_mode, context_scope)
            context_scope["agent_inputs"] = validated_inputs
            attrs["context_scope"] = context_scope
            if not attrs.get("purpose"):
                attrs["purpose"] = tmpl.name
        else:
            # input_values is transport-only for free-form conversations.
            attrs.pop("input_values", None)
        return attrs

    @staticmethod
    def _template_context_scope(template, submitted_scope):
        """Keep data exposure under the template's control, not the client's."""
        if submitted_scope is not None and not isinstance(submitted_scope, dict):
            raise serializers.ValidationError({"context_scope": "上下文范围必须是对象。"})

        defaults = dict(template.context_scope_default or {})
        submitted_scope = submitted_scope or {}
        permitted_selections = set(defaults.get("allowed_selections") or [])
        safe_selection_keys = {"related_tasks", "selected_materials"}
        supplied_selections = set(submitted_scope) & safe_selection_keys
        disallowed = supplied_selections - permitted_selections
        if disallowed:
            raise serializers.ValidationError({
                "context_scope": f"该 AI 模板不允许选择：{', '.join(sorted(disallowed))}。"
            })

        # Context booleans (including approved_materials and consistency) stay
        # exactly as the platform template declares.  For compatible old clients,
        # submitted boolean keys are simply ignored rather than exposing more data.
        context_scope = defaults
        for key in supplied_selections:
            values = submitted_scope[key]
            if not isinstance(values, list) or any(not str(value).isdigit() for value in values):
                raise serializers.ValidationError({"context_scope": f"{key} 必须是材料或步骤 ID 列表。"})
            context_scope[key] = [int(value) for value in values]
        return context_scope

    @staticmethod
    def _validate_selected_context(project, workspace_mode, context_scope):
        """Selections are IDs, never client-trusted titles, and stay inside one safe project."""
        selected_ids = context_scope.get("selected_materials", [])
        if workspace_mode == "opening" and selected_ids:
            raise serializers.ValidationError({"context_scope": "开题模式不能引用项目材料。"})
        if not selected_ids:
            return
        if project is None:
            raise serializers.ValidationError({"project": "引用材料前必须选择当前项目。"})
        materials = list(Material.objects.filter(project=project, id__in=selected_ids).prefetch_related("revisions__attachments"))
        if len(materials) != len(set(selected_ids)):
            raise serializers.ValidationError({"context_scope": "只能引用当前项目中的材料。"})
        unsafe = []
        for material in materials:
            for revision in material.revisions.all():
                if revision.attachments.exclude(scan_status=MaterialAttachment.ScanStatus.CLEAN).exists():
                    unsafe.append(material.title)
                    break
        if unsafe:
            raise serializers.ValidationError({"context_scope": f"材料附件尚未通过安全检查：{', '.join(unsafe)}。"})


class AIConversationMessageSerializer(serializers.ModelSerializer):
    verification_items = serializers.SerializerMethodField()

    class Meta:
        model = AIConversationMessage
        fields = ["id", "role", "content", "status", "generation_log", "artifact_payload", "verification_items", "error_message", "created_at", "updated_at"]
        read_only_fields = ["id", "role", "status", "generation_log", "artifact_payload", "error_message", "created_at", "updated_at"]

    def get_verification_items(self, obj):
        return obj.generation_log.verification_items if obj.generation_log_id else []


class AIConversationSerializer(serializers.ModelSerializer):
    current_agent = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    message_count = serializers.SerializerMethodField()
    project_title = serializers.CharField(source="project.title", read_only=True, allow_null=True)

    class Meta:
        model = AIConversation
        fields = ["id", "project", "opening_project", "project_title", "title", "workspace_mode", "paper_type", "current_agent", "is_archived", "message_count", "created_at", "updated_at"]
        read_only_fields = ["id", "opening_project", "project_title", "message_count", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()

    def validate_current_agent(self, value):
        # The model stores an empty string for an unselected Agent, while the
        # public API may receive null from a newly opened workbench.
        return value or ""

    def validate_project(self, project):
        user = self.context["request"].user
        if project is None:
            return project
        if user.role == Account.Role.TEACHER:
            if project.primary_teacher_id != user.id:
                raise serializers.ValidationError("只能选择本人负责的指导项目。")
            return project
        if not (project.leader_id == user.id or project.members.filter(account=user).exists()):
            raise serializers.ValidationError("无项目权限。")
        return project


class AgentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTemplate
        fields = ["id", "key", "name", "description", "role", "category", "system_instruction",
                  "prompt_template", "input_schema", "context_scope_default", "workflow", "applicable_stages", "quick_tasks", "project_types", "output_contract", "is_active", "school", "order",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at", "school"]  # school 由后端按角色强制写入

    def validate_key(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("key 不能为空。")
        return value.strip()


class CompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = "__all__"
        read_only_fields = ["school"]


class AnnouncementSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ["id", "school", "title", "body", "audience", "author", "status", "published_at", "is_read"]
        read_only_fields = ["school", "author", "published_at", "is_read"]

    def get_is_read(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.reads.filter(account=request.user).exists())


class ReportExportSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportExport
        fields = ["id", "project", "requested_by", "format", "status", "project_version", "material_manifest", "error_message", "created_at", "completed_at", "download_url"]
        read_only_fields = ["requested_by", "status", "project_version", "material_manifest", "error_message", "completed_at", "download_url"]

    def get_download_url(self, obj):
        if not self.context.get("request") or obj.status != ReportExport.Status.COMPLETED or not obj.file:
            return None
        return f"/api/report-exports/{obj.pk}/download/"


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    project_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "is_read", "created_at", "actor_name", "project_id"]

    def get_actor_name(self, obj):
        if not obj.actor_id:
            return None
        return obj.actor.get_full_name() or obj.actor.username

    def get_project_id(self, obj):
        return obj.project_id

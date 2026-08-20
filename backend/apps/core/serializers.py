from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import serializers
from .models import AIGenerationLog, Account, AgentTemplate, Announcement, AuditEvent, Competition, Material, MaterialAttachment, MaterialRevision, MemberInvitation, Notification, Project, ProjectGrowth, ProjectMember, ProjectTask, PublicCaseRequest, ReportExport, School, Template, TemplateMaterial, UploadSession
from .tasks import process_uploaded_material


class ProjectMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="account.username", read_only=True)
    class Meta: model = ProjectMember; fields = ["id", "account", "username", "role"]

class ProjectSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(many=True, read_only=True)
    growth = serializers.SerializerMethodField()
    school_name = serializers.CharField(source="school.name", read_only=True)
    is_primary = serializers.SerializerMethodField()
    days_until_purge = serializers.SerializerMethodField()
    class Meta: model = Project; fields = ["id", "school", "school_name", "title", "problem", "plan", "summary", "leader", "primary_teacher", "template_snapshot", "project_type", "status", "members", "growth", "is_archived", "archived_at", "deleted_at", "trashed_at", "days_until_purge", "is_primary", "created_at"]; read_only_fields = ["school", "leader", "template_snapshot", "primary_teacher", "status", "is_archived", "archived_at", "deleted_at", "trashed_at", "days_until_purge"]
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
    attachments = MaterialAttachmentSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    source_summary = serializers.SerializerMethodField()
    verification_summary = serializers.SerializerMethodField()

    class Meta:
        model = MaterialRevision
        fields = ["id", "material", "material_title", "project_title", "author", "author_name", "content", "truth_confirmed", "revision_note", "status", "reviewer", "review_comment", "created_at", "attachments", "uploaded_files", "source_summary", "verification_summary"]
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

    class Meta: model = Material; fields = ["id", "project", "task", "template_material", "title", "status", "required", "report_section", "report_order", "revisions", "guidance", "reference"]

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
        fields = ["id", "task", "title", "required", "submission_type", "report_section", "order", "guidance", "reference_file"]

class TemplateSerializer(serializers.ModelSerializer):
    class Meta: model = Template; fields = "__all__"; read_only_fields = ["school", "owner"]

class PublicCaseRequestSerializer(serializers.ModelSerializer):
    selected_material_summaries = serializers.SerializerMethodField()
    project_title = serializers.CharField(source="project.title", read_only=True)
    school_name = serializers.CharField(source="project.school.name", read_only=True)
    class Meta:
        model = PublicCaseRequest
        fields = ["id", "project", "project_title", "school_name", "applicant", "public_summary", "tags", "discipline", "application_scene", "outcome_form", "cover", "selected_materials", "selected_material_summaries", "status", "teacher_reviewer", "review_comment", "admin_reviewer"]
        read_only_fields = ["applicant", "teacher_reviewer", "review_comment", "admin_reviewer", "status", "selected_material_summaries"]

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

    class Meta:
        model = AIGenerationLog
        fields = ["id", "project", "actor", "actor_name", "purpose", "agent_key", "task", "material", "prompt", "context_scope", "referenced_sources", "output", "artifact_payload", "verification_items", "paper_type", "saved_material_revision", "model_name", "status", "error_message", "created_at", "completed_at"]
        read_only_fields = ["actor", "output", "artifact_payload", "verification_items", "saved_material_revision", "model_name", "status", "error_message", "completed_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project") or getattr(self.instance, "project", None)
        task = attrs.get("task")
        material = attrs.get("material")
        if task and project and task.project_id != project.id:
            raise serializers.ValidationError({"task": "所选步骤不属于该项目。"})
        if material and project and material.project_id != project.id:
            raise serializers.ValidationError({"material": "所选材料不属于该项目。"})
        if material and task and material.task_id and material.task_id != task.id:
            raise serializers.ValidationError({"material": "所选材料不属于该步骤。"})
        agent_key = attrs.get("agent_key")
        if agent_key:
            user = self.context["request"].user
            tmpl = (
                AgentTemplate.objects.filter(key=agent_key, is_active=True)
                .filter(Q(school=None) | Q(school=user.school))
                .filter(role__in=[user.role, AgentTemplate.Role.BOTH])
                .first()
            )
            if not tmpl:
                raise serializers.ValidationError({"agent_key": "指定的 AI 模板不存在或无权限使用。"})
            if not attrs.get("purpose"):
                attrs["purpose"] = tmpl.name
        return attrs


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

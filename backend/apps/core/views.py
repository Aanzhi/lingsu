import clamd
import redis
import json
import time
import requests

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import File
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from rest_framework import status, viewsets
from rest_framework.renderers import BaseRenderer
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes, renderer_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import hashlib
import secrets
from pathlib import Path
from io import BytesIO
from .ai_config import AIConfigError, get_ai_configuration_state, get_configured_ai_api_key, save_configured_ai_api_key
from .models import AIGenerationLog, AIConversation, AIConversationMessage, Account, AgentTemplate, Announcement, AnnouncementRead, AuditEvent, Competition, Material, MaterialAttachment, MaterialRevision, MemberInvitation, Notification, Project, ProjectGrowth, ProjectMember, ProjectTask, PublicCaseRequest, ReportExport, School, Template, UploadPart, UploadSession
from .ai_agents import normalize_workspace_mode, workspace_mode_requires_project
from .notifiers import notify
from .serializers import AIGenerationLogSerializer, AIConversationMessageSerializer, AIConversationSerializer, AgentTemplateSerializer, AnnouncementSerializer, AuditEventSerializer, CompetitionSerializer, MaterialAttachmentSerializer, MaterialRevisionSerializer, MaterialSerializer, MemberInvitationSerializer, NotificationSerializer, ProjectMemberSerializer, ProjectSerializer, ProjectTaskSerializer, PublicCaseRequestSerializer, ReportExportSerializer, SchoolSerializer, TemplateSerializer, UploadSessionSerializer
from .tasks import generate_ai_response, generate_general_ai_response, generate_report_export, process_uploaded_material
from .workflows.cases import consent_public_case_request, resubmit_public_case_request, review_platform_case_request, validate_public_case_request
from .workflows.materials import create_material_draft, review_material_revision, save_ai_output_as_material, submit_material_revision
from .workflows.memberships import assign_member, cancel_member_invitation, create_member_invitation, decide_member_invitation, respond_to_invitation
from .workflows.projects import claim_project
from .services import build_blank_reference
from .conversation_utils import conversation_title_from_prompt, is_generic_conversation_title
from .workflows.ai import accessible_ai_logs, conversation_stream_key, create_ai_request, publish_conversation_event


def school_queryset(queryset, user, field="school"):
    if user.role == "platform_admin": return queryset
    return queryset.filter(**{field: user.school})

def teacher(user):
    return user.role == "teacher"

def platform_admin(user): return user.role == "platform_admin"


def _dependency_status(check):
    """Run a short, read-only dependency probe without exposing configuration."""
    try:
        check()
        return "healthy"
    except Exception:
        return "unavailable"


def _redis_status():
    broker_url = getattr(settings, "CELERY_BROKER_URL", "").strip()
    if not broker_url:
        return "not_configured"
    return _dependency_status(lambda: redis.Redis.from_url(
        broker_url, socket_connect_timeout=2, socket_timeout=2,
    ).ping())


def _clamav_status():
    if not getattr(settings, "ATTACHMENT_UPLOADS_ENABLED", True) or not getattr(settings, "CLAMAV_ENABLED", True):
        return "disabled"
    host = getattr(settings, "CLAMAV_HOST", "").strip()
    if not host:
        return "not_configured"
    return _dependency_status(lambda: clamd.ClamdNetworkSocket(
        host=host,
        port=getattr(settings, "CLAMAV_PORT", 3310),
        timeout=min(getattr(settings, "CLAMAV_TIMEOUT", 120), 2),
    ).ping())


def _document_converter_status():
    if not getattr(settings, "DOCUMENT_CONVERTER_ENABLED", True):
        return "disabled"
    converter_url = getattr(settings, "DOCUMENT_CONVERTER_URL", "").strip()
    if not converter_url:
        return "not_configured"

    def probe():
        response = requests.get(f"{converter_url.rstrip('/')}/health", timeout=2)
        response.raise_for_status()

    return _dependency_status(probe)


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class RegisterThrottle(AnonRateThrottle):
    scope = "register"


class ServerSentEventRenderer(BaseRenderer):
    """Allow DRF content negotiation to pass through a native SSE response."""

    media_type = "text/event-stream"
    format = "event-stream"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data

def require_authorized_school(user):
    if not platform_admin(user) and (not user.school or not user.school.is_authorized):
        raise PermissionDenied("学校授权已停用或到期，当前仅可查看历史内容。")

def project_member(project, user):
    return project.leader_id == user.id or project.members.filter(account=user).exists() or project.primary_teacher_id == user.id


def _can_manage_project(user, project):
    """Whether the user can change lifecycle state of a project (archive / trash / restore)."""
    return (
        project.leader_id == user.id
        or project.primary_teacher_id == user.id
        or project.members.filter(account=user, role="leader").exists()
    )


def accessible_projects(user):
    if platform_admin(user):
        raise PermissionDenied("平台管理员不能访问学校项目过程数据。")
    base = Project.objects.filter(school=user.school)
    if user.role == Account.Role.STUDENT:
        return base.filter(Q(leader=user) | Q(members__account=user)).distinct()
    if user.role == Account.Role.TEACHER:
        return base.filter(primary_teacher=user)
    return base.none()


def announcement_audience_queryset(queryset, user):
    if platform_admin(user):
        return queryset
    audience = "students" if user.role == "student" else "teachers"
    visible = Q(status="published", audience__in=["all", audience])
    if user.role == "teacher":
        visible |= Q(author=user)
    return queryset.filter(visible)


class CompetitionViewSet(viewsets.ModelViewSet):
    serializer_class = CompetitionSerializer

    def get_queryset(self):
        if platform_admin(self.request.user):
            return Competition.objects.all()
        audience = "students" if self.request.user.role == Account.Role.STUDENT else "teachers"
        return Competition.objects.filter(
            Q(school__isnull=True) | Q(school=self.request.user.school),
            status=Competition.Status.PUBLISHED,
            audience__in=[Competition.Audience.ALL, audience],
        )

    def perform_create(self, serializer):
        if not platform_admin(self.request.user): raise PermissionDenied("仅平台管理员可发布赛事。")
        serializer.save(school=None)

    def update(self, request, *args, **kwargs):
        if not platform_admin(request.user): raise PermissionDenied("仅平台管理员可管理赛事。")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not platform_admin(request.user): raise PermissionDenied("仅平台管理员可管理赛事。")
        return super().destroy(request, *args, **kwargs)


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        if platform_admin(self.request.user):
            return Announcement.objects.filter(school__isnull=True)
        base = Announcement.objects.filter(Q(school__isnull=True) | Q(school=self.request.user.school))
        return announcement_audience_queryset(base, self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        audience = serializer.validated_data.get("audience", "all")
        if user.role == "teacher" and audience != "students":
            raise PermissionDenied("教师只能发布面向学生的公告。")
        if user.role not in ("teacher", "platform_admin"): raise PermissionDenied("仅教师或平台管理员可发布公告。")
        if not platform_admin(user): require_authorized_school(user)
        item = serializer.save(school=None if platform_admin(user) else user.school, author=user, published_at=timezone.now() if serializer.validated_data.get("status") == "published" else None)
        self._broadcast_school_announcement(item)

    @staticmethod
    def _broadcast_school_announcement(item):
        if not item.school_id or item.status != Announcement.Status.PUBLISHED:
            return
        roles = [Account.Role.STUDENT] if item.audience == Announcement.Audience.STUDENTS else [Account.Role.STUDENT, Account.Role.TEACHER]
        kind = Notification.Kind.SCHOOL_ANNOUNCEMENT
        for recipient in Account.objects.filter(school_id=item.school_id, role__in=roles):
            if Notification.objects.filter(recipient=recipient, kind=kind, link="/student/announcements").exists():
                continue
            notify(
                recipient,
                kind=kind,
                title=item.title,
                body=item.body,
                actor=item.author,
                link="/student/announcements",
            )

    def update(self, request, *args, **kwargs):
        item = self.get_object()
        if not platform_admin(request.user): require_authorized_school(request.user)
        if platform_admin(request.user) and item.school_id is None:
            return super().update(request, *args, **kwargs)
        if request.user.role == Account.Role.TEACHER and item.author_id == request.user.id:
            response = super().update(request, *args, **kwargs)
            item.refresh_from_db()
            self._broadcast_school_announcement(item)
            return response
        raise PermissionDenied("无权修改该公告。")

    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        if not platform_admin(request.user): require_authorized_school(request.user)
        if platform_admin(request.user) and item.school_id is None or request.user.role == Account.Role.TEACHER and item.author_id == request.user.id:
            return super().destroy(request, *args, **kwargs)
        raise PermissionDenied("无权删除该公告。")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        announcement = self.get_object()
        AnnouncementRead.objects.get_or_create(announcement=announcement, account=request.user)
        return Response(self.get_serializer(announcement).data)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    def get_queryset(self):
        if platform_admin(self.request.user):
            raise PermissionDenied("平台管理员不能访问学校项目过程数据。")
        base = school_queryset(Project.objects.prefetch_related("members__account"), self.request.user)
        if self.request.user.role == "student":
            base = base.filter(Q(leader=self.request.user) | Q(members__account=self.request.user)).distinct()
        if self.request.user.role == "teacher":
            base = base.filter(primary_teacher=self.request.user)
        include_archived = self.request.query_params.get("include_archived") in ("1", "true", "yes")
        include_trashed = self.request.query_params.get("include_trashed") in ("1", "true", "yes")
        only_archived = self.request.query_params.get("only_archived") in ("1", "true", "yes")
        if only_archived:
            base = base.filter(is_archived=True)
        elif not include_archived:
            base = base.filter(is_archived=False)
        if not include_trashed:
            base = base.filter(deleted_at__isnull=True)
        return base
    def perform_create(self, serializer):
        if self.request.user.role != "student": raise PermissionDenied("仅学生可创建项目草稿。")
        require_authorized_school(self.request.user)
        project = serializer.save(school=self.request.user.school, leader=self.request.user, primary_teacher=None, status=Project.Status.UNCLAIMED)
        project.members.create(account=self.request.user, role="leader")
        ProjectGrowth.objects.get_or_create(project=project)

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("项目变更必须通过明确的业务操作完成。")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("项目不能直接删除，请使用归档或移入回收站。")

    @action(detail=True, methods=["post"])
    def update_basics(self, request, pk=None):
        """Leader 编辑非流程类项目字段（标题/问题/方案/总结），并写审计。"""
        project = self._get_scoped_project(request, pk)
        if project.leader_id != request.user.id:
            raise PermissionDenied("仅项目负责人可编辑项目基本信息。")
        require_authorized_school(request.user)
        allowed = ("title", "problem", "plan", "summary")
        changed = {}
        for field in allowed:
            if field in request.data:
                value = request.data[field]
                if field == "title":
                    value = (value or "").strip()
                    if not value:
                        return Response({"detail": "项目标题不能为空。"}, status=status.HTTP_400_BAD_REQUEST)
                if getattr(project, field) != value:
                    changed[field] = {"from": getattr(project, field), "to": value}
                    setattr(project, field, value)
        if not changed:
            return Response(
                {"detail": "没有需要更新的字段。", "project": self.get_serializer(project).data},
                status=status.HTTP_200_OK,
            )
        project.save(update_fields=list(changed.keys()))
        AuditEvent.objects.create(
            school=project.school, actor=request.user,
            action=AuditEvent.Action.PROJECT_UPDATED,
            changes={"project_id": project.id, "title": project.title, "fields": list(changed.keys())},
        )
        return Response(self.get_serializer(project).data, status=status.HTTP_200_OK)

    def _get_scoped_project(self, request, pk):
        """Use AllProjectsManager so trashed items can still be restored by the owner."""
        return get_object_or_404(Project.all_objects.filter(school=request.user.school), pk=pk)

    @action(detail=False, methods=["get"])
    def trashed(self, request):
        """List projects that the caller has moved to the recycle bin."""
        return Response(self.get_serializer(self._trashed_queryset(request), many=True).data)

    def _trashed_queryset(self, request):
        base = Project.all_objects.filter(school=request.user.school, deleted_at__isnull=False)
        if request.user.role == Account.Role.STUDENT:
            return base.filter(Q(leader=request.user) | Q(members__account=request.user)).distinct()
        if request.user.role == Account.Role.TEACHER:
            return base.filter(primary_teacher=request.user)
        return base.none()

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        project = self._get_scoped_project(request, pk)
        if not _can_manage_project(request.user, project):
            raise PermissionDenied("仅项目负责人、指导教师或学校管理员可归档项目。")
        if project.status != Project.Status.COMPLETED:
            raise ValidationError({"status": "仅已完成的项目可以归档。"})
        if project.is_archived:
            return Response(self.get_serializer(project).data)
        project.is_archived = True
        project.archived_at = timezone.now()
        project.save(update_fields=["is_archived", "archived_at"])
        AuditEvent.objects.create(school=project.school, actor=request.user, action=AuditEvent.Action.PROJECT_ARCHIVED, changes={"project_id": project.id, "title": project.title})
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        project = self._get_scoped_project(request, pk)
        if not _can_manage_project(request.user, project):
            raise PermissionDenied("仅项目负责人、指导教师或学校管理员可恢复归档。")
        if not project.is_archived:
            return Response(self.get_serializer(project).data)
        project.is_archived = False
        project.archived_at = None
        project.save(update_fields=["is_archived", "archived_at"])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def trash(self, request, pk=None):
        project = self.get_object()
        if not _can_manage_project(request.user, project):
            raise PermissionDenied("仅项目负责人或指导教师可将项目移入回收站。")
        if project.is_archived:
            raise ValidationError({"status": "已归档项目不可删除，请先恢复。"})
        if project.deleted_at:
            return Response(self.get_serializer(project).data)
        now = timezone.now()
        project.deleted_at = now
        project.trashed_at = now
        project.save(update_fields=["deleted_at", "trashed_at"])
        if request.user.primary_project_id == project.id:
            request.user.primary_project = None
            request.user.save(update_fields=["primary_project"])
        AuditEvent.objects.create(school=project.school, actor=request.user, action=AuditEvent.Action.PROJECT_TRASHED, changes={"project_id": project.id, "title": project.title})
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        project = self._get_scoped_project(request, pk)
        if not _can_manage_project(request.user, project):
            raise PermissionDenied("仅项目负责人或指导教师可恢复项目。")
        if not project.deleted_at:
            return Response(self.get_serializer(project).data)
        project.deleted_at = None
        project.trashed_at = None
        project.save(update_fields=["deleted_at", "trashed_at"])
        AuditEvent.objects.create(school=project.school, actor=request.user, action=AuditEvent.Action.PROJECT_RESTORED, changes={"project_id": project.id, "title": project.title})
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def set_primary(self, request, pk=None):
        project = self.get_object()
        if request.user.role != Account.Role.STUDENT:
            raise PermissionDenied("仅学生可设置主项目。")
        if not project.members.filter(account=request.user).exists() and project.leader_id != request.user.id:
            raise PermissionDenied("仅项目成员可将该项目设为主项目。")
        if project.is_archived or project.deleted_at:
            raise ValidationError({"status": "归档或回收站项目不能设为主项目。"})
        request.user.primary_project = project
        request.user.save(update_fields=["primary_project"])
        return Response(self.get_serializer(project).data)

    @action(detail=False, methods=["get"])
    def pool(self, request):
        if not teacher(request.user): raise PermissionDenied("仅教师可查看项目池。")
        return Response(self.get_serializer(school_queryset(Project.objects.filter(status=Project.Status.UNCLAIMED), request.user), many=True).data)

    @action(detail=False, methods=["get"])
    def guided(self, request):
        if not teacher(request.user): raise PermissionDenied("仅教师可查看指导项目。")
        return Response(self.get_serializer(Project.objects.filter(school=request.user.school, primary_teacher=request.user), many=True).data)

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        require_authorized_school(request.user)
        if not teacher(request.user): raise PermissionDenied("仅教师可认领项目。")
        project = get_object_or_404(school_queryset(Project.objects.all(), request.user), pk=pk)
        project = claim_project(project, request.user, request.data.get("template"))
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        require_authorized_school(request.user)
        if not teacher(request.user):
            raise PermissionDenied("仅教师可分配组员。")
        project = self.get_object()
        invitee = get_object_or_404(
            Account.objects.filter(school=request.user.school, role="student"),
            pk=request.data.get("invitee"),
        )
        member = assign_member(project, request.user, invitee)
        return Response(ProjectMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class ProjectTaskViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProjectTaskSerializer

    def get_queryset(self):
        queryset = ProjectTask.objects.filter(project__in=accessible_projects(self.request.user)).select_related("project")
        project_id = self.request.query_params.get("project")
        return queryset.filter(project_id=project_id) if project_id else queryset


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False})
        user = request.user
        primary = getattr(user, "primary_project", None)
        return Response({
            "id": user.id,
            "username": user.username,
            "display_name": user.get_full_name() or user.username,
            "role": user.role,
            "school": user.school_id,
            "school_name": user.school.name if user.school_id else None,
            "must_change_password": user.must_change_password,
            "authorized": bool(user.school and user.school.is_authorized) if not platform_admin(user) else True,
            "primary_project": primary.id if primary and not primary.deleted_at and not primary.is_archived else None,
            "primary_project_title": primary.title if primary and not primary.deleted_at and not primary.is_archived else None,
        })


class StudentDirectoryView(APIView):
    def get(self, request):
        if request.user.role not in {Account.Role.STUDENT, Account.Role.TEACHER}:
            raise PermissionDenied("仅学生或教师可搜索本校项目成员。")
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        accounts = Account.objects.filter(
            school=request.user.school,
            role=Account.Role.STUDENT,
            is_active=True,
        ).exclude(pk=request.user.pk).filter(Q(username__icontains=query) | Q(first_name__icontains=query)).order_by("username")[:20]
        return Response([
            {"id": account.id, "username": account.username, "display_name": account.get_full_name() or account.username}
            for account in accounts
        ])


class ServiceStatusView(APIView):
    """Expose operational readiness without returning secrets or credentials."""

    def get(self, request):
        if not platform_admin(request.user):
            raise PermissionDenied("仅平台管理员可查看平台服务状态。")
        from django.db import connection

        database = "healthy"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            database = "unavailable"
        return Response({
            "database": database,
            "task_queue": _redis_status(),
            "virus_scan": _clamav_status(),
            "document_converter": _document_converter_status(),
            "storage": getattr(settings, "STORAGE_OPTIONS", {}).get("AWS_STORAGE_BUCKET_NAME") and "configured" or "local",
            "ai": "configured" if get_configured_ai_api_key() else "demo_mode",
        })


class PlatformAIConfigurationView(APIView):
    """Manage the single deployment-wide AI credential without returning it."""

    def _check_platform_admin(self, request):
        if not platform_admin(request.user):
            raise PermissionDenied("仅平台管理员可配置 AI 服务。")

    def _response(self, state):
        return {
            **state,
            "model": settings.OPENAI_MODEL,
            "base_url": settings.OPENAI_BASE_URL,
        }

    def get(self, request):
        self._check_platform_admin(request)
        return Response(self._response(get_ai_configuration_state()))

    def put(self, request):
        self._check_platform_admin(request)
        try:
            state = save_configured_ai_api_key(request.data.get("api_key"), request.user)
        except ValueError as exc:
            raise ValidationError({"api_key": str(exc)})
        except AIConfigError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(self._response(state))


class AIAvailabilityView(APIView):
    """Safe, role-scoped AI readiness for school users before they enter a prompt."""

    def get(self, request):
        if request.user.role not in (Account.Role.STUDENT, Account.Role.TEACHER):
            raise PermissionDenied("仅学生或教师可查看 AI 服务状态。")
        if not request.user.school_id:
            raise PermissionDenied("账号尚未绑定学校。")
        now = timezone.now()
        used = AIGenerationLog.objects.filter(
            project__school=request.user.school,
            created_at__year=now.year,
            created_at__month=now.month,
        ).count()
        if get_configured_ai_api_key():
            service_status = "configured"
        else:
            require_authorized_school(request.user)
            service_status = "demo_mode"
        if service_status == "configured" and used >= request.user.school.ai_quota:
            service_status = "quota_exhausted"
        return Response({"status": service_status, "remaining_quota": max(0, request.user.school.ai_quota - used)})


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return Response({
        "status": "ok",
        "capabilities": {
            "attachments": bool(getattr(settings, "ATTACHMENT_UPLOADS_ENABLED", True)),
            "pdf_export": bool(getattr(settings, "PDF_EXPORT_ENABLED", True)),
        },
    })


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"detail": "CSRF cookie ready."})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
@csrf_protect
def session_login(request):
    user = authenticate(request, username=request.data.get("username", ""), password=request.data.get("password", ""))
    if not user or not user.is_active:
        raise ValidationError({"detail": "账号或密码错误。"})
    login(request, user)
    primary = getattr(user, "primary_project", None)
    return Response({
        "id": user.id, "username": user.username, "display_name": user.get_full_name() or user.username, "role": user.role,
        "school": user.school_id, "school_name": user.school.name if user.school_id else None, "must_change_password": user.must_change_password,
        "authorized": True if platform_admin(user) else bool(user.school and user.school.is_authorized),
        "primary_project": primary.id if primary and not primary.deleted_at and not primary.is_archived else None,
        "primary_project_title": primary.title if primary and not primary.deleted_at and not primary.is_archived else None,
    })


@api_view(["POST"])
def session_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
def change_password(request):
    """修改当前登录用户的密码，并清除强制改密标记。"""
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied("请先登录。")
    old_password = request.data.get("old_password", "")
    new_password = request.data.get("new_password", "")
    confirm_password = request.data.get("confirm_password", "")
    if not user.check_password(old_password):
        return Response({"detail": "原密码不正确。"}, status=status.HTTP_400_BAD_REQUEST)
    if not new_password or new_password != confirm_password:
        return Response({"detail": "两次输入的新密码不一致。"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new_password, user)
    except ValidationError as exc:
        return Response({"detail": "；".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password"])
    return Response({"detail": "密码已修改。", "must_change_password": False}, status=status.HTTP_200_OK)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def demo_login(request):
    """Create a development-only student session for local interaction testing."""
    if not settings.DEBUG:
        raise PermissionDenied("演示登录仅在开发环境可用。")
    school, _ = School.objects.get_or_create(name="灵溯演示学校")
    teacher, _ = Account.objects.get_or_create(
        username="demo-teacher",
        defaults={"school": school, "role": Account.Role.TEACHER, "must_change_password": False},
    )
    student, _ = Account.objects.get_or_create(
        username="demo-student",
        defaults={"school": school, "role": Account.Role.STUDENT, "must_change_password": False},
    )
    admin, _ = Account.objects.get_or_create(username="demo-platform", defaults={"role": Account.Role.PLATFORM_ADMIN, "is_staff": True, "must_change_password": False})
    requested = request.data.get("role")
    actor = admin if requested == "platform_admin" else teacher if requested == "teacher" else student
    login(request, actor)
    return Response({
        "user": {"id": actor.id, "username": actor.username, "role": actor.role, "school": school.id},
        "teacher_id": teacher.id,
        "teacher_name": teacher.get_full_name() or "王老师",
    })


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
@csrf_protect
def register(request):
    code = request.data.get("invite_code", "").strip()
    role = request.data.get("role")
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")
    display_name = request.data.get("display_name", "").strip()
    school = School.objects.filter(invite_code=code, is_active=True).first()
    if not school or not school.is_authorized: raise ValidationError({"invite_code": "邀请码无效或学校未获授权。"})
    if role not in ("student", "teacher"): raise ValidationError({"role": "请选择学生或教师。"})
    if not username or not password: raise ValidationError("请填写账号和密码。")
    if Account.objects.filter(username=username).exists(): raise ValidationError({"username": "该账号已存在。"})
    try:
        validate_password(password, user=Account(username=username, first_name=display_name))
    except Exception as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc
    user = Account.objects.create_user(username=username, password=password, first_name=display_name, school=school, role=role, must_change_password=False)
    login(request, user)
    return Response({"id": user.id, "username": user.username, "display_name": user.get_full_name() or user.username, "role": user.role, "school": school.id, "school_name": school.name, "authorized": True, "must_change_password": False}, status=status.HTTP_201_CREATED)


class SchoolViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolSerializer
    queryset = School.objects.all().order_by("name")
    def get_queryset(self):
        if not platform_admin(self.request.user): raise PermissionDenied("仅平台管理员可管理学校空间。")
        return super().get_queryset()
    def perform_create(self, serializer):
        if not platform_admin(self.request.user): raise PermissionDenied("仅平台管理员可创建学校空间。")
        serializer.save()

    def perform_update(self, serializer):
        school = self.get_object()
        changed = {
            field: value
            for field, value in serializer.validated_data.items()
            if getattr(school, field) != value
        }
        serializer.save()
        if changed:
            AuditEvent.objects.create(
                school=school,
                actor=self.request.user,
                action=AuditEvent.Action.SCHOOL_UPDATED,
                changes=changed,
            )

    @action(detail=True, methods=["post"])
    def reset_invite_code(self, request, pk=None):
        school = self.get_object(); school.invite_code = secrets.token_urlsafe(8); school.save(update_fields=["invite_code"])
        AuditEvent.objects.create(school=school, actor=request.user, action=AuditEvent.Action.INVITE_CODE_RESET)
        return Response(self.get_serializer(school).data)

    @action(detail=True, methods=["get"], url_path="audit-events")
    def audit_events(self, request, pk=None):
        school = self.get_object()
        events = school.audit_events.select_related("actor").all()
        return Response(AuditEventSerializer(events, many=True).data)


class MaterialViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MaterialSerializer
    def get_queryset(self):
        queryset = Material.objects.filter(project__in=accessible_projects(self.request.user)).select_related("project", "task")
        project_id = self.request.query_params.get("project")
        return queryset.filter(project_id=project_id) if project_id else queryset

    @action(detail=True, methods=["get"])
    def reference(self, request, pk=None):
        material = self.get_object()
        file_field, original_name = material.effective_reference
        if file_field:
            reference = {"url": f"/api/materials/{material.pk}/reference/download/", "original_name": original_name}
        elif material.effective_guidance:
            safe = (material.title or "参考范本").replace("/", "_")
            reference = {"url": f"/api/materials/{material.pk}/reference/download/", "original_name": f"{safe}_参考范本.docx"}
        else:
            reference = None
        return Response({"guidance": material.effective_guidance, "reference": reference})

    @action(detail=True, methods=["put"])
    def set_reference(self, request, pk=None):
        require_authorized_school(request.user)
        if platform_admin(request.user):
            raise PermissionDenied("平台管理员不能修改项目材料模板。")
        if not teacher(request.user):
            raise PermissionDenied("仅主指导教师可配置材料模板。")
        material = self.get_object()
        if material.project.primary_teacher_id != request.user.id:
            raise PermissionDenied("只能配置本人指导项目的材料模板。")
        guidance = request.data.get("guidance")
        reference_file = request.FILES.get("reference_file")
        if guidance is not None:
            material.guidance_override = guidance
        if reference_file is not None:
            suffix = Path(reference_file.name).suffix.lower()
            if suffix not in {".docx", ".md", ".pdf"}:
                raise ValidationError({"reference_file": f"仅支持 .docx/.md/.pdf 范本，当前为 {suffix}"})
            if material.reference_file_override:
                material.reference_file_override.delete(save=False)
            material.reference_file_override = reference_file
        material.save()
        return Response(self.get_serializer(material).data)

    @action(detail=True, methods=["delete"])
    def reset_reference(self, request, pk=None):
        require_authorized_school(request.user)
        if platform_admin(request.user):
            raise PermissionDenied("平台管理员不能修改项目材料模板。")
        if not teacher(request.user):
            raise PermissionDenied("仅主指导教师可配置材料模板。")
        material = self.get_object()
        if material.project.primary_teacher_id != request.user.id:
            raise PermissionDenied("只能配置本人指导项目的材料模板。")
        if material.reference_file_override:
            material.reference_file_override.delete(save=False)
        material.reference_file_override = None
        material.guidance_override = ""
        material.save()
        return Response(self.get_serializer(material).data)

    @action(detail=True, methods=["get"], url_path="reference/download")
    def reference_download(self, request, pk=None):
        material = self.get_object()
        file_field, original_name = material.effective_reference
        if file_field:
            try:
                return FileResponse(file_field.open("rb"), as_attachment=True, filename=original_name)
            except Exception:
                raise Http404("参考范本文件读取失败。")
        guidance = material.effective_guidance
        if not guidance:
            raise Http404("该材料暂无可下载的参考范本。")
        content, filename = build_blank_reference(material.title, guidance)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if filename.endswith(".docx") else "text/markdown; charset=utf-8"
        return FileResponse(BytesIO(content), as_attachment=True, filename=filename, content_type=content_type)
class MaterialRevisionViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialRevisionSerializer
    def get_queryset(self): return MaterialRevision.objects.filter(material__project__in=accessible_projects(self.request.user)).select_related("material__project", "author").prefetch_related("attachments")
    def perform_create(self, serializer):
        require_authorized_school(self.request.user)
        if self.request.user.role != Account.Role.STUDENT:
            raise PermissionDenied("仅项目学生可创建材料版本。")
        create_material_draft(serializer, self.request.user)

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("材料版本不可覆盖，请创建新版本。")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("材料版本属于审计记录，不能删除。")

    @action(detail=False, methods=["get"])
    def pending_reviews(self, request):
        if not teacher(request.user):
            raise PermissionDenied("仅教师可查看待审核材料。")
        revisions = self.get_queryset().filter(status="submitted")
        return Response(self.get_serializer(revisions.order_by("created_at"), many=True).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        require_authorized_school(request.user)
        revision = self.get_object()
        if request.user.role != Account.Role.STUDENT:
            raise PermissionDenied("仅学生可提交材料。")
        truth_confirmed = request.data.get("truth_confirmed")
        if truth_confirmed is False or truth_confirmed is None:
            blocked = submit_material_revision(revision, request.user, False)
            return blocked
        if truth_confirmed is not True:
            raise ValidationError({"truth_confirmed": "提交前必须明确确认材料真实性。"})
        blocked = submit_material_revision(revision, request.user, truth_confirmed)
        if blocked:
            return blocked
        return Response(self.get_serializer(revision).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def review(self, request, pk=None):
        require_authorized_school(request.user)
        revision = MaterialRevision.objects.filter(material__project__school=request.user.school).select_for_update().select_related("material__project", "author").get(pk=pk)
        if not teacher(request.user):
            raise PermissionDenied("仅主指导教师可审核。")
        outcome = request.data.get("outcome")
        comment = request.data.get("comment", "").strip()
        review_material_revision(revision, request.user, outcome, comment)
        return Response(self.get_serializer(revision).data)


class MaterialAttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MaterialAttachmentSerializer

    def get_queryset(self):
        return MaterialAttachment.objects.filter(revision__material__project__in=accessible_projects(self.request.user))

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        if attachment.scan_status in (MaterialAttachment.ScanStatus.PENDING, MaterialAttachment.ScanStatus.PROCESSING):
            return Response({"detail": "文件正在进行安全检查，请稍后重试。"}, status=423)
        if attachment.scan_status == MaterialAttachment.ScanStatus.INFECTED:
            return Response({"detail": "文件未通过安全检查，已禁止下载。"}, status=410)
        if attachment.scan_status == MaterialAttachment.ScanStatus.FAILED and settings.FILE_SCAN_REQUIRED:
            return Response({"detail": "文件安全检查失败，暂不可下载。"}, status=423)
        try:
            response = FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.original_name)
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except FileNotFoundError as exc:
            raise Http404 from exc


class UploadSessionViewSet(viewsets.ModelViewSet):
    serializer_class = UploadSessionSerializer
    http_method_names = ["get", "post", "put", "head", "options"]

    def get_queryset(self):
        return UploadSession.objects.filter(
            revision__material__project__in=accessible_projects(self.request.user),
            revision__author=self.request.user,
        ).select_related("revision__material__project").prefetch_related("parts")

    def perform_create(self, serializer):
        require_authorized_school(self.request.user)
        if not settings.ATTACHMENT_UPLOADS_ENABLED:
            raise ValidationError("当前核心部署未启用附件上传；请先保存文本材料，或联系管理员启用安全扫描。")
        if self.request.user.role != Account.Role.STUDENT:
            raise PermissionDenied("仅项目学生可上传材料附件。")
        revision = serializer.validated_data["revision"]
        material, project = revision.material, revision.material.project
        if not project_member(project, self.request.user):
            raise PermissionDenied("无项目权限。")
        if project.status != Project.Status.ACTIVE or not project.primary_teacher_id:
            raise ValidationError("项目尚未由教师认领并启动，不能上传正式材料。")
        if revision.status != "draft" or material.status == "submitted":
            raise ValidationError("只能为未提交的材料草稿上传附件。")
        serializer.save(expires_at=timezone.now() + timedelta(hours=settings.UPLOAD_SESSION_TTL_HOURS))

    def _active_session(self, session):
        if session.status != UploadSession.Status.ACTIVE:
            raise ValidationError("该上传会话已结束。")
        if session.expires_at <= timezone.now():
            session.status = UploadSession.Status.EXPIRED
            session.save(update_fields=["status"])
            self._delete_parts(session)
            return None
        return session

    @staticmethod
    def _delete_parts(session):
        """Delete temporary part blobs before removing their database rows."""
        parts = list(session.parts.all())
        for part in parts:
            if part.file:
                part.file.delete(save=False)
        UploadPart.objects.filter(pk__in=[part.pk for part in parts]).delete()

    def _require_active(self, session):
        if self._active_session(session) is None:
            from rest_framework.exceptions import APIException
            error = APIException("上传会话已过期，请重新选择文件。")
            error.status_code = status.HTTP_410_GONE
            raise error

    @action(detail=True, methods=["put"], url_path=r"parts/(?P<part_index>[^/.]+)")
    @transaction.atomic
    def upload_part(self, request, pk=None, part_index=None):
        require_authorized_school(request.user)
        session = self.get_queryset().select_for_update().get(pk=pk)
        self._require_active(session)
        try:
            index = int(part_index)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"part_index": "分块序号必须是整数。"}) from exc
        if index < 0 or index >= session.part_count:
            raise ValidationError({"part_index": "分块序号超出范围。"})
        upload = request.FILES.get("chunk")
        if not upload:
            raise ValidationError({"chunk": "请提供分块文件。"})
        expected_size = session.chunk_size if index < session.part_count - 1 else session.total_size - session.chunk_size * (session.part_count - 1)
        if upload.size != expected_size:
            raise ValidationError({"chunk": "分块大小与会话定义不一致。"})
        digest = hashlib.sha256()
        for chunk in upload.chunks():
            digest.update(chunk)
        actual_sha256 = digest.hexdigest()
        header_sha256 = request.headers.get("X-Chunk-Sha256", "").lower()
        if not header_sha256 or header_sha256 != actual_sha256:
            raise ValidationError({"chunk": "分块哈希校验失败。"})
        existing = session.parts.filter(index=index).first()
        if existing:
            if existing.sha256 == actual_sha256 and existing.size == upload.size:
                return Response({"index": index, "status": "already_uploaded"})
            return Response({"detail": "该分块已存在且内容不一致。"}, status=status.HTTP_409_CONFLICT)
        upload.seek(0)
        UploadPart.objects.create(session=session, index=index, file=upload, size=upload.size, sha256=actual_sha256)
        return Response({"index": index, "status": "uploaded"}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request, pk=None):
        require_authorized_school(request.user)
        session = self.get_queryset().select_for_update().prefetch_related("parts").get(pk=pk)
        if session.status == UploadSession.Status.COMPLETED and session.attachment_id:
            return Response({"attachment_id": session.attachment_id, "status": "completed"})
        self._require_active(session)
        parts = list(session.parts.order_by("index"))
        expected_indexes = list(range(session.part_count))
        if [part.index for part in parts] != expected_indexes:
            return Response({"detail": "分块尚未全部上传，不能完成合并。"}, status=status.HTTP_409_CONFLICT)
        digest = hashlib.sha256()
        total = 0
        import tempfile
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as merged:
            for part in parts:
                with part.file.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                        total += len(chunk)
                        merged.write(chunk)
            actual_sha256 = digest.hexdigest()
            if total != session.total_size:
                return Response({"detail": "合并文件大小校验失败。"}, status=status.HTTP_400_BAD_REQUEST)
            if session.expected_sha256 and actual_sha256 != session.expected_sha256:
                return Response({"detail": "整体哈希校验失败。"}, status=status.HTTP_400_BAD_REQUEST)
            merged.seek(0)
            attachment = MaterialAttachment(
                revision=session.revision,
                original_name=session.original_name,
                content_type=session.content_type,
                size=total,
                sha256=actual_sha256,
                scan_status=MaterialAttachment.ScanStatus.PENDING,
            )
            attachment.file.save(session.original_name, File(merged), save=False)
            attachment.save()
        session.status = UploadSession.Status.COMPLETED
        session.attachment = attachment
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "attachment", "completed_at"])
        self._delete_parts(session)
        transaction.on_commit(lambda: process_uploaded_material.delay(session.revision_id))
        return Response({"attachment_id": attachment.id, "status": "completed"})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def abort(self, request, pk=None):
        session = self.get_queryset().select_for_update().get(pk=pk)
        if session.status == UploadSession.Status.ACTIVE:
            self._delete_parts(session)
            session.status = UploadSession.Status.ABORTED
            session.save(update_fields=["status"])
        return Response(self.get_serializer(session).data)



class MemberInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = MemberInvitationSerializer
    def get_queryset(self):
        base = MemberInvitation.objects.select_related("project", "invitee", "inviter")
        if platform_admin(self.request.user):
            raise PermissionDenied("平台管理员不能访问学校项目成员数据。")
        if self.request.user.role == "teacher": return base.filter(project__primary_teacher=self.request.user)
        return base.filter(Q(invitee=self.request.user) | Q(inviter=self.request.user))

    @action(detail=False, methods=["get"])
    def pending_teacher(self, request):
        if not teacher(request.user): raise PermissionDenied("仅教师可查看成员确认队列。")
        queryset = self.get_queryset().filter(status=MemberInvitation.Status.PENDING_TEACHER)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def pending_student(self, request):
        if request.user.role != Account.Role.STUDENT: raise PermissionDenied("仅学生可查看自己的邀请。")
        queryset = self.get_queryset().filter(invitee=request.user, status=MemberInvitation.Status.PENDING_STUDENT)
        return Response(self.get_serializer(queryset, many=True).data)
    def perform_create(self, serializer):
        require_authorized_school(self.request.user)
        create_member_invitation(serializer, self.request.user)
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        require_authorized_school(request.user); invitation = respond_to_invitation(self.get_object(), request.user, accept=True)
        return Response(self.get_serializer(invitation).data)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        require_authorized_school(request.user); invitation = respond_to_invitation(self.get_object(), request.user, accept=False)
        return Response(self.get_serializer(invitation).data)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        require_authorized_school(request.user)
        cancel_member_invitation(self.get_object(), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        require_authorized_school(request.user); invitation = self.get_object()
        approved = request.data.get("approved")
        if not isinstance(approved, bool):
            raise ValidationError({"approved": "请提供 true 或 false 布尔值。"})
        invitation = decide_member_invitation(invitation, request.user, approved)
        return Response(self.get_serializer(invitation).data)


class TemplateViewSet(viewsets.ModelViewSet):
    serializer_class = TemplateSerializer
    def get_queryset(self): return school_queryset(Template.objects.all(), self.request.user)
    def perform_create(self, serializer):
        if not teacher(self.request.user): raise PermissionDenied("仅教师或管理员可管理模板。")
        require_authorized_school(self.request.user)
        serializer.save(school=self.request.user.school, owner=self.request.user)

    def perform_update(self, serializer):
        if not teacher(self.request.user): raise PermissionDenied("仅教师可管理模板。")
        require_authorized_school(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        if not teacher(self.request.user): raise PermissionDenied("仅教师可管理模板。")
        require_authorized_school(self.request.user)
        instance.delete()


class PublicCaseRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PublicCaseRequestSerializer
    http_method_names = ["get", "post", "head", "options"]
    def get_queryset(self):
        if platform_admin(self.request.user):
            return PublicCaseRequest.objects.all().select_related("project__school").prefetch_related("selected_materials__revisions")
        if self.request.user.role == Account.Role.STUDENT:
            owned = Q(project__in=accessible_projects(self.request.user))
            return PublicCaseRequest.objects.filter(owned | Q(status=PublicCaseRequest.Status.PUBLISHED)).distinct().select_related("project__school").prefetch_related("selected_materials__revisions")
        if self.request.user.role == Account.Role.TEACHER:
            return PublicCaseRequest.objects.filter(Q(project__primary_teacher=self.request.user) | Q(status=PublicCaseRequest.Status.PUBLISHED)).distinct().select_related("project__school").prefetch_related("selected_materials__revisions")
        return PublicCaseRequest.objects.none()
    def perform_create(self, serializer):
        require_authorized_school(self.request.user)
        project = serializer.validated_data["project"]
        request_type = serializer.validated_data.get("request_type", PublicCaseRequest.RequestType.STUDENT_SCHOOL)
        visibility_scope = serializer.validated_data.get(
            "visibility_scope",
            PublicCaseRequest.VisibilityScope.PLATFORM if request_type == PublicCaseRequest.RequestType.TEACHER_PLATFORM else PublicCaseRequest.VisibilityScope.SCHOOL,
        )
        validate_public_case_request(project, self.request.user, serializer.validated_data.get("selected_materials", []), request_type, visibility_scope)
        initial_status = PublicCaseRequest.Status.WAITING_STUDENT if request_type == PublicCaseRequest.RequestType.TEACHER_PLATFORM else PublicCaseRequest.Status.PENDING_TEACHER
        item = serializer.save(applicant=self.request.user, request_type=request_type, visibility_scope=visibility_scope, status=initial_status)
        AuditEvent.objects.create(
            school=project.school, actor=self.request.user, action=AuditEvent.Action.CASE_SUBMITTED,
            changes={"project_id": project.id, "case_id": item.id, "selected_material_count": item.selected_materials.count()},
        )
        if request_type == PublicCaseRequest.RequestType.TEACHER_PLATFORM:
            notify(
                project.leader,
                kind=Notification.Kind.CASE_CONSENT_REQUIRED,
                title=f"教师邀请项目「{project.title}」公开展示",
                body="请确认是否同意将项目成果提交到全平台案例库。",
                actor=self.request.user,
                project=project,
                link=f"/student/public-applications?projectId={project.id}",
            )
    @action(detail=True, methods=["post"])
    def resubmit(self, request, pk=None):
        require_authorized_school(request.user)
        item = self.get_object()
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        resubmit_public_case_request(item, request.user, serializer.validated_data)
        AuditEvent.objects.create(
            school=item.project.school, actor=request.user, action=AuditEvent.Action.CASE_SUBMITTED,
            changes={"project_id": item.project_id, "case_id": item.id, "resubmitted": True, "selected_material_count": item.selected_materials.count()},
        )
        return Response(self.get_serializer(item).data)
    @action(detail=True, methods=["post"])
    def teacher_approve(self, request, pk=None):
        require_authorized_school(request.user)
        item = self.get_object()
        if item.project.primary_teacher_id != request.user.id: raise PermissionDenied("仅指导教师可审核。")
        if item.request_type != PublicCaseRequest.RequestType.STUDENT_SCHOOL:
            raise ValidationError("教师发起的公域邀请需要学生同意后进入平台审核。")
        if item.status != PublicCaseRequest.Status.PENDING_TEACHER: raise ValidationError("该申请已处理。")
        item.status, item.visibility_scope, item.teacher_reviewer, item.review_comment = PublicCaseRequest.Status.PUBLISHED, PublicCaseRequest.VisibilityScope.SCHOOL, request.user, ""
        item.save(update_fields=["status", "visibility_scope", "teacher_reviewer", "review_comment"])
        AuditEvent.objects.create(
            school=item.project.school, actor=request.user, action=AuditEvent.Action.CASE_REVIEWED,
            changes={"project_id": item.project_id, "case_id": item.id, "outcome": "published"},
        )
        notify(item.applicant, kind=Notification.Kind.CASE_PUBLISHED,
               title=f"公开案例申请「{item.project.title}」已通过，案例已发布",
               actor=request.user, project=item.project,
               link="/student/public-applications")
        return Response(self.get_serializer(item).data)
    @action(detail=True, methods=["post"])
    def teacher_reject(self, request, pk=None):
        require_authorized_school(request.user)
        item = self.get_object()
        if item.project.primary_teacher_id != request.user.id: raise PermissionDenied("仅指导教师可审核。")
        if item.status != PublicCaseRequest.Status.PENDING_TEACHER: raise ValidationError("该申请已处理。")
        comment = request.data.get("comment", "").strip()
        if not comment: raise ValidationError({"comment": "驳回必须填写可执行的修改意见。"})
        item.status, item.teacher_reviewer, item.review_comment = PublicCaseRequest.Status.REJECTED, request.user, comment
        item.save(update_fields=["status", "teacher_reviewer", "review_comment"])
        AuditEvent.objects.create(
            school=item.project.school, actor=request.user, action=AuditEvent.Action.CASE_REVIEWED,
            changes={"project_id": item.project_id, "case_id": item.id, "outcome": "rejected"},
        )
        notify(item.applicant, kind=Notification.Kind.CASE_REJECTED,
               title=f"公开案例申请「{item.project.title}」被驳回",
               body=comment, actor=request.user, project=item.project,
               link="/student/public-applications")
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    def teacher_invite(self, request, pk=None):
        require_authorized_school(request.user)
        item = self.get_object()
        if item.project.primary_teacher_id != request.user.id:
            raise PermissionDenied("仅指导教师可发起全平台展示邀请。")
        if item.project.status != Project.Status.COMPLETED:
            raise ValidationError("项目完成后才能发起全平台展示邀请。")
        if item.status not in {PublicCaseRequest.Status.REJECTED, PublicCaseRequest.Status.PENDING_TEACHER}:
            raise ValidationError("该成果当前不能重新发起教师公域邀请。")
        item.request_type = PublicCaseRequest.RequestType.TEACHER_PLATFORM
        item.visibility_scope = PublicCaseRequest.VisibilityScope.PLATFORM
        item.applicant = request.user
        item.status = PublicCaseRequest.Status.WAITING_STUDENT
        item.student_consent_at = None
        item.student_consent_by = None
        item.teacher_reviewer = request.user
        item.review_comment = ""
        item.save(update_fields=["request_type", "visibility_scope", "applicant", "status", "student_consent_at", "student_consent_by", "teacher_reviewer", "review_comment"])
        notify(
            item.project.leader,
            kind=Notification.Kind.CASE_CONSENT_REQUIRED,
            title=f"教师邀请项目「{item.project.title}」公开展示",
            body="请确认是否同意将项目成果提交到全平台案例库。",
            actor=request.user,
            project=item.project,
            link=f"/student/public-applications?projectId={item.project.id}",
        )
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    def student_consent(self, request, pk=None):
        require_authorized_school(request.user)
        item = self.get_object()
        consent_public_case_request(item, request.user)
        AuditEvent.objects.create(
            school=item.project.school,
            actor=request.user,
            action=AuditEvent.Action.STUDENT_CONSENT_GIVEN,
            changes={"project_id": item.project_id, "case_id": item.id, "visibility_scope": item.visibility_scope},
        )
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    def platform_review(self, request, pk=None):
        if not platform_admin(request.user):
            raise PermissionDenied("仅平台管理员可审核全平台展示申请。")
        approved = request.data.get("approved")
        if not isinstance(approved, bool):
            raise ValidationError({"approved": "请提供 true 或 false 布尔值。"})
        item = self.get_object()
        review_platform_case_request(item, request.user, approved, str(request.data.get("comment", "")))
        AuditEvent.objects.create(
            school=item.project.school,
            actor=request.user,
            action=AuditEvent.Action.CASE_REVIEWED,
            changes={"project_id": item.project_id, "case_id": item.id, "outcome": "published" if approved else "rejected", "scope": "platform"},
        )
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    def set_visibility(self, request, pk=None):
        if not platform_admin(request.user): raise PermissionDenied("仅平台管理员可治理公开案例。")
        visible = request.data.get("visible")
        if not isinstance(visible, bool):
            raise ValidationError({"visible": "请提供 true 或 false 布尔值。"})
        item = self.get_object()
        if visible and item.request_type == PublicCaseRequest.RequestType.TEACHER_PLATFORM:
            if not item.student_consent_at:
                raise ValidationError("学生尚未同意公域展示，平台不能直接发布。")
            if item.status not in {PublicCaseRequest.Status.PUBLISHED, PublicCaseRequest.Status.OFFLINE}:
                raise ValidationError("该成果尚未完成平台审核，不能直接发布。")
        item.status = PublicCaseRequest.Status.PUBLISHED if visible else PublicCaseRequest.Status.OFFLINE; item.admin_reviewer = request.user; item.save()
        AuditEvent.objects.create(
            school=item.project.school, actor=request.user, action=AuditEvent.Action.CASE_VISIBILITY_CHANGED,
            changes={"project_id": item.project_id, "case_id": item.id, "visible": visible},
        )
        return Response(self.get_serializer(item).data)


class AIConversationViewSet(viewsets.ModelViewSet):
    serializer_class = AIConversationSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        first_user_prompt = AIConversationMessage.objects.filter(
            conversation=OuterRef("pk"),
            role=AIConversationMessage.Role.USER,
        ).order_by("created_at", "id").values("content")[:1]
        if user.role == Account.Role.STUDENT:
            return AIConversation.objects.filter(owner=user).select_related("project").annotate(
                history_preview=Subquery(first_user_prompt),
            )
        if user.role == Account.Role.TEACHER:
            return AIConversation.objects.filter(owner=user, project__primary_teacher=user).select_related("project").annotate(
                history_preview=Subquery(first_user_prompt),
            )
        return AIConversation.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in {Account.Role.STUDENT, Account.Role.TEACHER}:
            raise PermissionDenied("只有学生或教师可以创建 AI 对话。")
        mode = normalize_workspace_mode(serializer.validated_data.get("workspace_mode", AIConversation.WorkspaceMode.RESEARCH))
        project = serializer.validated_data.get("project")
        if user.role == Account.Role.TEACHER:
            if project is None:
                raise ValidationError({"project": "教师指导会话必须绑定本人负责的项目。"})
            if project.primary_teacher_id != user.id:
                raise PermissionDenied("只能在本人负责的项目中创建指导会话。")
            if mode == AIConversation.WorkspaceMode.OPENING:
                raise ValidationError({"workspace_mode": "教师指导会话不支持开题模式。"})
        elif mode == AIConversation.WorkspaceMode.OPENING and project is not None:
            raise ValidationError({"project": "开题工作台不绑定项目，请从无项目会话开始。"})
        serializer.save(owner=user, workspace_mode=mode)

    def perform_update(self, serializer):
        conversation = self.get_object()
        if "project" in serializer.validated_data and serializer.validated_data["project"] != conversation.project:
            raise ValidationError({"project": "对话创建后不能切换项目，请新建对话。"})
        mode = normalize_workspace_mode(serializer.validated_data.get("workspace_mode", conversation.workspace_mode))
        project = serializer.validated_data.get("project", conversation.project)
        if request_user := self.request.user:
            if request_user.role == Account.Role.TEACHER and (project is None or project.primary_teacher_id != request_user.id):
                raise PermissionDenied("只能在本人负责的项目中使用指导会话。")
            if request_user.role == Account.Role.TEACHER and mode == AIConversation.WorkspaceMode.OPENING:
                raise ValidationError({"workspace_mode": "教师指导会话不支持开题模式。"})
        if mode == AIConversation.WorkspaceMode.OPENING and project is not None:
            raise ValidationError({"project": "开题工作台不绑定项目，请从无项目会话开始。"})
        serializer.save()

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        conversation = self.get_object()
        conversation.is_archived = True
        conversation.save(update_fields=["is_archived", "updated_at"])
        return Response(self.get_serializer(conversation).data)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.method == "GET":
            return Response(AIConversationMessageSerializer(conversation.messages.all(), many=True).data)
        return self.create_message(request, pk=pk)

    @action(detail=True, methods=["post"], url_path=r"messages/(?P<message_id>[^/.]+)/retry")
    @transaction.atomic
    def retry_message(self, request, pk=None, message_id=None):
        """Requeue one failed assistant message without duplicating its user prompt."""
        conversation = self.get_object()
        if conversation.is_archived:
            raise ValidationError("已归档对话不能重试消息。")
        message = get_object_or_404(conversation.messages, pk=message_id)
        if message.role != AIConversationMessage.Role.ASSISTANT:
            raise ValidationError("只有助手消息可以重试。")
        if message.status != AIConversationMessage.Status.FAILED:
            raise ValidationError("只有生成失败的消息可以重试。")
        original_user_message = conversation.messages.filter(
            role=AIConversationMessage.Role.USER, created_at__lte=message.created_at,
        ).order_by("-created_at", "-id").first()
        if original_user_message is None:
            raise ValidationError("找不到可重试的原始用户问题。")

        stream_key = conversation_stream_key(message.id)
        try:
            redis.Redis.from_url(
                getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            ).delete(stream_key)
        except Exception:
            # Redis cleanup is best effort; the next stream starts from the new event id.
            pass

        message.content = ""
        message.status = AIConversationMessage.Status.QUEUED
        message.error_message = ""
        message.artifact_payload = {}

        retry_agent_key = conversation.current_agent or (message.generation_log.agent_key if message.generation_log else None)
        api_key = get_configured_ai_api_key()
        if not api_key and not conversation.project_id:
            message.content = (
                "研究问题助手需要配置真实 AI 服务后才能生成候选。"
                if retry_agent_key == "proposal-topic"
                else f"这是通用咨询：你问的是“{original_user_message.content}”。我可以先帮你梳理概念、拆解问题和制定下一步；如果需要结合项目材料，请新建一个绑定项目的对话。"
            )
            message.status = AIConversationMessage.Status.COMPLETED
            message.save(update_fields=["content", "status", "error_message", "artifact_payload", "updated_at"])
            publish_conversation_event(message.id, "message.started", {})
            publish_conversation_event(message.id, "message.delta", {"delta": message.content})
            publish_conversation_event(message.id, "message.done", {"message_id": message.id})
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=["updated_at"])
            return Response(AIConversationMessageSerializer(message).data, status=status.HTTP_200_OK)

        if conversation.project_id:
            old_log = message.generation_log
            if old_log is None:
                raise ValidationError("项目消息缺少生成记录，无法重试。")
            payload = {
                "project": old_log.project_id,
                "workspace_mode": old_log.workspace_mode,
                "purpose": old_log.purpose,
                "agent_key": old_log.agent_key if not old_log.agent_key or AgentTemplate.resolve(old_log.agent_key, request.user.school, request.user.role) else None,
                "task": old_log.task_id,
                "material": old_log.material_id,
                "prompt": old_log.prompt,
                "paper_type": old_log.paper_type,
                "context_scope": old_log.context_scope or {},
            }
            log_serializer = AIGenerationLogSerializer(data=payload, context={"request": request})
            log_serializer.is_valid(raise_exception=True)
            values = log_serializer.validated_data
            values.pop("input_values", None)
            new_log = create_ai_request(log_serializer, request.user, settings.OPENAI_MODEL)
            new_log.conversation = conversation
            new_log.message = message
            new_log.status = AIGenerationLog.Status.QUEUED
            new_log.save(update_fields=["conversation", "message", "status"])
            message.generation_log = new_log
            message.save(update_fields=["content", "status", "error_message", "artifact_payload", "generation_log", "updated_at"])
            transaction.on_commit(lambda: generate_ai_response.delay(new_log.id))
        else:
            message.generation_log = None
            message.save(update_fields=["content", "status", "error_message", "artifact_payload", "generation_log", "updated_at"])
            transaction.on_commit(lambda: generate_general_ai_response.delay(message.id))

        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])
        return Response(AIConversationMessageSerializer(message).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def create_message(self, request, pk=None):
        conversation = self.get_object()
        if conversation.is_archived:
            raise ValidationError("已归档对话不能继续发送消息。")
        content = str(request.data.get("content", "")).strip()
        if not content:
            raise ValidationError({"content": "消息不能为空。"})
        project = conversation.project
        mode_supplied = "workspace_mode" in request.data
        workspace_mode = normalize_workspace_mode(request.data.get("workspace_mode") or conversation.workspace_mode)
        if workspace_mode == AIConversation.WorkspaceMode.OPENING and project is not None:
            raise ValidationError({"workspace_mode": "开题工作台不能读取当前项目，请新建无项目开题会话。"})
        if mode_supplied and workspace_mode_requires_project(workspace_mode) and project is None:
            raise ValidationError({"project": "研究或答辩工作台需要先选择当前项目。"})
        agent_key = request.data.get("agent_key") or conversation.current_agent or None
        api_key = get_configured_ai_api_key()
        if project is None and agent_key == "proposal-topic" and not api_key:
            return Response(
                {"detail": "研究问题助手需要配置真实 AI 服务后才能生成候选。"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        should_name_conversation = is_generic_conversation_title(conversation.title) and not conversation.messages.filter(
            role=AIConversationMessage.Role.USER,
        ).exists()
        if should_name_conversation:
            conversation.title = conversation_title_from_prompt(content)
        user_message = AIConversationMessage.objects.create(
            conversation=conversation, role=AIConversationMessage.Role.USER, content=content,
        )
        assistant = AIConversationMessage.objects.create(
            conversation=conversation, role=AIConversationMessage.Role.ASSISTANT,
            content="", status=AIConversationMessage.Status.QUEUED,
        )
        if project is None:
            # General consultation remains project-free and never creates a material-bearing AI log.
            if api_key:
                transaction.on_commit(lambda: generate_general_ai_response.delay(assistant.id))
            else:
                assistant.content = f"这是通用咨询：你问的是“{content}”。我可以先帮你梳理概念、拆解问题和制定下一步；如果需要结合项目材料，请新建一个绑定项目的对话。"
                assistant.status = AIConversationMessage.Status.COMPLETED
                assistant.save(update_fields=["content", "status", "updated_at"])
                publish_conversation_event(assistant.id, "message.started", {})
                publish_conversation_event(assistant.id, "message.delta", {"delta": assistant.content})
                publish_conversation_event(assistant.id, "message.done", {"message_id": assistant.id})
            conversation.current_agent = agent_key or ""
        else:
            if not project_member(project, request.user):
                raise PermissionDenied("无项目权限。")
            # Conversations created before the global seed may carry a retired
            # agent key; keep those legacy messages usable while explicit new
            # selections still go through strict serializer validation.
            if not request.data.get("agent_key") and agent_key and not AgentTemplate.resolve(agent_key, request.user.school, request.user.role):
                agent_key = None
            paper_type = request.data.get("paper_type") or conversation.paper_type or ""
            task = request.data.get("task")
            material = request.data.get("material")
            input_values = request.data.get("input_values")
            context_scope = request.data.get("context_scope")
            payload = {
                "project": project.id,
                "workspace_mode": workspace_mode,
                "purpose": agent_key or "对话咨询",
                "agent_key": agent_key,
                "task": task,
                "material": material,
                "prompt": content,
                "paper_type": paper_type,
                "input_values": input_values,
                "context_scope": context_scope or {},
            }
            payload = {key: value for key, value in payload.items() if value is not None}
            log_serializer = AIGenerationLogSerializer(data=payload, context={"request": request})
            log_serializer.is_valid(raise_exception=True)
            values = log_serializer.validated_data
            values.pop("input_values", None)
            log = create_ai_request(log_serializer, request.user, settings.OPENAI_MODEL)
            log.conversation = conversation
            log.message = assistant
            log.status = AIGenerationLog.Status.QUEUED
            log.save(update_fields=["conversation", "message", "status"])
            conversation.current_agent = values.get("agent_key") or ""
            conversation.paper_type = values.get("paper_type") or ""
            assistant.generation_log = log
            assistant.save(update_fields=["generation_log", "updated_at"])
            transaction.on_commit(lambda: generate_ai_response.delay(log.id))
        conversation.workspace_mode = workspace_mode
        conversation.updated_at = timezone.now()
        update_fields = ["updated_at", "current_agent", "paper_type", "workspace_mode"]
        if should_name_conversation:
            update_fields.append("title")
        conversation.save(update_fields=update_fields)
        return Response(AIConversationMessageSerializer(assistant).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="create_from_opening")
    @transaction.atomic
    def create_from_opening(self, request, pk=None):
        """Create one unclaimed project only after the student confirms an opening artifact."""
        require_authorized_school(request.user)
        conversation = self.get_object()
        if conversation.workspace_mode != AIConversation.WorkspaceMode.OPENING or conversation.project_id:
            raise ValidationError("只有无项目的开题工作台可以创建项目。")
        if conversation.opening_project_id:
            return Response(ProjectSerializer(conversation.opening_project, context={"request": request}).data, status=status.HTTP_200_OK)
        if request.data.get("confirm") is not True:
            raise ValidationError({"confirm": "请明确确认后再创建项目。"})

        message_id = request.data.get("message_id")
        messages = conversation.messages.filter(role=AIConversationMessage.Role.ASSISTANT, status=AIConversationMessage.Status.COMPLETED)
        message = messages.filter(pk=message_id).first() if message_id else messages.order_by("-created_at", "-id").first()
        if message is None:
            raise ValidationError("请先完成一次开题对话，再创建项目。")
        artifact = message.artifact_payload or {}
        title = str(request.data.get("title") or artifact.get("project_title") or "").strip()
        plan = str(request.data.get("plan") or artifact.get("project_plan") or "").strip()
        candidates = artifact.get("candidates") or []
        if not title or not isinstance(candidates, list) or not candidates:
            raise ValidationError("开题草稿缺少项目标题或研究问题候选。")
        try:
            candidate_index = int(request.data.get("candidate_index", artifact.get("recommended_index", 0)))
        except (TypeError, ValueError):
            raise ValidationError({"candidate_index": "研究问题候选编号无效。"})
        if candidate_index < 0 or candidate_index >= len(candidates) or not isinstance(candidates[candidate_index], dict):
            raise ValidationError({"candidate_index": "研究问题候选不存在。"})
        problem = str(request.data.get("problem") or candidates[candidate_index].get("question") or "").strip()
        if not problem:
            raise ValidationError("请选择一个完整的研究问题。")
        project_type = str(request.data.get("project_type") or artifact.get("project_type") or "research").strip()
        if project_type not in {"research", "invention", "engineering"}:
            project_type = "research"
        project = Project.objects.create(
            school=request.user.school,
            title=title,
            problem=problem,
            plan=plan,
            project_type=project_type,
            leader=request.user,
            status=Project.Status.UNCLAIMED,
        )
        project.members.create(account=request.user, role="leader")
        conversation.opening_project = project
        conversation.save(update_fields=["opening_project", "updated_at"])
        if not request.user.primary_project_id:
            request.user.primary_project = project
            request.user.save(update_fields=["primary_project"])
        AuditEvent.objects.create(
            school=project.school,
            actor=request.user,
            action=AuditEvent.Action.PROJECT_UPDATED,
            changes={"project_id": project.id, "created_from_opening": conversation.id, "title": project.title},
        )
        return Response(ProjectSerializer(project, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path=r"messages/(?P<message_id>[^/.]+)/stream", renderer_classes=[ServerSentEventRenderer])
    def stream(self, request, pk=None, message_id=None):
        conversation = self.get_object()
        message = get_object_or_404(conversation.messages, pk=message_id)
        last_id = request.headers.get("Last-Event-ID") or request.query_params.get("last_event_id") or "0-0"
        key = conversation_stream_key(message.id)
        client = redis.Redis.from_url(getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"), decode_responses=True)

        def events():
            cursor = last_id
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    rows = client.xread({key: cursor}, block=1000, count=50)
                except Exception:
                    rows = []
                if rows:
                    for _, entries in rows:
                        for event_id, fields in entries:
                            cursor = event_id
                            yield f"id: {event_id}\nevent: {fields.get('event', 'message.delta')}\ndata: {fields.get('payload', '{}')}\n\n"
                            if fields.get("event") in {"message.done", "message.error"}:
                                return
                current = AIConversationMessage.objects.get(pk=message.id)
                if current.status in {AIConversationMessage.Status.COMPLETED, AIConversationMessage.Status.FAILED} and not rows:
                    if current.status == AIConversationMessage.Status.COMPLETED:
                        yield f"event: message.done\ndata: {json.dumps({'message_id': current.id})}\n\n"
                    else:
                        yield f"event: message.error\ndata: {json.dumps({'error': current.error_message}, ensure_ascii=False)}\n\n"
                    return
                yield ": keep-alive\n\n"

        response = StreamingHttpResponse(events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AIGenerationLogViewSet(viewsets.ModelViewSet):
    serializer_class = AIGenerationLogSerializer
    http_method_names = ["get", "post", "head", "options"]
    def get_queryset(self):
        queryset = accessible_ai_logs(self.request.user)
        project_id = self.request.query_params.get("project")
        return queryset.filter(project_id=project_id) if project_id else queryset
    def perform_create(self, serializer):
        require_authorized_school(self.request.user)
        project = serializer.validated_data.get("project")
        workspace_mode = serializer.validated_data.get("workspace_mode", "research")
        if project is None:
            if self.request.user.role != Account.Role.STUDENT or workspace_mode != "opening":
                raise ValidationError({"project": "研究或答辩 AI 必须绑定当前项目。"})
        elif not project_member(project, self.request.user):
            raise PermissionDenied("无项目权限。")
        record = create_ai_request(serializer, self.request.user, settings.OPENAI_MODEL)
        transaction.on_commit(lambda: generate_ai_response.delay(record.id))

    @action(detail=True, methods=["post"], url_path="save_as_material")
    @transaction.atomic
    def save_as_material(self, request, pk=None):
        require_authorized_school(request.user)
        # Check visibility before locking.  A nullable project relation makes
        # PostgreSQL reject FOR UPDATE on the outer join produced by the
        # student opening-log queryset.
        get_object_or_404(self.get_queryset().filter(pk=pk), pk=pk)
        log = AIGenerationLog.objects.select_for_update().get(pk=pk)
        material_id = request.data.get("material") or log.material_id
        if not material_id:
            raise ValidationError({"material": "请选择要保存到的项目材料。"})
        material = Material.objects.select_related("project").filter(pk=material_id).first()
        if not material:
            raise ValidationError({"material": "所选材料不存在。"})
        content = request.data["content"] if "content" in request.data else None
        revision_note = request.data["revision_note"] if "revision_note" in request.data else None
        revision = save_ai_output_as_material(log, material, request.user, content=content, revision_note=revision_note)
        return Response(MaterialRevisionSerializer(revision, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AgentTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = AgentTemplateSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if platform_admin(user):
            return AgentTemplate.objects.all()  # 管理员看全部（含停用）
        qs = AgentTemplate.objects.filter(is_active=True)
        qs = qs.filter(role__in=[user.role, AgentTemplate.Role.BOTH])
        qs = qs.filter(Q(school=None) | Q(school=user.school))  # 全局 + 本校校本
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if platform_admin(user):
            serializer.save(school=None)  # 管理员只建全局模板
        else:
            raise PermissionDenied("仅平台管理员可配置 Skills。")

    def perform_update(self, serializer):
        obj = self.get_object()
        user = self.request.user
        if not platform_admin(user):
            raise PermissionDenied("仅平台管理员可配置 Skills。")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not platform_admin(user):
            raise PermissionDenied("仅平台管理员可配置 Skills。")
        instance.delete()


class ReportExportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportExportSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = ReportExport.objects.filter(project__in=accessible_projects(self.request.user)).select_related("project", "requested_by")
        project_id = self.request.query_params.get("project")
        return queryset.filter(project_id=project_id).order_by("-created_at") if project_id else queryset.order_by("-created_at")

    def perform_create(self, serializer):
        require_authorized_school(self.request.user)
        project = serializer.validated_data["project"]
        if self.request.user.role != Account.Role.STUDENT or project.leader_id != self.request.user.id:
            raise PermissionDenied("仅项目负责人可生成报告。")
        if not accessible_projects(self.request.user).filter(pk=project.pk).exists():
            raise PermissionDenied("无项目权限。")
        if serializer.validated_data["format"] == ReportExport.Format.PDF and not settings.PDF_EXPORT_ENABLED:
            raise ValidationError("当前核心部署未启用 PDF 转换，请导出 Word 文档。")
        export = serializer.save(requested_by=self.request.user)
        AuditEvent.objects.create(
            school=project.school,
            actor=self.request.user,
            action=AuditEvent.Action.REPORT_EXPORT_REQUESTED,
            changes={"project_id": project.id, "export_id": export.id, "format": export.format},
        )
        transaction.on_commit(lambda: generate_report_export.delay(export.id))

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        export = self.get_object()
        if export.status != ReportExport.Status.COMPLETED or not export.file:
            raise Http404
        try:
            response = FileResponse(export.file.open("rb"), as_attachment=True, filename=export.file.name.rsplit("/", 1)[-1])
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except FileNotFoundError as exc:
            raise Http404 from exc


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related("actor", "project").order_by("-created_at")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        note = self.get_object()
        note.is_read = True
        note.save(update_fields=["is_read"])
        return Response(self.get_serializer(note).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({"detail": "已全部标记为已读。"})

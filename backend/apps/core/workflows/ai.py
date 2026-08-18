"""AI access and school-quota rules shared by the API entry point."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.core.models import AIGenerationLog, Account, School


def accessible_ai_logs(actor):
    base = AIGenerationLog.objects.select_related("project", "actor").order_by("-created_at")
    if actor.role == Account.Role.STUDENT:
        return base.filter(project__school=actor.school, actor=actor)
    if actor.role == Account.Role.TEACHER:
        return base.filter(project__school=actor.school, project__primary_teacher=actor)
    raise PermissionDenied("平台管理员不能查看学校项目 AI 记录。")


def create_ai_request(serializer, actor, model_name):
    """Reserve one current-month school quota slot and create one queued request."""
    now = timezone.now()
    with transaction.atomic():
        school = School.objects.select_for_update().get(pk=actor.school_id)
        used = AIGenerationLog.objects.filter(
            project__school=school,
            created_at__year=now.year,
            created_at__month=now.month,
        ).count()
        if used >= school.ai_quota:
            from rest_framework.exceptions import Throttled
            raise Throttled(detail="学校本月 AI 配额已用完。")
        return serializer.save(actor=actor, model_name=model_name)

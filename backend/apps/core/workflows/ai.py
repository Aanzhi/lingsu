"""AI access, quota and conversation stream rules shared by the API entry point."""

import json
import redis
from django.conf import settings

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.core.models import AIGenerationLog, Account, School


def accessible_ai_logs(actor):
    base = AIGenerationLog.objects.select_related("project", "actor").order_by("-created_at")
    if actor.role == Account.Role.STUDENT:
        return base.filter(Q(project__school=actor.school) | Q(project__isnull=True), actor=actor)
    if actor.role == Account.Role.TEACHER:
        return base.filter(
            project__school=actor.school,
            project__primary_teacher=actor,
        ).filter(
            Q(actor=actor) | Q(saved_material_revision__isnull=False)
        ).distinct()
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


def conversation_stream_key(message_id):
    return f"ai:conversation-message:{message_id}:events"


def publish_conversation_event(message_id, event, payload=None):
    try:
        client = redis.Redis.from_url(getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"), decode_responses=True)
        return client.xadd(conversation_stream_key(message_id), {
            "event": event, "payload": json.dumps(payload or {}, ensure_ascii=False),
        }, maxlen=500, approximate=True)
    except Exception:
        return None

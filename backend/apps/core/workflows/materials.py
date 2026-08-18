"""Business rules for immutable material revisions and teacher reviews."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.core.models import AuditEvent, Material, MaterialAttachment, MaterialRevision, Notification, Project, ProjectGrowth, ProjectTask
from apps.core.notifiers import notify


EDITABLE_MATERIAL_STATUSES = {Material.Status.DRAFT, Material.Status.REVISION_REQUIRED}


def create_material_draft(serializer, actor):
    """Create a revision only when its project and material can accept a draft."""
    material = serializer.validated_data["material"]
    project = material.project
    is_member = (
        project.leader_id == actor.id
        or project.members.filter(account=actor).exists()
    )
    if not is_member:
        raise PermissionDenied("无项目权限。")
    if project.status != Project.Status.ACTIVE or not project.primary_teacher_id:
        raise ValidationError("项目尚未由教师认领并启动，不能创建正式材料。")
    if material.status not in EDITABLE_MATERIAL_STATUSES:
        raise ValidationError("该材料已提交或通过审核，不能创建替换版本。")
    return serializer.save(author=actor)


def submit_material_revision(revision, actor, truth_confirmed):
    """Move one draft to review. The leader owns the formal submission decision."""
    if not truth_confirmed:
        return Response(
            {"detail": "提交前须确认内容已按真实项目核对。"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    project = revision.material.project
    if actor.id != project.leader_id:
        raise PermissionDenied("仅项目负责人可正式提交材料。")
    if revision.status != MaterialRevision.Status.DRAFT:
        raise ValidationError("只有草稿版本可以提交。")
    if project.status != Project.Status.ACTIVE or not project.primary_teacher_id:
        raise ValidationError("项目尚未由教师认领并启动，不能提交正式材料。")
    material = revision.material
    if material.status not in EDITABLE_MATERIAL_STATUSES:
        raise ValidationError("该材料当前不能再次提交。")

    scan_statuses = set(revision.attachments.values_list("scan_status", flat=True))
    if scan_statuses & {MaterialAttachment.ScanStatus.INFECTED, MaterialAttachment.ScanStatus.FAILED}:
        raise ValidationError("附件未通过安全检查，不能提交审核。")
    if scan_statuses & {MaterialAttachment.ScanStatus.PENDING, MaterialAttachment.ScanStatus.PROCESSING}:
        return Response({"detail": "附件仍在进行安全检查，请稍后重试。"}, status=409)
    if not revision.content.strip() and not revision.attachments.exists():
        raise ValidationError("请填写正文或上传附件。")

    revision.truth_confirmed = True
    revision.status = MaterialRevision.Status.SUBMITTED
    revision.save(update_fields=["truth_confirmed", "status"])
    material.status = Material.Status.SUBMITTED
    material.save(update_fields=["status"])
    if material.task_id:
        material.task.status = ProjectTask.Status.PENDING_REVIEW
        material.task.save(update_fields=["status"])
    AuditEvent.objects.create(
        school=project.school,
        actor=actor,
        action=AuditEvent.Action.MATERIAL_SUBMITTED,
        changes={"project_id": project.id, "material_id": material.id, "revision_id": revision.id},
    )
    return None


def review_material_revision(revision, teacher, outcome, comment):
    """Apply an approval or repair request and advance the task map when complete."""
    if revision.material.project.primary_teacher_id != teacher.id:
        raise PermissionDenied("仅主指导教师可审核。")
    if revision.status != MaterialRevision.Status.SUBMITTED:
        raise ValidationError("只有待审核版本可以审核。")
    if outcome not in {"approved", "revision_required"}:
        raise ValidationError({"outcome": "值须为 approved 或 revision_required。"})
    if outcome == "revision_required" and not comment:
        raise ValidationError({"comment": "打回必须填写可执行意见。"})

    with transaction.atomic():
        revision.status = outcome
        revision.reviewer = teacher
        revision.review_comment = comment
        revision.save(update_fields=["status", "reviewer", "review_comment"])
        material = revision.material
        material.status = outcome
        material.save(update_fields=["status"])

        if material.task_id:
            _update_task_after_review(material.task, outcome)
        if outcome == "approved":
            _record_growth(material.project, material.task)
        AuditEvent.objects.create(
            school=material.project.school,
            actor=teacher,
            action=AuditEvent.Action.MATERIAL_REVIEWED,
            changes={
                "project_id": material.project_id,
                "material_id": material.id,
                "revision_id": revision.id,
                "outcome": outcome,
            },
        )

        leader = material.project.leader
        if outcome == "approved":
            notify(leader, kind=Notification.Kind.MATERIAL_APPROVED,
                   title=f"材料「{material.title}」已通过审核",
                   actor=teacher, project=material.project,
                   link=f"/student/projects/{material.project_id}/materials")
        else:
            notify(leader, kind=Notification.Kind.MATERIAL_REVISION_REQUIRED,
                   title=f"材料「{material.title}」需要修订",
                   body=comment or "",
                   actor=teacher, project=material.project,
                   link=f"/student/projects/{material.project_id}/materials")


def _update_task_after_review(task, outcome):
    if outcome == "revision_required":
        task.status = ProjectTask.Status.REVISION_REQUIRED
        task.save(update_fields=["status"])
        return

    required_materials = task.materials.filter(required=True)
    is_complete = required_materials.exists() and not required_materials.exclude(status=Material.Status.APPROVED).exists()
    task.status = ProjectTask.Status.COMPLETED if is_complete else ProjectTask.Status.AVAILABLE
    task.save(update_fields=["status"])
    if not is_complete:
        return

    project = task.project
    if not project.tasks.exclude(status=ProjectTask.Status.COMPLETED).exists():
        project.status = Project.Status.COMPLETED
        project.save(update_fields=["status"])


def _record_growth(project, task):
    growth, _ = ProjectGrowth.objects.get_or_create(project=project)
    today = timezone.localdate()
    if growth.last_activity_date != today:
        growth.experience += task.xp_reward if task else 100
        growth.streak_days = growth.streak_days + 1 if growth.last_activity_date == today - timedelta(days=1) else 1
        growth.last_activity_date = today
    growth.level = 1 + growth.experience // 300
    growth.title = "证据探索者" if growth.level >= 2 else "探索新手"
    growth.save(update_fields=["experience", "level", "streak_days", "last_activity_date", "title"])

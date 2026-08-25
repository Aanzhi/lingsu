"""Rules protecting the public case library from premature or unsafe publication."""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.models import Material, Notification, Project, PublicCaseRequest
from apps.core.notifiers import notify


def validate_public_case_request(project, applicant, selected_materials, request_type=PublicCaseRequest.RequestType.STUDENT_SCHOOL, visibility_scope=PublicCaseRequest.VisibilityScope.SCHOOL):
    if request_type == PublicCaseRequest.RequestType.STUDENT_SCHOOL:
        if project.leader_id != applicant.id:
            raise PermissionDenied("仅项目负责人可申请校内公开。")
        if visibility_scope != PublicCaseRequest.VisibilityScope.SCHOOL:
            raise ValidationError("学生发起的成果申请只能在校内展示。")
    elif request_type == PublicCaseRequest.RequestType.TEACHER_PLATFORM:
        if project.primary_teacher_id != applicant.id:
            raise PermissionDenied("仅项目指导教师可发起全平台展示邀请。")
        if visibility_scope != PublicCaseRequest.VisibilityScope.PLATFORM:
            raise ValidationError("教师发起的成果邀请只能进入全平台审核。")
    else:
        raise ValidationError({"request_type": "成果申请类型无效。"})
    if project.status != Project.Status.COMPLETED:
        raise ValidationError("项目完成后才能申请公开案例。")
    materials = list(selected_materials)
    if not materials:
        raise ValidationError({"selected_materials": "请至少选择一项已通过材料对外展示。"})
    invalid = [material.id for material in materials if material.project_id != project.id or material.status != Material.Status.APPROVED]
    if invalid:
        raise ValidationError({"selected_materials": "只能选择本项目已通过的材料公开。"})


def consent_public_case_request(case, student):
    if case.request_type != PublicCaseRequest.RequestType.TEACHER_PLATFORM:
        raise ValidationError("该成果不是教师发起的公域展示邀请。")
    if case.project.leader_id != student.id and not case.project.members.filter(account=student).exists():
        raise PermissionDenied("只有项目学生可以处理成果展示邀请。")
    if case.status != PublicCaseRequest.Status.WAITING_STUDENT:
        raise ValidationError("该成果邀请当前不等待学生同意。")
    case.student_consent_at = timezone.now()
    case.student_consent_by = student
    case.status = PublicCaseRequest.Status.PENDING_PLATFORM
    case.visibility_scope = PublicCaseRequest.VisibilityScope.PLATFORM
    case.save(update_fields=["student_consent_at", "student_consent_by", "status", "visibility_scope"])
    notify(
        case.applicant,
        kind=Notification.Kind.CASE_PENDING_PLATFORM,
        title=f"成果「{case.project.title}」已获学生同意，等待平台审核",
        actor=student,
        project=case.project,
        link=f"/teacher/cases/{case.id}",
    )
    return case


def review_platform_case_request(case, reviewer, approved, comment=""):
    if case.request_type != PublicCaseRequest.RequestType.TEACHER_PLATFORM:
        raise ValidationError("只有教师公域邀请需要平台审核。")
    if case.status != PublicCaseRequest.Status.PENDING_PLATFORM:
        raise ValidationError("该成果当前不在平台审核队列。")
    if approved:
        case.status = PublicCaseRequest.Status.PUBLISHED
        case.review_comment = ""
    else:
        if not comment.strip():
            raise ValidationError({"comment": "平台驳回必须填写可执行的修改意见。"})
        case.status = PublicCaseRequest.Status.REJECTED
        case.review_comment = comment.strip()
    case.platform_reviewer = reviewer
    case.admin_reviewer = reviewer
    case.save(update_fields=["status", "review_comment", "platform_reviewer", "admin_reviewer"])
    recipient = case.project.leader
    notify(
        recipient,
        kind=Notification.Kind.CASE_PUBLISHED if approved else Notification.Kind.CASE_REJECTED,
        title=f"成果「{case.project.title}」{'已发布到全平台' if approved else '需要修改后重新申请'}",
        body=case.review_comment,
        actor=reviewer,
        project=case.project,
        link="/student/public-applications",
    )
    return case


def resubmit_public_case_request(case, applicant, values):
    if case.applicant_id != applicant.id or case.project.leader_id != applicant.id:
        raise PermissionDenied("仅项目负责人可重提公开申请。")
    if case.status != PublicCaseRequest.Status.REJECTED:
        raise ValidationError("只有被驳回的公开申请可以重提。")
    selected_materials = values.get("selected_materials", case.selected_materials.all())
    validate_public_case_request(case.project, applicant, selected_materials)

    for field in ("public_summary", "tags", "discipline", "application_scene", "outcome_form", "cover"):
        if field in values:
            setattr(case, field, values[field])
    case.status = PublicCaseRequest.Status.PENDING_TEACHER
    case.teacher_reviewer = None
    case.review_comment = ""
    case.save()
    if "selected_materials" in values:
        case.selected_materials.set(selected_materials)
    return case

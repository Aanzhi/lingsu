"""Rules protecting the public case library from premature or unsafe publication."""

from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.models import Material, Project, PublicCaseRequest


def validate_public_case_request(project, applicant, selected_materials):
    if project.leader_id != applicant.id:
        raise PermissionDenied("仅项目负责人可申请公开。")
    if project.status != Project.Status.COMPLETED:
        raise ValidationError("项目完成后才能申请公开案例。")
    materials = list(selected_materials)
    if not materials:
        raise ValidationError({"selected_materials": "请至少选择一项已通过材料对外展示。"})
    invalid = [material.id for material in materials if material.project_id != project.id or material.status != Material.Status.APPROVED]
    if invalid:
        raise ValidationError({"selected_materials": "只能选择本项目已通过的材料公开。"})


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

"""Project lifecycle rules: teacher claim, template snapshot, and task creation."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditEvent, Material, Project, ProjectTask, Template
from apps.core.services import get_or_create_default_template


def claim_project(project, teacher, template_id=None):
    """Atomically assign one teacher and turn an unclaimed draft into a task map."""
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project.pk)
        if project.status != Project.Status.UNCLAIMED or project.primary_teacher_id:
            raise ValidationError("该项目已被认领。")
        template = _resolve_template(project, teacher, template_id)
        snapshot = _instantiate_template(project, template)
        project.primary_teacher = teacher
        project.status = Project.Status.ACTIVE
        project.template_snapshot = snapshot
        project.save(update_fields=["primary_teacher", "status", "template_snapshot"])
        AuditEvent.objects.create(
            school=project.school,
            actor=teacher,
            action=AuditEvent.Action.PROJECT_CLAIMED,
            changes={"project_id": project.id, "template_id": template.id},
        )
        return project


def _resolve_template(project, teacher, template_id):
    if template_id:
        template = Template.objects.filter(
            pk=template_id,
            school=teacher.school,
            is_published=True,
        ).first()
        if not template:
            raise ValidationError({"template": "所选模板不存在、未发布或不属于本校。"})
        return template
    return get_or_create_default_template(
        school=teacher.school,
        owner=teacher,
        category=project.project_type,
    )


def _instantiate_template(project, template):
    snapshot = []
    task_order = 0
    stages = template.stages.prefetch_related("tasks__materials").all()
    for stage in stages:
        for source_task in stage.tasks.all():
            task_order += 1
            task = ProjectTask.objects.create(
                project=project,
                template_task=source_task,
                stage_name=stage.name,
                stage_order=stage.order,
                title=source_task.name,
                description=source_task.description,
                order=task_order,
                status=ProjectTask.Status.AVAILABLE,
            )
            snapshot.append({"stage": stage.name, "title": source_task.name, "order": task_order})
            for source_material in source_task.materials.all():
                Material.objects.create(
                    project=project,
                    task=task,
                    template_material=source_material,
                    title=source_material.title,
                    required=source_material.required,
                    report_section=source_material.report_section,
                    report_order=source_material.order,
                )
    return snapshot

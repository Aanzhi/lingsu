"""Membership invitation state transitions for active, teacher-guided projects."""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.models import AuditEvent, MemberInvitation, Notification, Project, ProjectMember
from apps.core.notifiers import notify


def create_member_invitation(serializer, inviter):
    project = serializer.validated_data["project"]
    invitee = serializer.validated_data["invitee"]
    if project.leader_id != inviter.id:
        raise PermissionDenied("仅项目负责人可邀请成员。")
    if project.status != Project.Status.ACTIVE or not project.primary_teacher_id:
        raise ValidationError("项目需先由教师认领并启动，才能邀请成员。")
    if invitee.school_id != project.school_id or invitee.role != "student":
        raise ValidationError("只能邀请本校学生。")
    invitation = serializer.save(inviter=inviter)
    notify(
        invitation.invitee,
        kind=Notification.Kind.INVITATION_PENDING,
        title=f"邀请你加入项目「{project.title}」",
        body="接受后还需主指导教师确认，才能进入正式项目团队。",
        actor=inviter,
        project=project,
        link="/student/invitations",
    )
    return invitation


def respond_to_invitation(invitation, student, accept):
    with transaction.atomic():
        invitation = MemberInvitation.objects.select_for_update().select_related("project").get(pk=invitation.pk)
        if invitation.invitee_id != student.id:
            raise PermissionDenied("仅被邀请学生可处理邀请。")
        if invitation.status != MemberInvitation.Status.PENDING_STUDENT:
            raise ValidationError("该邀请当前不能再次处理。")
        invitation.status = MemberInvitation.Status.PENDING_TEACHER if accept else MemberInvitation.Status.REJECTED
        invitation.save(update_fields=["status"])
        _record_decision(invitation, student, "accepted" if accept else "rejected_by_student")
        leader = invitation.project.leader
        if accept:
            notify(leader, kind=Notification.Kind.INVITATION_ACCEPTED,
                   title=f"{student.get_full_name() or student.username} 接受了项目「{invitation.project.title}」的成员邀请",
                   actor=student, project=invitation.project,
                   link=f"/student/projects/{invitation.project_id}")
        else:
            notify(leader, kind=Notification.Kind.INVITATION_REJECTED,
                   title=f"{student.get_full_name() or student.username} 拒绝了项目「{invitation.project.title}」的成员邀请",
                   actor=student, project=invitation.project,
                   link=f"/student/projects/{invitation.project_id}")
        return invitation


def decide_member_invitation(invitation, teacher, approved):
    with transaction.atomic():
        invitation = MemberInvitation.objects.select_for_update().select_related("project").get(pk=invitation.pk)
        if invitation.project.primary_teacher_id != teacher.id:
            raise PermissionDenied("仅主指导教师可确认成员。")
        if invitation.status != MemberInvitation.Status.PENDING_TEACHER:
            raise ValidationError("成员尚未等待教师确认。")
        invitation.status = MemberInvitation.Status.APPROVED if approved else MemberInvitation.Status.REJECTED
        invitation.save(update_fields=["status"])
        if approved:
            ProjectMember.objects.get_or_create(
                project=invitation.project,
                account=invitation.invitee,
                defaults={"role": "member"},
            )
            notify(invitation.invitee, kind=Notification.Kind.MEMBER_ASSIGNED,
                   title=f"你已加入项目「{invitation.project.title}」",
                   actor=teacher, project=invitation.project,
                   link=f"/student/projects/{invitation.project_id}")
        else:
            notify(invitation.invitee, kind=Notification.Kind.INVITATION_REJECTED,
                   title=f"教师未通过你加入项目「{invitation.project.title}」的申请",
                   actor=teacher, project=invitation.project,
                   link=f"/student/projects/{invitation.project_id}")
        _record_decision(invitation, teacher, "approved" if approved else "rejected_by_teacher")
        return invitation


def assign_member(project, teacher, invitee):
    """教师直接将本校学生加入自己指导的项目（一步到位，无需学生二次确认）。"""
    if project.primary_teacher_id != teacher.id:
        raise PermissionDenied("仅主指导教师可分配组员。")
    if project.status != Project.Status.ACTIVE or not project.primary_teacher_id:
        raise ValidationError("项目需先由教师认领并启动，才能分配组员。")
    if invitee.school_id != project.school_id or invitee.role != "student":
        raise ValidationError("只能分配本校学生。")
    with transaction.atomic():
        member, _ = ProjectMember.objects.get_or_create(
            project=project, account=invitee, defaults={"role": "member"},
        )
        MemberInvitation.objects.update_or_create(
            project=project,
            invitee=invitee,
            defaults={"inviter": teacher, "status": MemberInvitation.Status.APPROVED},
        )
        AuditEvent.objects.create(
            school=project.school,
            actor=teacher,
            action=AuditEvent.Action.MEMBER_ASSIGNED,
            changes={"project_id": project.id, "invitee_id": invitee.id},
        )
        notify(invitee, kind=Notification.Kind.MEMBER_ASSIGNED,
               title=f"教师已将你加入项目「{project.title}」",
               actor=teacher, project=project,
               link=f"/student/projects/{project.id}")
    return member


def _record_decision(invitation, actor, decision):
    AuditEvent.objects.create(
        school=invitation.project.school,
        actor=actor,
        action=AuditEvent.Action.MEMBER_INVITATION_DECIDED,
        changes={"project_id": invitation.project_id, "invitation_id": invitation.id, "decision": decision},
    )

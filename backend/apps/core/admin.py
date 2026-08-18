from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AIGenerationLog, Account, Announcement, AuditEvent, Competition, Material, MaterialAttachment, MaterialRevision, MemberInvitation, Project, ProjectGrowth, ProjectMember, ProjectTask, PublicCaseRequest, ReportExport, School, Template, TemplateMaterial, TemplateStage, TemplateTask

admin.site.register(School)
admin.site.register(Account, UserAdmin)
admin.site.register([Template, TemplateStage, TemplateTask, TemplateMaterial, Project, ProjectTask, ProjectGrowth, ProjectMember, MemberInvitation, Material, MaterialRevision, MaterialAttachment, PublicCaseRequest, ReportExport, AIGenerationLog, Competition, Announcement, AuditEvent])

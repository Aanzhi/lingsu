from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import AIGenerationLogViewSet, AIConversationViewSet, AgentTemplateViewSet, AIAvailabilityView, AnnouncementViewSet, CompetitionViewSet, MaterialAttachmentViewSet, MaterialRevisionViewSet, MaterialViewSet, MemberInvitationViewSet, MeView, NotificationViewSet, PlatformAIConfigurationView, ProjectTaskViewSet, ProjectViewSet, PublicCaseRequestViewSet, ReportExportViewSet, SchoolViewSet, ServiceStatusView, StudentDirectoryView, TemplateViewSet, UploadSessionViewSet, change_password, csrf, demo_login, health, register, session_login, session_logout

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("project-tasks", ProjectTaskViewSet, basename="project-task")
router.register("materials", MaterialViewSet, basename="material")
router.register("material-revisions", MaterialRevisionViewSet, basename="material-revision")
router.register("material-attachments", MaterialAttachmentViewSet, basename="material-attachment")
router.register("upload-sessions", UploadSessionViewSet, basename="upload-session")
router.register("templates", TemplateViewSet, basename="template")
router.register("public-case-requests", PublicCaseRequestViewSet, basename="public-case-request")
router.register("ai-logs", AIGenerationLogViewSet, basename="ai-log")
router.register("ai-conversations", AIConversationViewSet, basename="ai-conversation")
router.register("ai-agents", AgentTemplateViewSet, basename="ai-agent")
router.register("report-exports", ReportExportViewSet, basename="report-export")
router.register("competitions", CompetitionViewSet, basename="competition")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("schools", SchoolViewSet, basename="school")
router.register("member-invitations", MemberInvitationViewSet, basename="member-invitation")
router.register("notifications", NotificationViewSet, basename="notification")
urlpatterns = [
    path("me/", MeView.as_view()),
    path("accounts/students/", StudentDirectoryView.as_view()),
    path("health/", health),
    path("service-status/", ServiceStatusView.as_view()),
    path("platform-ai-config/", PlatformAIConfigurationView.as_view()),
    path("ai-availability/", AIAvailabilityView.as_view()),
    path("csrf/", csrf),
    path("login/", session_login),
    path("logout/", session_logout),
    path("demo-login/", demo_login),
    path("register/", register),
    path("change-password/", change_password),
] + router.urls

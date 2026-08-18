from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.core.models import Account, AuditEvent, School


class PlatformConfigurationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="配置学校", license_expires_at=date.today() + timedelta(days=365))
        self.platform = Account.objects.create_user(username="configuration-platform", role=Account.Role.PLATFORM_ADMIN)
        self.teacher = Account.objects.create_user(username="configuration-teacher", school=self.school, role=Account.Role.TEACHER)

    def test_platform_can_read_non_secret_service_status(self):
        client = APIClient(); client.force_authenticate(self.platform)
        response = client.get("/api/service-status/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("database", response.data)
        self.assertIn("ai", response.data)
        self.assertIn("task_queue", response.data)
        self.assertNotIn("OPENAI_API_KEY", str(response.data))
        self.assertNotIn("password", str(response.data).lower())

    @patch("apps.core.views.requests.get")
    @patch("apps.core.views.redis.Redis.from_url")
    @patch("apps.core.views.clamd.ClamdNetworkSocket")
    def test_service_status_checks_reachable_dependencies_without_exposing_connection_details(self, scanner, redis_client, get):
        redis_client.return_value.ping.return_value = True
        scanner.return_value.ping.return_value = "PONG"
        get.return_value.raise_for_status.return_value = None
        client = APIClient(); client.force_authenticate(self.platform)

        response = client.get("/api/service-status/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["task_queue"], "healthy")
        self.assertEqual(response.data["virus_scan"], "healthy")
        self.assertEqual(response.data["document_converter"], "healthy")
        self.assertNotIn("redis://", str(response.data))

    def test_school_configuration_is_not_visible_to_teacher(self):
        client = APIClient(); client.force_authenticate(self.teacher)
        self.assertEqual(client.get("/api/service-status/").status_code, 403)

    def test_school_configuration_changes_are_audited_without_sensitive_values(self):
        client = APIClient(); client.force_authenticate(self.platform)

        update = client.patch(
            f"/api/schools/{self.school.id}/",
            {"ai_quota": 240, "storage_quota_mb": 20480, "is_active": False},
            format="json",
        )
        reset = client.post(f"/api/schools/{self.school.id}/reset_invite_code/")
        events = client.get(f"/api/schools/{self.school.id}/audit-events/")

        self.assertEqual(update.status_code, 200)
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(events.status_code, 200)
        self.assertEqual([event["action"] for event in events.data], ["invite_code_reset", "school_updated"])
        self.assertEqual(events.data[1]["changes"], {"is_active": False, "ai_quota": 240, "storage_quota_mb": 20480})
        self.assertNotIn(reset.data["invite_code"], str(events.data))
        self.assertEqual(AuditEvent.objects.filter(school=self.school, actor=self.platform).count(), 2)

    def test_platform_rejects_string_boolean_values_when_updating_school_authorization(self):
        client = APIClient(); client.force_authenticate(self.platform)

        response = client.patch(
            f"/api/schools/{self.school.id}/", {"is_active": "false"}, format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.school.refresh_from_db()
        self.assertTrue(self.school.is_active)

    def test_platform_can_create_school_without_explicit_authorization_flag(self):
        client = APIClient(); client.force_authenticate(self.platform)

        response = client.post("/api/schools/", {"name": "默认授权学校"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["is_active"])

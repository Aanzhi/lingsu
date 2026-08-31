from datetime import date, timedelta

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
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

    @override_settings(ATTACHMENT_UPLOADS_ENABLED=False, PDF_EXPORT_ENABLED=False)
    def test_health_declares_disabled_core_deployment_capabilities(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["capabilities"], {"attachments": False, "pdf_export": False})

    @override_settings(CLAMAV_ENABLED=True, CLAMAV_HOST="clamav")
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

    def test_platform_can_read_masked_ai_configuration_without_plaintext(self):
        client = APIClient(); client.force_authenticate(self.platform)
        with override_settings(AI_CONFIG_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            response = client.put(
                "/api/platform-ai-config/",
                {
                    "api_key": "sk-live-1234567890-END",
                    "model": "deepseek-v4-flash-260425",
                    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["masked_key"], "sk-l********-END")
            self.assertEqual(response.data["model"], "deepseek-v4-flash-260425")
            self.assertEqual(response.data["base_url"], "https://ark.cn-beijing.volces.com/api/v3")
            self.assertNotIn("sk-live-1234567890-END", str(response.data))
            self.assertNotIn("encrypted_api_key", response.data)

            read = client.get("/api/platform-ai-config/")
            self.assertEqual(read.status_code, 200)
            self.assertEqual(read.data["masked_key"], "sk-l********-END")
            self.assertEqual(read.data["model"], "deepseek-v4-flash-260425")
            self.assertEqual(read.data["base_url"], "https://ark.cn-beijing.volces.com/api/v3")
            self.assertNotIn("sk-live-1234567890-END", str(read.data))

    def test_platform_can_update_provider_settings_without_resubmitting_existing_key(self):
        client = APIClient(); client.force_authenticate(self.platform)
        encryption_key = Fernet.generate_key().decode()
        with override_settings(AI_CONFIG_ENCRYPTION_KEY=encryption_key):
            first = client.put(
                "/api/platform-ai-config/",
                {
                    "api_key": "sk-live-1234567890-END",
                    "model": "deepseek-v4-flash-260425",
                    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                },
                format="json",
            )
            second = client.put(
                "/api/platform-ai-config/",
                {"api_key": "", "model": "new-model", "base_url": "https://example.test/v1"},
                format="json",
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["masked_key"], first.data["masked_key"])
        self.assertEqual(second.data["model"], "new-model")
        self.assertEqual(second.data["base_url"], "https://example.test/v1")
        record = self.platform.updated_platform_ai_configurations.get(key="default")
        self.assertEqual(Fernet(encryption_key).decrypt(record.encrypted_api_key.encode()).decode(), "sk-live-1234567890-END")

    def test_platform_can_persist_provider_settings_using_existing_environment_key(self):
        client = APIClient(); client.force_authenticate(self.platform)
        encryption_key = Fernet.generate_key().decode()
        with override_settings(
            AI_CONFIG_ENCRYPTION_KEY=encryption_key,
            OPENAI_API_KEY="sk-env-fallback",
            OPENAI_MODEL="env-model",
            OPENAI_BASE_URL="https://env.example/v1",
        ):
            response = client.put(
                "/api/platform-ai-config/",
                {"api_key": "", "model": "db-model", "base_url": "https://db.example/v1"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["masked_key"], "sk-e********back")
        record = self.platform.updated_platform_ai_configurations.get(key="default")
        self.assertEqual(Fernet(encryption_key).decrypt(record.encrypted_api_key.encode()).decode(), "sk-env-fallback")
        self.assertEqual(record.model, "db-model")
        self.assertEqual(record.base_url, "https://db.example/v1")

    def test_platform_rejects_empty_model_and_non_http_provider_url(self):
        client = APIClient(); client.force_authenticate(self.platform)
        with override_settings(AI_CONFIG_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            empty_model = client.put(
                "/api/platform-ai-config/",
                {"api_key": "sk-test", "model": "", "base_url": "https://example.test/v1"},
                format="json",
            )
            invalid_url = client.put(
                "/api/platform-ai-config/",
                {"api_key": "sk-test", "model": "test-model", "base_url": "ftp://example.test/v1"},
                format="json",
            )

        self.assertEqual(empty_model.status_code, 400)
        self.assertIn("model", empty_model.data)
        self.assertEqual(invalid_url.status_code, 400)
        self.assertIn("base_url", invalid_url.data)

    def test_non_platform_accounts_cannot_read_or_write_ai_configuration(self):
        client = APIClient(); client.force_authenticate(self.teacher)
        self.assertEqual(client.get("/api/platform-ai-config/").status_code, 403)
        self.assertEqual(
            client.put("/api/platform-ai-config/", {"api_key": "sk-denied"}, format="json").status_code,
            403,
        )

    @override_settings(AI_CONFIG_ENCRYPTION_KEY="")
    def test_platform_gets_actionable_error_when_encryption_key_is_missing(self):
        client = APIClient(); client.force_authenticate(self.platform)
        response = client.put(
            "/api/platform-ai-config/",
            {
                "api_key": "sk-no-encryption",
                "model": "test-model",
                "base_url": "https://example.test/v1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 503)

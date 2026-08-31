from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.core.ai_config import AIConfigError, get_ai_configuration_state, get_configured_ai_api_key, mask_ai_api_key, save_configured_ai_api_key
from apps.core.models import Account, PlatformAIConfiguration


class AIConfigServiceTests(TestCase):
    def setUp(self):
        self.actor = Account.objects.create_user(
            username="ai-config-admin",
            role=Account.Role.PLATFORM_ADMIN,
        )
        self.fernet_key = Fernet.generate_key().decode()

    def test_mask_keeps_only_the_first_and_last_four_characters(self):
        self.assertEqual(mask_ai_api_key("sk-proj-0123456789-END"), "sk-p********-END")

    def test_short_or_empty_values_never_echo_secret_characters(self):
        self.assertEqual(mask_ai_api_key("12345678"), "********")
        self.assertEqual(mask_ai_api_key(""), "")

    @override_settings(AI_CONFIG_ENCRYPTION_KEY="")
    def test_save_requires_an_independent_encryption_key(self):
        with self.assertRaises(AIConfigError):
            save_configured_ai_api_key("sk-secret", self.actor)
        self.assertFalse(PlatformAIConfiguration.objects.exists())

    @override_settings(AI_CONFIG_ENCRYPTION_KEY="")
    def test_environment_value_is_fallback_when_database_has_no_record(self):
        with override_settings(OPENAI_API_KEY="sk-env-fallback"):
            self.assertEqual(get_configured_ai_api_key(), "sk-env-fallback")
            self.assertEqual(get_ai_configuration_state()["masked_key"], "sk-e********back")

    def test_database_value_wins_over_environment_value(self):
        with override_settings(
            AI_CONFIG_ENCRYPTION_KEY=self.fernet_key,
            OPENAI_API_KEY="sk-env-fallback",
        ):
            save_configured_ai_api_key("sk-db-secret-value", self.actor)
            self.assertEqual(get_configured_ai_api_key(), "sk-db-secret-value")
            self.assertEqual(get_ai_configuration_state()["masked_key"], "sk-d********alue")
            record = PlatformAIConfiguration.objects.get(key="default")
            self.assertNotIn("sk-db-secret-value", record.encrypted_api_key)

from django.test import SimpleTestCase, override_settings


class RuntimeConfigurationTests(SimpleTestCase):
    def test_local_development_trusts_both_loopback_hostnames(self):
        from django.conf import settings

        origins = settings.CSRF_TRUSTED_ORIGINS
        self.assertTrue(any(origin.startswith("http://localhost:") for origin in origins))
        self.assertTrue(any(origin.startswith("http://127.0.0.1:") for origin in origins))

    @override_settings(DEBUG=False)
    def test_clickjacking_middleware_is_installed_for_production(self):
        from django.conf import settings

        self.assertIn("django.middleware.clickjacking.XFrameOptionsMiddleware", settings.MIDDLEWARE)

    def test_static_files_are_served_by_whitenoise_behind_reverse_proxy(self):
        from django.conf import settings

        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE)
        self.assertEqual(
            settings.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )

    def test_ai_provider_base_url_is_optional_and_not_a_secret(self):
        from django.conf import settings

        self.assertTrue(hasattr(settings, "OPENAI_BASE_URL"))
        self.assertIsInstance(settings.OPENAI_BASE_URL, str)
        self.assertNotIn("KEY", settings.OPENAI_BASE_URL.upper())

    @override_settings(OPENAI_API_KEY="configured")
    def test_openai_key_setting_is_available_to_the_client(self):
        from django.conf import settings

        self.assertEqual(settings.OPENAI_API_KEY, "configured")

    def test_cookie_security_can_be_disabled_only_by_explicit_environment_override(self):
        from config import settings as project_settings

        self.assertIn('DJANGO_SESSION_COOKIE_SECURE', project_settings.COOKIE_SECURITY_ENV_NAMES)
        self.assertIn('DJANGO_CSRF_COOKIE_SECURE', project_settings.COOKIE_SECURITY_ENV_NAMES)

    @override_settings(DEBUG=False, FILE_SCAN_REQUIRED=False, CLAMAV_HOST="")
    def test_production_configuration_rejects_missing_file_scanner(self):
        from apps.core.checks import production_file_scanner_check

        messages = production_file_scanner_check(None)

        self.assertIn("core.E001", [message.id for message in messages])

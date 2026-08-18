from django.test import SimpleTestCase

from config.storage import build_storage_settings


class StorageConfigurationTests(SimpleTestCase):
    def test_local_private_storage_remains_default(self):
        storages, options = build_storage_settings({"STORAGE_BACKEND": "local"})

        self.assertEqual(storages["default"]["BACKEND"], "django.core.files.storage.FileSystemStorage")
        self.assertEqual(options, {})

    def test_s3_storage_is_private_and_supports_minio_endpoint(self):
        storages, options = build_storage_settings({
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET_NAME": "lingsu-private",
            "S3_ENDPOINT_URL": "http://minio:9000",
            "S3_ACCESS_KEY_ID": "access",
            "S3_SECRET_ACCESS_KEY": "secret",
            "S3_REGION_NAME": "us-east-1",
        })

        self.assertEqual(storages["default"]["BACKEND"], "storages.backends.s3.S3Storage")
        self.assertEqual(options["AWS_STORAGE_BUCKET_NAME"], "lingsu-private")
        self.assertEqual(options["AWS_S3_ENDPOINT_URL"], "http://minio:9000")
        self.assertIsNone(options["AWS_DEFAULT_ACL"])
        self.assertTrue(options["AWS_QUERYSTRING_AUTH"])
        self.assertFalse(options["AWS_S3_FILE_OVERWRITE"])

    def test_s3_configuration_requires_bucket_and_credentials(self):
        with self.assertRaisesMessage(ValueError, "S3_BUCKET_NAME"):
            build_storage_settings({"STORAGE_BACKEND": "s3"})


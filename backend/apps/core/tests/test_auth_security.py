from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Account, School


class AuthSecurityTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="安全学校", invite_code="SECURE")
        Account.objects.create_user(
            username="csrf-user", password="correct-pass-123", school=self.school, role="student",
        )

    def test_login_and_registration_require_an_explicit_csrf_handshake(self):
        client = APIClient(enforce_csrf_checks=True)
        blocked_login = client.post(
            "/api/login/", {"username": "csrf-user", "password": "correct-pass-123"}, format="json",
        )
        blocked_register = client.post("/api/register/", {
            "invite_code": "SECURE", "role": "student", "username": "csrf-new",
            "password": "correct-pass-456", "display_name": "CSRF 新用户",
        }, format="json")
        handshake = client.get("/api/csrf/")
        token = handshake.cookies["csrftoken"].value
        accepted_login = client.post(
            "/api/login/", {"username": "csrf-user", "password": "correct-pass-123"},
            format="json", HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(blocked_login.status_code, 403)
        self.assertEqual(blocked_register.status_code, 403)
        self.assertEqual(handshake.status_code, 200)
        self.assertEqual(accepted_login.status_code, 200)

    def test_registration_rejects_common_or_short_passwords(self):
        client = APIClient()
        response = client.post("/api/register/", {
            "invite_code": "SECURE", "role": "student", "username": "weak-user",
            "password": "12345678", "display_name": "弱密码",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_change_password_requires_correct_old_password_and_updates_flag(self):
        user = Account.objects.get(username="csrf-user")
        client = APIClient()
        client.force_authenticate(user)

        wrong_old = client.post("/api/change-password/", {
            "old_password": "wrong", "new_password": "new-pass-789", "confirm_password": "new-pass-789",
        }, format="json")
        self.assertEqual(wrong_old.status_code, 400)

        mismatch = client.post("/api/change-password/", {
            "old_password": "correct-pass-123", "new_password": "new-pass-789", "confirm_password": "other",
        }, format="json")
        self.assertEqual(mismatch.status_code, 400)

        ok = client.post("/api/change-password/", {
            "old_password": "correct-pass-123", "new_password": "new-pass-789", "confirm_password": "new-pass-789",
        }, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(ok.data["must_change_password"])

        user.refresh_from_db()
        self.assertTrue(user.check_password("new-pass-789"))
        self.assertFalse(user.must_change_password)

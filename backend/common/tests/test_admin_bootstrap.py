from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from common.admin_bootstrap import KNOWN_ADMIN_EMAILS
from services.university_service.models import University

User = get_user_model()

PASSWORD = "Strong-Development-Password-842!"


class BootstrapAdminsCommandTests(APITestCase):
    def run_bootstrap(self) -> str:
        out = StringIO()
        call_command("bootstrap_admins", stdout=out)
        return out.getvalue()

    def test_promotes_existing_allowlisted_user(self):
        email = KNOWN_ADMIN_EMAILS[0]
        user = User.objects.create_user(
            username=email,
            email=email.upper(),  # matched case-insensitively
            password=PASSWORD,
            role=User.Role.STUDENT,
        )

        output = self.run_bootstrap()

        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(PASSWORD))  # password untouched
        self.assertIn("promoted:", output)

    def test_is_idempotent(self):
        email = KNOWN_ADMIN_EMAILS[0]
        User.objects.create_user(
            username=email, email=email, password=PASSWORD, role=User.Role.STUDENT
        )

        self.run_bootstrap()
        second_output = self.run_bootstrap()

        user = User.objects.get(email__iexact=email)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertIn("already_admin:", second_output)

    def test_missing_users_do_not_crash_and_create_nothing(self):
        output = self.run_bootstrap()

        self.assertIn("missing:", output)
        self.assertEqual(User.objects.count(), 0)

    def test_promoted_admin_can_access_import_endpoint(self):
        email = KNOWN_ADMIN_EMAILS[1]
        user = User.objects.create_user(
            username=email, email=email, password=PASSWORD, role=User.Role.STUDENT
        )
        self.run_bootstrap()
        user.refresh_from_db()

        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("university-import:job-detail", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 404)


class SeedDemoStartupSafetyTests(APITestCase):
    def test_default_mode_does_not_touch_university_table(self):
        email = KNOWN_ADMIN_EMAILS[0]
        user = User.objects.create_user(
            username=email, email=email, password=PASSWORD, role=User.Role.STUDENT
        )

        call_command("seed_demo", stdout=StringIO())  # no --with-demo-data

        # Production-safe default: no university (or other heavy) rows are written...
        self.assertEqual(University.objects.count(), 0)
        # ...but allow-listed operators are still promoted.
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)

    def test_with_demo_data_flag_seeds_universities(self):
        call_command("seed_demo", "--with-demo-data", stdout=StringIO())
        self.assertGreater(University.objects.count(), 0)

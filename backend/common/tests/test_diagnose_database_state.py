from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from common.management.commands.diagnose_database_state import (
    detect_supabase_ref,
    mask_email,
    sanitize_host,
)

User = get_user_model()


class DiagnoseDatabaseStateHelperTests(TestCase):
    def test_sanitize_host_masks_supabase_host_but_keeps_suffix(self):
        sanitized = sanitize_host("db.zhipvgmchntayiyuafdk.supabase.co")
        self.assertIn("supabase.co", sanitized)
        self.assertNotIn("zhipvgmchntayiyuafdk", sanitized)

    def test_detect_supabase_ref_from_direct_host(self):
        ref = detect_supabase_ref("db.zhipvgmchntayiyuafdk.supabase.co", "postgres")
        self.assertEqual(ref, "zhipvgmchntayiyuafdk")

    def test_detect_supabase_ref_from_pooler_username(self):
        ref = detect_supabase_ref(
            "aws-0-eu-central-1.pooler.supabase.com", "postgres.zhipvgmchntayiyuafdk"
        )
        self.assertEqual(ref, "zhipvgmchntayiyuafdk")

    def test_detect_supabase_ref_absent_for_other_hosts(self):
        self.assertIsNone(detect_supabase_ref("db.example.com", "uniway"))

    def test_mask_email_hides_most_of_local_part(self):
        self.assertEqual(mask_email("timarus52111@gmail.com"), "ti***@gmail.com")


class DiagnoseDatabaseStateCommandTests(TestCase):
    def _run(self, *args) -> str:
        out = StringIO()
        call_command("diagnose_database_state", *args, stdout=out)
        return out.getvalue()

    def test_reports_tables_counts_and_no_secrets(self):
        output = self._run()
        self.assertIn("vendor:", output)
        self.assertIn("django_migrations exists: True", output)
        self.assertIn("auth_service_user exists: True", output)
        self.assertIn("total users: 0", output)
        self.assertIn("StudentProfile rows: 0", output)
        self.assertIn("ApplicationTrackerItem rows: 0", output)
        self.assertIn("EssayWorkspace rows: 0", output)
        self.assertIn("SavedUniversity rows: 0", output)
        self.assertIn("RoadmapTask rows: 0", output)
        self.assertIn("no writes were performed", output)
        # Secrets must never appear -- not the password key nor a raw URL.
        self.assertNotIn("PASSWORD", output)
        self.assertNotIn("postgresql://", output)
        self.assertNotIn("sqlite:///", output)

    def test_target_email_lookup_reports_found_and_missing(self):
        missing = self._run("--email", "someone@example.com")
        self.assertIn("target email (so***@example.com) found: False", missing)

        User.objects.create_user(
            username="audituser", email="someone@example.com", password="testpass123"
        )
        found = self._run("--email", "SOMEONE@example.com")
        self.assertIn("found: True", found)

    def test_command_performs_no_writes(self):
        User.objects.create_user(
            username="keepme", email="keepme@example.com", password="testpass123"
        )
        before = User.objects.count()
        self._run()
        self.assertEqual(User.objects.count(), before)

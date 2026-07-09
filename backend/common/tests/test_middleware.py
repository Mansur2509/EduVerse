from django.test import TestCase, override_settings
from django.urls import reverse


class RequestTimingMiddlewareTests(TestCase):
    @override_settings(SLOW_REQUEST_THRESHOLD_MS=0)
    def test_slow_request_logs_warning_with_duration_and_path(self):
        with self.assertLogs("common.middleware", level="WARNING") as captured:
            response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        log_line = "\n".join(captured.output)
        self.assertIn("path=/api/v1/health/", log_line)
        self.assertIn("duration_ms=", log_line)
        self.assertIn("status=200", log_line)

    def test_fast_request_does_not_log_at_warning(self):
        with self.assertLogs("common.middleware", level="DEBUG") as captured:
            self.client.get(reverse("health"))

        log_line = "\n".join(captured.output)
        self.assertNotIn("WARNING", log_line)

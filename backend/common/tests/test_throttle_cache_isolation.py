from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle


@patch.dict(SimpleRateThrottle.THROTTLE_RATES, {"auth_refresh": "1/hour"})
class ThrottleCacheIsolationRegressionTests(APITestCase):
    """Regression test for a bug where DRF throttle counters (stored in
    Django's cache, which test transaction rollback never resets) leaked
    between unrelated test methods. `ScopedRateThrottle`/`ScopedIPRateThrottle`
    key their cache entry by client IP for anonymous requests, and the Django
    test client always uses the same IP, so one test's throttled request
    silently consumed quota that a later, unrelated test then paid for with
    an unexpected 429. Test methods run in alphabetical order within a
    class, so "test_a_..." runs before "test_b_...". See common/apps.py's
    _patch_test_cache_isolation for the fix: the cache is cleared after
    every test method.
    """

    def test_a_consumes_the_single_allowed_request_this_hour(self):
        response = self.client.post(reverse("auth:token-refresh"), {}, format="json")
        self.assertNotEqual(response.status_code, 429)

    def test_b_is_not_throttled_by_the_previous_tests_request(self):
        response = self.client.post(reverse("auth:token-refresh"), {}, format="json")
        self.assertNotEqual(response.status_code, 429)

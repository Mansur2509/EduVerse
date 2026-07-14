from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"

    def ready(self):
        _patch_test_cache_isolation()


def _patch_test_cache_isolation() -> None:
    """Clear every cache after each Django test method finishes.

    DRF's ScopedRateThrottle/ScopedIPRateThrottle store request counters in
    Django's cache framework. Test-case transaction rollback resets the
    database between tests but never touches the cache, so throttle quota
    consumed by one test -- especially the IP-keyed throttle, whose cache key
    is identical for every request the Django test client makes -- silently
    carries over into unrelated later tests and can turn a legitimate
    request into a 429. `SimpleTestCase._post_teardown` runs after every
    single test method for every Django/DRF test case and is never invoked
    outside the test runner, so patching it here is inert in normal
    request handling.
    """
    from django.test import SimpleTestCase

    if getattr(SimpleTestCase, "_uniway_cache_isolation_patched", False):
        return

    original_post_teardown = SimpleTestCase._post_teardown

    def _post_teardown(self, *args, **kwargs):
        original_post_teardown(self, *args, **kwargs)
        from django.core.cache import caches

        for cache in caches.all():
            cache.clear()

    SimpleTestCase._post_teardown = _post_teardown
    SimpleTestCase._uniway_cache_isolation_patched = True


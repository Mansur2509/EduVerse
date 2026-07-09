import logging
import time

from django.conf import settings

logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    """Logs every request's duration; WARNING-level when it exceeds
    `settings.SLOW_REQUEST_THRESHOLD_MS`, so a slow endpoint (N+1 query,
    missing cache, external call) shows up in production logs the same way
    the AI call paths already log their own duration_ms.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - started_at) * 1000)

        log_level = logging.WARNING if duration_ms >= settings.SLOW_REQUEST_THRESHOLD_MS else logging.DEBUG
        logger.log(
            log_level,
            "HTTP request method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response

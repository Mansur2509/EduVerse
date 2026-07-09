"""Startup guard: catch the CORS/CSRF/ALLOWED_HOSTS misconfigurations that
fail silently instead of loudly.

A trailing slash or path on a CORS/CSRF origin, or a protocol prefix on an
ALLOWED_HOSTS entry, does not raise anywhere in Django -- the origin/host
simply never matches, and the symptom is a confusing "CORS blocked" or
"DisallowedHost" error in production with no indication of the actual typo.
Raising ImproperlyConfigured at settings-import time turns that into a loud,
immediate deploy error instead. Mirrors `database_guard.py`'s pattern: exempt
in local development (DEBUG=true) so `runserver` never needs extra env vars.
"""

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured


def _looks_like_host_with_protocol(host: str) -> bool:
    return "://" in host


def _looks_like_origin_with_trailing_slash_or_path(origin: str) -> bool:
    without_scheme = origin.split("://", 1)[-1]
    return "/" in without_scheme


def _looks_like_origin_missing_protocol(origin: str) -> bool:
    return "://" not in origin


def validate_deploy_config(
    *, debug: bool, allowed_hosts: list[str], cors_allowed_origins: list[str], csrf_trusted_origins: list[str]
) -> None:
    """Raise ImproperlyConfigured for common production env-var format bugs.

    Local development (debug=True) is exempt so a developer's own localhost
    entries -- which legitimately have no protocol requirement issue here --
    never block `runserver`.
    """

    if debug:
        return

    bad_hosts = [host for host in allowed_hosts if _looks_like_host_with_protocol(host)]
    if bad_hosts:
        raise ImproperlyConfigured(
            f"DJANGO_ALLOWED_HOSTS contains a value with a protocol prefix: {bad_hosts!r}. "
            "ALLOWED_HOSTS entries are bare hostnames only, e.g. "
            "\"eduverse-vvw2.onrender.com,uni-way-beta.vercel.app\" -- remove the \"https://\"."
        )

    bad_cors = [
        origin
        for origin in cors_allowed_origins
        if _looks_like_origin_missing_protocol(origin) or _looks_like_origin_with_trailing_slash_or_path(origin)
    ]
    if bad_cors:
        raise ImproperlyConfigured(
            f"CORS_ALLOWED_ORIGINS contains a malformed origin: {bad_cors!r}. Each origin needs a "
            "protocol and no trailing slash or path, e.g. \"https://uni-way-beta.vercel.app\" -- "
            "a trailing slash or missing scheme means the origin will never match a real request "
            "and the browser will silently block every cross-origin call."
        )

    bad_csrf = [
        origin
        for origin in csrf_trusted_origins
        if _looks_like_origin_missing_protocol(origin) or _looks_like_origin_with_trailing_slash_or_path(origin)
    ]
    if bad_csrf:
        raise ImproperlyConfigured(
            f"CSRF_TRUSTED_ORIGINS contains a malformed origin: {bad_csrf!r}. Each origin needs a "
            "protocol and no trailing slash or path, e.g. \"https://uni-way-beta.vercel.app\"."
        )

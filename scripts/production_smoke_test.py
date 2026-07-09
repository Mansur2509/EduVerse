#!/usr/bin/env python3
"""Production smoke test for the UniWay backend.

Hits a small set of real endpoints against a live deployment and reports
status code, response time, and pass/fail against a per-endpoint threshold.
Never prints the access token -- only whether one was supplied.

Usage:
    python scripts/production_smoke_test.py --base-url https://eduverse-vvw2.onrender.com
    python scripts/production_smoke_test.py --base-url https://eduverse-vvw2.onrender.com --access-token "***"

Without --access-token, only the public health check runs. With a token,
the four authenticated cached-read endpoints are also checked. This script
never logs in, creates, or mutates anything -- every request is a GET.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class Check:
    name: str
    path: str
    threshold_seconds: float
    requires_auth: bool


CHECKS: tuple[Check, ...] = (
    Check("health", "/api/v1/health/", threshold_seconds=2.0, requires_auth=False),
    Check(
        "profile_assessment_cached",
        "/api/v1/profile-assessment/me/",
        threshold_seconds=5.0,
        requires_auth=True,
    ),
    Check(
        "recommendations_cached",
        "/api/v1/recommendations/me/",
        threshold_seconds=5.0,
        requires_auth=True,
    ),
    Check("strategy_cached", "/api/v1/strategy/me/", threshold_seconds=5.0, requires_auth=True),
    Check(
        "university_list",
        "/api/v1/universities/?page=1&page_size=5",
        threshold_seconds=5.0,
        requires_auth=True,
    ),
)


@dataclass(frozen=True)
class CheckResult:
    check: Check
    status_code: int | None
    duration_seconds: float
    error: str | None

    @property
    def passed(self) -> bool:
        if self.error is not None:
            return False
        if self.status_code is None or self.status_code >= 400:
            return False
        return self.duration_seconds <= self.check.threshold_seconds


def run_check(base_url: str, check: Check, *, access_token: str | None) -> CheckResult:
    url = base_url.rstrip("/") + check.path
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    request = urllib.request.Request(url, headers=headers, method="GET")
    started_at = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            response.read()
            duration = time.monotonic() - started_at
            return CheckResult(check=check, status_code=response.status, duration_seconds=duration, error=None)
    except urllib.error.HTTPError as error:
        duration = time.monotonic() - started_at
        return CheckResult(check=check, status_code=error.code, duration_seconds=duration, error=None)
    except urllib.error.URLError as error:
        duration = time.monotonic() - started_at
        return CheckResult(check=check, status_code=None, duration_seconds=duration, error=str(error.reason))
    except TimeoutError:
        duration = time.monotonic() - started_at
        return CheckResult(check=check, status_code=None, duration_seconds=duration, error="request timed out")


def print_result(result: CheckResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    status_code = result.status_code if result.status_code is not None else "n/a"
    detail = f" ({result.error})" if result.error else ""
    print(
        f"[{status}] {result.check.name:<28} status={status_code:<5} "
        f"duration={result.duration_seconds:.2f}s threshold={result.check.threshold_seconds:.1f}s{detail}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="e.g. https://eduverse-vvw2.onrender.com")
    parser.add_argument(
        "--access-token",
        default=None,
        help="Optional bearer token; enables the authenticated checks. Never printed.",
    )
    args = parser.parse_args()

    has_token = bool(args.access_token)
    print(f"Base URL: {args.base_url}")
    print(f"Access token supplied: {has_token}")
    print()

    results: list[CheckResult] = []
    for check in CHECKS:
        if check.requires_auth and not has_token:
            print(f"[SKIP] {check.name:<28} (no --access-token supplied)")
            continue
        result = run_check(args.base_url, check, access_token=args.access_token)
        results.append(result)
        print_result(result)

    print()
    failed = [result for result in results if not result.passed]
    if failed:
        print(f"{len(failed)} of {len(results)} check(s) failed.")
        return 1

    print(f"All {len(results)} check(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

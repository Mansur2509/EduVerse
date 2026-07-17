from __future__ import annotations

import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from services.university_service.models import University, UniversityFieldVerification

# Wikipedia's public REST API -- not a scraper, not a third-party image
# search. `thumbnail.source` is Wikipedia's own editorially-curated lead
# image for the article, typically hosted on Wikimedia Commons under a free
# license. This is the only source this command is allowed to write from;
# see the "Real, attributed imagery only" comment on University.cover_image_url.
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
REQUEST_TIMEOUT_SECONDS = 10
FIELD_NAME = "cover_image_url"
# Wikipedia's REST API returns 403 for the default `python-requests/x.y` user
# agent -- per their robot policy (https://w.wiki/4wJS) a descriptive,
# attributable user agent identifying the application is required.
REQUEST_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "UniWay-CoverImageFetcher/1.0 (https://github.com/Mansur2509/UniWay; contact via repository issues)",
}


class Command(BaseCommand):
    help = (
        "Populate University.cover_image_url from Wikipedia's REST API summary "
        "endpoint for published, non-demo universities that don't have one yet. "
        "Only ever writes an image when the returned Wikipedia article title "
        "matches the university name exactly (case-insensitive) -- this is a "
        "safety gate against attaching the wrong institution's image. Dry-run "
        "by default; pass --commit to write."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually write cover_image_url and the source verification row.",
        )
        parser.add_argument(
            "--slug",
            default=None,
            help="Optional single university slug to process instead of the full catalog.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Also re-fetch universities that already have a cover_image_url.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        queryset = University.objects.filter(is_published=True, is_demo=False)
        if options["slug"]:
            queryset = queryset.filter(slug=options["slug"])
        if not options["overwrite"]:
            queryset = queryset.filter(cover_image_url="")

        universities = list(queryset.order_by("name"))
        if not universities:
            self.stdout.write("No universities need a cover image fetch.")
            return

        matched = 0
        skipped = 0
        for university in universities:
            result = self._fetch_summary(university.name)
            if result is None:
                skipped += 1
                self.stdout.write(f"[skip] {university.name}: no Wikipedia summary found.")
                continue

            title, thumbnail_url, article_url = result
            if title.strip().casefold() != university.name.strip().casefold():
                skipped += 1
                self.stdout.write(
                    f"[skip] {university.name}: Wikipedia title \"{title}\" does not "
                    "match exactly -- refusing to guess."
                )
                continue
            if not thumbnail_url:
                skipped += 1
                self.stdout.write(f"[skip] {university.name}: matched page has no thumbnail image.")
                continue

            matched += 1
            self.stdout.write(f"[match] {university.name}: {thumbnail_url}")
            if not commit:
                continue

            university.cover_image_url = thumbnail_url
            university.cover_image_source_title = f"Wikipedia — {title}"
            university.cover_image_source_url = article_url
            university.cover_image_retrieved_at = timezone.now()
            university.save(
                update_fields=[
                    "cover_image_url",
                    "cover_image_source_title",
                    "cover_image_source_url",
                    "cover_image_retrieved_at",
                ]
            )
            UniversityFieldVerification.objects.update_or_create(
                university=university,
                field_name=FIELD_NAME,
                defaults={
                    "status": UniversityFieldVerification.Status.PARTIAL,
                    "source_url": article_url,
                    "last_verified_date": datetime.date.today(),
                    "note": (
                        "Image sourced from Wikipedia's REST API summary endpoint "
                        "(Wikimedia Commons-hosted); may be an institutional seal or "
                        "crest rather than campus photography."
                    ),
                },
            )

        mode = "committed" if commit else "dry-run, use --commit to write"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done ({mode}): {matched} matched, {skipped} skipped, "
                f"{len(universities)} considered."
            )
        )

    def _fetch_summary(self, name: str) -> tuple[str, str | None, str] | None:
        encoded_title = name.strip().replace(" ", "_")
        url = WIKIPEDIA_SUMMARY_URL.format(title=encoded_title)
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers=REQUEST_HEADERS)
        except requests.RequestException:
            return None
        if response.status_code != 200:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None

        title = payload.get("title")
        if not isinstance(title, str) or not title:
            return None
        thumbnail = payload.get("thumbnail") or {}
        thumbnail_url = thumbnail.get("source") if isinstance(thumbnail, dict) else None
        content_urls = payload.get("content_urls") or {}
        desktop = content_urls.get("desktop") if isinstance(content_urls, dict) else {}
        article_url = desktop.get("page") if isinstance(desktop, dict) else None
        if not article_url:
            return None
        return title, thumbnail_url, article_url

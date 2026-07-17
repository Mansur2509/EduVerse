from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase

from services.university_service.models import University, UniversityFieldVerification


def _summary_response(title, thumbnail_source=None, page_url="https://en.wikipedia.org/wiki/X"):
    response = Mock()
    response.status_code = 200
    payload = {
        "title": title,
        "content_urls": {"desktop": {"page": page_url}},
    }
    if thumbnail_source:
        payload["thumbnail"] = {"source": thumbnail_source}
    response.json.return_value = payload
    return response


class FetchUniversityCoverImagesTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            slug="exact-match-university",
            name="Exact Match University",
            country="United States",
            official_website="https://example.com",
            is_published=True,
            is_demo=False,
        )

    @patch("services.university_service.management.commands.fetch_university_cover_images.requests.get")
    def test_exact_title_match_with_commit_writes_image_and_verification(self, mock_get):
        mock_get.return_value = _summary_response(
            "Exact Match University",
            thumbnail_source="https://upload.wikimedia.org/example.png",
            page_url="https://en.wikipedia.org/wiki/Exact_Match_University",
        )

        call_command("fetch_university_cover_images", "--commit")

        self.university.refresh_from_db()
        self.assertEqual(self.university.cover_image_url, "https://upload.wikimedia.org/example.png")
        self.assertEqual(self.university.cover_image_source_title, "Wikipedia — Exact Match University")
        self.assertEqual(
            self.university.cover_image_source_url,
            "https://en.wikipedia.org/wiki/Exact_Match_University",
        )
        self.assertIsNotNone(self.university.cover_image_retrieved_at)
        verification = UniversityFieldVerification.objects.get(
            university=self.university, field_name="cover_image_url"
        )
        self.assertEqual(verification.status, UniversityFieldVerification.Status.PARTIAL)

    @patch("services.university_service.management.commands.fetch_university_cover_images.requests.get")
    def test_dry_run_matches_but_does_not_write(self, mock_get):
        mock_get.return_value = _summary_response(
            "Exact Match University", thumbnail_source="https://upload.wikimedia.org/example.png"
        )

        call_command("fetch_university_cover_images")

        self.university.refresh_from_db()
        self.assertEqual(self.university.cover_image_url, "")
        self.assertFalse(
            UniversityFieldVerification.objects.filter(
                university=self.university, field_name="cover_image_url"
            ).exists()
        )

    @patch("services.university_service.management.commands.fetch_university_cover_images.requests.get")
    def test_title_mismatch_is_skipped_never_guessed(self, mock_get):
        mock_get.return_value = _summary_response(
            "Some Other Institution Entirely",
            thumbnail_source="https://upload.wikimedia.org/wrong.png",
        )

        call_command("fetch_university_cover_images", "--commit")

        self.university.refresh_from_db()
        self.assertEqual(self.university.cover_image_url, "")

    @patch("services.university_service.management.commands.fetch_university_cover_images.requests.get")
    def test_missing_thumbnail_is_skipped(self, mock_get):
        mock_get.return_value = _summary_response("Exact Match University", thumbnail_source=None)

        call_command("fetch_university_cover_images", "--commit")

        self.university.refresh_from_db()
        self.assertEqual(self.university.cover_image_url, "")

    @patch("services.university_service.management.commands.fetch_university_cover_images.requests.get")
    def test_network_error_is_handled_gracefully(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("boom")

        call_command("fetch_university_cover_images", "--commit")

        self.university.refresh_from_db()
        self.assertEqual(self.university.cover_image_url, "")

    @patch("services.university_service.management.commands.fetch_university_cover_images.requests.get")
    def test_demo_universities_are_never_fetched(self, mock_get):
        University.objects.create(
            slug="demo-university",
            name="Demo University",
            country="Demoland",
            official_website="https://example.com/demo",
            is_published=True,
            is_demo=True,
        )

        call_command("fetch_university_cover_images", "--commit")

        mock_get.assert_called_once()

    @patch("services.university_service.management.commands.fetch_university_cover_images.requests.get")
    def test_existing_image_is_skipped_unless_overwrite(self, mock_get):
        self.university.cover_image_url = "https://upload.wikimedia.org/already-set.png"
        self.university.save(update_fields=["cover_image_url"])

        call_command("fetch_university_cover_images", "--commit")

        mock_get.assert_not_called()

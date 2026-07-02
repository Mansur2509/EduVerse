from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from services.user_profile_service.academic_normalization import (
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    SCALE_5,
    SCALE_10,
    SCALE_20,
    SCALE_CUSTOM_UNKNOWN,
    SCALE_PERCENTAGE,
    normalize_academic_record,
)
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


class AcademicNormalizationUnitTests(SimpleTestCase):
    def test_five_point_gpa_normalizes_to_four_point_estimate(self):
        result = normalize_academic_record(
            original_gpa_value=Decimal("4.80"),
            original_gpa_scale=Decimal("5.00"),
            original_gpa_scale_type=SCALE_5,
        )

        self.assertEqual(result.normalized_gpa_4, Decimal("3.84"))
        self.assertEqual(result.normalized_percentage, Decimal("96.00"))
        self.assertEqual(result.confidence, CONFIDENCE_MEDIUM)

    def test_percentage_scale_uses_conservative_bands(self):
        result = normalize_academic_record(
            original_gpa_value=Decimal("95"),
            original_gpa_scale=Decimal("100"),
            original_gpa_scale_type=SCALE_PERCENTAGE,
        )

        self.assertEqual(result.normalized_gpa_4, Decimal("3.80"))
        self.assertEqual(result.confidence, CONFIDENCE_MEDIUM)

    def test_unknown_scale_does_not_convert_confidently(self):
        result = normalize_academic_record(
            original_gpa_value=Decimal("11"),
            original_gpa_scale=Decimal("13"),
            original_gpa_scale_type=SCALE_CUSTOM_UNKNOWN,
        )

        self.assertIsNone(result.normalized_gpa_4)
        self.assertEqual(result.confidence, CONFIDENCE_LOW)

    def test_ten_point_scale_converts_proportionally(self):
        result = normalize_academic_record(
            original_gpa_value=Decimal("9"),
            original_gpa_scale=Decimal("10"),
            original_gpa_scale_type=SCALE_10,
        )

        self.assertEqual(result.normalized_percentage, Decimal("90.00"))
        self.assertEqual(result.normalized_gpa_4, Decimal("3.60"))
        self.assertEqual(result.confidence, CONFIDENCE_MEDIUM)

    def test_twenty_point_scale_converts_proportionally(self):
        result = normalize_academic_record(
            original_gpa_value=Decimal("17"),
            original_gpa_scale=Decimal("20"),
            original_gpa_scale_type=SCALE_20,
        )

        self.assertEqual(result.normalized_percentage, Decimal("85.00"))
        self.assertEqual(result.normalized_gpa_4, Decimal("3.40"))
        self.assertEqual(result.confidence, CONFIDENCE_MEDIUM)

    def test_ten_and_twenty_point_scales_infer_from_bare_scale_value(self):
        ten_point = normalize_academic_record(
            original_gpa_value=Decimal("9"),
            original_gpa_scale=Decimal("10"),
            original_gpa_scale_type=None,
        )
        twenty_point = normalize_academic_record(
            original_gpa_value=Decimal("17"),
            original_gpa_scale=Decimal("20"),
            original_gpa_scale_type=None,
        )

        self.assertEqual(ten_point.normalized_gpa_4, Decimal("3.60"))
        self.assertEqual(twenty_point.normalized_gpa_4, Decimal("3.40"))


class AcademicNormalizationApiTests(APITestCase):
    def test_profile_representation_does_not_show_raw_five_point_as_four_point(self):
        user = User.objects.create_user(
            username="gpauser", email="gpauser@test.com", password="testpass123"
        )
        profile, _ = ensure_profile_records(user)
        profile.gpa = Decimal("4.80")
        profile.gpa_scale = Decimal("5.00")
        profile.save()

        self.client.force_authenticate(user)
        response = self.client.get("/api/profile/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["original_gpa_value"]), Decimal("4.80"))
        self.assertEqual(Decimal(response.data["original_gpa_scale"]), Decimal("5.00"))
        self.assertEqual(Decimal(response.data["normalized_gpa_4"]), Decimal("3.84"))
        self.assertNotEqual(response.data["normalized_gpa_4"], response.data["original_gpa_value"])

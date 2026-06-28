from django.conf import settings
from django.db import models

from common.validators import validate_http_url


class University(models.Model):
    class InstitutionType(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class TestPolicy(models.TextChoices):
        REQUIRED = "required", "Required"
        OPTIONAL = "optional", "Optional"
        BLIND = "blind", "Blind"
        VARIES = "varies", "Varies by program"

    name = models.CharField(max_length=240)
    slug = models.SlugField(max_length=260, unique=True)
    country = models.CharField(max_length=100, db_index=True)
    city = models.CharField(max_length=120, blank=True)
    official_website = models.URLField(validators=[validate_http_url])
    summary = models.TextField(blank=True)
    institution_type = models.CharField(
        max_length=20, choices=InstitutionType.choices, blank=True
    )
    is_published = models.BooleanField(default=False, db_index=True)

    # True for clearly-labeled fictional demonstration records (see seed_demo.py).
    # Real, source-backed universities must always have is_demo=False so the
    # default catalog search/listing can exclude fictional entries.
    is_demo = models.BooleanField(default=False, db_index=True)

    # Admissions statistics. All fields are nullable on purpose: a null value means
    # "not verified yet" and must never be displayed as zero or invented. Any
    # non-null value here should have a matching UniversityFieldVerification row
    # recording its source_url, last_verified_date, and verification_status.
    acceptance_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    gpa_average = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    sat_average = models.PositiveSmallIntegerField(null=True, blank=True)
    sat_p25 = models.PositiveSmallIntegerField(null=True, blank=True)
    sat_p75 = models.PositiveSmallIntegerField(null=True, blank=True)
    ielts_minimum = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    test_policy = models.CharField(max_length=20, choices=TestPolicy.choices, blank=True)
    tuition_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tuition_currency = models.CharField(max_length=10, blank=True, default="USD")
    application_deadline = models.DateField(null=True, blank=True)
    scholarship_available = models.BooleanField(null=True, blank=True)
    essay_requirements = models.TextField(blank=True)
    qs_ranking = models.PositiveIntegerField(null=True, blank=True)
    qs_ranking_year = models.PositiveSmallIntegerField(null=True, blank=True)

    admissions_url = models.URLField(blank=True, validators=[validate_http_url])
    financial_aid_url = models.URLField(blank=True, validators=[validate_http_url])
    application_portal_url = models.URLField(blank=True, validators=[validate_http_url])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=("country", "is_published"))]

    def __str__(self) -> str:
        return self.name


class UniversityProgram(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=240)
    degree_level = models.CharField(max_length=80, blank=True)
    official_url = models.URLField(blank=True, validators=[validate_http_url])


class UniversityRequirement(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="requirements")
    requirement_type = models.CharField(max_length=100, db_index=True)
    value = models.CharField(max_length=240)
    notes = models.TextField(blank=True)


class UniversityScholarship(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="scholarships")
    name = models.CharField(max_length=240)
    summary = models.TextField(blank=True)
    official_url = models.URLField(validators=[validate_http_url])
    deadline = models.DateField(null=True, blank=True)


class UniversityDataSource(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="data_sources")
    source_title = models.CharField(max_length=240)
    source_url = models.URLField(validators=[validate_http_url])
    is_official = models.BooleanField(default=True)
    published_at = models.DateField(null=True, blank=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)


class UniversityFieldVerification(models.Model):
    """Per-field sourcing record for a non-null University statistic.

    One row per (university, field_name). Its presence is what lets the
    frontend show "Verified" / "Partial" / "Estimated" instead of a bare
    number, and "Not verified yet" for any field with no row here.
    """

    class Status(models.TextChoices):
        VERIFIED = "verified", "Verified"
        PARTIAL = "partial", "Partial"
        ESTIMATED = "estimated", "Estimated"

    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="field_verifications"
    )
    field_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    source_url = models.URLField(validators=[validate_http_url])
    last_verified_date = models.DateField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ("field_name",)
        constraints = [
            models.UniqueConstraint(
                fields=("university", "field_name"),
                name="unique_university_field_verification",
            )
        ]

    def __str__(self) -> str:
        return f"{self.university.name}: {self.field_name} ({self.status})"


class SavedUniversity(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_universities"
    )
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "university"), name="unique_saved_university")
        ]


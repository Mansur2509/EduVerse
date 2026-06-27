from django.conf import settings
from django.db import models

from common.validators import validate_http_url


class University(models.Model):
    class InstitutionType(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

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

    # Admissions statistics. All fields are nullable on purpose: a null value means
    # "not verified yet" and must never be displayed as zero or invented.
    acceptance_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    gpa_average = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    sat_average = models.PositiveSmallIntegerField(null=True, blank=True)
    tuition_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tuition_currency = models.CharField(max_length=10, blank=True, default="USD")
    application_deadline = models.DateField(null=True, blank=True)
    scholarship_available = models.BooleanField(null=True, blank=True)

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


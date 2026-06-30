from django.core.exceptions import ValidationError
from django.db import models


class Exam(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False, db_index=True)

    def __str__(self) -> str:
        return self.name


class ExamSection(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("exam", "slug"), name="unique_exam_section_slug")
        ]


class Question(models.Model):
    class Origin(models.TextChoices):
        ORIGINAL = "original", "Original EduVerse content"
        LICENSED = "licensed", "Licensed content"

    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.ORIGINAL)
    provenance_note = models.CharField(max_length=240, default="Original EduVerse demonstration content")
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AnswerChoice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answer_choices")
    label = models.CharField(max_length=5)
    text = models.TextField()
    is_correct = models.BooleanField(default=False)


class Explanation(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name="explanation")
    text = models.TextField()


class OfficialExamDate(models.Model):
    class ExamType(models.TextChoices):
        SAT = "SAT", "SAT"
        AP = "AP", "AP"

    class VerificationStatus(models.TextChoices):
        VERIFIED = "verified", "Verified"
        PARTIAL = "partial", "Partial"
        OUTDATED = "outdated", "Outdated"

    exam_type = models.CharField(max_length=8, choices=ExamType.choices, db_index=True)
    name = models.CharField(max_length=160)
    test_date = models.DateField()
    registration_deadline = models.DateField(null=True, blank=True)
    late_registration_deadline = models.DateField(null=True, blank=True)
    score_release_window = models.CharField(max_length=160, blank=True)
    academic_year = models.CharField(max_length=20)
    region = models.CharField(max_length=120, blank=True)
    source_url = models.URLField()
    last_verified_date = models.DateField()
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PARTIAL,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("test_date", "exam_type")
        indexes = [
            models.Index(fields=("exam_type", "test_date")),
            models.Index(fields=("verification_status", "last_verified_date")),
        ]

    def clean(self):
        super().clean()
        if (
            self.verification_status == self.VerificationStatus.VERIFIED
            and "collegeboard.org" not in self.source_url.lower()
        ):
            raise ValidationError(
                {"source_url": "Verified SAT/AP dates must use an official College Board URL."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.exam_type} {self.name} ({self.test_date})"

from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    class GpaScaleType(models.TextChoices):
        FOUR_POINT = "4_0", "4.0 scale"
        FIVE_POINT = "5_0", "5.0 scale"
        PERCENTAGE_100 = "percentage_100", "100-point percentage"
        IB_45 = "ib_45", "IB / 45"
        A_LEVEL = "a_level", "A-Level"
        AP_HEAVY = "ap_heavy", "AP-heavy curriculum"
        UZBEKISTAN_5 = "uzbekistan_5", "Uzbekistan 5-point / lyceum scale"
        KAZAKHSTAN_LOCAL = "kazakhstan_local", "Kazakhstan local scale"
        KYRGYZSTAN_LOCAL = "kyrgyzstan_local", "Kyrgyzstan local scale"
        TAJIKISTAN_LOCAL = "tajikistan_local", "Tajikistan local scale"
        CUSTOM_UNKNOWN = "custom_unknown", "Custom / unknown"

    class CurriculumType(models.TextChoices):
        LOCAL_SCHOOL = "local_school", "Local school"
        ACADEMIC_LYCEUM = "academic_lyceum", "Academic lyceum"
        IB = "ib", "IB"
        A_LEVEL = "a_level", "A-Level"
        AP = "ap", "AP"
        NATIONAL_DIPLOMA = "national_diploma", "National diploma"
        FOUNDATION = "foundation", "Foundation"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown"

    class NormalizationConfidence(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class ScholarshipNeed(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"
        UNSURE = "unsure", "Not sure"

    class EssayStatus(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"
        NOT_YET = "not_yet", "Not yet"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    full_name = models.CharField(max_length=180, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True, db_index=True)
    city = models.CharField(max_length=120, blank=True)
    school_or_university = models.CharField(max_length=240, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    expected_graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    education_status = models.CharField(max_length=120, blank=True)
    gpa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    gpa_scale = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    original_gpa_value = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    original_gpa_scale = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    original_gpa_scale_type = models.CharField(
        max_length=32,
        choices=GpaScaleType.choices,
        default=GpaScaleType.CUSTOM_UNKNOWN,
    )
    normalized_gpa_4 = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    normalized_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    curriculum_type = models.CharField(
        max_length=32,
        choices=CurriculumType.choices,
        default=CurriculumType.UNKNOWN,
    )
    curriculum_country = models.CharField(max_length=100, blank=True)
    academic_normalization_confidence = models.CharField(
        max_length=12,
        choices=NormalizationConfidence.choices,
        default=NormalizationConfidence.LOW,
    )
    academic_normalization_note = models.TextField(blank=True)
    intended_degree = models.CharField(max_length=120, blank=True)
    intended_major = models.CharField(max_length=180, blank=True)
    intended_majors = models.JSONField(default=list, blank=True)
    target_countries = models.JSONField(default=list, blank=True)
    target_universities = models.JSONField(default=list, blank=True)
    university_unsure = models.BooleanField(default=False)
    major_unsure = models.BooleanField(default=False)
    languages = models.JSONField(default=list, blank=True)
    test_scores = models.JSONField(default=dict, blank=True)
    exam_plans = models.JSONField(default=dict, blank=True)
    preparation_needs = models.JSONField(default=list, blank=True)
    activities = models.JSONField(default=dict, blank=True)
    essay_status = models.CharField(
        max_length=12,
        choices=EssayStatus.choices,
        default=EssayStatus.NOT_YET,
    )
    essay_stage = models.CharField(max_length=120, blank=True)
    support_priorities = models.JSONField(default=list, blank=True)
    telegram_username = models.CharField(max_length=33, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    scholarship_need = models.CharField(
        max_length=10,
        choices=ScholarshipNeed.choices,
        default=ScholarshipNeed.UNSURE,
    )
    sat_level = models.CharField(max_length=100, blank=True)
    ielts_level = models.CharField(max_length=100, blank=True)
    essay_level = models.CharField(max_length=100, blank=True)
    onboarding_sections = models.JSONField(default=list, blank=True)
    onboarding_version = models.PositiveSmallIntegerField(default=1)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    interested_classes = models.JSONField(default=list, blank=True)
    ap_interests = models.JSONField(default=list, blank=True)
    activity_interests = models.JSONField(default=list, blank=True)
    career_interests = models.JSONField(default=list, blank=True)
    interests = models.JSONField(default=list, blank=True)
    mun_debate_interest = models.BooleanField(default=False)
    research_interest = models.BooleanField(default=False)
    finance_literacy_interest = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class Activity(models.Model):
    class Scale(models.TextChoices):
        SCHOOL = "school", "School-level"
        CITY = "city", "City-level"
        REGIONAL = "regional", "Regional-level"
        NATIONAL = "national", "National-level"
        INTERNATIONAL = "international", "International-level"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_activities",
    )
    title = models.CharField(max_length=150)
    role = models.CharField(max_length=150, blank=True)
    organization = models.CharField(max_length=150, blank=True)
    category = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    hours_per_week = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )
    weeks_per_year = models.PositiveSmallIntegerField(null=True, blank=True)
    scale = models.CharField(
        max_length=20, choices=Scale.choices, default=Scale.SCHOOL, blank=True
    )
    impact_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=1500, blank=True)
    proof_link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Honor(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_honors",
    )
    title = models.CharField(max_length=150)
    issuing_organization = models.CharField(max_length=150, blank=True)
    level = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    result_rank = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=1500, blank=True)
    proof_link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Olympiad(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_olympiads",
    )
    name = models.CharField(max_length=150)
    subject = models.CharField(max_length=100, blank=True)
    level = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    result = models.CharField(max_length=100, blank=True)
    rank_percentile = models.CharField(max_length=50, blank=True)
    description = models.TextField(max_length=1500, blank=True)
    proof_link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Sport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_sports",
    )
    sport_name = models.CharField(max_length=150)
    level = models.CharField(max_length=100, blank=True)
    years_trained = models.CharField(max_length=100, blank=True)
    peak_result = models.CharField(max_length=150, blank=True)
    competition_name = models.CharField(max_length=150, blank=True)
    description = models.TextField(max_length=1500, blank=True)
    proof_link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ResearchProject(models.Model):
    class Stage(models.TextChoices):
        PLANNING = "planning", "Planning"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        PUBLISHED = "published", "Published"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_research_projects",
    )
    title = models.CharField(max_length=150)
    field = models.CharField(max_length=150, blank=True)
    research_question = models.TextField(max_length=500, blank=True)
    sample_size = models.CharField(max_length=100, blank=True)
    countries_region = models.CharField(max_length=150, blank=True)
    methods_used = models.CharField(max_length=150, blank=True)
    current_stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.ACTIVE, blank=True
    )
    manuscript_link = models.URLField(blank=True)
    publication_status = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=1500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class EssayDraft(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_essays",
    )
    essay_type = models.CharField(max_length=100, blank=True)
    school_program = models.CharField(max_length=150, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    word_limit = models.PositiveSmallIntegerField(null=True, blank=True)
    draft_status = models.CharField(max_length=100, blank=True)
    last_reviewed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class PortfolioProject(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_portfolio_projects",
    )
    title = models.CharField(max_length=150)
    project_type = models.CharField(max_length=100, blank=True)
    link = models.URLField(blank=True)
    tech_stack = models.CharField(max_length=150, blank=True)
    users_impact = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=1500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

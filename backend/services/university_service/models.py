from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
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
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    # Denominator for gpa_average (e.g. 4.00, 5.00, 100.00). Existing rows have
    # no recorded scale, so a null value is NOT assumed to mean "4.0 scale" --
    # `academic_normalization.py` infers it conservatively (PERFORMANCE-012
    # PART 2) rather than risk comparing mismatched scales (a 0-4 student GPA
    # diffed straight against a 0-100 benchmark).
    gpa_average_scale = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    sat_average = models.PositiveSmallIntegerField(null=True, blank=True)
    sat_p25 = models.PositiveSmallIntegerField(null=True, blank=True)
    sat_p75 = models.PositiveSmallIntegerField(null=True, blank=True)
    ielts_minimum = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    # The score that is competitive (not just the minimum) for admitted students.
    # Nullable like every other statistic — null means "not verified yet".
    ielts_competitive = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True
    )
    test_policy = models.CharField(max_length=20, choices=TestPolicy.choices, blank=True)
    tuition_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tuition_currency = models.CharField(max_length=10, blank=True, default="USD")
    tuition_original_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    tuition_original_currency = models.CharField(max_length=10, blank=True)
    tuition_usd_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, db_index=True
    )
    total_cost_original_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    total_cost_original_currency = models.CharField(max_length=10, blank=True)
    total_cost_usd_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, db_index=True
    )
    currency_conversion_rate = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    currency_conversion_date = models.DateField(null=True, blank=True)
    currency_conversion_source = models.CharField(max_length=240, blank=True)
    currency_conversion_confidence = models.CharField(max_length=20, blank=True)
    cost_notes = models.TextField(blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    scholarship_available = models.BooleanField(null=True, blank=True)
    essay_requirements = models.TextField(blank=True)

    # Real, attributed imagery only -- never a fabricated or unverified
    # hotlinked photo. Blank means "no image available" and the frontend must
    # fall back to the existing designed gradient header, never a broken
    # image. cover_image_source_title/url are shown to students as visible
    # attribution (e.g. "Image: Wikipedia") whenever cover_image_url is set;
    # the fetch_university_cover_images command always writes them together.
    cover_image_url = models.URLField(blank=True, validators=[validate_http_url])
    cover_image_source_title = models.CharField(max_length=240, blank=True)
    cover_image_source_url = models.URLField(blank=True, validators=[validate_http_url])
    cover_image_retrieved_at = models.DateTimeField(null=True, blank=True)

    # Raw, source-backed text blocks preserved verbatim from imported datasets when
    # the content is too unstructured to split into discrete records safely. These
    # are displayed as-is (never parsed into invented structure) so a beta user can
    # always read the original requirement text. Empty string means "not provided".
    application_requirements = models.TextField(blank=True)
    ap_recommendations = models.TextField(blank=True)
    deadlines_text = models.TextField(blank=True)
    financial_aid_notes = models.TextField(blank=True)
    scholarships_text = models.TextField(blank=True)
    # Importer-generated data-quality caveats (e.g. "possible placeholder SAT
    # values", "GPA stored as text", "raw tuition preserved"). Shown in the
    # Sources tab so questionable data is transparent, never silently trusted.
    data_quality_notes = models.TextField(blank=True)

    qs_ranking = models.PositiveIntegerField(null=True, blank=True)
    qs_ranking_year = models.PositiveSmallIntegerField(null=True, blank=True)
    global_rank = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    the_rank = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    national_rank = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    ranking_source = models.CharField(max_length=120, blank=True)
    ranking_source_url = models.URLField(blank=True, validators=[validate_http_url])
    ranking_year = models.PositiveSmallIntegerField(null=True, blank=True)
    ranking_last_verified_date = models.DateField(null=True, blank=True)
    ranking_confidence = models.CharField(max_length=20, blank=True)
    national_ranking_source = models.CharField(max_length=120, blank=True)

    admissions_url = models.URLField(blank=True, validators=[validate_http_url])
    financial_aid_url = models.URLField(blank=True, validators=[validate_http_url])
    application_portal_url = models.URLField(blank=True, validators=[validate_http_url])
    international_office_url = models.URLField(blank=True, validators=[validate_http_url])
    virtual_info_session_url = models.URLField(blank=True, validators=[validate_http_url])
    # A second, distinct admissions link some sources publish alongside
    # `admissions_url` (e.g. a general admissions info page vs. a "how to
    # apply" page). Kept separate rather than overwriting `admissions_url`
    # since either may be the more useful link depending on the source.
    admissions_website = models.URLField(blank=True, validators=[validate_http_url])

    # Bulk-import public fields (added for the ~450-university dataset import).
    # All optional/raw-text-preserving: null/blank means "not provided", never
    # invented. Free-text fields are stored verbatim rather than force-parsed
    # into structured data when the source prose is too varied to normalize
    # safely.
    majors_list = models.JSONField(default=list, blank=True)
    admissions_cycle_target = models.CharField(max_length=240, blank=True)
    standardized_testing_policy_text = models.TextField(blank=True)
    # Distinct from `sat_average` (which existing fit-scoring code already
    # reads with its own semantics) -- this is specifically the dataset's
    # "SAT 50th percentile" column and must never be conflated with it.
    sat_p50 = models.PositiveSmallIntegerField(null=True, blank=True)
    qs_overall_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    need_based_aid_notes = models.TextField(blank=True)
    merit_scholarship_notes = models.TextField(blank=True)
    other_scholarships_notes = models.TextField(blank=True)
    scholarship_links_text = models.TextField(blank=True)
    profile_evidence_notes = models.TextField(blank=True)
    activities_notes = models.TextField(blank=True)
    honors_olympiads_notes = models.TextField(blank=True)
    research_experience_notes = models.TextField(blank=True)
    portfolio_notes = models.TextField(blank=True)
    essay_drafts_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=("country", "is_published"))]

    def __str__(self) -> str:
        return self.name


class ExchangeRate(models.Model):
    class Confidence(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    currency_code = models.CharField(max_length=10, db_index=True)
    usd_rate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        help_text="USD value of one unit of currency_code.",
    )
    effective_date = models.DateField(db_index=True)
    source = models.CharField(max_length=240)
    confidence = models.CharField(
        max_length=12,
        choices=Confidence.choices,
        default=Confidence.MEDIUM,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-effective_date", "currency_code")
        constraints = [
            models.UniqueConstraint(
                fields=("currency_code", "effective_date", "source"),
                name="unique_exchange_rate_source_date",
            )
        ]

    def save(self, *args, **kwargs):
        self.currency_code = self.currency_code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.currency_code} -> USD ({self.effective_date})"


class UniversityProgram(models.Model):
    class MajorCluster(models.TextChoices):
        STEM = "stem", "STEM"
        BUSINESS_ECONOMICS_FINANCE = (
            "business_economics_finance",
            "Business / Economics / Finance",
        )
        SOCIAL_SCIENCES = "social_sciences", "Social sciences"
        HUMANITIES = "humanities", "Humanities"
        LAW_POLITICS_IR = "law_politics_ir", "Law / Politics / IR"
        MEDICINE_BIOLOGY_HEALTH = (
            "medicine_biology_health",
            "Medicine / Biology / Health",
        )
        ENGINEERING = "engineering", "Engineering"
        COMPUTER_SCIENCE_AI_DATA = (
            "computer_science_ai_data",
            "Computer science / AI / Data",
        )
        DESIGN_ARTS = "design_arts", "Design / Arts"
        EDUCATION = "education", "Education"
        ENVIRONMENTAL_SUSTAINABILITY = (
            "environmental_sustainability",
            "Environmental / Sustainability",
        )
        PUBLIC_POLICY_SOCIAL_IMPACT = (
            "public_policy_social_impact",
            "Public policy / Social impact",
        )
        PSYCHOLOGY_COGNITIVE_SCIENCE = (
            "psychology_cognitive_science",
            "Psychology / Cognitive science",
        )
        UNDECIDED_INTERDISCIPLINARY = (
            "undecided_interdisciplinary",
            "Undecided / Interdisciplinary",
        )
        OTHER = "other", "Other"

    class SourceConfidence(models.TextChoices):
        VERIFIED = "verified", "Verified"
        PARTIAL = "partial", "Partial"
        ESTIMATED = "estimated", "Estimated"

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=240)
    major_cluster = models.CharField(
        max_length=60,
        choices=MajorCluster.choices,
        blank=True,
        db_index=True,
    )
    degree_level = models.CharField(max_length=80, blank=True)
    department_or_school = models.CharField(max_length=180, blank=True)
    official_url = models.URLField(blank=True, validators=[validate_http_url])
    source_url = models.URLField(blank=True, validators=[validate_http_url])
    program_requirements_summary = models.TextField(blank=True)
    essay_requirements = models.TextField(blank=True)
    portfolio_required = models.BooleanField(null=True, blank=True)
    research_heavy = models.BooleanField(default=False)
    stem_heavy = models.BooleanField(default=False)
    interdisciplinary = models.BooleanField(default=False)
    source_confidence = models.CharField(
        max_length=20,
        choices=SourceConfidence.choices,
        blank=True,
    )
    last_verified_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=("university", "major_cluster")),
            models.Index(fields=("portfolio_required", "major_cluster")),
        ]


class UniversitySubjectRanking(models.Model):
    class Confidence(models.TextChoices):
        VERIFIED = "verified", "Verified"
        PARTIAL = "partial", "Partial"
        ESTIMATED = "estimated", "Estimated"

    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="subject_rankings"
    )
    program = models.ForeignKey(
        UniversityProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subject_rankings",
    )
    subject_area = models.CharField(max_length=160, db_index=True)
    major_cluster = models.CharField(
        max_length=60,
        choices=UniversityProgram.MajorCluster.choices,
        blank=True,
        db_index=True,
    )
    rank = models.PositiveIntegerField(db_index=True)
    source_name = models.CharField(max_length=120, db_index=True)
    source_url = models.URLField(validators=[validate_http_url])
    ranking_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    last_verified_date = models.DateField()
    confidence = models.CharField(
        max_length=20,
        choices=Confidence.choices,
        default=Confidence.PARTIAL,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("rank", "subject_area")
        indexes = [
            models.Index(fields=("major_cluster", "rank")),
            models.Index(fields=("source_name", "rank")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("university", "subject_area", "source_name", "ranking_year"),
                name="unique_university_subject_ranking_year",
            )
        ]

    def __str__(self) -> str:
        return f"{self.university.name}: {self.subject_area} #{self.rank}"


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


class PinnedUniversity(models.Model):
    """022 Phase 11: a university a student has explicitly chosen to always
    keep in their recommendation list. Pinned items are still scored and
    categorized by the same canonical Fit Engine and category derivation as
    everything else -- pinning changes *inclusion*, never the fit label.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pinned_universities"
    )
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="pinned_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "university"), name="unique_pinned_university")
        ]


class ExcludedUniversity(models.Model):
    """022 Phase 11: a university a student has explicitly asked never to
    see in their recommendation list. A hard filter, same tier as the
    confirmed-degree-mismatch/expired-deadline filters (022 Phase 4) -- an
    explicit user choice, not a scoring outcome.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="excluded_universities"
    )
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="excluded_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "university"), name="unique_excluded_university")
        ]


class UniversityImportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Mode(models.TextChoices):
        DRY_RUN = "dry_run", "Dry run"
        EXECUTE = "execute", "Execute"

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="university_import_jobs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    mode = models.CharField(max_length=20, choices=Mode.choices, db_index=True)
    original_filename = models.CharField(max_length=255)
    row_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    source_url_count = models.PositiveIntegerField(default=0)
    field_verification_count = models.PositiveIntegerField(default=0)
    parsed_deadline_count = models.PositiveIntegerField(default=0)
    parsed_essay_count = models.PositiveIntegerField(default=0)
    questionable_sat_count = models.PositiveIntegerField(default=0)
    processed_count = models.PositiveIntegerField(default=0)
    current_row = models.PositiveIntegerField(null=True, blank=True)
    current_university = models.CharField(max_length=255, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    summary_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "created_at")),
            models.Index(fields=("mode", "created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.mode}, {self.status})"


class UniversityDataImportBatch(models.Model):
    """Committed runs of the 72-column university data importer.

    Separate from `UniversityImportJob`, which belongs to the admin upload UI.
    This model is only for source-row fingerprinting and auditability.
    """

    source_file_name = models.CharField(max_length=255)
    committed = models.BooleanField(default=False, db_index=True)
    row_count = models.PositiveIntegerField(default=0)
    summary_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("source_file_name", "created_at")),
            models.Index(fields=("committed", "created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.source_file_name} ({'committed' if self.committed else 'dry-run'})"


class UniversityDataImportRowLog(models.Model):
    batch = models.ForeignKey(
        UniversityDataImportBatch,
        on_delete=models.CASCADE,
        related_name="row_logs",
    )
    source_file_name = models.CharField(max_length=255)
    source_sheet_name = models.CharField(max_length=255, blank=True)
    source_row_number = models.PositiveIntegerField(null=True, blank=True)
    row_number = models.PositiveIntegerField()
    row_hash = models.CharField(max_length=64, db_index=True)
    matched_university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_import_row_logs",
    )
    action = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("batch", "row_number")
        indexes = [
            models.Index(fields=("row_hash", "action")),
            models.Index(fields=("source_file_name", "row_number")),
            models.Index(fields=("source_file_name", "source_sheet_name", "source_row_number")),
        ]

    def __str__(self) -> str:
        sheet = f"{self.source_sheet_name} " if self.source_sheet_name else ""
        row_number = self.source_row_number or self.row_number
        return f"{self.source_file_name} {sheet}row {row_number}: {self.action}"


class UniversityGuidanceContext(models.Model):
    """Internal guidance/context layer for a university.

    Never serialized to the public API -- no public serializer references
    this model, so it is excluded from student-facing responses by omission
    rather than by an exclude-list. Backend services only (essay review,
    fit/strategy analysis, recommendation prep, profile improvement) should
    read this through `get_university_ai_context()`, which returns only the
    fields relevant to the requested purpose instead of the whole row.
    """

    university = models.OneToOneField(
        University, on_delete=models.CASCADE, related_name="guidance_context"
    )
    recommendation_letters = models.TextField(blank=True)
    what_they_look_for = models.TextField(blank=True)
    preferred_student_profile = models.TextField(blank=True)
    who_they_seek = models.TextField(blank=True)
    student_traits_mentioned = models.TextField(blank=True)
    alumni_profile_evidence = models.TextField(blank=True)
    published_admitted_student_essays = models.TextField(blank=True)
    official_admissions_messaging = models.TextField(blank=True)
    student_life_page_signals = models.TextField(blank=True)
    graduate_alumni_outcomes = models.TextField(blank=True)
    sample_admitted_essays = models.TextField(blank=True)
    essay_themes = models.TextField(blank=True)
    research_leadership_themes = models.TextField(blank=True)
    personality_traits_mentioned = models.TextField(blank=True)
    academic_interests_mentioned = models.TextField(blank=True)
    institutional_values = models.TextField(blank=True)
    source_urls = models.TextField(blank=True)
    last_verified_date = models.DateField(null=True, blank=True)
    verification_status = models.CharField(max_length=120, blank=True)
    data_source = models.TextField(blank=True)
    # Admin/source note (dataset column 59) -- internal only, never public.
    notes = models.TextField(blank=True)
    # Future-proofing safety net: the full raw column->value dict for this
    # guidance section, so a gap in the explicit field mapping above never
    # silently loses source data.
    raw_context_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Guidance context: {self.university.name}"


class UniversitySignalWeights(models.Model):
    """System-only profile-scoring vector for a university (dataset columns
    60-72). Never serialized to the public API and never shown to students as
    raw values -- intended for the fit/readiness engine
    (`compare_student_vector_to_university_weights`) only.
    """

    _score_validators = (MinValueValidator(0), MaxValueValidator(10))

    university = models.OneToOneField(
        University, on_delete=models.CASCADE, related_name="signal_weights"
    )
    profile_evidence_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    activities_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    honors_olympiads_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    research_experience_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    portfolio_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    subject_passion_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    curiosity_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    originality_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    leadership_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    community_impact_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    research_fit_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    olympiads_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=_score_validators
    )
    profile_scoring_source = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Signal weights: {self.university.name}"


class UniversityModerationRecord(models.Model):
    """One staff review action against a university's data. Multiple rows
    accumulate over time as an audit trail, mirroring EventModerationLog --
    the university's current review state is its most recent record.
    """

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        VERIFIED = "verified", "Verified"
        NEEDS_UPDATE = "needs_update", "Needs update"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    class IssueType(models.TextChoices):
        MISSING_SOURCE = "missing_source", "Missing source"
        OUTDATED_DATA = "outdated_data", "Outdated data"
        CONFLICTING_DATA = "conflicting_data", "Conflicting data"
        SHIFTED_ROW = "shifted_row", "Shifted row"
        BOILERPLATE = "boilerplate", "Boilerplate"
        USER_REPORT = "user_report", "User report"
        ADMIN_NOTE = "admin_note", "Admin note"

    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="moderation_records"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW, db_index=True
    )
    field_name = models.CharField(max_length=100, blank=True)
    issue_type = models.CharField(max_length=30, choices=IssueType.choices)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="university_moderation_records_created",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="university_moderation_records_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("university", "status"))]

    def __str__(self) -> str:
        return f"{self.university_id} moderation ({self.status})"


class UniversitySemanticFit(models.Model):
    """Cached AI-generated qualitative fit summary for one (user, university)
    pair (PERFORMANCE-011 PART 5). One row per pair, overwritten on refresh --
    mirrors AIProfileAssessment's "latest row + snapshot hash" cache protocol
    rather than keeping a full history, since only the current read matters.

    Validity is not a stored boolean: `services.university_service.semantic_fit`
    treats a row as stale (and reports it as "missing" to callers) whenever
    `profile_snapshot_hash`, `university_updated_at`, or `prompt_version` no
    longer match the current values -- so a stale row is never served, only
    ever overwritten by the next explicit refresh.
    """

    class Status(models.TextChoices):
        OK = "ok", "OK"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="semantic_fits"
    )
    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="semantic_fits"
    )
    profile_snapshot_hash = models.CharField(max_length=64)
    university_updated_at = models.DateTimeField()
    prompt_version = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    main_strength = models.CharField(max_length=300, blank=True)
    main_risk = models.CharField(max_length=300, blank=True)
    summary = models.CharField(max_length=600, blank=True)
    next_actions = models.JSONField(default=list, blank=True)
    model_provider = models.CharField(max_length=40, blank=True)
    model_name = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "university"), name="unique_semantic_fit_per_user_university")
        ]

    def __str__(self) -> str:
        return f"Semantic fit: user={self.user_id} university={self.university_id} ({self.status})"

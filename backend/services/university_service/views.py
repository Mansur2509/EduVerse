from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, F, Max, Min, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from common.pagination import CompactListPagination
from common.permissions import IsAdminOrReadOnly, IsAdminRole
from common.throttling import ScopedIPRateThrottle
from services.activity_service.models import AnalyticsEvent
from services.activity_service.services import track_event
from services.user_profile_service.services import (
    ensure_profile_records,
    get_profile_records_for_read,
)

from .currency import normalize_amount_to_usd
from .import_jobs import enqueue_university_import_job, mark_stale_university_import_job
from .models import (
    ExcludedUniversity,
    PinnedUniversity,
    SavedUniversity,
    University,
    UniversityFieldVerification,
    UniversityImportJob,
    UniversityModerationRecord,
    UniversityProgram,
    UniversitySubjectRanking,
)
from .recommendation_cache import (
    RECOMMENDATIONS_CACHE_SECONDS,
    STRATEGY_CACHE_SECONDS,
    invalidate_recommendation_caches,
    recommendations_cache_key,
    strategy_cache_key,
)
from .recommendations import (
    calculate_university_recommendations,
    diagnose_university_recommendations,
    explain_recommendation_for_university,
)
from .semantic_fit import build_fit_response, refresh_semantic_fit, semantic_fit_status
from .serializers import (
    ExcludedUniversitySerializer,
    PinnedUniversitySerializer,
    RecommendationPreferenceSerializer,
    SavedUniversityLiteSerializer,
    SavedUniversitySerializer,
    UniversityImportJobSerializer,
    UniversityImportUploadSerializer,
    UniversityListSerializer,
    UniversityModerationActionSerializer,
    UniversityModerationRecordSerializer,
    UniversitySerializer,
)
from .services import calculate_university_fit
from .strategy import build_application_strategy

User = get_user_model()

SELF_SERVICE_ACTIONS = {
    "list",
    "retrieve",
    "fit",
    "refresh_fit",
    "filter_options",
    "destinations",
    "shortlist",
    "shortlisted",
    "compare",
    "recommendations",
    "strategy",
    "pin",
    "pinned",
    "exclude",
    "excluded",
    "recommendation_preferences",
    "recommendation_explanation",
}

# filter_options scans every published university across ~9 distinct-value/
# existence queries (~23 total with the per-choice .exists() checks for
# institution types and major clusters) -- this data changes only when the
# catalogue is edited or re-imported, so a short cache turns "every request"
# into "once per TTL per process" without risking stale data for long.
FILTER_OPTIONS_CACHE_SECONDS = 600
FILTER_OPTIONS_CACHE_KEY_TEMPLATE = "university-filter-options:include_demo={include_demo}"

UNIVERSITY_NULLS_LAST_ORDERINGS = {
    "acceptance_rate": (F("acceptance_rate").asc(nulls_last=True), "name"),
    "-acceptance_rate": (F("acceptance_rate").desc(nulls_last=True), "name"),
    "qs_ranking": (F("qs_ranking").asc(nulls_last=True), "name"),
    "-qs_ranking": (F("qs_ranking").desc(nulls_last=True), "name"),
    "global_rank": (F("global_rank").asc(nulls_last=True), "name"),
    "-global_rank": (F("global_rank").desc(nulls_last=True), "name"),
    "the_rank": (F("the_rank").asc(nulls_last=True), "name"),
    "-the_rank": (F("the_rank").desc(nulls_last=True), "name"),
    "national_rank": (F("national_rank").asc(nulls_last=True), "name"),
    "-national_rank": (F("national_rank").desc(nulls_last=True), "name"),
    "tuition_usd_amount": (F("tuition_usd_amount").asc(nulls_last=True), "name"),
    "-tuition_usd_amount": (F("tuition_usd_amount").desc(nulls_last=True), "name"),
    "total_cost_usd_amount": (F("total_cost_usd_amount").asc(nulls_last=True), "name"),
    "-total_cost_usd_amount": (F("total_cost_usd_amount").desc(nulls_last=True), "name"),
}

UNIVERSITY_LIST_ONLY_FIELDS = (
    "id",
    "name",
    "slug",
    "country",
    "city",
    "official_website",
    "summary",
    "institution_type",
    "is_published",
    "is_demo",
    "acceptance_rate",
    "gpa_average",
    "sat_average",
    "sat_p25",
    "sat_p50",
    "sat_p75",
    "ielts_minimum",
    "ielts_competitive",
    "test_policy",
    "tuition_amount",
    "tuition_currency",
    "tuition_original_amount",
    "tuition_original_currency",
    "tuition_usd_amount",
    "total_cost_original_amount",
    "total_cost_original_currency",
    "total_cost_usd_amount",
    "currency_conversion_confidence",
    "application_deadline",
    "scholarship_available",
    "cover_image_url",
    "cover_image_source_title",
    "cover_image_source_url",
    "qs_ranking",
    "qs_ranking_year",
    "global_rank",
    "the_rank",
    "national_rank",
    "ranking_source",
    "ranking_year",
    "ranking_confidence",
    "majors_list",
    "admissions_cycle_target",
    "created_at",
    "updated_at",
)


def build_university_filter_options(*, include_demo: bool) -> dict:
    """Recomputes the full filter-options payload (~23 queries: 9 distinct-
    value scans plus a per-choice .exists() check for each institution type
    and major cluster). Pulled out of the view so it can be cached by
    `cache.get_or_set` and unit-tested without going through a request.
    """

    queryset = University.objects.filter(is_published=True)
    if not include_demo:
        queryset = queryset.exclude(is_demo=True)

    def distinct_text(field_name: str) -> list[str]:
        return sorted(
            {
                value.strip()
                for value in queryset.values_list(field_name, flat=True)
                if isinstance(value, str) and value.strip()
            },
            key=str.lower,
        )

    university_suggestions = list(
        queryset.order_by("name").values("name", "slug", "country", "city")[:200]
    )
    return {
        "countries": distinct_text("country"),
        "cities": distinct_text("city"),
        "institution_types": [
            choice
            for choice, _label in University.InstitutionType.choices
            if queryset.filter(institution_type=choice).exists()
        ],
        "cost_confidences": distinct_text("currency_conversion_confidence"),
        "verification_statuses": [choice for choice, _label in UniversityFieldVerification.Status.choices],
        "major_clusters": [
            choice
            for choice, _label in UniversityProgram.MajorCluster.choices
            if queryset.filter(programs__major_cluster=choice).exists()
        ],
        "program_names": sorted(
            {
                value.strip()
                for value in queryset.values_list("programs__name", flat=True)
                if isinstance(value, str) and value.strip()
            },
            key=str.lower,
        )[:500],
        "subject_areas": sorted(
            {
                value.strip()
                for value in queryset.values_list("subject_rankings__subject_area", flat=True)
                if isinstance(value, str) and value.strip()
            },
            key=str.lower,
        )[:500],
        "ranking_sources": sorted(
            {
                value.strip()
                for value in queryset.values_list("subject_rankings__source_name", flat=True)
                if isinstance(value, str) and value.strip()
            },
            key=str.lower,
        ),
        "universities": university_suggestions,
    }


# Real, uncontroversial geographic facts (ISO 3166-1 alpha-2 code for flag
# display, and the country's own primary/official language) -- never a claim
# about any specific university's language of instruction. A country missing
# from this map simply renders without a flag/language on its destination
# card (graceful fallback, never fabricated).
COUNTRY_METADATA: dict[str, dict[str, str]] = {
    "United States": {"code": "us", "primary_language": "English"},
    "United Kingdom": {"code": "gb", "primary_language": "English"},
    "Canada": {"code": "ca", "primary_language": "English"},
    "Singapore": {"code": "sg", "primary_language": "English"},
    "Italy": {"code": "it", "primary_language": "Italian"},
    "South Korea": {"code": "kr", "primary_language": "Korean"},
    "Australia": {"code": "au", "primary_language": "English"},
    "Germany": {"code": "de", "primary_language": "German"},
    "France": {"code": "fr", "primary_language": "French"},
    "Netherlands": {"code": "nl", "primary_language": "Dutch"},
    "Switzerland": {"code": "ch", "primary_language": "German, French, Italian"},
    "Japan": {"code": "jp", "primary_language": "Japanese"},
    "China": {"code": "cn", "primary_language": "Mandarin"},
    "Hong Kong": {"code": "hk", "primary_language": "Cantonese, English"},
    "Ireland": {"code": "ie", "primary_language": "English"},
    "New Zealand": {"code": "nz", "primary_language": "English"},
    "Sweden": {"code": "se", "primary_language": "Swedish"},
    "Spain": {"code": "es", "primary_language": "Spanish"},
}

DESTINATIONS_CACHE_SECONDS = 600
DESTINATIONS_CACHE_KEY_TEMPLATE = "university-destinations:include_demo={include_demo}"


def build_study_destinations(*, include_demo: bool) -> list[dict]:
    """Real, computed per-country aggregates for the "Study destinations"
    section -- every number is a live count/min/max over published
    universities, never invented. Demo/fictional countries (is_demo=True
    records) are excluded by default just like the rest of the catalog.
    """

    queryset = University.objects.filter(is_published=True)
    if not include_demo:
        queryset = queryset.exclude(is_demo=True)

    rows = (
        queryset.exclude(country="")
        .values("country")
        .annotate(
            university_count=Count("id", distinct=True),
            min_tuition_usd=Min("tuition_usd_amount"),
            max_tuition_usd=Max("tuition_usd_amount"),
            scholarship_count=Count("id", filter=Q(scholarship_available=True), distinct=True),
        )
        .order_by("-university_count", "country")
    )

    destinations = []
    for row in rows:
        country = row["country"]
        metadata = COUNTRY_METADATA.get(country, {})
        destinations.append(
            {
                "country": country,
                "country_code": metadata.get("code"),
                "primary_language": metadata.get("primary_language"),
                "university_count": row["university_count"],
                "min_tuition_usd": row["min_tuition_usd"],
                "max_tuition_usd": row["max_tuition_usd"],
                "has_scholarships": row["scholarship_count"] > 0,
            }
        )
    return destinations


class UniversityViewSet(ModelViewSet):
    throttle_scope = None
    serializer_class = UniversitySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    search_fields = ("name", "city", "country", "programs__name")
    filterset_fields = {
        "institution_type": ["exact"],
        "scholarship_available": ["exact"],
        "test_policy": ["exact"],
        # Requirement-threshold filters: each keeps only universities whose
        # published number is at/below (or within) what the student enters.
        # Universities without the published value are excluded by these
        # filters rather than being guessed at.
        "ielts_minimum": ["lte"],
        "sat_average": ["lte", "gte"],
        "gpa_average": ["lte", "gte"],
        "acceptance_rate": ["lte", "gte"],
        "currency_conversion_confidence": ["exact"],
    }
    ordering_fields = (
        "name",
        "country",
        "created_at",
        "acceptance_rate",
        "qs_ranking",
        "global_rank",
        "the_rank",
        "national_rank",
        "tuition_usd_amount",
        "total_cost_usd_amount",
    )

    def get_serializer_class(self):
        if self.action == "list":
            return UniversityListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if self.action == "list":
            queryset = University.objects.only(*UNIVERSITY_LIST_ONLY_FIELDS)
        else:
            rankings_with_program = UniversitySubjectRanking.objects.select_related("program")
            queryset = University.objects.prefetch_related(
                Prefetch("programs__subject_rankings", queryset=rankings_with_program),
                Prefetch("subject_rankings", queryset=rankings_with_program),
                "requirements",
                "scholarships",
                "data_sources",
                "field_verifications",
            )
        user = self.request.user
        if not (user.is_authenticated and user.is_admin_role):
            queryset = queryset.filter(is_published=True)

        if self.action == "list":
            include_demo = self.request.query_params.get("include_demo", "").lower() == "true"
            if not include_demo:
                queryset = queryset.exclude(is_demo=True)
            verification_status = self.request.query_params.get("verification_status", "")
            valid_statuses = {choice[0] for choice in UniversityFieldVerification.Status.choices}
            if verification_status in valid_statuses:
                queryset = queryset.filter(
                    field_verifications__status=verification_status
                ).distinct()

        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            if self.request.query_params.get("search", "").strip():
                queryset = queryset.distinct()
            country = self.request.query_params.get("country", "").strip()
            city = self.request.query_params.get("city", "").strip()
            if country:
                queryset = queryset.filter(country__icontains=country)
            if city:
                queryset = queryset.filter(city__icontains=city)
            queryset = self._apply_cost_status_filter(queryset)
            queryset = self._apply_program_and_ranking_filters(queryset)
        ordering = self.request.query_params.get("ordering", "")
        custom_ordering = UNIVERSITY_NULLS_LAST_ORDERINGS.get(ordering)
        if self.action == "list" and custom_ordering:
            return queryset.order_by(*custom_ordering)
        return queryset

    @action(detail=False, methods=["get"], url_path="filter-options")
    def filter_options(self, request):
        include_demo = bool(
            request.user.is_authenticated
            and request.user.is_admin_role
            and request.query_params.get("include_demo", "").lower() == "true"
        )
        cache_key = FILTER_OPTIONS_CACHE_KEY_TEMPLATE.format(include_demo=include_demo)
        payload = cache.get_or_set(
            cache_key, lambda: build_university_filter_options(include_demo=include_demo),
            FILTER_OPTIONS_CACHE_SECONDS,
        )
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="destinations")
    def destinations(self, request):
        include_demo = bool(
            request.user.is_authenticated
            and request.user.is_admin_role
            and request.query_params.get("include_demo", "").lower() == "true"
        )
        cache_key = DESTINATIONS_CACHE_KEY_TEMPLATE.format(include_demo=include_demo)
        payload = cache.get_or_set(
            cache_key, lambda: build_study_destinations(include_demo=include_demo),
            DESTINATIONS_CACHE_SECONDS,
        )
        return Response({"results": payload})

    def _apply_program_and_ranking_filters(self, queryset):
        params = self.request.query_params
        uses_related_filter = False
        major_cluster = params.get("major_cluster", "").strip()
        if major_cluster:
            queryset = queryset.filter(programs__major_cluster=major_cluster)
            uses_related_filter = True

        program_search = params.get("program_search", "").strip()
        if program_search:
            queryset = queryset.filter(programs__name__icontains=program_search)
            uses_related_filter = True

        subject_area = params.get("subject_area", "").strip()
        if subject_area:
            queryset = queryset.filter(subject_rankings__subject_area__icontains=subject_area)
            uses_related_filter = True

        ranking_source = params.get("ranking_source", "").strip()
        if ranking_source:
            queryset = queryset.filter(subject_rankings__source_name__icontains=ranking_source)
            uses_related_filter = True

        subject_rank_min = params.get("subject_rank_min", "").strip()
        if subject_rank_min.isdigit():
            queryset = queryset.filter(subject_rankings__rank__gte=int(subject_rank_min))
            uses_related_filter = True

        subject_rank_max = params.get("subject_rank_max", "").strip()
        if subject_rank_max.isdigit():
            queryset = queryset.filter(subject_rankings__rank__lte=int(subject_rank_max))
            uses_related_filter = True

        has_subject_ranking = params.get("has_subject_ranking", "").lower()
        if has_subject_ranking == "true":
            queryset = queryset.filter(subject_rankings__isnull=False)
            uses_related_filter = True
        elif has_subject_ranking == "false":
            queryset = queryset.filter(subject_rankings__isnull=True)
            uses_related_filter = True

        for key in ("portfolio_required", "research_heavy", "stem_heavy", "interdisciplinary"):
            value = params.get(key, "").lower()
            if value == "true":
                queryset = queryset.filter(**{f"programs__{key}": True})
                uses_related_filter = True
            elif value == "false":
                queryset = queryset.filter(**{f"programs__{key}": False})
                uses_related_filter = True

        source_confidence = params.get("source_confidence", "").strip()
        if source_confidence:
            queryset = queryset.filter(
                Q(programs__source_confidence=source_confidence)
                | Q(subject_rankings__confidence=source_confidence)
                | Q(ranking_confidence=source_confidence)
            )
            uses_related_filter = True

        for field_name in ("global_rank", "qs_ranking", "the_rank", "national_rank"):
            min_value = params.get(f"{field_name}_min", "").strip()
            max_value = params.get(f"{field_name}_max", "").strip()
            if min_value.isdigit():
                queryset = queryset.filter(**{f"{field_name}__gte": int(min_value)})
            if max_value.isdigit():
                queryset = queryset.filter(**{f"{field_name}__lte": int(max_value)})

        return queryset.distinct() if uses_related_filter else queryset

    def _apply_cost_status_filter(self, queryset):
        cost_status = self.request.query_params.get("cost_status", "")
        if cost_status not in {"within_budget", "above_budget", "needs_aid"}:
            return queryset

        user = self.request.user
        profile = getattr(user, "student_profile", None) if user.is_authenticated else None
        budget_amount = getattr(profile, "annual_budget_amount", None) if profile else None
        if profile is None or budget_amount is None:
            # No budget entered yet: budget-dependent filters can't be
            # evaluated honestly, so they're a no-op rather than hiding
            # everything or guessing.
            return queryset

        budget_currency = getattr(profile, "annual_budget_currency", "") or "USD"
        budget_usd, _rate, _status = normalize_amount_to_usd(budget_amount, budget_currency)
        if budget_usd is None:
            return queryset

        needs_aid_signal = profile.scholarship_need == profile.ScholarshipNeed.YES
        if cost_status == "needs_aid" and not needs_aid_signal:
            return queryset.none()
        if cost_status == "above_budget" and needs_aid_signal:
            return queryset.none()

        cost_known = Q(total_cost_usd_amount__isnull=False) | Q(tuition_usd_amount__isnull=False)
        within = Q(total_cost_usd_amount__lte=budget_usd) | Q(
            total_cost_usd_amount__isnull=True, tuition_usd_amount__lte=budget_usd
        )
        if cost_status == "within_budget":
            return queryset.filter(cost_known).filter(within)
        # above_budget and needs_aid share the same "cost exceeds budget" set;
        # which label applies depends on the user's own aid signal, checked above.
        return queryset.filter(cost_known).exclude(within)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["saved_university_ids"] = set(
                SavedUniversity.objects.filter(user=user).values_list("university_id", flat=True)
            )
        context["include_program_matching"] = self.action == "retrieve"
        return context

    def get_permissions(self):
        if self.action in SELF_SERVICE_ACTIONS:
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=["get"], url_path="fit")
    def fit(self, request, slug=None):
        # Deterministic-first (PERFORMANCE-011 PART 5): always fast, never
        # calls AI. `semantic_fit_status` is a pure cache read -- the only
        # code path that can call AI is the explicit POST below.
        university = self.get_object()
        profile, _ = get_profile_records_for_read(request.user)
        deterministic_fit = calculate_university_fit(profile, university)
        status_value, semantic_record = semantic_fit_status(request.user, university)
        return Response(build_fit_response(deterministic_fit, status_value, semantic_record))

    @action(
        detail=True,
        methods=["post"],
        url_path="fit/refresh",
        throttle_classes=[ScopedRateThrottle, ScopedIPRateThrottle],
        throttle_scope="ai_fit_refresh",
    )
    def refresh_fit(self, request, slug=None):
        # Explicit user action only. Returns the same shape as GET .../fit/
        # plus `refresh_reason` so the caller can tell a fresh AI result apart
        # from a rate-limit/unavailable/no-op-because-already-cached response.
        university = self.get_object()
        result = refresh_semantic_fit(request.user, university)
        profile, _ = ensure_profile_records(request.user)
        deterministic_fit = calculate_university_fit(profile, university)
        status_value, semantic_record = semantic_fit_status(request.user, university)
        payload = build_fit_response(deterministic_fit, status_value, semantic_record)
        payload["refresh_reason"] = result["reason"]
        return Response(payload)

    @action(detail=True, methods=["post", "delete"], url_path="shortlist")
    def shortlist(self, request, slug=None):
        university = self.get_object()
        if request.method == "POST":
            saved, created = SavedUniversity.objects.get_or_create(
                user=request.user, university=university
            )
            if created:
                track_event(
                    user=request.user,
                    event_type=AnalyticsEvent.EventType.UNIVERSITY_SHORTLISTED,
                    entity_type="university",
                    entity_id=university.id,
                )
                invalidate_recommendation_caches(request.user)
            serializer = SavedUniversitySerializer(
                saved, context=self.get_serializer_context()
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        deleted, _ = SavedUniversity.objects.filter(user=request.user, university=university).delete()
        if deleted:
            invalidate_recommendation_caches(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="shortlist")
    def shortlisted(self, request):
        is_lite = request.query_params.get("lite") in ("1", "true", "True")
        queryset = SavedUniversity.objects.filter(user=request.user).select_related("university")
        if not is_lite:
            # The lite payload only needs University's own columns (covered by
            # select_related above); the full payload nests programs/rankings/
            # requirements/scholarships/data_sources/field_verifications, so
            # prefetch those once here instead of per-row N+1 queries.
            # UniversitySubjectRankingSerializer also reads `.program.name` per
            # ranking, so select_related("program") on both ranking prefetches
            # avoids a query per ranking on top of the prefetch itself.
            rankings_with_program = UniversitySubjectRanking.objects.select_related("program")
            queryset = queryset.prefetch_related(
                Prefetch("university__programs__subject_rankings", queryset=rankings_with_program),
                Prefetch("university__subject_rankings", queryset=rankings_with_program),
                "university__requirements",
                "university__scholarships",
                "university__data_sources",
                "university__field_verifications",
            )
        queryset = queryset.order_by("-created_at")

        self.pagination_class = CompactListPagination
        page = self.paginate_queryset(queryset)
        serializer_class = SavedUniversityLiteSerializer if is_lite else SavedUniversitySerializer
        serializer = serializer_class(
            page if page is not None else queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"], url_path="pin")
    def pin(self, request, slug=None):
        """022 Phase 11: pinning always keeps a university in the student's
        recommendation list (with an honestly computed fit label) regardless
        of quota/diversity capping.
        """

        university = self.get_object()
        if request.method == "POST":
            ExcludedUniversity.objects.filter(user=request.user, university=university).delete()
            pinned, created = PinnedUniversity.objects.get_or_create(user=request.user, university=university)
            if created:
                invalidate_recommendation_caches(request.user)
                track_event(
                    user=request.user,
                    event_type=AnalyticsEvent.EventType.UNIVERSITY_PINNED,
                    entity_type="university",
                    entity_id=university.id,
                )
            serializer = PinnedUniversitySerializer(pinned, context=self.get_serializer_context())
            return Response(
                serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        deleted, _ = PinnedUniversity.objects.filter(user=request.user, university=university).delete()
        if deleted:
            invalidate_recommendation_caches(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="pinned")
    def pinned(self, request):
        queryset = (
            PinnedUniversity.objects.filter(user=request.user)
            .select_related("university")
            .order_by("-created_at")
        )
        serializer = PinnedUniversitySerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"], url_path="exclude")
    def exclude(self, request, slug=None):
        """022 Phase 11: an explicit, unconditional veto -- takes priority
        over a pin for the same university (see calculate_university_recommendations).
        """

        university = self.get_object()
        if request.method == "POST":
            PinnedUniversity.objects.filter(user=request.user, university=university).delete()
            excluded, created = ExcludedUniversity.objects.get_or_create(
                user=request.user, university=university
            )
            if created:
                invalidate_recommendation_caches(request.user)
                track_event(
                    user=request.user,
                    event_type=AnalyticsEvent.EventType.UNIVERSITY_EXCLUDED,
                    entity_type="university",
                    entity_id=university.id,
                )
            serializer = ExcludedUniversitySerializer(excluded, context=self.get_serializer_context())
            return Response(
                serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        deleted, _ = ExcludedUniversity.objects.filter(user=request.user, university=university).delete()
        if deleted:
            invalidate_recommendation_caches(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="excluded")
    def excluded(self, request):
        queryset = (
            ExcludedUniversity.objects.filter(user=request.user)
            .select_related("university")
            .order_by("-created_at")
        )
        serializer = ExcludedUniversitySerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=["get", "patch"], url_path="recommendation-preferences")
    def recommendation_preferences(self, request):
        _, preferences = ensure_profile_records(request.user)
        if request.method == "GET":
            return Response(RecommendationPreferenceSerializer(preferences).data)
        serializer = RecommendationPreferenceSerializer(preferences, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_recommendation_caches(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="recommendation-explanation")
    def recommendation_explanation(self, request, slug=None):
        university = self.get_object()
        profile, preferences = get_profile_records_for_read(request.user)
        return Response(explain_recommendation_for_university(profile, university, preferences))

    @action(detail=False, methods=["get"], url_path="compare")
    def compare(self, request):
        raw_ids = [value.strip() for value in request.query_params.get("ids", "").split(",") if value.strip()]
        if len(raw_ids) < 2 or len(raw_ids) > 4:
            raise ValidationError(
                {"ids": "Provide between 2 and 4 university ids separated by commas."}
            )
        try:
            ids = [int(value) for value in raw_ids]
        except ValueError as exc:
            raise ValidationError({"ids": "University ids must be integers."}) from exc

        by_id = {university.id: university for university in self.get_queryset().filter(id__in=ids)}
        ordered = [by_id[item_id] for item_id in ids if item_id in by_id]
        if len(ordered) != len(ids):
            raise ValidationError({"ids": "One or more universities were not found."})

        serializer = self.get_serializer(ordered, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="recommendations")
    def recommendations(self, request):
        # Short-TTL cache (PERFORMANCE-011 PART 7): this scans the whole
        # published catalogue, so it's the heaviest of the self-service
        # actions. See recommendation_cache.py for why the TTL is short and
        # why shortlist/tracking actions explicitly invalidate it.
        payload = cache.get_or_set(
            recommendations_cache_key(request.user),
            lambda: calculate_university_recommendations(
                *get_profile_records_for_read(request.user)
            ),
            RECOMMENDATIONS_CACHE_SECONDS,
        )
        # 022 Phase 13: log every list the student is actually shown (not just
        # cache misses) so future ranking work has real impression history to
        # evaluate against -- see track_event() for the sanitization guarantee.
        track_event(
            user=request.user,
            event_type=AnalyticsEvent.EventType.RECOMMENDATION_IMPRESSION,
            entity_type="recommendation_list",
            metadata={
                "result_count": len(payload.get("recommendations", [])),
                "excluded_by_user_count": payload.get("excluded_by_user_count", 0),
                "list_size_limited": bool(payload.get("list_size_limited")),
            },
        )
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="strategy")
    def strategy(self, request):
        payload = cache.get_or_set(
            strategy_cache_key(request.user),
            lambda: build_application_strategy(*get_profile_records_for_read(request.user)),
            STRATEGY_CACHE_SECONDS,
        )
        return Response(payload)


class AdminUniversityImportBaseView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "university_import"
    mode: str

    def post(self, request):
        upload_serializer = UniversityImportUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        job = enqueue_university_import_job(
            uploaded_by=request.user,
            mode=self.mode,
            uploaded_file=upload_serializer.validated_data["file"],
        )
        return Response(
            UniversityImportJobSerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )


class AdminUniversityImportDryRunView(AdminUniversityImportBaseView):
    mode = UniversityImportJob.Mode.DRY_RUN


class AdminUniversityImportExecuteView(AdminUniversityImportBaseView):
    mode = UniversityImportJob.Mode.EXECUTE


class AdminUniversityImportJobDetailView(RetrieveAPIView):
    serializer_class = UniversityImportJobSerializer
    permission_classes = [IsAdminRole]
    queryset = UniversityImportJob.objects.select_related("uploaded_by")

    def get_object(self):
        job = super().get_object()
        if mark_stale_university_import_job(job):
            job.refresh_from_db()
        return job


_OPEN_MODERATION_STATUSES = (
    UniversityModerationRecord.Status.PENDING_REVIEW,
    UniversityModerationRecord.Status.NEEDS_UPDATE,
)
_TERMINAL_MODERATION_STATUSES = {
    UniversityModerationRecord.Status.VERIFIED,
    UniversityModerationRecord.Status.REJECTED,
    UniversityModerationRecord.Status.ARCHIVED,
}


class AdminUniversityReviewQueueView(ListAPIView):
    """The one open (pending/needs-update) moderation record per university.

    Uses a plain Python reduction rather than Postgres-only `DISTINCT ON`,
    since local dev and tests run against SQLite.
    """

    serializer_class = UniversityModerationRecordSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        records = (
            UniversityModerationRecord.objects.filter(status__in=_OPEN_MODERATION_STATUSES)
            .select_related("university", "created_by", "resolved_by")
            .order_by("university_id", "-created_at")
        )
        latest_by_university: dict[int, UniversityModerationRecord] = {}
        for record in records:
            latest_by_university.setdefault(record.university_id, record)
        return list(latest_by_university.values())


class AdminUniversityModerationActionView(GenericAPIView):
    serializer_class = UniversityModerationActionSerializer
    permission_classes = [IsAdminRole]

    def patch(self, request, *args, **kwargs):
        university = get_object_or_404(University, pk=kwargs["pk"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        is_terminal = data["status"] in _TERMINAL_MODERATION_STATUSES
        record = UniversityModerationRecord.objects.create(
            university=university,
            status=data["status"],
            field_name=data.get("field_name", ""),
            issue_type=data["issue_type"],
            description=data.get("description", ""),
            created_by=request.user,
            resolved_by=request.user if is_terminal else None,
            resolved_at=timezone.now() if is_terminal else None,
        )
        track_event(
            user=request.user,
            event_type=AnalyticsEvent.EventType.ADMIN_MODERATION_ACTION,
            entity_type="university",
            entity_id=university.id,
            metadata={"status": data["status"]},
        )
        return Response(
            UniversityModerationRecordSerializer(record).data, status=status.HTTP_201_CREATED
        )


class AdminRecommendationDiagnosticsView(APIView):
    """022 Phase 12: authorized-internal-only trace of how a specific
    student's recommendation list was built (candidate pool size, hard-filter
    removal reason codes, category-cap outcomes, cache hit/miss). Admin-gated
    like every other Admin* view in this module -- never reachable by an
    ordinary user, and never returns another user's data to a non-admin.
    """

    permission_classes = [IsAdminRole]

    def get(self, request, user_id: int):
        target_user = get_object_or_404(User, pk=user_id)
        profile, preferences = get_profile_records_for_read(target_user)
        return Response(diagnose_university_recommendations(profile, preferences))

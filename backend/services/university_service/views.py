from django.db.models import F, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from common.permissions import IsAdminOrReadOnly, IsAdminRole
from services.user_profile_service.services import ensure_profile_records

from .currency import normalize_amount_to_usd
from .import_jobs import enqueue_university_import_job, mark_stale_university_import_job
from .models import (
    SavedUniversity,
    University,
    UniversityFieldVerification,
    UniversityImportJob,
    UniversityProgram,
)
from .recommendations import calculate_university_recommendations
from .serializers import (
    SavedUniversitySerializer,
    UniversityImportJobSerializer,
    UniversityImportUploadSerializer,
    UniversitySerializer,
)
from .services import calculate_university_fit
from .strategy import build_application_strategy

SELF_SERVICE_ACTIONS = {
    "list",
    "retrieve",
    "fit",
    "filter_options",
    "shortlist",
    "shortlisted",
    "compare",
    "recommendations",
    "strategy",
}

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


class UniversityViewSet(ModelViewSet):
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

    def get_queryset(self):
        queryset = University.objects.prefetch_related(
            "programs",
            "programs__subject_rankings",
            "subject_rankings",
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
        queryset = University.objects.filter(is_published=True)
        if not (request.user.is_authenticated and request.user.is_admin_role):
            queryset = queryset.exclude(is_demo=True)
        elif request.query_params.get("include_demo", "").lower() != "true":
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
        return Response(
            {
                "countries": distinct_text("country"),
                "cities": distinct_text("city"),
                "institution_types": [
                    choice
                    for choice, _label in University.InstitutionType.choices
                    if queryset.filter(institution_type=choice).exists()
                ],
                "cost_confidences": distinct_text("currency_conversion_confidence"),
                "verification_statuses": [
                    choice for choice, _label in UniversityFieldVerification.Status.choices
                ],
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
        )

    def _apply_program_and_ranking_filters(self, queryset):
        params = self.request.query_params
        major_cluster = params.get("major_cluster", "").strip()
        if major_cluster:
            queryset = queryset.filter(programs__major_cluster=major_cluster)

        program_search = params.get("program_search", "").strip()
        if program_search:
            queryset = queryset.filter(programs__name__icontains=program_search)

        subject_area = params.get("subject_area", "").strip()
        if subject_area:
            queryset = queryset.filter(subject_rankings__subject_area__icontains=subject_area)

        ranking_source = params.get("ranking_source", "").strip()
        if ranking_source:
            queryset = queryset.filter(subject_rankings__source_name__icontains=ranking_source)

        subject_rank_min = params.get("subject_rank_min", "").strip()
        if subject_rank_min.isdigit():
            queryset = queryset.filter(subject_rankings__rank__gte=int(subject_rank_min))

        subject_rank_max = params.get("subject_rank_max", "").strip()
        if subject_rank_max.isdigit():
            queryset = queryset.filter(subject_rankings__rank__lte=int(subject_rank_max))

        has_subject_ranking = params.get("has_subject_ranking", "").lower()
        if has_subject_ranking == "true":
            queryset = queryset.filter(subject_rankings__isnull=False)
        elif has_subject_ranking == "false":
            queryset = queryset.filter(subject_rankings__isnull=True)

        for key in ("portfolio_required", "research_heavy", "stem_heavy", "interdisciplinary"):
            value = params.get(key, "").lower()
            if value == "true":
                queryset = queryset.filter(**{f"programs__{key}": True})
            elif value == "false":
                queryset = queryset.filter(**{f"programs__{key}": False})

        source_confidence = params.get("source_confidence", "").strip()
        if source_confidence:
            queryset = queryset.filter(
                Q(programs__source_confidence=source_confidence)
                | Q(subject_rankings__confidence=source_confidence)
                | Q(ranking_confidence=source_confidence)
            )

        for field_name in ("global_rank", "qs_ranking", "the_rank", "national_rank"):
            min_value = params.get(f"{field_name}_min", "").strip()
            max_value = params.get(f"{field_name}_max", "").strip()
            if min_value.isdigit():
                queryset = queryset.filter(**{f"{field_name}__gte": int(min_value)})
            if max_value.isdigit():
                queryset = queryset.filter(**{f"{field_name}__lte": int(max_value)})

        return queryset.distinct()

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
        university = self.get_object()
        profile, _ = ensure_profile_records(request.user)
        return Response(calculate_university_fit(profile, university))

    @action(detail=True, methods=["post", "delete"], url_path="shortlist")
    def shortlist(self, request, slug=None):
        university = self.get_object()
        if request.method == "POST":
            saved, created = SavedUniversity.objects.get_or_create(
                user=request.user, university=university
            )
            serializer = SavedUniversitySerializer(
                saved, context=self.get_serializer_context()
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        SavedUniversity.objects.filter(user=request.user, university=university).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="shortlist")
    def shortlisted(self, request):
        queryset = (
            SavedUniversity.objects.filter(user=request.user)
            .select_related("university")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(queryset)
        serializer = SavedUniversitySerializer(
            page if page is not None else queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

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
        profile, preferences = ensure_profile_records(request.user)
        return Response(calculate_university_recommendations(profile, preferences))

    @action(detail=False, methods=["get"], url_path="strategy")
    def strategy(self, request):
        profile, preferences = ensure_profile_records(request.user)
        return Response(build_application_strategy(profile, preferences))


class AdminUniversityImportBaseView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
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

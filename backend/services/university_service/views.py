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

from .import_jobs import enqueue_university_import_job, mark_stale_university_import_job
from .models import SavedUniversity, University, UniversityImportJob
from .recommendations import calculate_university_recommendations
from .serializers import (
    SavedUniversitySerializer,
    UniversityImportJobSerializer,
    UniversityImportUploadSerializer,
    UniversitySerializer,
)
from .services import calculate_university_fit

SELF_SERVICE_ACTIONS = {
    "list",
    "retrieve",
    "fit",
    "shortlist",
    "shortlisted",
    "compare",
    "recommendations",
}


class UniversityViewSet(ModelViewSet):
    serializer_class = UniversitySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    search_fields = ("name", "city", "country", "programs__name")
    filterset_fields = ("country", "institution_type", "scholarship_available", "test_policy")
    ordering_fields = (
        "name",
        "country",
        "created_at",
        "acceptance_rate",
        "tuition_usd_amount",
        "total_cost_usd_amount",
    )

    def get_queryset(self):
        queryset = University.objects.prefetch_related(
            "programs",
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

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["saved_university_ids"] = set(
                SavedUniversity.objects.filter(user=user).values_list("university_id", flat=True)
            )
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

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from common.throttling import ScopedIPRateThrottle
from services.activity_service.models import AnalyticsEvent
from services.activity_service.services import track_event
from services.notification_service.models import Notification
from services.notification_service.services import create_notification

from .ai_scoring import score_essay as run_essay_scoring
from .feedback_engine import generate_feedback
from .models import EssayFeedback, EssayRevisionTask, EssayWorkspace
from .serializers import (
    AIEssayScoreReportSerializer,
    EssayFeedbackSerializer,
    EssayRevisionTaskCreateSerializer,
    EssayRevisionTaskSerializer,
    EssayWorkspaceListSerializer,
    EssayWorkspaceSerializer,
)
from .suggestion_engine import generate_essay_suggestions

AI_SCORE_REASON_STATUS = {
    "cached": status.HTTP_200_OK,
    "scored": status.HTTP_201_CREATED,
    "quota_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
    # Both of these mean "the AI path did not produce a usable score this
    # time" from the client's point of view -- a provider-level failure
    # (timeout/network/malformed response) and a response that failed our own
    # strict schema/content validation are both retryable, temporary, and
    # never a raw backend crash. Using the same 503 (not 502, which implies a
    # broken gateway/infra) keeps the frontend's error handling uniform and
    # avoids surfacing an alarming "Bad Gateway" for what is actually a
    # controlled, sanitized response with a JSON body.
    "ai_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "validation_failed": status.HTTP_503_SERVICE_UNAVAILABLE,
    "missing_essay_text": status.HTTP_400_BAD_REQUEST,
    "essay_too_long": status.HTTP_400_BAD_REQUEST,
    # A review is already running for this exact essay (another tab, a
    # double-click, or a client retry after what looked like a timeout but
    # hadn't actually finished) -- 409 Conflict, not a failure of this request.
    "review_already_running": status.HTTP_409_CONFLICT,
}


class EssayWorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = EssayWorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return EssayWorkspaceListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = (
            EssayWorkspace.objects.filter(user=self.request.user)
            .select_related("university", "application", "application__university")
            .prefetch_related("feedback_entries", "revision_tasks")
        )
        # `EssayWorkspaceSerializer` never serializes ai_score_reports (each
        # report carries a raw_output_json blob), so only prefetch it for the
        # actions that actually read it -- prefetching it for every list/
        # retrieve call was pure wasted memory across every essay in the page.
        if self.action in ("scores", "score_latest"):
            queryset = queryset.prefetch_related("ai_score_reports")
        return queryset

    def get_throttles(self):
        if self.action == "score":
            self.throttle_scope = "ai_essay_score"
            return [ScopedRateThrottle(), ScopedIPRateThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="feedback")
    def feedback(self, request, pk=None):
        essay = self.get_object()

        if request.method == "GET":
            latest = essay.feedback_entries.first()
            if latest is None:
                return Response({"detail": "No feedback has been generated yet.", "feedback": None})
            return Response({"detail": "", "feedback": EssayFeedbackSerializer(latest).data})

        result = generate_feedback(essay)
        revision_task_payload = result.pop("revision_tasks")
        feedback_entry = EssayFeedback.objects.create(
            essay=essay,
            overall_label=result["overall_label"],
            structure_score=result["structure_score"],
            clarity_score=result["clarity_score"],
            authenticity_score=result["authenticity_score"],
            specificity_score=result["specificity_score"],
            grammar_score=result["grammar_score"],
            prompt_fit_score=result["prompt_fit_score"],
            word_count=result["word_count"],
            word_limit_status=result["word_limit_status"],
            summary=result["summary"],
            strengths=result["strengths"],
            issues=result["issues"],
            revision_tasks=revision_task_payload,
        )

        for item in revision_task_payload:
            existing = essay.revision_tasks.filter(
                category=item["category"], status=EssayRevisionTask.Status.TODO
            ).first()
            if existing:
                existing.title = item["title"]
                existing.description = item["description"]
                existing.save(update_fields=["title", "description"])
            else:
                EssayRevisionTask.objects.create(
                    essay=essay,
                    category=item["category"],
                    title=item["title"],
                    description=item["description"],
                )

        essay.last_reviewed_at = timezone.now()
        if essay.status in (
            EssayWorkspace.Status.SUGGESTED,
            EssayWorkspace.Status.PLANNED,
            EssayWorkspace.Status.NOT_STARTED,
        ) and result["word_count"] > 0:
            essay.status = EssayWorkspace.Status.DRAFTING
        if revision_task_payload and essay.status not in (
            EssayWorkspace.Status.SUBMITTED,
            EssayWorkspace.Status.READY,
        ):
            essay.status = EssayWorkspace.Status.NEEDS_REVISION
        elif not revision_task_payload and essay.status == EssayWorkspace.Status.NEEDS_REVISION:
            essay.status = EssayWorkspace.Status.REVIEWED
        essay.save(update_fields=["last_reviewed_at", "status", "updated_at"])

        return Response(
            {
                "detail": "",
                "feedback": EssayFeedbackSerializer(feedback_entry).data,
                "essay": EssayWorkspaceSerializer(essay, context=self.get_serializer_context()).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="score")
    def score(self, request, pk=None):
        essay = self.get_object()
        result = run_essay_scoring(essay, user=request.user)
        report = result["report"]
        track_event(
            user=request.user,
            event_type=AnalyticsEvent.EventType.ESSAY_REVIEW_REQUESTED,
            entity_type="essay",
            entity_id=essay.id,
            metadata={"reason": result["reason"]},
        )
        if result["reason"] == "scored" and report is not None:
            create_notification(
                user=request.user,
                notification_type=Notification.NotificationType.ESSAY_REVIEW_COMPLETED,
                title=f'Essay review ready for "{essay.title}"',
                message=f"Overall essay readiness: {report.overall_essay_readiness}/10.",
                action_url="/essays",
                related_entity_type="essay",
                related_entity_id=essay.id,
                dedup_key=f"essay_review_completed:{report.id}",
            )
        return Response(
            {
                "reason": result["reason"],
                "cached": result["cached"],
                "quota_remaining": result["quota_remaining"],
                "next_available_at": result["next_available_at"],
                "validation_code": result["validation_code"],
                "ai_error_kind": result["ai_error_kind"],
                "score": AIEssayScoreReportSerializer(report).data if report else None,
            },
            status=AI_SCORE_REASON_STATUS[result["reason"]],
        )

    @action(detail=True, methods=["get"], url_path="scores")
    def scores(self, request, pk=None):
        essay = self.get_object()
        reports = essay.ai_score_reports.all()
        return Response({"results": AIEssayScoreReportSerializer(reports, many=True).data})

    @action(detail=True, methods=["get"], url_path="score/latest")
    def score_latest(self, request, pk=None):
        essay = self.get_object()
        latest = essay.ai_score_reports.first()
        return Response({"score": AIEssayScoreReportSerializer(latest).data if latest else None})

    @action(detail=True, methods=["post"], url_path="revision-tasks")
    def create_revision_task(self, request, pk=None):
        essay = self.get_object()
        serializer = EssayRevisionTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(essay=essay)
        return Response(
            EssayRevisionTaskSerializer(task).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="generate-suggestions")
    def generate_suggestions(self, request):
        result = generate_essay_suggestions(request.user)
        queryset = self.get_queryset().filter(
            id__in=[essay.id for essay in [*result.created, *result.existing]]
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "created_count": len(result.created),
                "existing_count": len(result.existing),
                "essays": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class EssayRevisionTaskViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EssayRevisionTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EssayRevisionTask.objects.filter(essay__user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_status = serializer.validated_data.get("status", instance.status)
        if new_status == EssayRevisionTask.Status.COMPLETED and instance.completed_at is None:
            serializer.save(completed_at=timezone.now())
        else:
            serializer.save()

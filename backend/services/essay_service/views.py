from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .feedback_engine import generate_feedback
from .models import EssayFeedback, EssayRevisionTask, EssayWorkspace
from .serializers import (
    EssayFeedbackSerializer,
    EssayRevisionTaskCreateSerializer,
    EssayRevisionTaskSerializer,
    EssayWorkspaceSerializer,
)


class EssayWorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = EssayWorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            EssayWorkspace.objects.filter(user=self.request.user)
            .select_related("university")
            .prefetch_related("feedback_entries", "revision_tasks")
        )

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
        if essay.status == EssayWorkspace.Status.NOT_STARTED and result["word_count"] > 0:
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

    @action(detail=True, methods=["post"], url_path="revision-tasks")
    def create_revision_task(self, request, pk=None):
        essay = self.get_object()
        serializer = EssayRevisionTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(essay=essay)
        return Response(
            EssayRevisionTaskSerializer(task).data, status=status.HTTP_201_CREATED
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

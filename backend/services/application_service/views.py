from django.db import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ApplicationMilestone, ApplicationTrackerItem
from .serializers import (
    ApplicationMilestoneCreateSerializer,
    ApplicationMilestoneSerializer,
    ApplicationTrackerItemSerializer,
)


class ApplicationTrackerViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationTrackerItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("status", "university")

    def get_queryset(self):
        return (
            ApplicationTrackerItem.objects.filter(user=self.request.user)
            .select_related("university", "target_program")
            .prefetch_related("milestones")
        )

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError as exc:
            raise ValidationError(
                {"university": "You already have an application tracker item for this university."}
            ) from exc

    @action(detail=True, methods=["get", "post"], url_path="milestones")
    def milestones(self, request, pk=None):
        application = self.get_object()

        if request.method == "GET":
            milestones = application.milestones.all()
            return Response(ApplicationMilestoneSerializer(milestones, many=True).data)

        serializer = ApplicationMilestoneCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        milestone = serializer.save(application=application)
        return Response(
            ApplicationMilestoneSerializer(milestone).data, status=status.HTTP_201_CREATED
        )


class ApplicationMilestoneViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ApplicationMilestoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ApplicationMilestone.objects.filter(application__user=self.request.user)

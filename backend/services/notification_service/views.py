from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
    NotificationStatusUpdateSerializer,
)
from .services import ensure_notification_preference


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter in Notification.Status.values:
            queryset = queryset.filter(status=status_filter)
        return queryset


class NotificationStatusUpdateView(generics.GenericAPIView):
    serializer_class = NotificationStatusUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def patch(self, request, pk=None):
        notification = generics.get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification.status = serializer.validated_data["status"]
        notification.save(update_fields=["status"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(
            user=request.user, status=Notification.Status.UNREAD
        ).update(status=Notification.Status.READ)
        return Response({"updated": updated})


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        preference = ensure_notification_preference(request.user)
        return Response(NotificationPreferenceSerializer(preference).data)

    def patch(self, request):
        preference = ensure_notification_preference(request.user)
        serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

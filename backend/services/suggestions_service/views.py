from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SuggestedItem
from .serializers import SuggestedItemSerializer
from .services import add_suggestion_to_roadmap, generate_suggestions


class SuggestionQuerysetMixin:
    def get_queryset(self):
        queryset = SuggestedItem.objects.filter(user=self.request.user).select_related(
            "linked_university",
            "linked_application__university",
            "linked_essay",
            "linked_roadmap_task",
        )
        status_param = self.request.query_params.get("status", SuggestedItem.Status.ACTIVE)
        if status_param:
            queryset = queryset.filter(status=status_param)
        suggestion_type = self.request.query_params.get("suggestion_type")
        if suggestion_type:
            queryset = queryset.filter(suggestion_type=suggestion_type)
        linked_university = self.request.query_params.get("linked_university")
        if linked_university:
            queryset = queryset.filter(linked_university_id=linked_university)
        linked_application = self.request.query_params.get("linked_application")
        if linked_application:
            queryset = queryset.filter(linked_application_id=linked_application)
        linked_essay = self.request.query_params.get("linked_essay")
        if linked_essay:
            queryset = queryset.filter(linked_essay_id=linked_essay)
        return queryset


class SuggestionListView(SuggestionQuerysetMixin, generics.ListAPIView):
    serializer_class = SuggestedItemSerializer
    permission_classes = [IsAuthenticated]


class GenerateSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        items = generate_suggestions(request.user)
        serializer = SuggestedItemSerializer(items, many=True, context={"request": request})
        return Response({"suggestions": serializer.data})


class AddSuggestionToRoadmapView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        suggestion = generics.get_object_or_404(
            SuggestedItem.objects.filter(user=request.user),
            pk=pk,
        )
        task = add_suggestion_to_roadmap(suggestion)
        serializer = SuggestedItemSerializer(suggestion, context={"request": request})
        return Response(
            {"suggestion": serializer.data, "roadmap_task_id": task.id},
            status=status.HTTP_201_CREATED,
        )


class DismissSuggestionView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        suggestion = generics.get_object_or_404(
            SuggestedItem.objects.filter(user=request.user),
            pk=pk,
        )
        suggestion.status = SuggestedItem.Status.DISMISSED
        suggestion.dismissed_at = timezone.now()
        suggestion.save(update_fields=("status", "dismissed_at", "updated_at"))
        serializer = SuggestedItemSerializer(suggestion, context={"request": request})
        return Response(serializer.data)

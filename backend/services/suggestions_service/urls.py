from django.urls import path

from .views import (
    AddSuggestionToRoadmapView,
    DismissSuggestionView,
    GenerateSuggestionsView,
    SuggestionListView,
)

urlpatterns = [
    path("", SuggestionListView.as_view(), name="suggestion-list"),
    path("generate/", GenerateSuggestionsView.as_view(), name="suggestion-generate"),
    path(
        "<int:pk>/add-to-roadmap/",
        AddSuggestionToRoadmapView.as_view(),
        name="suggestion-add-to-roadmap",
    ),
    path("<int:pk>/dismiss/", DismissSuggestionView.as_view(), name="suggestion-dismiss"),
]

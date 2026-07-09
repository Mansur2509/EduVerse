from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.permissions import IsAdminRole
from services.user_profile_service.services import ensure_profile_records

from .recommendations import compute_profile_recommendations
from .serializers import AIProfileAssessmentSerializer
from .services import (
    DISCLAIMER,
    get_latest_valid_assessment,
    latest_assessment_envelope,
    run_profile_assessment,
)
from .strategy import build_profile_strategy

User = get_user_model()


def _serialize_envelope(result):
    return {
        "assessment": AIProfileAssessmentSerializer(result.assessment).data
        if result.assessment
        else None,
        "cached": result.cached,
        "reason": result.reason,
        "can_refresh": result.can_refresh,
        "next_available_at": result.next_available_at,
        "ai_available": result.ai_available,
        "disclaimer": DISCLAIMER,
    }


class LatestProfileAssessmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize_envelope(latest_assessment_envelope(request.user)))


class RunProfileAssessmentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def post(self, request):
        return Response(_serialize_envelope(run_profile_assessment(request.user)))


class AdminRunProfileAssessmentView(APIView):
    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def post(self, request, user_id: int):
        target_user = get_object_or_404(User, pk=user_id)
        return Response(
            _serialize_envelope(run_profile_assessment(target_user, force=True))
        )


class ProfileRecommendationsView(APIView):
    """PROTOCOL-008 PART 7/9: gap-based recommendations from the cached
    assessment only. Never triggers a fresh AI call on render -- if nothing
    is cached yet, this reports `needs_assessment` instead.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        assessment = get_latest_valid_assessment(request.user)
        if assessment is None:
            return Response({"recommendations": [], "needs_assessment": True})
        return Response(
            {
                "recommendations": compute_profile_recommendations(assessment),
                "needs_assessment": False,
            }
        )


class ProfileStrategyView(APIView):
    """PROTOCOL-008 PART 7/10: the 7/30/90-day + before-deadline action plan.
    Built from real tracked applications, exam dates, and evidence gaps --
    never triggers a fresh AI call on render. Works even before any profile
    assessment has run, since deadlines/exams/essays/recommenders are real
    data independent of AI; `needs_assessment` only flags that the
    benchmark-gap framing is not yet available.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, preferences = ensure_profile_records(request.user)
        assessment = get_latest_valid_assessment(request.user)
        strategy = build_profile_strategy(request.user, profile, preferences, assessment)
        return Response({**strategy, "needs_assessment": assessment is None})

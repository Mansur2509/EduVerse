from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MentorProfile, MentorshipSession
from .serializers import (
    BlockUserSerializer,
    MentorshipSessionSerializer,
    PublicMentorProfileSerializer,
    SessionRequestSerializer,
    SessionStatusUpdateSerializer,
)
from .services import (
    MentorAccessError,
    block_user,
    create_session_request,
    transition_session,
    visible_mentors_queryset,
)

User = get_user_model()


class MentorBrowseView(APIView):
    """Public browse/search surface -- always filtered through
    `visible_mentors_queryset()`, never a raw `MentorProfile.objects.all()`,
    so an unverified mentor can never be discovered here."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # No select_related("user") here: PublicMentorProfileSerializer never
        # touches the related user (see its own docstring), so eager-loading
        # it would just be an unused join on every browse request.
        mentors = visible_mentors_queryset()
        return Response({"results": PublicMentorProfileSerializer(mentors, many=True).data})


class MentorshipSessionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = MentorshipSession.objects.filter(
            student=request.user
        ) | MentorshipSession.objects.filter(mentor__user=request.user)
        return Response(
            {"results": MentorshipSessionSerializer(sessions.distinct(), many=True).data}
        )

    def post(self, request):
        serializer = SessionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mentor = get_object_or_404(MentorProfile, pk=serializer.validated_data["mentor_id"])
        try:
            session = create_session_request(
                student=request.user, mentor=mentor, topic=serializer.validated_data.get("topic", "")
            )
        except MentorAccessError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            MentorshipSessionSerializer(session).data, status=status.HTTP_201_CREATED
        )


class MentorshipSessionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        # select_related("mentor") so transition_session()'s access-check
        # (session.mentor.user_id) doesn't cost a second query on top of
        # this lookup.
        session = get_object_or_404(MentorshipSession.objects.select_related("mentor"), pk=pk)
        serializer = SessionStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            transition_session(
                session=session, actor=request.user, new_status=serializer.validated_data["status"]
            )
        except MentorAccessError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(MentorshipSessionSerializer(session).data)


class BlockMentorUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BlockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blocked_user = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        block_user(blocker=request.user, blocked=blocked_user)
        return Response(status=status.HTTP_204_NO_CONTENT)

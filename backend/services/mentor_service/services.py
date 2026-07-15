"""Mentor marketplace safety foundation (POST-V1-021 Phase 8).

Given a likely-minor user base, every function here defaults to the more
restrictive behavior: unverified mentors are never visible, a block in
either direction blocks new requests in both directions, and no contact
info (email/phone/external handle) is ever returned by any serializer in
this app.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from .models import MentorBlock, MentorProfile, MentorshipSession


class MentorAccessError(Exception):
    pass


def visible_mentors_queryset():
    """The only queryset any student-facing browse/search endpoint may use.
    An unverified or not-accepting mentor never appears here."""
    return MentorProfile.objects.filter(is_verified=True, is_accepting_requests=True)


def is_blocked_pair(*, user_a, user_b) -> bool:
    return MentorBlock.objects.filter(
        Q(blocker=user_a, blocked=user_b) | Q(blocker=user_b, blocked=user_a)
    ).exists()


def create_session_request(*, student, mentor: MentorProfile, topic: str = "") -> MentorshipSession:
    if not mentor.is_verified or not mentor.is_accepting_requests:
        raise MentorAccessError("This mentor is not currently accepting requests.")
    if is_blocked_pair(user_a=student, user_b=mentor.user):
        raise MentorAccessError("You cannot request a session with this mentor.")
    return MentorshipSession.objects.create(mentor=mentor, student=student, topic=topic)


def transition_session(
    *, session: MentorshipSession, actor, new_status: str
) -> MentorshipSession:
    """Enforces both the state machine (see
    `MentorshipSession.ALLOWED_TRANSITIONS`) and that only the mentor or the
    student in this exact session may change its status."""
    if actor.id not in (session.student_id, session.mentor.user_id):
        raise MentorAccessError("You are not part of this session.")
    if not session.can_transition_to(new_status):
        raise ValueError(f"Cannot move a {session.status} session to {new_status}.")
    session.status = new_status
    update_fields = ["status"]
    if new_status in (MentorshipSession.Status.ACCEPTED, MentorshipSession.Status.DECLINED):
        session.responded_at = timezone.now()
        update_fields.append("responded_at")
    session.save(update_fields=update_fields)
    return session


def block_user(*, blocker, blocked) -> MentorBlock:
    block, _ = MentorBlock.objects.get_or_create(blocker=blocker, blocked=blocked)
    return block

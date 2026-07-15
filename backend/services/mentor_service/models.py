from django.conf import settings
from django.db import models


class MentorProfile(models.Model):
    """POST-V1-021 Phase 8: safety-first mentor marketplace foundation.

    `is_verified` gates visibility in every student-facing browse/search
    endpoint -- an unverified mentor is never discoverable. Verification is
    a human/product decision (see docs/POST_V1_PRODUCT_ROADMAP_021.md
    Module E); this foundation only enforces that the gate exists and is
    respected everywhere, not who gets verified."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentor_profile"
    )
    is_verified = models.BooleanField(default=False, db_index=True)
    bio = models.TextField(max_length=2000, blank=True)
    expertise_areas = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    is_accepting_requests = models.BooleanField(default=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"MentorProfile(user={self.user_id}, verified={self.is_verified})"


class MentorAvailabilitySlot(models.Model):
    mentor = models.ForeignKey(
        MentorProfile, on_delete=models.CASCADE, related_name="availability_slots"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ("starts_at",)


class MentorBlock(models.Model):
    """Either party can block the other; blocking is checked in both
    directions before any new session request can be created."""

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentor_blocks_made"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentor_blocks_received"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("blocker", "blocked"), name="unique_mentor_block_pair")
        ]


class MentorshipSession(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    # Transitions a REQUESTED session may legally move to. Every other
    # (from, to) pair is rejected -- e.g. an already-DECLINED session can
    # never later become ACCEPTED.
    ALLOWED_TRANSITIONS = {
        Status.REQUESTED: {Status.ACCEPTED, Status.DECLINED, Status.CANCELLED},
        Status.ACCEPTED: {Status.COMPLETED, Status.CANCELLED},
        Status.DECLINED: set(),
        Status.CANCELLED: set(),
        Status.COMPLETED: set(),
    }

    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name="sessions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentorship_sessions"
    )
    slot = models.ForeignKey(
        MentorAvailabilitySlot, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    topic = models.CharField(max_length=200, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def __str__(self) -> str:
        return f"MentorshipSession(mentor={self.mentor_id}, student={self.student_id}, {self.status})"

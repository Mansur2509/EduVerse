"""Tiny, startup-safe admin bootstrap shared by the management commands and the
seed_demo hook.

It only ever promotes *already-existing* allow-listed users to admin. It never
creates users, never changes passwords, and never touches the university (or any
other heavy) tables — so it is safe to run during web-service startup, unlike the
full demo seeding which performs `update_or_create` on `university_service_university`
and can hit a Supabase statement timeout while locking those rows.
"""

from __future__ import annotations

# Real UniWay operators who should hold admin access (e.g. for the admin-only
# university import page). Add an email here and, once that person has registered,
# the next deploy (or a `bootstrap_admins` run) grants them admin — no Render shell.
KNOWN_ADMIN_EMAILS = (
    "timarus52111@gmail.com",
    "khamidjonovmansurjon@gmail.com",
    "iilich6304@gmail.com",
)

# Fields that define UniWay admin access. `User.is_admin_role` is
# `is_staff or is_superuser or role == "admin"`, checked by the `IsAdminRole`
# permission; `is_superuser` is intentionally left untouched.
ADMIN_ROLE = "admin"


def promote_known_admins(user_model, emails=KNOWN_ADMIN_EMAILS) -> dict[str, list[str]]:
    """Idempotently promote allow-listed existing users to admin.

    Returns a report dict with ``promoted`` / ``already_admin`` / ``missing``
    lists. A missing or ambiguously-matched email is reported, never fatal, and
    never causes a user to be created.
    """
    promoted: list[str] = []
    already_admin: list[str] = []
    missing: list[str] = []

    for email in emails:
        matches = list(user_model.objects.filter(email__iexact=email).order_by("id"))
        if len(matches) != 1:
            missing.append(email)
            continue
        user = matches[0]
        if user.role == ADMIN_ROLE and user.is_staff:
            already_admin.append(user.email)
            continue
        user.role = ADMIN_ROLE
        user.is_staff = True
        user.save(update_fields=["role", "is_staff"])
        promoted.append(user.email)

    return {"promoted": promoted, "already_admin": already_admin, "missing": missing}

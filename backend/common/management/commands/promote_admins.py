from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Promote existing UniWay users to admin access by email."

    def add_arguments(self, parser):
        parser.add_argument(
            "--emails",
            nargs="+",
            required=True,
            help="One or more existing user email addresses to promote.",
        )

    def handle(self, *args, **options):
        raw_emails = options["emails"]
        emails = [email.strip().lower() for email in raw_emails if email.strip()]
        if not emails:
            raise CommandError("Provide at least one non-empty email address.")

        promoted: list[str] = []
        already_admin: list[str] = []
        missing_users: list[str] = []
        skipped: list[str] = []
        seen: set[str] = set()

        for email in emails:
            if email in seen:
                skipped.append(f"{email} (duplicate input)")
                continue
            seen.add(email)

            users = list(User.objects.filter(email__iexact=email).order_by("id"))
            if not users:
                missing_users.append(email)
                continue
            if len(users) > 1:
                skipped.append(f"{email} (multiple case-insensitive matches)")
                continue

            user = users[0]
            if user.is_admin_role and user.role == User.Role.ADMIN and user.is_staff:
                already_admin.append(user.email)
                continue

            user.role = User.Role.ADMIN
            user.is_staff = True
            user.save(update_fields=["role", "is_staff"])
            promoted.append(user.email)

        self._write_report("promoted", promoted)
        self._write_report("already_admin", already_admin)
        self._write_report("missing_users", missing_users)
        self._write_report("skipped", skipped)

    def _write_report(self, label: str, values: list[str]) -> None:
        self.stdout.write(f"{label}:")
        if not values:
            self.stdout.write("- none")
            return
        for value in values:
            self.stdout.write(f"- {value}")

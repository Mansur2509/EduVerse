"""Fast, startup-safe admin bootstrap.

Promotes the allow-listed operators (see common/admin_bootstrap.py) to admin if
they already exist. Designed to be called from the Render start command instead
of the full `seed_demo`:

    python manage.py migrate --noinput && python manage.py bootstrap_admins && gunicorn ...

It never creates users, never touches universities, and is idempotent — so it
cannot lock university rows or time out during web-service startup.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from common.admin_bootstrap import promote_known_admins

User = get_user_model()


class Command(BaseCommand):
    help = "Promote allow-listed existing users to admin (fast, startup-safe; no user creation, no university writes)."

    def handle(self, *args, **options):
        report = promote_known_admins(User)
        for label in ("promoted", "already_admin", "missing"):
            values = report[label]
            self.stdout.write(f"{label}:")
            if values:
                for value in values:
                    self.stdout.write(f"- {value}")
            else:
                self.stdout.write("- none")

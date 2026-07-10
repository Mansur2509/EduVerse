from django.core.management.base import BaseCommand

from services.notification_service.services import generate_all_notifications


class Command(BaseCommand):
    help = (
        "Generate deadline/exam/roadmap/recommendation/essay/event notifications for all "
        "users. Idempotent (safe to run repeatedly, e.g. from a daily cron) -- each "
        "notification has a stable dedup key so re-running never creates duplicates."
    )

    def handle(self, *args, **options):
        counts = generate_all_notifications()
        total = sum(counts.values())
        for label, count in counts.items():
            self.stdout.write(f"  {label}: {count}")
        self.stdout.write(self.style.SUCCESS(f"Created {total} notification(s)."))

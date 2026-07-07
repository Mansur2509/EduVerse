from django.core.management.base import BaseCommand, CommandError

from services.university_service.data_import import (
    ImportConfigurationError,
    import_universities_data,
)


def _safe_line(text: str) -> str:
    """Never let a console-encoding issue on the operator's terminal crash
    report printing -- replace anything the terminal can't display."""
    try:
        return text.encode("ascii", errors="backslashreplace").decode("ascii")
    except Exception:  # noqa: BLE001 - report printing must never raise
        return "(unprintable line)"


class Command(BaseCommand):
    help = (
        "Import the ~450-university / 72-column dataset (public data, "
        "guidance/context layer, and system-only scoring vector). "
        "Always run --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to a .csv, .tsv, or .xlsx file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate only -- rolls back every database change.",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually write changes to the database.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="With --commit: overwrite already-known universities' data instead of skipping them.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Only process the first N data rows (useful for a quick sanity check).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        commit = options["commit"]
        if dry_run == commit:
            raise CommandError("Pass exactly one of --dry-run or --commit.")
        if options["update_existing"] and not commit:
            raise CommandError("--update-existing only applies together with --commit.")

        try:
            summary = import_universities_data(
                options["path"],
                commit=commit,
                update_existing=options["update_existing"],
                limit=options["limit"],
            )
        except ImportConfigurationError as error:
            raise CommandError(str(error)) from error

        mode_label = "COMMITTED" if commit else "DRY RUN (rolled back, nothing was saved)"
        lines = [
            f"mode: {mode_label}",
            f"rows read: {summary.rows_read}",
            f"universities created: {summary.created}",
            f"universities updated: {summary.updated}",
            f"universities skipped (already exist, not updated): {summary.skipped_existing}",
            f"rows skipped due to errors: {summary.skipped_errors}",
            f"rows missing required Name/Country/City: {summary.missing_required}",
            f"duplicate keys within this file: {summary.duplicate_keys_in_file}",
            f"public fields imported (non-empty values set): {summary.public_fields_imported}",
            f"guidance contexts imported: {summary.guidance_contexts_imported}",
            f"signal vectors imported: {summary.signal_vectors_imported}",
            f"warnings: {len(summary.warnings)}",
            f"errors: {len(summary.errors)}",
        ]
        for line in lines:
            self.stdout.write(_safe_line(line))

        if summary.warnings:
            self.stdout.write(self.style.WARNING(f"-- first {min(20, len(summary.warnings))} warnings --"))
            for warning in summary.warnings[:20]:
                self.stdout.write(_safe_line(f"  {warning}"))

        if summary.errors:
            self.stdout.write(self.style.ERROR(f"-- first {min(20, len(summary.errors))} errors --"))
            for error_line in summary.errors[:20]:
                self.stdout.write(_safe_line(f"  {error_line}"))

        if commit:
            self.stdout.write(self.style.SUCCESS("Import committed."))
        else:
            self.stdout.write(self.style.SUCCESS("Dry run complete -- no data was written."))

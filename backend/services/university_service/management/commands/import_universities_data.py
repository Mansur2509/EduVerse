from django.core.management.base import BaseCommand, CommandError

from services.university_service.data_import import (
    ImportConfigurationError,
    import_universities_data,
)


def _safe_line(text: str) -> str:
    try:
        return text.encode("ascii", errors="backslashreplace").decode("ascii")
    except Exception:  # noqa: BLE001 - report printing must never crash
        return "(unprintable line)"


class Command(BaseCommand):
    help = (
        "Clean, dedupe, dry-run, and safely upsert the 72-column university "
        "dataset. Defaults to dry-run unless --commit is passed."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to a .csv, .tsv, or .xlsx file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate only. This is the default when --commit is absent.",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually write safe create/update changes to the database.",
        )
        parser.add_argument(
            "--missing-only",
            action="store_true",
            help="For existing universities, fill only empty/unknown fields.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help=(
                "Allow safe improvement of existing fields. Good existing scalar "
                "values still go to manual review instead of silent overwrite."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Only process the first N data rows.",
        )
        parser.add_argument(
            "--audit-out",
            default=None,
            help="Optional CSV path for cell-level audit output.",
        )
        parser.add_argument(
            "--manual-review-out",
            default=None,
            help="Optional CSV path for ambiguous matches/conflicts.",
        )
        parser.add_argument(
            "--force-reprocess",
            action="store_true",
            help="Reprocess rows even when their row hash was committed before.",
        )

    def handle(self, *args, **options):
        commit = bool(options["commit"])
        if options["dry_run"] and commit:
            raise CommandError("Pass either --dry-run or --commit, not both.")
        if options["update_existing"] and not commit:
            raise CommandError("--update-existing only applies together with --commit.")
        if options["force_reprocess"] and not commit:
            raise CommandError("--force-reprocess only applies together with --commit.")

        missing_only = bool(options["missing_only"] or not options["update_existing"])

        try:
            summary = import_universities_data(
                options["path"],
                commit=commit,
                update_existing=options["update_existing"],
                missing_only=missing_only,
                limit=options["limit"],
                audit_out=options["audit_out"],
                manual_review_out=options["manual_review_out"],
                force_reprocess=options["force_reprocess"],
            )
        except ImportConfigurationError as error:
            raise CommandError(str(error)) from error

        mode_label = "COMMITTED" if commit else "DRY RUN (rolled back, nothing was saved)"
        lines = [
            f"mode: {mode_label}",
            f"rows read: {summary.rows_read}",
            f"universities created: {summary.created}",
            f"universities updated: {summary.updated}",
            f"universities skipped duplicate/already imported: {summary.skipped_duplicate_rows}",
            f"universities skipped existing/no new data: {summary.skipped_existing}",
            f"rows skipped due to errors: {summary.skipped_errors}",
            f"rows missing required Name/Country/City: {summary.missing_required}",
            f"duplicate keys within this file: {summary.duplicate_keys_in_file}",
            f"skipped invalid cells: {summary.invalid_cells}",
            f"skipped placeholder cells: {summary.placeholder_cells}",
            f"skipped commentary cells: {summary.commentary_cells}",
            f"skipped generic country-average cells: {summary.generic_country_average_cells}",
            f"conflicts requiring manual review: {summary.conflicts}",
            f"ambiguous university matches: {summary.ambiguous_matches}",
            f"public fields imported: {summary.public_fields_imported}",
            f"guidance contexts changed: {summary.guidance_contexts_imported}",
            f"signal vectors changed: {summary.signal_vectors_imported}",
            f"audit rows: {len(summary.audit_entries)}",
            f"manual review rows: {len(summary.manual_review_entries)}",
        ]
        for line in lines:
            self.stdout.write(_safe_line(line))

        if options["audit_out"]:
            self.stdout.write(_safe_line(f"audit csv: {options['audit_out']}"))
        if options["manual_review_out"]:
            self.stdout.write(_safe_line(f"manual review csv: {options['manual_review_out']}"))

        if summary.errors:
            self.stdout.write(self.style.ERROR(f"-- first {min(20, len(summary.errors))} errors --"))
            for error_line in summary.errors[:20]:
                self.stdout.write(_safe_line(f"  {error_line}"))

        if commit:
            self.stdout.write(self.style.SUCCESS("Import committed."))
        else:
            self.stdout.write(self.style.SUCCESS("Dry run complete -- no data was written."))

from __future__ import annotations

import logging
import tempfile
import threading
from contextlib import suppress
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import close_old_connections
from django.utils import timezone

from .models import UniversityImportJob
from .xlsx_import import (
    ImportReport,
    ParsedRow,
    execute_import_rows,
    load_xlsx_rows,
    plan_import_rows,
)

MAX_IMPORT_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_STALE_AFTER_MINUTES = 15

logger = logging.getLogger(__name__)


def university_import_stale_after() -> timedelta:
    raw_minutes = getattr(
        settings,
        "UNIVERSITY_IMPORT_STALE_AFTER_MINUTES",
        DEFAULT_STALE_AFTER_MINUTES,
    )
    try:
        minutes = int(raw_minutes)
    except (TypeError, ValueError):
        minutes = DEFAULT_STALE_AFTER_MINUTES
    return timedelta(minutes=max(minutes, 1))


def _report_summary(report: ImportReport) -> dict:
    return {
        "created": report.created,
        "updated": report.updated,
        "skipped": report.skipped,
        "warnings": report.warnings_count,
        "placeholder_sat": report.placeholder_sat,
        "parsed_deadlines": report.parsed_deadlines,
        "parsed_essays": report.parsed_essays,
        "source_urls": report.source_urls,
        "fields_verified": report.fields_verified,
    }


def _apply_report_counts(job: UniversityImportJob, summary: dict) -> None:
    job.created_count = summary["created"]
    job.updated_count = summary["updated"]
    job.skipped_count = summary["skipped"]
    job.warning_count = summary["warnings"]
    job.source_url_count = summary["source_urls"]
    job.field_verification_count = summary["fields_verified"]
    job.parsed_deadline_count = summary["parsed_deadlines"]
    job.parsed_essay_count = summary["parsed_essays"]
    job.questionable_sat_count = summary["placeholder_sat"]


def _summary_with_progress(summary_json: object, progress: dict) -> dict:
    payload = dict(summary_json) if isinstance(summary_json, dict) else {}
    current = payload.get("progress")
    progress_payload = dict(current) if isinstance(current, dict) else {}
    progress_payload.update(progress)
    payload["progress"] = progress_payload
    return payload


def _save_job_progress(
    job: UniversityImportJob,
    *,
    stage: str,
    row_count: int | None = None,
    processed_count: int | None = None,
    current_row: int | None = None,
    current_university: str | None = None,
    report: ImportReport | None = None,
) -> None:
    now = timezone.now()
    progress: dict = {
        "stage": stage,
        "last_heartbeat_at": now.isoformat(),
    }
    update_fields: list[str] = ["last_heartbeat_at", "summary_json"]
    job.last_heartbeat_at = now

    if row_count is not None:
        job.row_count = row_count
        progress["row_count"] = row_count
        update_fields.append("row_count")
    if processed_count is not None:
        job.processed_count = processed_count
        progress["processed_count"] = processed_count
        update_fields.append("processed_count")
    if current_row is not None:
        job.current_row = current_row
        progress["current_row"] = current_row
        update_fields.append("current_row")
    if current_university is not None:
        job.current_university = current_university[:255]
        progress["current_university"] = job.current_university
        update_fields.append("current_university")
    if report is not None:
        summary = _report_summary(report)
        _apply_report_counts(job, summary)
        progress["summary"] = summary
        update_fields.extend(
            [
                "created_count",
                "updated_count",
                "skipped_count",
                "warning_count",
                "source_url_count",
                "field_verification_count",
                "parsed_deadline_count",
                "parsed_essay_count",
                "questionable_sat_count",
            ]
        )

    job.summary_json = _summary_with_progress(job.summary_json, progress)
    job.save(update_fields=tuple(dict.fromkeys(update_fields)))


def is_university_import_job_stale(
    job: UniversityImportJob,
    *,
    now=None,
) -> bool:
    if job.status != UniversityImportJob.Status.RUNNING or not job.started_at:
        return False
    reference = job.last_heartbeat_at or job.started_at
    return (now or timezone.now()) - reference > university_import_stale_after()


def mark_stale_university_import_job(job: UniversityImportJob) -> bool:
    now = timezone.now()
    if not is_university_import_job_stale(job, now=now):
        return False

    minutes = int(university_import_stale_after().total_seconds() // 60)
    job.status = UniversityImportJob.Status.FAILED
    job.error_message = (
        f"Import job timed out after {minutes} minutes without a progress "
        "heartbeat. The run may have been interrupted after partial writes; "
        "review the catalog before rerunning. No second import was started."
    )
    job.finished_at = now
    job.last_heartbeat_at = now
    job.summary_json = _summary_with_progress(
        job.summary_json,
        {
            "stage": "stale",
            "last_heartbeat_at": now.isoformat(),
            "processed_count": job.processed_count,
            "row_count": job.row_count,
            "current_row": job.current_row,
            "current_university": job.current_university,
        },
    )
    job.save(
        update_fields=(
            "status",
            "error_message",
            "finished_at",
            "last_heartbeat_at",
            "summary_json",
        )
    )
    logger.warning("University import job %s marked stale/failed.", job.id)
    return True


def save_uploaded_workbook(uploaded_file: UploadedFile) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(
        delete=False,
        prefix="uniway_university_import_",
        suffix=suffix or ".xlsx",
    ) as temporary:
        for chunk in uploaded_file.chunks():
            temporary.write(chunk)
        return Path(temporary.name)


def enqueue_university_import_job(
    *,
    uploaded_by,
    mode: str,
    uploaded_file: UploadedFile,
) -> UniversityImportJob:
    job = UniversityImportJob.objects.create(
        uploaded_by=uploaded_by,
        mode=mode,
        original_filename=Path(uploaded_file.name).name[:255],
    )
    workbook_path = save_uploaded_workbook(uploaded_file)

    if getattr(settings, "UNIVERSITY_IMPORT_RUN_INLINE", False):
        run_university_import_job(job.id, workbook_path)
        job.refresh_from_db()
        return job

    thread = threading.Thread(
        target=run_university_import_job,
        args=(job.id, workbook_path),
        name=f"university-import-job-{job.id}",
        daemon=True,
    )
    thread.start()
    return job


def run_university_import_job(job_id: int, workbook_path: str | Path) -> None:
    close_old_connections()
    path = Path(workbook_path)
    try:
        job = UniversityImportJob.objects.get(pk=job_id)
        now = timezone.now()
        job.status = UniversityImportJob.Status.RUNNING
        job.started_at = now
        job.last_heartbeat_at = now
        job.error_message = ""
        job.processed_count = 0
        job.current_row = None
        job.current_university = ""
        job.summary_json = _summary_with_progress(
            {},
            {
                "stage": "starting",
                "last_heartbeat_at": now.isoformat(),
                "processed_count": 0,
            },
        )
        job.save(
            update_fields=(
                "status",
                "started_at",
                "last_heartbeat_at",
                "error_message",
                "processed_count",
                "current_row",
                "current_university",
                "summary_json",
            )
        )
        logger.info(
            "University import job %s started in %s mode for %s.",
            job.id,
            job.mode,
            job.original_filename,
        )

        _save_job_progress(job, stage="parsing_workbook")
        rows = load_xlsx_rows(path)
        _save_job_progress(job, stage="workbook_parsed", row_count=len(rows))
        logger.info("University import job %s loaded %s XLSX rows.", job.id, len(rows))

        import_kwargs = {
            "replace_existing": False,
            "include_questionable": False,
            "source_label": f"Admin upload: {job.original_filename}",
            "default_verification": "partial",
        }
        if job.mode == UniversityImportJob.Mode.DRY_RUN:
            # TRUE read-only preflight: a single bulk SELECT, no writes, no row
            # locks, no rollback. It cannot time out locking university rows.
            _save_job_progress(job, stage="planning", row_count=len(rows))
            report = plan_import_rows(rows, **import_kwargs)
            _save_job_progress(
                job,
                stage="planned",
                row_count=len(rows),
                processed_count=len(report.rows),
                report=report,
            )
        else:
            # Writer uses short per-row transactions internally; no outer atomic
            # block, so no single long-held lock across all rows.
            def progress_callback(
                report: ImportReport,
                parsed: ParsedRow,
                processed_count: int,
            ) -> None:
                _save_job_progress(
                    job,
                    stage="executing",
                    row_count=len(rows),
                    processed_count=processed_count,
                    current_row=parsed.index,
                    current_university=parsed.name,
                    report=report,
                )

            report = execute_import_rows(
                rows,
                **import_kwargs,
                progress_callback=progress_callback,
            )

        report_payload = report.as_dict()
        summary = report_payload["summary"]
        finished_at = timezone.now()
        last_row = report.rows[-1] if report.rows else None
        processed_count = len(report.rows)
        report_payload["progress"] = {
            "stage": "completed",
            "last_heartbeat_at": finished_at.isoformat(),
            "row_count": len(rows),
            "processed_count": processed_count,
            "current_row": last_row.row_number if last_row else None,
            "current_university": last_row.name if last_row else "",
        }
        job.status = UniversityImportJob.Status.COMPLETED
        job.row_count = len(rows)
        job.processed_count = processed_count
        job.current_row = last_row.row_number if last_row else None
        job.current_university = last_row.name[:255] if last_row else ""
        job.created_count = summary["created"]
        job.updated_count = summary["updated"]
        job.skipped_count = summary["skipped"]
        job.warning_count = summary["warnings"]
        job.source_url_count = summary["source_urls"]
        job.field_verification_count = summary["fields_verified"]
        job.parsed_deadline_count = summary["parsed_deadlines"]
        job.parsed_essay_count = summary["parsed_essays"]
        job.questionable_sat_count = summary["placeholder_sat"]
        job.summary_json = report_payload
        job.finished_at = finished_at
        job.last_heartbeat_at = finished_at
        job.save(
            update_fields=(
                "status",
                "row_count",
                "processed_count",
                "current_row",
                "current_university",
                "created_count",
                "updated_count",
                "skipped_count",
                "warning_count",
                "source_url_count",
                "field_verification_count",
                "parsed_deadline_count",
                "parsed_essay_count",
                "questionable_sat_count",
                "summary_json",
                "finished_at",
                "last_heartbeat_at",
            )
        )
        logger.info("University import job %s completed.", job.id)
    except Exception as exc:
        logger.exception("University import job %s failed.", job_id)
        try:
            job = UniversityImportJob.objects.get(pk=job_id)
            now = timezone.now()
            job.status = UniversityImportJob.Status.FAILED
            job.error_message = str(exc)[:4000]
            job.finished_at = now
            job.last_heartbeat_at = now
            job.summary_json = _summary_with_progress(
                job.summary_json,
                {
                    "stage": "failed",
                    "last_heartbeat_at": now.isoformat(),
                    "processed_count": job.processed_count,
                    "row_count": job.row_count,
                    "current_row": job.current_row,
                    "current_university": job.current_university,
                },
            )
            job.save(
                update_fields=(
                    "status",
                    "error_message",
                    "finished_at",
                    "last_heartbeat_at",
                    "summary_json",
                )
            )
        except UniversityImportJob.DoesNotExist:
            pass
    finally:
        with suppress(OSError):
            path.unlink(missing_ok=True)
        close_old_connections()

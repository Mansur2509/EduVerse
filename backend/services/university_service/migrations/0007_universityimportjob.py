# Generated for UNIWAY-UNIVERSITY-IMPORT-ADMIN-001.

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("university_service", "0006_import_universities_dataset"),
    ]

    operations = [
        migrations.CreateModel(
            name="UniversityImportJob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "mode",
                    models.CharField(
                        choices=[
                            ("dry_run", "Dry run"),
                            ("execute", "Execute"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("original_filename", models.CharField(max_length=255)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("skipped_count", models.PositiveIntegerField(default=0)),
                ("warning_count", models.PositiveIntegerField(default=0)),
                ("source_url_count", models.PositiveIntegerField(default=0)),
                ("field_verification_count", models.PositiveIntegerField(default=0)),
                ("parsed_deadline_count", models.PositiveIntegerField(default=0)),
                ("parsed_essay_count", models.PositiveIntegerField(default=0)),
                ("questionable_sat_count", models.PositiveIntegerField(default=0)),
                ("summary_json", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="university_import_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(fields=["status", "created_at"], name="university__status_e7b5b8_idx"),
                    models.Index(fields=["mode", "created_at"], name="university__mode_855c51_idx"),
                ],
            },
        ),
    ]

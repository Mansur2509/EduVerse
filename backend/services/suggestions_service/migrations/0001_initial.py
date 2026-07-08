# Generated manually for UNIWAY-DEPTH-POLISH-001.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import common.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("application_service", "0001_initial"),
        ("essay_service", "0001_initial"),
        ("roadmap_service", "0002_alter_roadmaptask_source_type"),
        ("university_service", "0004_university_international_office_url_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SuggestedItem",
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
                    "suggestion_type",
                    models.CharField(
                        choices=[
                            ("exam_date", "Exam date"),
                            ("exam_plan", "Exam plan"),
                            ("essay_deadline", "Essay deadline"),
                            ("essay_word_limit", "Essay word limit"),
                            ("application_deadline", "Application deadline"),
                            ("scholarship_deadline", "Scholarship deadline"),
                            ("scholarship_type", "Scholarship type"),
                            ("course_recommendation", "Course recommendation"),
                            ("ap_recommendation", "AP recommendation"),
                            ("document_deadline", "Document deadline"),
                            ("profile_gap", "Profile gap"),
                            ("roadmap_instruction", "Roadmap instruction"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                ("title", models.CharField(max_length=240)),
                ("description", models.TextField(blank=True)),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("urgent", "Urgent"),
                        ],
                        db_index=True,
                        default="medium",
                        max_length=10,
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("official", "Official"),
                            ("verified_university_data", "Verified university data"),
                            ("planning_window", "Planning window"),
                            ("profile_based", "Profile based"),
                            ("roadmap_based", "Roadmap based"),
                            ("missing_data_warning", "Missing data warning"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("dismissed", "Dismissed"),
                            ("added_to_roadmap", "Added to roadmap"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                ("recommended_start_date", models.DateField(blank=True, null=True)),
                ("recommended_end_date", models.DateField(blank=True, null=True)),
                ("official_deadline", models.DateField(blank=True, null=True)),
                ("word_limit", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "source_url",
                    models.URLField(blank=True, validators=[common.validators.validate_http_url]),
                ),
                ("evidence_note", models.TextField(blank=True)),
                ("dedup_key", models.CharField(db_index=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("dismissed_at", models.DateTimeField(blank=True, null=True)),
                ("added_to_roadmap_at", models.DateTimeField(blank=True, null=True)),
                (
                    "linked_application",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="suggested_items",
                        to="application_service.applicationtrackeritem",
                    ),
                ),
                (
                    "linked_essay",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="suggested_items",
                        to="essay_service.essayworkspace",
                    ),
                ),
                (
                    "linked_roadmap_task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="suggested_items",
                        to="roadmap_service.roadmaptask",
                    ),
                ),
                (
                    "linked_university",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="suggested_items",
                        to="university_service.university",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="suggested_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": (
                    "status",
                    "recommended_end_date",
                    "official_deadline",
                    "-priority",
                    "created_at",
                ),
            },
        ),
        migrations.AddConstraint(
            model_name="suggesteditem",
            constraint=models.UniqueConstraint(
                fields=("user", "dedup_key"),
                name="unique_suggestion_per_user_key",
            ),
        ),
        migrations.AddIndex(
            model_name="suggesteditem",
            index=models.Index(fields=("user", "status"), name="suggestions_user_id_d5e6f9_idx"),
        ),
        migrations.AddIndex(
            model_name="suggesteditem",
            index=models.Index(fields=("user", "suggestion_type"), name="suggestions_user_id_d177ea_idx"),
        ),
    ]

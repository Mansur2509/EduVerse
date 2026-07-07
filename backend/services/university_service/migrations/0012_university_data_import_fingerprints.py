import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("university_service", "0011_university_activities_notes_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="UniversityDataImportBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file_name", models.CharField(max_length=255)),
                ("committed", models.BooleanField(db_index=True, default=False)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("summary_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="UniversityDataImportRowLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file_name", models.CharField(max_length=255)),
                ("row_number", models.PositiveIntegerField()),
                ("row_hash", models.CharField(db_index=True, max_length=64)),
                ("action", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="row_logs",
                        to="university_service.universitydataimportbatch",
                    ),
                ),
                (
                    "matched_university",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_import_row_logs",
                        to="university_service.university",
                    ),
                ),
            ],
            options={
                "ordering": ("batch", "row_number"),
            },
        ),
        migrations.AddIndex(
            model_name="universitydataimportbatch",
            index=models.Index(fields=["source_file_name", "created_at"], name="university__source__016274_idx"),
        ),
        migrations.AddIndex(
            model_name="universitydataimportbatch",
            index=models.Index(fields=["committed", "created_at"], name="university__committ_e7c1fd_idx"),
        ),
        migrations.AddIndex(
            model_name="universitydataimportrowlog",
            index=models.Index(fields=["row_hash", "action"], name="university__row_has_f68975_idx"),
        ),
        migrations.AddIndex(
            model_name="universitydataimportrowlog",
            index=models.Index(fields=["source_file_name", "row_number"], name="university__source__a49dac_idx"),
        ),
    ]

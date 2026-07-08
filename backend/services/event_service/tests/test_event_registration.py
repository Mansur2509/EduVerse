from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from services.event_service.models import (
    Event,
    EventCategory,
    EventLocation,
    EventRegistration,
    EventSource,
)
from services.user_profile_service.models import StudentProfile, UserPreference

User = get_user_model()


class EventRegistrationTests(APITestCase):
    def setUp(self):
        self.category = EventCategory.objects.create(name="Workshop", slug="workshop")
        self.event = self.create_event(slug="published-workshop")
        self.user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="Strong-Development-Password-842!",
        )
        StudentProfile.objects.create(
            user=self.user,
            full_name="Student Example",
            country="Uzbekistan",
            city="Tashkent",
            school_or_university="Example Academic School",
            grade="11",
            intended_degree="bachelor",
            intended_majors=["Computer Science"],
            languages=["Uzbek", "English"],
            telegram_username="@student_example",
            phone="+998 90 123 45 67",
        )
        UserPreference.objects.create(user=self.user, interests=["Research", "Debate"])

    def create_event(
        self,
        *,
        slug,
        status=Event.Status.PUBLISHED,
        capacity=10,
        deadline_days=5,
    ):
        starts_at = timezone.now() + timedelta(days=10)
        event = Event.objects.create(
            category=self.category,
            title=slug.replace("-", " ").title(),
            slug=slug,
            short_description="Original demonstration event.",
            description="Original demonstration event description.",
            organizer_name="Demo organizer",
            format=Event.Format.OFFLINE,
            is_online=False,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            deadline=timezone.now() + timedelta(days=deadline_days),
            capacity=capacity,
            price_type=Event.PriceType.FREE,
            is_free=True,
            moderation_status=status,
            visibility=Event.Visibility.PUBLIC,
        )
        EventLocation.objects.create(
            event=event,
            country="Uzbekistan",
            city="Tashkent",
            venue="Demo venue",
        )
        EventSource.objects.create(
            event=event,
            source_title="Demo source",
            source_url=f"https://example.com/{slug}",
            is_official=False,
        )
        return event

    def test_authenticated_user_can_list_and_view_published_events(self):
        pending_event = self.create_event(
            slug="pending-workshop",
            status=Event.Status.PENDING_REVIEW,
        )
        self.client.force_authenticate(self.user)

        list_response = self.client.get(reverse("events:list"))
        detail_response = self.client.get(
            reverse("events:detail", kwargs={"slug": self.event.slug})
        )
        pending_response = self.client.get(
            reverse("events:detail", kwargs={"slug": pending_event.slug})
        )

        self.assertEqual(list_response.status_code, 200)
        slugs = [item["slug"] for item in list_response.data["results"]]
        self.assertIn(self.event.slug, slugs)
        self.assertNotIn(pending_event.slug, slugs)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["slug"], self.event.slug)
        self.assertEqual(pending_response.status_code, 404)

    def test_anonymous_event_catalog_is_rejected(self):
        list_response = self.client.get(reverse("events:list"))
        detail_response = self.client.get(
            reverse("events:detail", kwargs={"slug": self.event.slug})
        )

        self.assertEqual(list_response.status_code, 401)
        self.assertEqual(detail_response.status_code, 401)

    def test_authenticated_user_registers_with_profile_snapshot(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("events:register", kwargs={"slug": self.event.slug}),
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        registration = EventRegistration.objects.get(user=self.user, event=self.event)
        self.assertEqual(registration.status, EventRegistration.Status.REGISTERED)
        self.assertEqual(registration.registration_data["full_name"], "Student Example")
        self.assertEqual(registration.registration_data["interests"], ["Research", "Debate"])
        self.assertEqual(registration.contact_snapshot["email"], self.user.email)
        self.assertEqual(
            registration.payment_status,
            EventRegistration.PaymentStatus.NOT_REQUIRED,
        )

    def test_duplicate_registration_is_prevented(self):
        self.client.force_authenticate(self.user)
        url = reverse("events:register", kwargs={"slug": self.event.slug})
        self.client.post(url, format="json")

        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            EventRegistration.objects.filter(
                user=self.user,
                event=self.event,
                status=EventRegistration.Status.REGISTERED,
            ).count(),
            1,
        )

    def test_user_can_list_cancel_and_reregister(self):
        self.client.force_authenticate(self.user)
        register_url = reverse("events:register", kwargs={"slug": self.event.slug})
        cancel_url = reverse(
            "events:cancel-registration",
            kwargs={"slug": self.event.slug},
        )
        self.client.post(register_url, format="json")

        list_response = self.client.get(reverse("events:my-registrations"))
        cancel_response = self.client.post(cancel_url, format="json")
        empty_list_response = self.client.get(reverse("events:my-registrations"))
        reregister_response = self.client.post(register_url, format="json")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.data["status"], EventRegistration.Status.CANCELLED)
        self.assertEqual(empty_list_response.data["count"], 0)
        self.assertEqual(reregister_response.status_code, 200)
        self.assertEqual(reregister_response.data["status"], EventRegistration.Status.REGISTERED)
        self.assertEqual(
            EventRegistration.objects.filter(user=self.user, event=self.event).count(),
            1,
        )

    def test_event_catalog_accepts_page_size_query(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(f"{reverse('events:list')}?page=1&page_size=21")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["registration_form_fields"], [])
        self.assertIsNone(response.data["results"][0]["registration_ticket"])

    def test_event_catalog_empty_list_accepts_page_size_query(self):
        Event.objects.all().delete()
        self.client.force_authenticate(self.user)

        response = self.client.get(f"{reverse('events:list')}?page=1&page_size=21")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_my_registrations_accepts_page_size_query_for_empty_user(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(f"{reverse('events:my-registrations')}?page=1&page_size=21")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_my_registrations_accepts_page_size_query_for_registered_user(self):
        self.client.force_authenticate(self.user)
        self.client.post(reverse("events:register", kwargs={"slug": self.event.slug}), format="json")

        response = self.client.get(f"{reverse('events:my-registrations')}?page=1&page_size=21")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["ticket"]["status"], "active")

    def test_core_event_lists_skip_optional_infrastructure_when_tables_unavailable(self):
        self.client.force_authenticate(self.user)
        self.client.post(reverse("events:register", kwargs={"slug": self.event.slug}), format="json")

        with (
            patch(
                "services.event_service.serializers.event_infrastructure_tables_available",
                return_value=False,
            ),
            patch(
                "services.event_service.views.event_infrastructure_tables_available",
                return_value=False,
            ),
        ):
            catalog_response = self.client.get(f"{reverse('events:list')}?page=1&page_size=21")
            registrations_response = self.client.get(
                f"{reverse('events:my-registrations')}?page=1&page_size=21"
            )

        self.assertEqual(catalog_response.status_code, 200, catalog_response.data)
        self.assertEqual(registrations_response.status_code, 200, registrations_response.data)
        self.assertEqual(catalog_response.data["results"][0]["registration_form_fields"], [])
        self.assertIsNone(catalog_response.data["results"][0]["registration_ticket"])
        self.assertIsNone(registrations_response.data["results"][0]["ticket"])
        self.assertEqual(registrations_response.data["results"][0]["answers"], [])

    def test_seeded_demo_student_event_lists_accept_page_size_query(self):
        call_command("seed_demo", "--with-demo-data", stdout=StringIO())
        demo_user = User.objects.get(email="student.demo@uniway.local")
        self.client.force_authenticate(demo_user)

        catalog_response = self.client.get(f"{reverse('events:list')}?page=1&page_size=21")
        registrations_response = self.client.get(
            f"{reverse('events:my-registrations')}?page=1&page_size=21"
        )

        self.assertEqual(catalog_response.status_code, 200, catalog_response.data)
        self.assertGreaterEqual(catalog_response.data["count"], 1)
        self.assertEqual(registrations_response.status_code, 200, registrations_response.data)
        self.assertGreaterEqual(registrations_response.data["count"], 1)

    def test_anonymous_registration_is_rejected(self):
        response = self.client.post(
            reverse("events:register", kwargs={"slug": self.event.slug}),
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_capacity_deadline_and_publication_are_enforced(self):
        full_event = self.create_event(slug="full-event", capacity=1)
        first_user = User.objects.create_user(
            username="first@example.com",
            email="first@example.com",
            password="Strong-Development-Password-842!",
        )
        EventRegistration.objects.create(user=first_user, event=full_event)
        expired_event = self.create_event(slug="expired-event", deadline_days=-1)
        pending_event = self.create_event(
            slug="not-published-event",
            status=Event.Status.PENDING_REVIEW,
        )
        self.client.force_authenticate(self.user)

        full_response = self.client.post(
            reverse("events:register", kwargs={"slug": full_event.slug}),
            format="json",
        )
        expired_response = self.client.post(
            reverse("events:register", kwargs={"slug": expired_event.slug}),
            format="json",
        )
        pending_response = self.client.post(
            reverse("events:register", kwargs={"slug": pending_event.slug}),
            format="json",
        )

        self.assertEqual(full_response.status_code, 400)
        self.assertEqual(expired_response.status_code, 400)
        self.assertEqual(pending_response.status_code, 400)

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from services.event_service.models import (
    Event,
    EventCategory,
    EventLocation,
    EventRegistration,
    EventSource,
)
from services.exam_content_service.models import (
    AnswerChoice,
    Exam,
    ExamSection,
    Explanation,
    Question,
)
from services.subscription_service.models import Plan, Subscription, UsageLimit
from services.university_service.models import (
    University,
    UniversityDataSource,
    UniversityProgram,
    UniversityScholarship,
)
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()

DEMO_PASSWORD = "EduVerse-Demo-842!"


class Command(BaseCommand):
    help = "Create safe, clearly labeled demonstration data for local development."

    def handle(self, *args, **options):
        self.seed_usage_limits()
        demo_users = self.seed_demo_accounts()
        self.seed_university()
        self.seed_event(demo_users)
        self.seed_question()
        self.stdout.write(self.style.SUCCESS("EduVerse demo data is ready."))

    def seed_demo_accounts(self):
        accounts = {
            "student": ("student.demo@eduverse.local", User.Role.STUDENT),
            "organizer": ("organizer.demo@eduverse.local", User.Role.ORGANIZER),
            "admin": ("admin.demo@eduverse.local", User.Role.ADMIN),
        }
        users = {}
        for key, (email, role) in accounts.items():
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={"username": email, "role": role},
            )
            user.username = email
            user.role = role
            user.is_active = True
            user.is_staff = role == User.Role.ADMIN
            user.set_password(DEMO_PASSWORD)
            user.save()

            profile, preferences = ensure_profile_records(user)
            profile.full_name = f"EduVerse Demo {role.title()}"
            profile.birth_date = date(2004, 4, 12)
            profile.country = "Uzbekistan"
            profile.city = "Tashkent"
            profile.school_or_university = "EduVerse Demo Academy"
            profile.grade = "12"
            profile.expected_graduation_year = timezone.now().year + 1
            profile.education_status = "school_student"
            profile.gpa = "4.50"
            profile.gpa_scale = "5.00"
            profile.intended_degree = "bachelor"
            profile.intended_major = "Computer Science"
            profile.intended_majors = ["Computer Science", "Economics"]
            profile.target_countries = ["United States", "United Kingdom"]
            profile.target_universities = []
            profile.university_unsure = True
            profile.major_unsure = False
            profile.test_scores = {"sat": 1450, "ielts": 7.5}
            profile.exam_plans = {
                "taken": [],
                "planned": [
                    {
                        "name": "SAT",
                        "date": f"{timezone.now().year + 1}-03-13",
                        "target_score": "1500",
                    }
                ],
            }
            profile.preparation_needs = ["SAT preparation"]
            profile.activities = {
                "extracurriculars": ["Coding club"],
                "honors": [],
                "sports": [],
                "olympiads": [],
                "research_projects": ["Demo research project"],
                "mun_debate": [],
                "volunteering": ["Peer tutoring"],
                "leadership": [],
                "work_internships": [],
            }
            profile.essay_status = "not_yet"
            profile.essay_stage = "planning"
            profile.support_priorities = ["University research"]
            profile.scholarship_need = "yes"
            profile.onboarding_sections = [
                "identity",
                "academic",
                "exams",
                "activities",
                "support",
            ]
            profile.onboarding_completed_at = timezone.now()
            profile.telegram_username = f"@eduverse_demo_{key}"
            profile.save()

            preferences.interested_classes = [
                "SAT Math",
                "AP Computer Science",
                "Research Basics",
            ]
            preferences.career_interests = ["Technology", "Research"]
            preferences.interests = ["Events", "Academic planning"]
            preferences.research_interest = True
            preferences.save()
            Subscription.objects.update_or_create(
                user=user,
                defaults={"plan": Plan.FREE},
            )
            users[key] = user
        return users

    def seed_usage_limits(self):
        limits = {
            Plan.FREE: (5, 1, 25),
            Plan.STARTER: (50, 5, 100),
            Plan.GROWTH: (150, 15, 300),
            Plan.PREMIUM: (500, 50, 1000),
        }
        for plan, values in limits.items():
            UsageLimit.objects.update_or_create(
                plan=plan,
                defaults={
                    "ai_messages_per_month": values[0],
                    "essay_reviews_per_month": values[1],
                    "saved_events": values[2],
                    "feature_flags": {"event_map": True, "university_database": True},
                },
            )

    def seed_university(self):
        today = timezone.now().date()
        next_year = today.year + 1
        demo_universities = (
            {
                "slug": "eduverse-demo-university",
                "name": "EduVerse Demo University",
                "country": "Demoland",
                "city": "Sample City",
                "institution_type": "",
                "summary": "Fictional development record. Not a real institution. "
                "All admissions statistics are intentionally unverified to demonstrate "
                "honest empty states.",
                "acceptance_rate": None,
                "gpa_average": None,
                "sat_average": None,
                "tuition_amount": None,
                "application_deadline": None,
                "scholarship_available": None,
            },
            {
                "slug": "lakeview-institute-of-technology",
                "name": "Lakeview Institute of Technology",
                "country": "Demoland",
                "city": "Lakeview",
                "institution_type": University.InstitutionType.PRIVATE,
                "summary": "Fictional development record used to demonstrate a fully "
                "populated university profile. Not a real institution.",
                "acceptance_rate": "18.00",
                "gpa_average": "3.70",
                "sat_average": 1420,
                "tuition_amount": "42000.00",
                "application_deadline": date(next_year, 1, 15),
                "scholarship_available": True,
            },
            {
                "slug": "northfield-state-university",
                "name": "Northfield State University",
                "country": "Sampleton",
                "city": "Northfield",
                "institution_type": University.InstitutionType.PUBLIC,
                "summary": "Fictional development record used to demonstrate a "
                "higher-acceptance public university profile. Not a real institution.",
                "acceptance_rate": "65.00",
                "gpa_average": "3.20",
                "sat_average": 1180,
                "tuition_amount": "12000.00",
                "application_deadline": date(next_year, 3, 1),
                "scholarship_available": True,
            },
            {
                "slug": "crestwood-liberal-arts-college",
                "name": "Crestwood Liberal Arts College",
                "country": "Sampleton",
                "city": "Crestwood",
                "institution_type": University.InstitutionType.PRIVATE,
                "summary": "Fictional development record used to demonstrate a partially "
                "verified profile with an unknown scholarship status. Not a real institution.",
                "acceptance_rate": "28.00",
                "gpa_average": "3.60",
                "sat_average": None,
                "tuition_amount": "51000.00",
                "application_deadline": date(next_year, 1, 5),
                "scholarship_available": None,
            },
            {
                "slug": "harborview-polytechnic",
                "name": "Harborview Polytechnic",
                "country": "Testford",
                "city": "Harborview",
                "institution_type": University.InstitutionType.PUBLIC,
                "summary": "Fictional development record used to demonstrate a highly "
                "selective profile with unverified tuition. Not a real institution.",
                "acceptance_rate": "8.00",
                "gpa_average": "3.90",
                "sat_average": 1520,
                "tuition_amount": None,
                "application_deadline": None,
                "scholarship_available": True,
            },
            {
                "slug": "summit-community-college",
                "name": "Summit Community College",
                "country": "Testford",
                "city": "Summit",
                "institution_type": University.InstitutionType.PUBLIC,
                "summary": "Fictional development record used to demonstrate an "
                "accessible-admission profile with unverified academic averages. "
                "Not a real institution.",
                "acceptance_rate": "85.00",
                "gpa_average": None,
                "sat_average": None,
                "tuition_amount": "6000.00",
                "application_deadline": date(next_year, 8, 1),
                "scholarship_available": True,
            },
            {
                "slug": "ashford-global-university",
                "name": "Ashford Global University",
                "country": "Demoland",
                "city": "Ashford",
                "institution_type": University.InstitutionType.PRIVATE,
                "summary": "Fictional development record used to demonstrate a fully "
                "unverified profile shown entirely as 'Not verified yet'. "
                "Not a real institution.",
                "acceptance_rate": None,
                "gpa_average": None,
                "sat_average": None,
                "tuition_amount": None,
                "application_deadline": None,
                "scholarship_available": None,
            },
            {
                "slug": "brightwater-college-of-arts",
                "name": "Brightwater College of Arts",
                "country": "Sampleton",
                "city": "Brightwater",
                "institution_type": University.InstitutionType.PRIVATE,
                "summary": "Fictional development record used to demonstrate a profile "
                "missing a verified test-score average. Not a real institution.",
                "acceptance_rate": "42.00",
                "gpa_average": "3.45",
                "sat_average": None,
                "tuition_amount": "38000.00",
                "application_deadline": date(next_year, 2, 1),
                "scholarship_available": False,
            },
        )

        for demo in demo_universities:
            slug = demo["slug"]
            university, _ = University.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": demo["name"],
                    "country": demo["country"],
                    "city": demo["city"],
                    "institution_type": demo["institution_type"],
                    "official_website": f"https://example.com/{slug}",
                    "summary": demo["summary"],
                    "acceptance_rate": demo["acceptance_rate"],
                    "gpa_average": demo["gpa_average"],
                    "sat_average": demo["sat_average"],
                    "tuition_amount": demo["tuition_amount"],
                    "tuition_currency": "USD",
                    "application_deadline": demo["application_deadline"],
                    "scholarship_available": demo["scholarship_available"],
                    "is_published": True,
                },
            )
            UniversityDataSource.objects.update_or_create(
                university=university,
                source_url=f"https://example.com/{slug}",
                defaults={
                    "source_title": "Fictional demonstration source",
                    "is_official": False,
                },
            )

        lakeview = University.objects.get(slug="lakeview-institute-of-technology")
        UniversityProgram.objects.update_or_create(
            university=lakeview,
            name="Computer Science",
            defaults={
                "degree_level": "Bachelor",
                "official_url": "https://example.com/lakeview-institute-of-technology/cs",
            },
        )
        crestwood = University.objects.get(slug="crestwood-liberal-arts-college")
        UniversityScholarship.objects.update_or_create(
            university=crestwood,
            name="Fictional Need-Based Grant",
            defaults={
                "summary": "Fictional demonstration scholarship record. Not a real award.",
                "official_url": "https://example.com/crestwood-liberal-arts-college/scholarship",
                "deadline": date(next_year, 1, 5),
            },
        )

    def seed_event(self, demo_users):
        now = timezone.now()
        demo_events = (
            {
                "slug": "eduverse-demo-planning-workshop",
                "category": ("workshop", "Workshop"),
                "title": "EduVerse Demo Planning Workshop",
                "short_description": "A fictional workshop for testing event discovery and registration.",
                "description": (
                    "Fictional local development event for testing the EduVerse event module. "
                    "It is not a real opportunity."
                ),
                "format": Event.Format.HYBRID,
                "is_online": True,
                "starts_at": now + timedelta(days=45),
                "deadline": now + timedelta(days=30),
                "capacity": 40,
                "location": ("Uzbekistan", "Tashkent", "Demo Academic Center"),
                "status": Event.Status.PUBLISHED,
            },
            {
                "slug": "eduverse-demo-research-webinar",
                "category": ("research", "Research opportunity"),
                "title": "EduVerse Demo Research Webinar",
                "short_description": "A fictional online research-planning session for local development.",
                "description": (
                    "Fictional webinar record used to demonstrate online event details, filtering, "
                    "capacity, and profile-based registration."
                ),
                "format": Event.Format.ONLINE,
                "is_online": True,
                "starts_at": now + timedelta(days=60),
                "deadline": now + timedelta(days=50),
                "capacity": 100,
                "location": ("Online", "", "EduVerse Demo Stream"),
                "status": Event.Status.PUBLISHED,
            },
            {
                "slug": "eduverse-demo-policy-forum",
                "category": ("conference", "Conference"),
                "title": "EduVerse Demo Student Policy Forum",
                "short_description": "A fictional organizer submission ready for moderation review.",
                "description": (
                    "Fictional pending event used to demonstrate the organizer and admin "
                    "moderation workflow."
                ),
                "format": Event.Format.OFFLINE,
                "is_online": False,
                "starts_at": now + timedelta(days=75),
                "deadline": now + timedelta(days=60),
                "capacity": 80,
                "location": ("Uzbekistan", "Tashkent", "Demo Civic Hall"),
                "status": Event.Status.PENDING_REVIEW,
            },
        )
        for demo in demo_events:
            category_slug, category_name = demo["category"]
            category, _ = EventCategory.objects.get_or_create(
                slug=category_slug,
                defaults={"name": category_name},
            )
            event, _ = Event.objects.update_or_create(
                slug=demo["slug"],
                defaults={
                    "category": category,
                    "organizer": demo_users["organizer"],
                    "title": demo["title"],
                    "short_description": demo["short_description"],
                    "description": demo["description"],
                    "organizer_name": "EduVerse Demo Organizer",
                    "format": demo["format"],
                    "is_online": demo["is_online"],
                    "online_url": (
                        f"https://example.com/{demo['slug']}" if demo["is_online"] else ""
                    ),
                    "starts_at": demo["starts_at"],
                    "ends_at": demo["starts_at"] + timedelta(hours=2),
                    "deadline": demo["deadline"],
                    "capacity": demo["capacity"],
                    "price_type": Event.PriceType.FREE,
                    "is_free": True,
                    "visibility": Event.Visibility.PUBLIC,
                    "language": "English",
                    "eligibility": "Demonstration only",
                    "moderation_status": demo["status"],
                },
            )
            country, city, venue = demo["location"]
            EventLocation.objects.update_or_create(
                event=event,
                defaults={"country": country, "city": city, "venue": venue},
            )
            EventSource.objects.update_or_create(
                event=event,
                defaults={
                    "source_title": "Fictional demonstration source",
                    "source_url": f"https://example.com/{demo['slug']}",
                    "is_official": False,
                },
            )

        workshop = Event.objects.get(slug="eduverse-demo-planning-workshop")
        EventRegistration.objects.update_or_create(
            user=demo_users["student"],
            event=workshop,
            defaults={
                "status": EventRegistration.Status.REGISTERED,
                "payment_status": EventRegistration.PaymentStatus.NOT_REQUIRED,
                "registration_data": {"source": "seed_demo"},
                "contact_snapshot": {
                    "full_name": "EduVerse Demo Student",
                    "email": "student.demo@eduverse.local",
                    "telegram_username": "@eduverse_demo_student",
                },
            },
        )

    def seed_question(self):
        exam, _ = Exam.objects.update_or_create(
            slug="sat-demo",
            defaults={
                "name": "SAT-style Demo",
                "description": "Original demonstration content aligned to general public skill categories.",
                "is_published": True,
            },
        )
        section, _ = ExamSection.objects.get_or_create(
            exam=exam,
            slug="math",
            defaults={"name": "Math"},
        )
        question, _ = Question.objects.get_or_create(
            section=section,
            prompt="A study group reads 18 pages each day for 5 days. How many pages do they read in total?",
            defaults={
                "origin": Question.Origin.ORIGINAL,
                "provenance_note": "Original EduVerse arithmetic demonstration question.",
                "is_published": True,
            },
        )
        choices = (("A", "23", False), ("B", "72", False), ("C", "90", True), ("D", "108", False))
        for label, text, is_correct in choices:
            AnswerChoice.objects.update_or_create(
                question=question,
                label=label,
                defaults={"text": text, "is_correct": is_correct},
            )
        Explanation.objects.update_or_create(
            question=question,
            defaults={"text": "Multiply the daily pages by the number of days: 18 × 5 = 90."},
        )

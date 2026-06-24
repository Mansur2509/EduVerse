# EduVerse

EduVerse is an academic student-success platform for admissions planning, original exam practice, event discovery, profile building, research guidance, career exploration, and foundational financial literacy.

This repository currently contains the Phase 0 foundation:

- `frontend/` — Next.js App Router UI using TypeScript, Tailwind CSS, and Feature-Sliced Design
- `backend/` — modular Django and Django REST Framework API
- `docs/` — product, architecture, security, API, design, data, deployment, task, and decision records
- `compose.yaml` — local PostgreSQL, backend, and frontend services

## Quick start

Copy environment examples before running:

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
```

Frontend with Bun:

```powershell
cd frontend
bun install
bun run dev
```

Backend with Python 3.12+:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Or run the complete local stack after installing Docker:

```powershell
docker compose up --build
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for environment details and [docs/TASKS.md](docs/TASKS.md) for the implementation roadmap.

## How to preview the beta locally

BETA-PREVIEW-001 connects the completed authentication, profile, event, organizer, and moderation workflows to a coherent dashboard and localized preview pages for upcoming modules.

One-time frontend setup:

```powershell
cd D:\Eduverce\frontend
npm install
npm run prepare:preview
```

Start the backend in PowerShell terminal 1:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Eduverce\backend\scripts\run-local-preview.ps1
```

Start the frontend in terminal 2:

```powershell
cd D:\Eduverce\frontend
npm run preview:beta
```

Open `http://127.0.0.1:3000`. The root route opens a full-screen EduVerse sign-in/register gateway. Every product route requires an active backend-confirmed session; after authentication the dashboard, profile, events, organizer, moderation, and preview modules become available according to role.

New and incomplete accounts must finish the six-step academic onboarding before the application shell opens. Draft answers are saved to the self-only profile API, and exam dates later appear as dashboard countdowns.

The complete PowerShell/Git Bash guide and troubleshooting notes are in [docs/LOCAL_PREVIEW.md](docs/LOCAL_PREVIEW.md).

## Authentication

AUTH-001 and AUTH-GUARD-001 provide JWT registration, login, rotating refresh, authenticated blacklist logout, current-user endpoints, and a global application gate. Protected shell/content never mounts before `/api/auth/me/` confirms the session.

For the complete request/response contract and the temporary localStorage security trade-off, see [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) and [docs/SECURITY.md](docs/SECURITY.md).

## Frontend foundation

The application uses a strict ivory/navy/crimson academic V1 system with crisp corners and a supported dark token set. Internal dependency-free localization covers English, Russian, Uzbek Latin, and Uzbek Cyrillic. See [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) and [docs/I18N.md](docs/I18N.md).

## Student profile

PROFILE-001 provides a self-only profile API under `/api/profile/`, computed completion, academic goals, test results, language/interests, and optional contact fields. The localized `/profile` page edits this foundation without performing admission matching or roadmap generation.

## Organizer workflow

ORGANIZER-001 adds draft-first organizer management under `/api/organizer/`, admin moderation under `/api/admin/events/`, status logs, privacy-limited participant lists, and localized role-aware frontend routes under `/organizer/events` and `/admin/events/moderation`.

## Events

EVENTS-001 provides the authenticated student catalog and detail API under `/api/events/`, profile-snapshot registration, cancellation, and “My events”. Demo seed data creates fictional published events suitable for local testing. Payments, QR tickets, Telegram, custom forms, and exports are intentionally deferred.
# EduVerse

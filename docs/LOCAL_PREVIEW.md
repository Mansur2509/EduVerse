# Local Beta Preview

This guide is the supported founder-friendly Windows path for opening the current UniWay beta. It uses the existing project environments and a local SQLite database. Docker and PostgreSQL are not required for this preview.

## Prerequisites

Open PowerShell and confirm:

```powershell
node -v
npm -v
```

The repository already contains the backend virtual environment and local Python dependencies used by Codex. If either directory is missing, do not run `pip install` blindly; set up the backend from `requirements.txt` in a dedicated environment.

## First frontend setup

Run once:

```powershell
cd D:\UniWay\frontend
npm install
npm run prepare:preview
```

`prepare:preview` copies `.env.example` to `.env.local` only when `.env.local` does not already exist.

Git Bash equivalent:

```bash
cd /d/UniWay/frontend
npm install
npm run prepare:preview
```

## Start the backend

Open PowerShell terminal 1:

```powershell
powershell -ExecutionPolicy Bypass -File D:\UniWay\backend\scripts\run-local-preview.ps1
```

The script:

1. uses the existing `backend/.venv` and `backend/.deps`;
2. selects `backend/uniway_local.sqlite3`;
3. applies committed migrations;
4. loads safe fictional demo data;
5. starts Django at `http://127.0.0.1:8000`.

Keep this terminal open.

## Start the frontend

Open terminal 2:

```powershell
cd D:\UniWay\frontend
npm run preview:beta
```

Git Bash:

```bash
cd /d/UniWay/frontend
npm run preview:beta
```

Open:

```text
http://127.0.0.1:3000
```

The preview command checks that dependencies and `.env.local` exist. The backend must be reachable to enter the product: when session confirmation is unavailable, the frontend intentionally shows a full-screen retry state instead of protected UI.

After sign-in, accounts without completed onboarding stay in the required six-step setup. The product sidebar and modules appear only after the backend confirms onboarding completion.

## Local demo accounts

`run-local-preview.ps1` runs the safe fictional demo seed command. It creates local-only accounts for founder review:

| Role | Email | Password |
| --- | --- | --- |
| Student | `student.demo@uniway.local` | `UniWay-Demo-842!` |
| Organizer | `organizer.demo@uniway.local` | `UniWay-Demo-842!` |
| Admin | `admin.demo@uniway.local` | `UniWay-Demo-842!` |

These are development credentials for the local SQLite preview only. They are not production accounts, not a backdoor, and must not be reused outside local founder/demo environments.

## Founder demo checklist

Before a live founder review, walk through this path:

1. Open `http://127.0.0.1:3000` while logged out and confirm the full-screen sign-in/register gate appears without the product sidebar.
2. Try one invalid login and confirm a clean error message appears.
3. Register a new account and confirm it lands in the required onboarding flow before showing the app shell.
4. Complete onboarding or sign in as `student.demo@uniway.local`, then review `/dashboard`, `/profile`, `/events`, `/events/my`, and at least one event detail page.
5. Sign in as `organizer.demo@uniway.local` and review `/organizer/events`, draft/edit/submit flows, custom registration form editing, event status clarity, participants, CSV export, ticket verification, and check-in.
6. Sign in as `admin.demo@uniway.local` and review `/admin/events/moderation`, including the pending fictional event.
7. Review `/pricing`, `/universities`, `/roadmap`, `/essays`, `/exams`, `/finance`, `/activities`, and `/research` as honest preview pages.
8. Check a narrow/mobile viewport for horizontal overflow, readable cards, and reachable navigation.
9. Confirm Event Map/catalog remains visible on the Free plan and does not imply paid gating.

Known V1 demo limitations: payments, external Telegram delivery, QR image rendering/scanning, Google Sheets export, AI gateway, and real map tiles are intentionally deferred. Demo records are fictional and admissions guidance must be verified against official sources.

## Suggested review routes

- `/dashboard` — authenticated command center
- `/profile` — profile completion and editing
- `/events` — authenticated moderated event catalog
- `/events/my` — current registrations
- `/organizer/events` — organizer workflow for organizer/admin roles
- `/admin/events/moderation` — moderation workflow for admin roles
- `/universities`, `/roadmap`, `/essays`, `/exams`
- `/finance`, `/activities`, `/research`, `/pricing`

Use browser responsive mode to review narrow/mobile layouts.

## Common errors

### `npm is not recognized`

Install a current Node.js LTS release, reopen the terminal, then confirm `node -v` and `npm -v`.

### `Could not read package.json`

The terminal is in the wrong directory:

```powershell
cd D:\UniWay\frontend
```

In Git Bash use `/d/UniWay/frontend`, not `D:\UniWay\frontend`.

### Frontend dependencies are missing

```powershell
cd D:\UniWay\frontend
npm install
```

Do not run `npm audit fix --force` during preview setup; forced upgrades may introduce breaking dependency changes.

### `.env.local` is missing

```powershell
cd D:\UniWay\frontend
npm run prepare:preview
```

### Backend is not reachable

Start terminal 1 with:

```powershell
powershell -ExecutionPolicy Bypass -File D:\UniWay\backend\scripts\run-local-preview.ps1
```

### Port 3000 or 8000 is already in use

Close the older UniWay development terminal before starting another instance. Do not terminate unrelated processes.

### PostgreSQL connection error

Use `run-local-preview.ps1`; it explicitly selects the local SQLite preview database. Direct `python manage.py runserver` uses the normal project database configuration and may expect PostgreSQL.

## Stop the preview

Press `Ctrl+C` in both terminal windows.

The local SQLite file is ignored by Git and may be retained between preview sessions.

## Verified local environment

The LOCAL-RUN-001 path was verified on June 23, 2026 with:

- Node.js `v24.11.1`
- npm `11.6.2`
- Next.js `15.5.19`
- the repository-local Django environment

The verification included Django health and demo event responses, frontend `/events` HTTP 200, TypeScript checking, and a production frontend build.

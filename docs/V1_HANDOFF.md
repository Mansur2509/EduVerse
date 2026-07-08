# UniWay V1 Beta Handoff

Date: 2026-06-23

This document freezes the current V1 beta state. Do not start a new feature until a founder visual review has been completed.

## Current product state

UniWay V1 beta is a local founder-reviewable product shell with authenticated access, mandatory onboarding, student profile, event catalog/registration, organizer event management, admin moderation, dashboard, pricing, and honest preview pages for future modules.

The app is gated by backend-confirmed auth and onboarding. Demo users exist for student, organizer, and admin role review.

## Completed modules

- AUTH-001
- UI-SYSTEM-001
- I18N-001
- PROFILE-001
- EVENTS-001
- ORGANIZER-001
- BETA-PREVIEW-001
- LOCAL-RUN-001
- BETA-QA-001
- AUTH-GUARD-001
- V1-UI-REDESIGN-001
- V1-BRAND-REDESIGN-002
- ONBOARDING-GATE-001
- V1-ADMISSIONS-ONBOARDING-FINAL-001
- V1-FINAL-POLISH-CONTINUE-001
- V1-DEMO-STABILIZATION-001

## Known limitations

- Full founder visual review still needs to be done manually.
- Event map is still a preview/list-map hybrid, not a full production interactive map.
- University database is still preview-level.
- SAT/IELTS/AP banks are not production-ready.
- AI gateway is not implemented yet.
- Payments are not implemented yet.
- Payments, external Telegram delivery, QR image rendering/scanning, and Google Sheets export are not implemented yet.

## Known risks

- Browser visual QA was partially blocked by the local browser tooling after initial auth/register/onboarding checks.
- Local auth still uses browser token storage; production hardening remains AUTH-002.
- Demo accounts are local-only credentials for founder preview and must not become production access paths.
- The current Git state in this environment appears fully untracked, so review/staging must be handled carefully before any commit.

## What not to touch next

- Do not start UNIVERSITY-001, AI, payments, external Telegram delivery, Google Sheets, or new modules before founder visual review.
- Do not change the auth guard or onboarding gate unless founder review finds a blocking issue.
- Do not replace the current V1 academic visual direction.
- Do not add dependencies or internet-dependent tooling during the freeze.

## Recommended next task order

1. FOUNDER-VISUAL-REVIEW-001
2. UNIVERSITY-001
3. FORMS-001
4. EVENT-MAP-REAL-001
5. ROADMAP-001
6. ESSAY-FEEDBACK-001
7. AI-GATEWAY-001
8. SUBSCRIPTIONS-001
9. DEPLOYMENT-001

Exact next prompt title to use later:

```text
FOUNDER-VISUAL-REVIEW-001: Manual founder visual QA for UniWay V1 beta.
```

## Latest checks passed

The latest completed stabilization run passed:

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate --noinput`
- `python manage.py test` — 39 tests passed
- `ruff check .`
- `npm run check:i18n` — 892 keys across 4 locales
- `npm run typecheck`
- `npm run lint`
- `npm run build`

Register/login/onboarding smoke QA also passed:

- Register returned access token.
- Fresh registered account stayed gated in onboarding.
- Student, organizer, and admin demo users logged in with correct roles.
- Demo users had completed onboarding.

## Founder demo checklist

1. Open the app logged out and confirm only the auth gate appears.
2. Try invalid login and confirm a clean error.
3. Register a new account and confirm mandatory onboarding appears before the app shell.
4. Sign in as the student demo user and review `/dashboard`, `/profile`, `/events`, `/events/my`, and one event detail page.
5. Sign in as the organizer demo user and review `/organizer/events`, draft/edit/submit status clarity, and participants.
6. Sign in as the admin demo user and review `/admin/events/moderation`.
7. Review `/pricing`, `/universities`, `/roadmap`, `/essays`, `/exams`, `/finance`, `/activities`, and `/research`.
8. Check a narrow/mobile viewport for horizontal overflow and navigation usability.
9. Confirm Event Map/catalog remains available on the Free plan.

## Exact local beta launch commands

Backend terminal:

```powershell
powershell -ExecutionPolicy Bypass -File D:\UniWay\backend\scripts\run-local-preview.ps1
```

Frontend terminal:

```powershell
cd D:\UniWay\frontend
npm run preview:beta
```

Open:

```text
http://127.0.0.1:3000
```

## Demo accounts

Password for all demo accounts:

```text
UniWay-Demo-842!
```

- `student.demo@uniway.local`
- `organizer.demo@uniway.local`
- `admin.demo@uniway.local`

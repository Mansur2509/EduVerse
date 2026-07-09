# Production Deployment Checklist

This is the operational checklist for deploying UniWay (backend on Render,
frontend on Vercel) to production. See `docs/SECURITY.md` for the broader
threat model and `docs/DEPLOYMENT.md` for environment separation and the
required-variables list. This doc is the step-by-step "am I safe to deploy
right now" list.

## 1. Secret rotation (only if a secret was ever exposed)

If `DATABASE_URL`, the Supabase database password, `DJANGO_SECRET_KEY`, or any
provider API key was ever committed, pasted in chat, or otherwise exposed:

- [ ] Rotate the Supabase database password immediately (Supabase dashboard →
      Project Settings → Database → Reset password).
- [ ] Update Render's `DATABASE_URL` environment variable with the new
      connection string once the password is rotated.
- [ ] Redeploy the backend service on Render after the environment variable
      change (Render does not hot-reload env vars into a running instance).
- [ ] If `DJANGO_SECRET_KEY` was exposed, generate a new one and update it on
      Render too — an exposed secret key lets an attacker forge signed
      sessions/tokens.
- [ ] Rotate any exposed third-party API key (Gemini/OpenRouter) from that
      provider's console, then update Render.

## 2. Environment variables (Render — backend)

- [ ] `DJANGO_DEBUG=false`
- [ ] `DJANGO_SECRET_KEY` is set to a real generated value (never the
      `.env.example` placeholder).
- [ ] `DATABASE_URL` is set (the app refuses to boot without it when
      `DJANGO_DEBUG=false` — see `config/database_guard.py`).
- [ ] `DJANGO_ALLOWED_HOSTS` — comma-separated, **no protocol, no path**:
      ```
      eduverse-vvw2.onrender.com,uni-way-beta.vercel.app,example.com
      ```
- [ ] `CORS_ALLOWED_ORIGINS` — comma-separated, **protocol required, no
      trailing slash**:
      ```
      https://uni-way-beta.vercel.app,https://example.com
      ```
- [ ] `CSRF_TRUSTED_ORIGINS` — same format as CORS above (protocol required,
      no trailing slash):
      ```
      https://uni-way-beta.vercel.app,https://example.com
      ```
- [ ] `DJANGO_SECURE_COOKIES=true`
- [ ] Gemini/OpenRouter keys set and not blank.

A trailing slash on a CORS/CSRF origin (`https://example.com/`) or a bare host
with no scheme silently fails to match — Django compares the origin string
exactly. Double-check by pasting the value and looking for a stray `/` at the
end.

## 3. Environment variables (Vercel — frontend)

- [ ] Every `NEXT_PUBLIC_*` API base URL points at the production backend,
      not `localhost`.
- [ ] No provider secret (Gemini key, database URL, JWT secret) is ever set
      with a `NEXT_PUBLIC_` prefix — that prefix ships the value to every
      browser.

## 4. Start command

- [ ] The production start command runs migrations then gunicorn, and does
      **not** call `seed_demo`:
      ```
      python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
      ```
- [ ] `seed_demo` only appears in local `compose.yaml` (Docker Compose dev
      topology) — confirm it has not been copied into the Render dashboard's
      start/build command.

## 5. Pre-deploy checks

Run from `backend/`:

```
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
ruff check .
git diff --check
```

Run from `frontend/`:

```
npm run typecheck
npm run lint
npm run build
npm run check:i18n
```

## 6. Deploy

- [ ] Push to `main` (only after explicit approval — this repo does not
      auto-push).
- [ ] Trigger/verify the Render backend deploy.
- [ ] Trigger/verify the Vercel frontend deploy.

## 7. Post-deploy smoke test

Run `scripts/production_smoke_test.py` against the live backend (see that
script's own docstring for usage). At minimum:

- [ ] `/api/v1/health/` responds 200 in under 2s.
- [ ] An authenticated request (e.g. `/api/v1/profile-assessment/me/`)
      succeeds with a real access token.
- [ ] The university list endpoint responds in a reasonable time and does not
      call AI.

## 8. Manual browser QA

- [ ] Log in with a real (or demo) account.
- [ ] Dashboard loads without a raw JSON error or infinite spinner.
- [ ] Universities list loads.
- [ ] Essay review page handles an AI-unavailable state gracefully.
- [ ] No raw i18n keys visible anywhere touched by this deploy.

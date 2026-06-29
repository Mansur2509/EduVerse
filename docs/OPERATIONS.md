# Operations

## Backend cold starts (Render free tier)

### Problem

The backend is deployed on Render's free tier, which spins the service down
after ~15 minutes with no inbound traffic. The first request after a spin-down
is a **cold start**: Render boots a fresh container and only then serves the
request. Measured behaviour:

| State | `/api/v1/health/` response time |
| --- | --- |
| Cold (after >15 min idle) | **hung past 90s** on the first request |
| Warm (subsequent requests) | **~0.8s**, consistent across 10 consecutive runs |

This single fact explains every symptom reported for the Universities, Event
Map, Essays, and Applications pages:

- **"Infinite spinner that never resolves"** — the first request hit a
  cold-starting backend, and the frontend had no request timeout, so the
  browser's `fetch` stayed pending indefinitely.
- **"We could not load…" error** — the cold start eventually exceeded a network
  limit and the connection was reset, so `fetch` rejected and the screen showed
  its (correct) error state.
- **"Sometimes fast, sometimes very slow" (Event Map)** — warm vs. cold; the
  data and query are identical, only the container state differs.
- **"Blank page, no spinner, no error" (Essays)** — a *separate* bug (see
  below), not cold start.

The endpoints themselves are healthy. With the backend warm, all four return
`200` with valid JSON (Universities ~35 KB, Events ~2.5 KB, Essays/Applications
empty lists for a new user). CORS is correctly configured (the Vercel origin is
whitelisted, verified via an `OPTIONS` preflight), the Events query already uses
`select_related` + a count annotation (no N+1), and Supabase RLS does not block
Django (it connects server-side and returns full data).

### The blank-page bug (separate root cause)

The Essays "completely blank, no feedback" state was **not** cold start. The app
had **no React error boundary** anywhere in the tree, and the i18n `t()` helper
threw (`undefined.replace(...)`) when given a missing/dynamic key. Any
render-time throw therefore unmounted the whole route into a blank page. Fixed
by (a) adding `app/error.tsx` + `app/global-error.tsx`, and (b) making `t()`
fall back to the key instead of throwing.

## Mitigations

Three options, in order of cost:

### 1. Keep-alive ping (free, implemented)

`.github/workflows/keepalive.yml` pings `/api/v1/health/` every 10 minutes via
GitHub Actions, keeping the service warm during active hours. Best-effort:
GitHub cron can lag a few minutes and is disabled after 60 days of repo
inactivity. For a stronger free guarantee, point an external monitor
(UptimeRobot, cron-job.org) at the same health URL on a 5-10 minute interval.

### 2. Frontend resilience + honest UX (implemented)

Even with keep-alive, a cold start can still happen (e.g. first visit of the
day). The frontend now degrades gracefully instead of hanging or going blank:

- **Request timeout + auto-retry** — `apiRequest` caps every call at
  `REQUEST_TIMEOUT_MS` (60s) and converts a timeout/network failure into a
  typed `ApiError` rather than hanging forever. Because the first failed request
  is also what *triggers* the Render wake-up, safe idempotent GET reads are
  automatically retried once after ~2.5s, so a page self-heals through a cold
  start instead of forcing the user to press "Try again". Non-GET requests are
  never auto-retried.
- **"Waking up" messaging** — if any load takes longer than 5s, the loading
  state adds: *"The server may be waking up. The first load after a period of
  inactivity can take up to a minute."* Applied to the auth/session gate (the
  first request on app load) and to the Universities, Event Map, Essays, and
  Applications screens.
- **Error boundaries** — `app/error.tsx` and `app/global-error.tsx` guarantee a
  clear, retryable message instead of a blank page for any render-time error.

### 3. Upgrade Render (paid, recommended for launch)

Render's **Starter** instance type (~$7/month per service at time of writing)
does **not** spin down, eliminating cold starts entirely. Recommended before any
public launch or live admissions-reviewer demo, where a 60-90s first-load delay
is unacceptable and keep-alive's best-effort guarantee is too weak. Until then,
options 1 + 2 are the interim solution.

## Supabase RLS cleanup (tracked, not blocking)

Supabase reports RLS warnings because Django created tables in the public
schema. This is a security-hardening follow-up, **not** a functional bug: Django
uses a server-side connection that is not subject to RLS, which is why all
endpoints return real data. Tracked for a later security pass.

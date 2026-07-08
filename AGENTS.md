# UniWay Agent Guide

UniWay is a production-minded student success platform. Repository documentation is the project memory and the source of truth for implementation decisions.

## Required reading

Before changing code:

1. Read this file.
2. Read `docs/TASKS.md` and the documentation relevant to the task.
3. Search for related code; do not scan the full repository unless necessary.
4. Implement one task at a time with the smallest practical diff.

## Product rules

- The product must feel academic, calm, premium, trustworthy, and useful.
- AI is a supporting capability, not the visual identity.
- Event Map is a core V1 feature and remains available on every plan.
- Never claim or imply guaranteed admission.
- Never display invented admission probabilities.
- Admissions comparisons use published ranges and always link to official sources.
- Essay tooling may critique and guide, but must not ghostwrite application essays.
- Financial content is educational and must not provide personalized financial, investment, tax, legal, or trading advice.
- Exam questions must be original. Never copy proprietary question banks or copyrighted preparation materials.
- Important AI or data-derived guidance must tell users to verify critical information with official sources.

## Architecture rules

- Keep the monorepo split into `frontend/`, `backend/`, and `docs/`.
- Frontend uses Next.js, TypeScript, Tailwind CSS, shadcn-compatible primitives, and Feature-Sliced Design.
- Respect FSD dependency direction: `app -> screens -> widgets -> features -> entities -> shared`.
- Backend is a modular Django/DRF application organized by service boundary so modules can be extracted later.
- Frontend never calls OpenRouter or another model provider directly.
- Avoid introducing a new framework, state library, database, or hosting dependency without documenting the decision.
- Keep public API behavior aligned with `docs/API_CONTRACTS.md`.

## Security rules

- Store secrets only in environment variables; never commit real credentials.
- Use the Django ORM and serializer validation for database writes.
- Default API access is authenticated; explicitly mark public read endpoints.
- Enforce role-based access for student, organizer, and admin actions.
- Keep CORS and CSRF origins allowlisted.
- Treat uploaded files, organizer event content, essays, and AI input as untrusted.
- Events submitted by organizers are never public before moderation.
- Log important moderation and AI usage actions without logging secrets or unnecessary private essay content.
- Review `docs/SECURITY.md` for every auth, upload, AI, billing, or moderation task.

## Coding standards

- TypeScript is strict; avoid `any`.
- Prefer small, accessible, server-rendered components until client behavior is needed.
- Python code follows PEP 8 and uses explicit validation and permissions.
- Add tests for new business rules and security-sensitive behavior.
- Keep modules focused and names domain-oriented.
- Do not refactor unrelated code during a feature task.

## Token-efficiency rules

- Use search to locate relevant files.
- Read only the files needed for the current task.
- Prefer small diffs and existing components.
- For reviews, start with `git diff`.
- Do not produce long explanations unless requested.
- Escalate to broad architecture review or a model council only for high-impact decisions.

## Completion checklist

After meaningful changes:

1. Run the relevant lint, type checks, and tests where the local toolchain permits.
2. Update `docs/TASKS.md`.
3. Update `docs/DECISIONS.md` when an architectural or product decision changed.
4. Summarize changed files, validation results, blockers, and the next task.


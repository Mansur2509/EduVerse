# UniWay Icon System 015

## Purpose

Icons improve scanning and action recognition without becoming decoration.
UniWay keeps an academic, restrained interface: text remains the source of
meaning, icons never imply admissions outcomes, and motion never delays an
action.

## Source and tokens

- `lucide-react` is the only general-purpose icon dependency.
- The Google `G` is the sole branded exception and lives in one shared
  `GoogleIcon` component.
- Shared rendering uses `AppIcon` from `frontend/src/shared/ui/icon.tsx`.
- Size scale: `xs` 14 px, `sm` 16 px, `md` 18 px, `lg` 20 px, `xl` 24 px.
- Default stroke width: `1.75`.
- Glyphs inherit `currentColor`; no route-specific hardcoded light/dark icon
  assets are required.
- The global `.lucide` rule keeps legacy Lucide usages on the same stroke while
  screens are incrementally moved through `AppIcon`.

## Accessibility contract

- Decorative glyphs use `aria-hidden` and are not focusable.
- Text remains present for status and action meaning; color/icon alone is not
  sufficient.
- Icon-only controls use `IconButton`, which requires a localized label and
  exposes it through both `aria-label` and `title`.
- Important icon-only touch targets are 40-44 px. Map pins retain a compact
  visual marker inside a 44 px interactive target.
- Loading glyphs have adjacent status text and spin only while work is active.
- `prefers-reduced-motion` disables spinner/transition movement through the
  existing global reduced-motion rule.
- Focus outlines are owned by the existing button/link/input system and remain
  visible in both themes.

## Navigation coverage

| Surface | Icon treatment |
| --- | --- |
| Primary shell | Dashboard, profile, events, my events, universities, roadmap, essays, applications, exams, finance, activities, research, and plans use distinct Lucide glyphs. |
| Account shell | Notifications and logout use named actions; the notification bell is a labeled 40 px control. |
| Organizer/admin | Organizer events, university import, event moderation, feedback, reports, organizers, and analytics keep distinct role-appropriate glyphs. |
| University context | Browse, recommendations, and strategy tabs use graduation, suggestion, and planning glyphs. |
| Application context | Applications, target universities, and strategy tabs use list, target, and route glyphs. |
| Admin review context | University review, reports, and organizer review tabs use shield, flag, and user-administration glyphs. |

Recommendations and strategy remain contextual instead of returning to the
already dense top-level sidebar. AP planning remains inside Exams. Personal
analytics remains a Dashboard module. No fake Settings route was created only
to satisfy an icon checklist.

## High-value action and state coverage

- Authentication: full name, email, password, password visibility, login,
  register, demo login, Google login, loading, and error/notice states.
- Profile: structured-section navigation, edit/delete actions, completion
  badges, and existing add/close/save actions.
- Notifications: type glyphs, unread/read/archive actions, open, refresh,
  loading, empty, error, and preferences.
- Shared UI: loading, retry, unsaved-change decisions, contextual tabs, support
  close, language, help, filters, pagination, and app-shell actions.
- Existing domain icons were retained for university facts, fit/source links,
  applications, essays, roadmap tasks, events/tickets/participants, organizer
  actions, moderation, and exam dates.

## Motion

- Color transitions use the existing 140 ms fast token.
- Chevrons rotate only for expandable state.
- Loading/refresh glyphs rotate only during active work.
- No icon changes layout size on hover; external-link movement is not required.
- No decorative or continuous notification animation is used.

# Design System

## Direction

UniWay should feel like a composed academic institution: premium, calm, trustworthy, and information-rich without being crowded. The V1 language combines Harvard-like crimson and editorial authority with Penn-like navy structure and clarity, without copying either institution's marks or layouts.

The current baseline is a warm ivory/light academic canvas with deep navy navigation, crimson actions, restrained gold accents, serif headings, and crisp geometry. Dark mode remains structurally supported through the same tokens. The interface avoids gradients, glass effects, neon, glowing AI treatments, robot imagery, chatbot-first layouts, oversized pill controls, and generic soft SaaS cards.

## Semantic tokens

Tokens are HSL channel values in `frontend/src/app/globals.css`. Tailwind aliases are defined in `frontend/tailwind.config.ts`.

| Token | Purpose |
| --- | --- |
| `background` | App canvas |
| `surface` | Navigation, headers, form controls |
| `card` | Standard cards and page panels |
| `elevated` | Nested or raised surfaces |
| `border` | Dividers and component outlines |
| `text` / `foreground` | Primary readable text |
| `muted-foreground` | Secondary text |
| `primary` | Crimson primary actions and active navigation |
| `primary-hover` | Primary interactive hover state |
| `navy` / `navy-foreground` | Institutional navigation and high-authority surfaces |
| `accent` | Academic gold highlights and supporting icons |
| `success` | Confirmed or completed state |
| `warning` | Deadlines and caution |
| `danger` | Errors and destructive state |
| `focus-ring` | Keyboard focus indication |

Components must consume semantic classes such as `bg-card`, `bg-surface`, `text-foreground`, and `text-danger`. Do not add hex colors or route-specific color palettes to feature components.

## Theme behavior

- The root document currently sets `data-theme="light"`.
- Light academic values live in `:root`.
- Dark values live in `[data-theme="dark"]`.
- Theme switching can be added later without changing component color classes.
- Both themes declare `color-scheme` so native controls render appropriately.

## Color usage

- Crimson is reserved for primary actions, active navigation, and key hierarchy.
- Navy is reserved for persistent navigation, institutional identity, and selected high-authority panels.
- Gold is an accent, not a competing primary action color.
- Success, warning, and danger colors communicate state and must always be accompanied by text.
- Borders should remain quiet; avoid bright outlines around every card.
- Text contrast should target WCAG 2.2 AA.

## Components

- Cards use semantic surfaces, thin borders, calm shadows, and corners no larger than 4px.
- Primary buttons use `primary`; secondary buttons use `surface` and `elevated`.
- Forms use the shared field class from `shared/ui/field.ts`.
- Status labels communicate with both text and color.
- Loading and empty states explain what is happening and suggest the next action.
- Desktop navigation uses a sidebar; small screens use a compact bottom navigation.
- On desktop the application owns one `100dvh` viewport: the fixed-width sidebar and main content scroll independently.
- Organizer and administrator links live in a separate role workspace section.
- Profile forms use a restrained content width and compact two-column field rhythm.
- Event Map V1 may use a coordinate-based map-preview/list hybrid when network tiles are unavailable.
- Beta preview modules share one visual contract: status badge, concise purpose, three to five capability cards, next planned feature, adjacent working CTA, and a guardrail when relevant.
- The dashboard is the primary command center. It prioritizes profile readiness, real event registrations, next actions, and module entry points rather than a chatbot surface.
- On small screens, the bottom navigation exposes the essential path while a horizontally scrollable module rail keeps the complete workspace reachable.
- The document canvas must not scroll horizontally. Wide navigation rails and tables own their own horizontal scrolling instead of expanding the page viewport.
- Role-denied states explain the required access and provide clear routes back to the dashboard and free Event Map.
- The unauthenticated experience is a full-screen institutional gateway. Protected navigation and page content must never render until `/api/auth/me/` confirms the backend session.
- Incomplete accounts receive a dedicated full-screen onboarding shell with a compact institutional header, six-step editorial layout, narrow step rail, consistent content width, and no product navigation.
- Pills are reserved for compact status labels only. Buttons, fields, cards, panels, navigation links, and progress bars use crisp corners.

## Typography and accessibility

- Serif headings support the academic character; sans-serif body text preserves readability.
- Maintain semantic heading order and comfortable line lengths.
- Minimum touch targets should remain close to 44px.
- Every interactive icon needs a translated accessible label.
- Visible keyboard focus uses the `focus-ring` token.
- Essential information must not exist only in color, maps, charts, or tooltips.

## shadcn/ui

Phase 0 includes shadcn-compatible local primitives. Generated primitives remain in `src/shared/ui`; feature folders compose them rather than creating parallel design systems.

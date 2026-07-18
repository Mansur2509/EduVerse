# Recommendation & Strategy Engine Audit (022 Phase 0)

Read in full before Phase 1: `services.py::calculate_university_fit`,
`recommendations.py`, `strategy.py`, `fit_vector.py`, `benchmark.py`,
`budget.py`, `major_matching.py` (all `backend/services/university_service/`),
`profile_assessment_service/{recommendations,strategy,services,deterministic}.py`,
`recommendation_cache.py`, `views.py` (both apps), and the frontend
`entities/recommendation`/`entities/strategy` types.

## Architecture as it actually exists (not as assumed)

Contrary to the task brief's working assumption, there is **one** canonical
per-university fit function today, not four competing scorers:

```
calculate_university_fit(profile, university)      # university_service/services.py
        ├─ called once per candidate by ──► calculate_university_recommendations()   # recommendations.py
        │                                           └─ called by ──► build_application_strategy()  # university_service/strategy.py (pure regroup, no rescoring)
        └─ feeds subscores/strengths/risks/missing_data used by the same two callers above

compute_profile_recommendations(assessment)         # profile_assessment_service/recommendations.py
        # university-INDEPENDENT profile-improvement actions from cached
        # assessment gaps (SAT/GPA/IELTS benchmark status, 12-signal severities,
        # capped-section reasons). Never touches a University row.

build_profile_strategy(user, profile, preferences, assessment)   # profile_assessment_service/strategy.py
        # the actual Strategy PAGE backend: 7/30/90-day deadline buckets +
        # testing/essay/recommender/activities plans, and embeds
        # build_application_strategy(...)'s output as one sub-key
        # ("university_list_strategy"). Does not rescore anything itself.
```

So the "four contradictory scoring systems" failure mode the brief warns
against has **not** happened architecturally — `calculate_university_fit` is
already the single source of truth, reused consistently. The real problems
are inside that one function and its caller, not duplication across four.
`compute_profile_recommendations` is close in shape to what Phase 9 calls the
"Improvement Strategy Engine" and should be extended, not replaced.

## Findings

| Current behavior | Problem | User impact | Required fix | Verification |
|---|---|---|---|---|
| `services.py` `CATEGORY_ORDER = ("reach", "competitive", "target", "safety")`; `recommendations.py` maps `category = "reach" if fit["category"] == "competitive" else fit["category"]`. `CATEGORY_QUOTAS` reserves 5/25 slots for `"dream"`. | **"Dream" can never be populated.** No code path ever assigns `"dream"`; the quota is permanently empty. Frontend types (`RecommendationCategory`) already expect `"dream"` as real, so this is a regression/dead-code bug, not a missing feature. | The portfolio silently ships as reach/target/safety only — a "4-tier" system that is actually 3 tiers wearing a 4-tier frontend contract. Users never see the label they'd expect for the most/least selective end of their list. | Phase 6 must define real Dream vs. Reach as two genuinely distinct tiers (not "competitive renamed"), each reachable from the fit calculation. | Persona-based test: for a candidate university with acceptance rate <5%, assert the item can resolve to `category == "dream"` under at least one profile shape, not just `"reach"`. |
| `_acceptance_rate_baseline_index(rate)` sets the **starting** category purely from acceptance rate (a selectivity/prestige-adjacent number); `index_shift` (±1 typically, ±2 max) comes only from GPA+SAT/IELTS direction. | **Category (bucket) membership never responds to extracurricular strength, financial fit, program fit, or application readiness** — those only move `fit_score` (sort order *within* a bucket), never which bucket an item lands in. | This is the direct, verifiable mechanism behind the reported symptom: a weak-extracurricular, high-financial-need profile can still see an elite/very-low-acceptance-rate school bucketed as merely "reach" (competitive→reach) as long as academic numbers are roughly in range — extracurricular and financial mismatch never demote it out of that bucket. | Phase 5's weighted ranking must let *all* profile-strength dimensions (not only academic) influence category, and Phase 7's uneven-profile rules must explicitly cap holistic/selective institutions for weak-extracurricular profiles. | Persona 1 (strong academics/weak extracurriculars/high need) must show Harvard/Stanford-tier schools capped to a small Dream allotment, not dominating Reach. |
| `CATEGORY_QUOTAS = {"dream": 5, "reach": 7, "target": 8, "safety": 6}` is fixed regardless of profile, country, budget, or candidate-pool composition; `_bucket_and_balance` just slices `bucket[:quota]` sorted by `fit_score`. | **No adaptive distribution.** If a country/budget-filtered pool has few genuine "target" matches, the quota still tries to fill from whatever is available, and there is no minimum-fit-score floor — a bucket can be filled with poor-fit items just to hit a count. | Users with narrow, legitimate constraints (single country, tight budget) get a list padded with weak fits rather than an honestly shorter, better-matched list. | Phase 6's distribution must flex to data availability and profile, and must be allowed to under-fill a bucket rather than force weak matches into it. | Test: a narrow-constraint persona (single country, low budget) produces a shorter but higher-average-fit list, not a padded 25. |
| The only **hard filter** in `calculate_university_recommendations` is country/region preference (`_country_matches_preference`). Cost (`_cost_risk`/`compare_cost_to_budget`), deadline urgency, and international-eligibility are all computed but only ever **labeled**, never used to exclude. | **No affordability, deadline, degree-level, or international-eligibility hard filtering.** An unaffordable, deadline-passed, or (if the data existed) international-ineligible university can still appear as a top recommendation with only a risk label attached. | A high-financial-need student can see unaffordable schools ranked highly with just a small warning icon; an expired-deadline school can still show as "recommended" this cycle. | Phase 4 must add real hard filters: expired deadline excluded outright; unaffordable-with-no-aid-signal excluded or demoted per Phase 7 Case E; program/degree-level excluded when verifiably absent. | Test: a university with `application_deadline` in the past never appears in `recommendations`; a >2x-budget university with no aid signal is excluded or moved to a clearly labeled non-primary tier for a high-need persona. |
| `University`/`UniversityProgram` models: confirmed `degree_level` exists on `UniversityProgram`; **no `intake`, no explicit `language_of_instruction`, no `accepts_international` field** exists on `University`. `is_published`/`is_demo` exist; no `is_archived`. | Several of Phase 4's stated hard filters (intake availability, international eligibility, archived-record exclusion) **cannot be implemented today without new fields or must be conservatively treated as "unknown."** | If Phase 4 is implemented assuming these fields exist, it will silently no-op or crash. | Treat intake/international-eligibility/archival as "unknown → passes the filter" (never invented as a false negative) until real fields are imported; do not claim these filters are enforced if the underlying data doesn't exist. | Code review: every new hard filter has an explicit `unknown` branch that does not exclude, plus a test asserting `unknown` never excludes. |
| `calculate_optional_evidence_fit`'s per-category base score is a **fixed ladder purely on `count`**: 0→38, 1→56, 2→70, 3+→82, per category (`activities`, `honors`, `olympiads`, `sports`, `research`, `essays`, `portfolio`, `volunteering`, `recommenders`), then weighted-summed. | **This is raw-activity-count scoring**, exactly what Phase 3 explicitly prohibits ("do not score extracurriculars by raw activity count... a student with 15 shallow activities should not automatically outrank a student with 3 deep activities"). No depth/duration/leadership/impact/initiative/recognition dimensions exist per-activity today. | Two students with identical activity *counts* but very different depth/impact currently score identically on this subscore. | Phase 3's activity-level structure (depth/duration/leadership/impact/initiative/recognition/major_relevance, each 0-5, plus confidence) must replace or sit alongside the count ladder; anti-gaming rules (duplicate-activity dedup, unverified "founder" titles, inflated member counts) must be added. | Persona 4 (excellent academics, almost no activities) vs. a hypothetical persona with many shallow activities must not tie on extracurricular subscore if depth data distinguishes them. |
| Missing GPA (`student_gpa is None`): `academic_score -= 14`. Missing SAT when a university expects one: `academic_score -= 10`. Missing IELTS when expected: `academic_score -= 8` plus `missing_fields.append(...)`. | **Missing evidence is partly penalized like weak evidence**, not cleanly separated as the task requires ("do not treat missing information as poor performance... distinguish weak evidence, missing evidence, genuinely weak profile dimension"). These flat penalties reduce `academic_score` the same way a confirmed-weak score would, just by a smaller fixed amount. | A student who simply hasn't taken the SAT yet (but a test-optional or unknown-requirement school) can be scored lower than a student with a *confirmed* low SAT in some score ranges, which is backwards. | Phase 2's explicit rule ("a student without SAT must not automatically lose points if the target university is test-optional or the test requirement is unknown") must replace flat missing-data penalties with a confidence reduction that does not move the score down for genuinely unknown/inapplicable data. | Unit test: student with no SAT vs. a university with no `sat_p25`/`sat_p75`/`sat_average` on file produces the *same* academic subscore as a student with no SAT and no test-required flag either way — never a penalty for both sides being unknown. |
| Recommendations/strategy views (`GET /universities/recommendations/`, `GET /universities/strategy/`) call `calculate_university_recommendations`/`build_application_strategy`, both pure-Python; `_score_personal_fit` and `qualitative_fit_status` are explicitly documented/verified as cache-reads, never triggering AI. | **This is already correct** — no AI call happens on an ordinary GET today. | None (this is a pass, not a gap). | Preserve this property exactly; any new Phase 1-11 code must keep GET endpoints AI-free. | Existing pattern: grep for AI-provider imports in any new module reachable from the GET view chain; add an explicit test mocking the AI client and asserting zero calls during a `recommendations`/`strategy` GET. |
| `recommendation_cache.py`: cache key includes `user.id` + `compute_profile_snapshot_hash(user)`; shortlist/tracking actions call `invalidate_recommendation_caches(user)` explicitly; TTL is a short 20s safety net, not the primary invalidation mechanism. | **This is already correct** and matches Phase 10's exact requirement (versioned profile fingerprint, deterministic cache key, scoped invalidation). | None (pass). | Extend `compute_profile_snapshot_hash` to cover any new profile-strength inputs (activity depth fields, financial-aid need, etc.) so the fingerprint invalidates on every field Phase 10 lists (major, country, GPA, test score, activity, financial need, essay, application round). | Test: changing each of Phase 10's listed fields individually changes `compute_profile_snapshot_hash`'s output. |
| `compute_profile_recommendations` (profile_assessment_service) already produces prioritized, evidence-linked action items (title/priority/linked_dimension/why_it_matters/evidence_from_profile/expected_impact/next_action) from cached assessment gaps. | **Good foundation, but university-blind** — it cannot say "improving your SAT would materially improve fit for 4 Reach universities" (Phase 10's example) because it never looks at the student's actual candidate/portfolio list. | Strategy actions read as generic ("your GPA is below benchmark") rather than tied to the specific universities in the user's own list. | Phase 9/10 must cross-reference this engine's gaps against the user's actual recommended/tracked portfolio to produce university-counted impact statements, without duplicating its scoring. | Test: an action's `affected_universities` count matches how many portfolio items actually have that specific risk code present. |
| No pin/exclude/regenerate/desired-count/category-distribution controls exist anywhere in `university_service` or `profile_assessment_service` views today. | Phase 11 (recommendation controls) is **wholly new**, not a rework. | Users cannot currently customize their recommendation list at all beyond shortlisting existing catalogue browsing. | Build fresh: a small persisted-preference model (or reuse of existing `preferences` param plumbing already threaded through `calculate_university_recommendations(profile, preferences=None, ...)` — the parameter exists but is unused by the function body today) plus pin/exclude sets. | New tests only; no regression risk since nothing exists to break. |
| No internal diagnostic view/structured logging exists for recommendation generation (candidate counts, filter removals, exclusion reasons). | Phase 12 is wholly new. | Debugging "why didn't X show up" currently requires reading source, not a request. | Build fresh, admin-gated, reusing `IsAdminRole` (already used elsewhere, e.g. `institution_service`, `feedback_service` admin views). | New tests only. |
| No ML-readiness event logging specific to recommendations (impressions/saves/pins/removals) exists; `activity_service.track_event()` (generic, sanitizing, best-effort) already exists and is used by 7+ other event types as of the 021 task. | Phase 13 needs new `AnalyticsEvent.EventType` members and call sites, reusing the existing helper — this is additive, not a new subsystem. | None yet (nothing logged today, so no wrong data to migrate). | Add new event types (`RECOMMENDATION_IMPRESSION`, `UNIVERSITY_PINNED`, `UNIVERSITY_EXCLUDED`, etc.) the same way 021 Phase 4 added its 7; reuse `track_event()`, never log essay text/private data. | Mirrors 021's own test pattern (`test_analytics_gaps_021.py`) almost exactly. |
| `major_matching.py`'s `CLUSTER_KEYWORDS` and `recommendations.py`'s `PROGRAM_CLUSTERS` are **two separately maintained keyword-cluster tables** for what is conceptually the same "major cluster" concept (`UniversityProgram.MajorCluster` choices). | Minor duplication risk: the two tables can drift (a keyword added to one but not the other), producing inconsistent cluster inference between the fit engine's `infer_major_clusters` and the recommendation engine's own `_clusters_for_majors`. | Low today (no observed inconsistency), but a maintenance hazard as Phase 1-9 work touches major-matching code. | Not in this task's required scope, but flag for consolidation if Phase 4/5 work touches either table — prefer extending `major_matching.py`'s single table over maintaining `recommendations.py`'s parallel one. | N/A (no test required by this task; noted for awareness). |

## What Phase 1+ can safely reuse as-is

- `calculate_university_fit`'s academic/program/essay/deadline/cost subscore
  functions (`_assess_academics`, `_score_program_fit`, `_score_essay_fit`,
  `_score_deadline_fit`, `_score_cost_fit`) — sound, already GPA-scale-aware,
  already distinguish missing-university-data from missing-student-data in
  most (not all — see table above) branches.
- `normalize_profile_academics`, `compare_academic_benchmark`,
  `normalize_university_gpa_benchmark` (GPA normalization + benchmark
  comparison) — already handles scale confidence and percentage-normalized
  comparison correctly (this was PERFORMANCE-012's own fix for exactly the
  "4.9/5.0 read as below an 88/100 benchmark" bug class).
- `fit_vector.py`'s 12-signal gap/severity/band model — reusable as the
  qualitative/holistic comparison primitive; do not build a second one.
- `resolve_benchmark`'s tiered fallback chain (dream→major/country→country→
  global-major→global, with a minimum-sample-size floor) — a good pattern
  for Phase 1's confidence-by-comparability requirement.
- `recommendation_cache.py`'s fingerprint + explicit-invalidation pattern.
- `compute_profile_recommendations`'s reason-code/evidence-linked action
  shape as the template for Phase 9's Strategy actions.
- `curriculum_rigor`/`calculate_major_curriculum_fit` (user_profile_service)
  for curriculum-aware academic context.

## What must change (summary of required fixes, Phase-mapped)

1. Fix the dead "dream" category (Phase 5-6).
2. Let extracurricular/financial/readiness dimensions affect **category**,
   not just sort order within a category (Phase 5-7).
3. Replace fixed 5/7/8/6 quotas with adaptive, data-aware distribution that
   can under-fill rather than pad with weak matches (Phase 6).
4. Add real hard filters: expired deadline, unaffordable-with-no-aid (Phase
   4/7), degree-level where data exists; treat genuinely absent fields
   (intake, international-eligibility) as non-excluding "unknown" (Phase 4).
5. Replace/extend the raw-count extracurricular ladder with a depth-based
   activity model (Phase 3).
6. Separate missing-data confidence reduction from weak-data score penalties
   across every subscore, not just the ones already correct (Phase 1-2).
7. Cross-reference profile-gap recommendations against the actual portfolio
   for university-counted impact statements (Phase 9-10).
8. Build pin/exclude/regenerate controls, diagnostics, and ML-readiness
   logging — all net-new, no existing code to reconcile (Phase 11-13).

## Explicitly not broken (do not "fix" what already works)

- No AI call on ordinary recommendation/strategy GETs.
- No duplicated fit-scoring system across recommendations vs. strategy.
- Cache invalidation is already versioned/deterministic/scoped.
- GPA normalization already handles scale ambiguity and percentage-based
  comparison correctly.

## Phase 13: ML-readiness logging (analytics only -- this is not ML)

The recommendation and strategy engines remain 100% deterministic and
explainable (canonical Fit Engine + rule-based weighting). No model is
trained, no prediction is served from a model, and nothing in the product
should describe this system as "AI-powered" or "machine learning."

What Phase 13 actually added is passive, sanitized analytics logging --
reusing the existing `activity_service.track_event()` pipeline the same way
021 Phase 4 did -- so that a real future ranking-model project would have
genuine, labeled behavioral history to evaluate against instead of starting
from zero:

- `RECOMMENDATION_IMPRESSION`: fired on every `/recommendations/` GET (not
  just cache misses), with `result_count` / `excluded_by_user_count` /
  `list_size_limited` metadata -- what the student was actually shown.
- `UNIVERSITY_PINNED` / `UNIVERSITY_EXCLUDED`: fired once, on creation, from
  the Phase 11 pin/exclude actions -- explicit positive/negative signal.
- Already covered by pre-existing events, reused as-is (no new code needed):
  `UNIVERSITY_SHORTLISTED` (save), `APPLICATION_CREATED` with
  `metadata.source` (recommendation-to-application conversion), and
  `APPLICATION_STATUS_CHANGED` with `metadata.from`/`to` (submitted /
  accepted / waitlisted / rejected -- the voluntarily-provided outcome
  signal, since students self-report their own application status).

As with every other analytics event, `track_event()`'s sanitizer strips
anything that isn't a short flat scalar, so essay text, recommendation
letters, and full profile/university payloads can never end up in this
table by construction.

Prerequisites before any future model (not started, not scheduled):
enough volume per university/category for the impression/outcome signal to
be statistically meaningful, a held-out evaluation set, and a documented
decision that the deterministic system's explainability is an acceptable
trade-off to give up for whatever the model would add.

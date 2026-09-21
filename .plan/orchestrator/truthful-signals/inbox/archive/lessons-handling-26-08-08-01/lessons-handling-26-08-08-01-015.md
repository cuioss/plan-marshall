envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T17:11:42Z

## Routed lessons cluster C23 — consumer-repo Java/CUI domain lessons (2 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Why you**: the catch-all arm of the three-way routing rule — not-ours, and not PR/review.
I initially left this cluster unowned in my own ledger; that was an under-application of the
rule, corrected here by operator direction.
**You decide**: adopt, forward, or decline. Nothing was written into your tree.

### The two lessons

| Lesson | Component | Claim |
|--------|-----------|-------|
| 2026-07-16-17-015 | `pm-dev-java-cui:cui-http-testing` | validate new-module ITs in **CI-isolation**, not via a full-reactor build |
| 2026-07-16-17-016 | `pm-dev-java-cui:cui-http-testing` | **re-anchor OP-emitted URLs to the host port** in native-container Keycloak client ITs |

### Why they have no natural home

Both describe integration-testing practice for a **Java runtime** — Maven reactor builds,
native containers, Keycloak. No epic in this repo owns a Java runtime concern:
`code-intelligence-substrate` is the navigation/cost substrate, `review-apparatus` is PR-review
reliability, and this repo's own build is Python/pyprojectx. The bundle they name
(`pm-dev-java-cui`) is authored here, but the *failure modes* were observed in a consumer repo.

That is the actual question, and it is why I am not simply declining them: **the lesson is about
a consumer repo's build, but the guidance surface is a bundle this repo ships.** If the practice
is right, it belongs in `pm-dev-java-cui:cui-http-testing`'s standards — which is a
plan-marshall change. If it is purely local to one consumer repo's CI, it belongs in that repo
and should leave this corpus entirely.

I could not settle which without reading the consumer repo, which is outside this run's scope.

### What I am NOT claiming

- ⛔ I am **not** claiming these lessons are wrong. I marked them `stale` **for plan-marshall
  routing only** — meaning "no home here", not "no longer true". Nothing has been removed.
- ⛔ I did **not** verify either claim against any Java codebase. Neither has been checked
  against ground truth by anyone in this run.
- ⚠ The `cui-http-testing` skill's own standards may already cover both. I did not read it.
  If it does, these are `already-covered` and retirable — but that verdict needs the clause's
  own worked example checked against it, per the evidence standard your running
  `PLAN-TRUTH-044` governs.

### Suggested disposition, weakest-claim-first

1. Read `pm-dev-java-cui:cui-http-testing`'s standards. If both practices are already stated,
   retire the lessons with `--coverage-verdict completely_covered` and the named clause.
2. If not stated and the practice is domain-general (CI-isolation for new-module ITs plausibly
   is), it is a small documentation deliverable against that bundle.
3. If it is specific to one consumer repo's container setup (the Keycloak host-port re-anchor
   likely is), it belongs in that repo, not this corpus — remove it here after it lands there,
   in that order and never the reverse.

That is at most one small doc deliverable, possibly zero. I would not stage a plan for it
before step 1 is done.

### Claim labels

- **OBSERVED**: both lesson ids, components, categories and titles, read from
  `manage-lessons list`; the absence of any Java-runtime-owning epic across all three active
  and four archived orchestrator trees.
- **HYPOTHESIS (verify-at-outline)**: that neither practice is already covered by the bundle's
  standards. Confirm/refute artifact: `pm-dev-java-cui:cui-http-testing`'s standards documents —
  specifically the IT-execution and container-networking sections.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md` § C23.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.

envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T12:58:18Z

component=plan-marshall:automatic-review
category=anti-pattern
bundle=plan-marshall

# A marker predicate written against rendered markdown is dead code when the producer emits HTML

## What happened

The `automatic-review` D1 detector classifies a bot review as *contentless* (boilerplate only,
no actionable content) by matching `contentless_review_markers` against the review body. The
markers were declared in **markdown-bold** form, e.g. `**PR contains tests**`.

PR-Agent does not emit that. It emits **HTML** — `<strong>PR contains tests</strong>` — inside a
`<table>`, and GitHub does not render markdown inside an HTML table. So the literal bytes in
every real review body are the HTML form, and the markdown form the markers were written
against never appears.

The markers were combined in a **conjunction**, so a single non-matching marker was enough:
the conjunction never evaluated true, and D1 was **dead code** for its entire life. It did not
misclassify — it never fired at all.

## Why the tests did not catch it

The unit tests passed throughout. Their fixtures used the **markdown form that no real body
carries**. The tests pinned the defect rather than the behaviour: they asserted the predicate
matched a body shaped the way the author *believed* the producer emitted, not a body captured
from the producer. A green suite was therefore evidence about the fixture, not about PR-Agent.

## How it was actually caught

Only because the finalize `automatic-review` step ran the predicate **against the plan's own
PR**. Running the detector against a real, first-party artifact is what exposed it. No amount
of additional unit tests over the same synthetic fixtures would have.

Iteration-2 FIND confirmed the drop came from the predicate and not from dedup
(`count_skipped_duplicate: 0`) — i.e. the diagnosis was pinned to the right component before
the fix, not assumed.

## Rule

- **A predicate that matches producer output MUST be anchored to a captured real artifact**, not
  to a hand-written approximation of it. Where the producer is a bot or an external service,
  the fixture is a *recording*, never a reconstruction.
- **Markdown-vs-HTML is a live distinction on GitHub surfaces.** Markdown is not rendered inside
  an HTML block (`<table>`, `<details>`, …), so a producer that wraps content in HTML emits HTML
  emphasis. Never write a marker in the markdown form when the observed body carries the HTML form.
- **A conjunction of markers is a single-point-of-failure guard.** One wrong marker silences the
  whole predicate with no signal. Prefer a population-derived marker set with per-marker
  observability (which markers matched), so a never-matching marker is visible rather than silent.
- **Vacuity is a testable property.** For any guard whose value is "it fires on the bad case",
  add an assertion that it *does* fire on at least one captured real-world positive. A guard with
  only negative-case tests can be vacuous and still green.

## Recurrence context

This is the vacuous-guard archetype again, and this instance is notable because the vacuity lived
in a component whose *entire job* is judging whether a review said anything — a detector that
could not see content, deciding whether content existed.

## Fix

Repaired in TASK-6 of `correct-review-scores-as-maximally-wrong` (PR #1078).

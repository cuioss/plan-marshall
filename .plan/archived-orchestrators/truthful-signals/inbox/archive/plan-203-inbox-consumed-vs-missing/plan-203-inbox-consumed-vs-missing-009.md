envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:35:28Z

component=plan-marshall:manage-tasks
category=bug
title=qgate keyword_drift searches a haystack narrower than the deliverable it checks, so it emits confident false positives

# qgate keyword_drift searches a haystack narrower than the deliverable it checks, so it emits confident false positives

Observed once in PLAN-203 at `4-plan` (finding `67edab`, severity `warning`, source
`plan-marshall:manage-tasks:qgate-mechanical-checks`).

## What happened

The mechanical check flagged:

> `keyword_drift: TASK-007 uses 'CI' not present in deliverable outline`

Verified against the outline, this is a **false positive**: deliverable 4's **Change-per-file**
narrative literally says *"a read-side ci call already holds"*, so TASK-007's use of `CI` is sourced
verbatim from the deliverable. **The check's haystack excludes Change-per-file text** while the
deliverable's authored surface includes it.

Disposition on the plan: `taken_into_account` — **not suppressed**, because the term is legitimately
present and suppressing would have hidden the detector defect behind a per-instance waiver.

## Rule

A drift detector whose haystack is a **subset** of the surface the author actually wrote will emit
confident, specific, wrong findings — and the natural disposition (suppress this instance) hides the
defect rather than fixing it. **A detector's haystack must be the same population the authoring
contract lets the author write into.** When a mechanical finding is refuted, ask whether the checker's
input scope, not the author's text, is the defect.

This is the epic archetype in a checker: an assertion made from an incomplete view, stated with the
same confidence as one made from a complete one.

Claim label: OBSERVED (first-party, single instance; the haystack gap is confirmed against the outline,
the *frequency* across other plans is unmeasured).

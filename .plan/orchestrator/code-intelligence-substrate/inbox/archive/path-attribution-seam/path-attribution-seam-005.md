envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T18:33:45Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall

# A count-prose sweep scoped to the ONE claim class that triggered it ships the other classes stale — enumerate by claim class, and never state a bare cardinality in a success criterion

## What happened

PLAN-CIS-023 added a twelfth extension point, which invalidated every count claim in `doc/concepts/`. Deliverable D7 was written to sweep them. As drafted, D7 swept only the **extension-POINT** count claims (`eleven` → `twelve`, `16` → `17`) and its success criterion read:

> "Every one of the eight count-prose sites in extension-architecture.adoc is updated"

The 3-outline Q-Gate (`scope_criterion_validator`) caught that the same change also invalidated a second, structurally identical claim class the sweep never mentioned — the **AXIS-count** claims:

- `doc/concepts/README.adoc:28` — "hanging off three deliberately disjoint hierarchies", on the *same line* D7 already edits for the point count.
- `doc/concepts/extension-architecture.adoc:24` — "The eleven points hang off three independent hierarchies", listed under the point-count sweep only, which does not touch `three`.
- `doc/concepts/extension-architecture.adoc:30` — "The three ABCs inherit from none of each other".

Because the criterion asserted a bare `eight`, a plan that satisfied it *exactly as written* would still ship stale prose. The stated cardinality was itself wrong: the file carried ten stale claims (eight point-count + two axis-count).

## What the fix found that the fix's own scope did not predict

Widening the sweep required reading `extension-architecture.adoc` end to end, which yielded **13 sites across three claim classes** — 9 point-count tokens, 3 axis-count tokens, and one *exclusivity* claim at line 20 (that derivation-resolver is the newest and only multiple-inheritance opt-in), a third class nobody had named. Line 24 turned out to carry one token of *each* class, so both had to move together.

A subsequent full sweep of all 22 files in `doc/concepts/` then surfaced a **fourth uncovered axis-count site** at `code-intelligence.adoc:113` that the widened 13-site enumeration still missed.

So the progression was: 8 claimed → 10 actual in one file → 13 across three classes in one file → a 14th in a different file only a full read found.

## The rules

**Do X — enumerate by claim class, not by the token that triggered you.** When a change invalidates a count, ask what *else* the same structural change counts. Adding an extension point changes the point count, the axis count if the point introduces an axis, and any exclusivity/superlative claim about the previously-newest member. Each is a separate class needing its own enumeration pass.

**Do X — success criteria enumerate lines, not cardinalities.** Replace "every one of the eight sites" with the explicit line list. A bare number is unfalsifiable at review time and silently wrong the moment the enumeration is incomplete — and it is the *criterion* that is wrong, so satisfying it proves nothing.

**Do X — a class-widening sweep needs a full re-read, not a re-grep of the widened pattern.** The 13-site enumeration was derived by reading one file completely and still missed a site in another file. Only reading the whole target directory closed it.

**Not Y — do not scope a count sweep from the diff that triggered it.** The triggering diff shows the token you changed, not the family of claims that token participates in.

**Not Y — do not over-apply.** The fix explicitly excluded the *historical* Axis-C rationale at `code-intelligence.adoc:42/44` (correct as a statement about the past) and pinned the remaining-five core-side count at line 16 as deliberately unchanged. A sweep that rewrites every matching token is as wrong as one that rewrites too few; the criterion must name the exclusions.

## Recurrence

This is the count-prose-staleness archetype the epic already tracks, and D7 *existed* to close it — the deliverable written to fix stale counts reproduced the defect in its own scope statement. Lesson `2026-06-25-10-001`, which the plan had explicitly heeded, already demands exact enumeration; heeding it at the plan level did not prevent under-enumeration at the deliverable level. That gap — a lesson applied to the plan but not propagated into each deliverable's success criterion — is the part worth acting on.

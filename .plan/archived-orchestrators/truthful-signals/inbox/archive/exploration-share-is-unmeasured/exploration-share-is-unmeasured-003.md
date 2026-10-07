envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:50:51Z

component=plan-marshall:manage-metrics
category=anti-pattern
title=Adding fields to a data-format doc without updating the SKILL.md enumeration of the same fields (doc-contract divergence, recurrence)

# Doc-contract divergence: a field enumeration exists in two documents and only one was updated

## Observation

Plan `exploration-share-is-unmeasured` (D2) added ten per-phase counters to `manage-metrics`. `data-format.md` was updated with all ten. `manage-metrics` SKILL.md's `enrich` field enumeration was **not** — it kept the pre-change list. Caught by `pre-submission-self-review`, not by any build/lint gate.

This is the recurring **doc-contract-divergence** archetype: the same normative list is materialised in two documents, and a change lands in one.

## Rule

- Before adding a field/flag/counter, search for **every** place the surrounding enumeration is restated. A field enumeration duplicated across `SKILL.md` and a `standards/*.md` is a source-of-truth duplicate; both are load-bearing contracts and both must move together.
- Prefer collapsing the duplication: one document owns the enumeration, the other xrefs it by name. Restating an enumeration is a defect waiting for the next field.
- `pre-submission-self-review` is currently the only gate that catches this class. That is a *detector*, not a fix — the structural remedy is de-duplication.

## Recurrence

Doc-contract divergence is a known recurring archetype in this repository. This is another instance, in a plan that was itself about making implicit facts explicit.

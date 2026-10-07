envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:33:22Z

component=plan-marshall:marshall-orchestrator
category=bug
title=epic.md Ordered Queue duplicates four status.json columns with no generated-block guard

# epic.md Ordered Queue duplicates four status.json columns with no generated-block guard

STAGED by PLAN-203's D4 gate, not fixed. Surface:
`marketplace/bundles/plan-marshall/skills/marshall-orchestrator/templates/epic.md`.

## Observation

The Ordered Queue table asserts `#`, `Plan`, `Workstream`, and `Status` per row. All four are held by
`status.json` `plans[]` (`order`, `id`, `workstream`, `status`), so **all four are DERIVABLE**.

Unlike the START-HERE block, the table is **NOT wrapped in BEGIN/END GENERATED markers** and no verb
regenerates it. Only `analyze.md` Step 4 item 4 mandates a manual reconcile, and **nothing verifies
that the reconcile happened**. `Surface (expected)` and `Notes` are genuinely NARRATIVE and would stay
hand-written.

## Why it matters

This is the **largest remaining hand-written surface carrying derivable values in the orchestrator
tree — strictly larger than the inbox count PLAN-203 fixed**. It has the identical drift path: a row
whose `Status` says `launched` while `status.json` says `shipped` is unfalsifiable at the reading site,
and the reader has no signal that the table is stale.

## Rule

Either render the four derivable columns into a generated block driven by `resume-summary`, or state
explicitly which of the two representations is authoritative. A manual-reconcile instruction with no
verification is not a guard.

Claim label: OBSERVED (first-party enumeration, D4 gate).

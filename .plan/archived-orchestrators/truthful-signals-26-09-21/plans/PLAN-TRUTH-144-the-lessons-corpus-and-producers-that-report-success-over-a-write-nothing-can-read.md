# PLAN-TRUTH-144: The lessons corpus, and producers that report success over a write nothing can read

## Objective

One target, one failure shape: a producer returns success for a write that no reader can subsequently
resolve. In the lessons store a lesson can be listed and then neither read nor retired; alongside it,
`manage-lessons add`, `record-step` and `record-metrics` each report a success whose record is unreadable or
indistinguishable from a placeholder. Merged because the remedy is one resolver seam and one honest-zero rule,
not four separate patches — and because D0 must decide whether that is true before any of them is written.

## Deliverables

8 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: find the PRODUCER, derive the affected store population, and settle whether the members share one remedy.** Re-ground every claim carried from PLAN-TRUTH-135 and PLAN-TRUTH-121 at HEAD. ⛔ Publish the swept population and its size; a remedy chosen before the population is derived is the archetype this epic exists to remove.
2. **D1 — Close the resolver gap at the SHARED seam, not at one verb.** Patching the verb that happened to be reported leaves every sibling verb broken. (PLAN-TRUTH-135 D1.)
3. **D2 — `not_found` must stop meaning two things.** Today it covers both *the lesson is absent* and *the lesson could not be resolved* — and a retry on the second DESTROYS the record. (PLAN-TRUTH-135 D2.)
4. **D3 — A retirement path for an already-stuck lesson, WITHOUT bypassing the tombstone.** The tombstone is what makes a retirement auditable; a recovery path that skips it trades one silent loss for another. (PLAN-TRUTH-135 D3.)
5. **D4 — `manage-lessons add` must not report success for an unreadable record.** (PLAN-TRUTH-121 D1.)
6. **D5 — `record-step`'s placeholder zeros become distinguishable from measured zeros.** The which-zero-is-this rule, applied to the step ledger. (PLAN-TRUTH-121 D2.)
7. **D6 — `record-metrics` emits typed facts.** (PLAN-TRUTH-121 D3.)
8. **D7 — Matched controls, one per member.** Each control pinned on the path that lies, with a matched control on the path that does not — a control that cannot fail proves nothing. (PLAN-TRUTH-135 D4 + PLAN-TRUTH-121 D4.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-135 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-135-a-lesson-can-be-listed-and-neither-read-nor-retired.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-121 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-121-producers-report-success-over-a-write-nothing-can-read.md` § `## Claim Labels` (verify-at-outline)

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/` — carried from PLAN-TRUTH-135
- `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` — carried from PLAN-TRUTH-135
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/lessons-handling.md` — carried from PLAN-TRUTH-135
- `test/plan-marshall/manage-lessons/` — carried from PLAN-TRUTH-135
- `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py` — carried from PLAN-TRUTH-135
- `marketplace/bundles/plan-marshall/skills/manage-lessons/**` — carried from PLAN-TRUTH-121
- `marketplace/bundles/plan-marshall/skills/manage-metrics/**` — carried from PLAN-TRUTH-121
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — carried from PLAN-TRUTH-121
- `test/plan-marshall/manage-lessons/**` — carried from PLAN-TRUTH-121
- `test/plan-marshall/manage-metrics/**` — carried from PLAN-TRUTH-121
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — carried from PLAN-TRUTH-121
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — carried from PLAN-TRUTH-121
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — carried from PLAN-TRUTH-121

## Dependencies and Sequencing

D0 gates everything, and its shared-remedy question decides whether D1–D3 and D4–D6 are one implementation
or two. Surface overlaps `manage-lessons` and `plan-orchestrator` with other merged plans in this epic; the
disjointness gate will sequence.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-135-a-lesson-can-be-listed-and-neither-read-nor-retired.md` (PLAN-TRUTH-135)
- `PLAN-TRUTH-121-producers-report-success-over-a-write-nothing-can-read.md` (PLAN-TRUTH-121)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-144-the-lessons-corpus-and-producers-that-report-success-over-a-write-nothing-can-read.md"
```

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.

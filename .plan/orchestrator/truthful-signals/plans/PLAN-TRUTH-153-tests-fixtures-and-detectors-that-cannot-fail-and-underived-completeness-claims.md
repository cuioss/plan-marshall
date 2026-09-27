# PLAN-TRUTH-153: Tests, fixtures and detectors that cannot fail, and underived completeness claims

## Objective

A check that cannot fail is worse than no check, because it publishes a clean verdict over a population it
never examined. Three families of them: tests and fixtures asserting properties nothing asserts, plugin-doctor
rules and detectors that are advertised but emit nothing and are read by nobody, and completeness claims that
are restated rather than derived — a count, a set, an *only*, a *nothing* asserted from memory instead of from
an independent enumeration. Merged because the remedy is one discipline — every set-guarding detector must be
population-derived, and must publish the population size — and one matched-control regime.

## Deliverables

11 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive all three populations before deleting or fixing anything.** The cannot-fail population (PLAN-TRUTH-116 D0), the plugin-doctor advertised-vs-emitting delta (PLAN-TRUTH-112 D0 — derive it BEFORE deleting anything), and the underived-completeness population (PLAN-TRUTH-117 D0). ⛔ Publish each population and its size.
2. **D1 — The merge-lock reentrancy test asserts a property nothing asserts.** (PLAN-TRUTH-116 D1.)
3. **D2 — `parse_stdin_task` silently truncates `verification.criteria` to one line.** (PLAN-TRUTH-116 D2.)
4. **D3 — `manage-tasks` has no post-creation write path for `verification`.** (PLAN-TRUTH-116 D3.)
5. **D4 — Delete the plugin-doctor rule ids with no emitter.** (PLAN-TRUTH-112 D1.)
6. **D5 — Delete the two detectors whose output nothing reads.** (PLAN-TRUTH-112 D2.)
7. **D6 — The third plugin-doctor member, per D0.** (PLAN-TRUTH-112 D3.)
8. **D7 — Correct the two false enforcement claims.** (PLAN-TRUTH-112 D4.)
9. **D8 — An outline-time content sweep for the prior enumeration string.** (PLAN-TRUTH-117 D1.)
10. **D9 — The vacuous-comparison topologies, which are NOT the same defect, and the hard-coded set-guarding literals.** ⛔ Every set-guarding detector must be population-derived; a check that can return 0 from an empty population MUST publish the population size. (PLAN-TRUTH-117 D2 + D3.)
11. **D10 — The two remaining completeness members, each with its own shape — plus the matched controls, which are the whole point.** (PLAN-TRUTH-117 D4 + PLAN-TRUTH-116 D4.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-116 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-116-a-test-or-fixture-that-cannot-fail.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-116 Claim Labels: 7 verdicts, 3 corroborated + 4 unverifiable.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-112 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-112-plugin-doctors-llm-phase-documents-rules-that-emit-nothing.md` § `## Claim Labels` (verify-at-outline)
  - verdict: contradicted | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: no | evidence: Pointer at PLAN-TRUTH-112 Claim Labels: 7 verdicts including one contradicted (index 3) - a premise the source records as refuted. Not yet re-scoped.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-117 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-117-restated-counts-and-underived-completeness-claims.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-117 Claim Labels: 6 verdicts, ALL SIX unverifiable - nothing about that source is settled either way.

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/**` — carried from PLAN-TRUTH-116
- `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — carried from PLAN-TRUTH-116
- `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — carried from PLAN-TRUTH-116
- `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_reentrant_acquire.py` — carried from PLAN-TRUTH-116
- `test/plan-marshall/manage-tasks/**` — carried from PLAN-TRUTH-116
- `test/conftest.py` — carried from PLAN-TRUTH-116
- `marketplace/bundles/plan-marshall/skills/manage-architecture/` — carried from PLAN-TRUTH-116
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/` — carried from PLAN-TRUTH-116
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/SKILL.md` — carried from PLAN-TRUTH-112
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-skills.md` — carried from PLAN-TRUTH-112
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md` — carried from PLAN-TRUTH-112
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/verification-guide.md` — carried from PLAN-TRUTH-112
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/safe-fixes-guide.md` — carried from PLAN-TRUTH-112
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_analysis.py` — carried from PLAN-TRUTH-112
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_shared.py` — carried from PLAN-TRUTH-112
- `test/plan-marshall/**` — carried from PLAN-TRUTH-112
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — carried from PLAN-TRUTH-117
- `test/_shared/_dispatch_roster.py` — carried from PLAN-TRUTH-117
- `marketplace/bundles/plan-marshall/skills/ref-documentation/**` — carried from PLAN-TRUTH-117
- `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md` — carried from PLAN-TRUTH-117
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — carried from PLAN-TRUTH-117
- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**` — added 2026-09-17,
  folded from `truth-166-architecture-refresh-migration-churn-010.md` (the documented-error-token candidate class)

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-116-a-test-or-fixture-that-cannot-fail.md` (PLAN-TRUTH-116)
- `PLAN-TRUTH-112-plugin-doctors-llm-phase-documents-rules-that-emit-nothing.md` (PLAN-TRUTH-112)
- `PLAN-TRUTH-117-restated-counts-and-underived-completeness-claims.md` (PLAN-TRUTH-117)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-153-tests-fixtures-and-detectors-that-cannot-fail-and-underived-completeness-claims.md"
```

## ⭐ FOLDED 2026-09-15 — TWO MORE CLAIM-OF-DERIVATION INSTANCES

Forwarded from `review-apparatus-041.md` § C-016 and § C-018. Expected Surface unchanged.

- **§ C-016** — a deliverable claimed its file list came from a content sweep; re-running the sweep
  refuted it. The claim-of-derivation archetype this deliverable's D0 already targets: a stated method
  nobody actually re-ran.
- **§ C-018** — a deliverable's own verification command could not collect the guards it claimed to
  exercise. Same shape: a completeness claim standing on a check that, when run, does not support it.

## ⭐ FOLDED 2026-09-17 — A DOCUMENTED ERROR TOKEN NO COMPONENT EMITS, AND THE DETECTOR CLASS THAT WOULD CATCH IT

Forwarded from `truth-166-architecture-refresh-migration-churn-010.md` (PR #1501; the instance was fixed
in-run as TASK-12 after CodeRabbit reported it, `80d835`). Expected Surface EXTENDED in the same act — see
the `ext-self-review-plan-marshall` entry added below.

`manage-architecture/standards/client-api.md` documented three error cases in one sentence. Two named the
wire value a caller matches on (`invalid_ref`, `snapshot_not_found`); the third named a **Python helper**
(`require_project_meta`) while the handler emits `error: data_not_found`. No caller branching on `error`
could ever match it — the documented contract was unimplementable as written, and nothing in the build gate
noticed, because the token is a real symbol, correctly spelled, in a file whose links and structure all
validate. ⭐ The document contained its own counter-example on the same line: the two sibling cases were
written from the consumer's vocabulary.

**What is owed here is the DETECTOR, not the instance.** This deliverable's subject is detectors that
cannot fail and completeness claims nobody derived; this adds a candidate class that is mechanical on both
sides — enumerate the `error:` values a component's handlers actually emit, enumerate the tokens its
standards document as error conditions, and report a documented token absent from the emitted set. ⚠ The
class is only worth adding with a **matched control**: a documented token that IS emitted must stay silent,
or the detector joins the population it was built to find.

## ⭐ ABSORBED 2026-09-18 (cleanup A5) — TWO SPECS MERGED IN, COMPONENT-FIRST

**D11 — from `PLAN-TRUTH-163`: the two deferred dispatch-workflow-pin test defects.** Re-read both
findings against `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` at HEAD
— they were deferred out of `plan-truth-157` as `taken_into_account` rather than fixed — and fix whichever
D0 confirms still needs it, with a matched control per fix. ⭐ Merged here because a deferred test defect
in a pin test IS this spec's subject: a test that cannot fail, in the file family D1–D3 already own.
`-163`'s own D0 collapses into this spec's D0.

**D12 — from `PLAN-TRUTH-155` D11: the `Bash` tool swallows non-zero exit codes, so every bare
`git diff --quiet` proof is vacuous.** Every such proof in the corpus asserts a property the runtime cannot
report. ⭐ Moved out of the documentation-surfaces spec because its subject is a **vacuous verification**,
not a stale document — `-155` sweeps prose, this spec sweeps checks that cannot fail, and this is the
second kind.

⚠ **Deliverable count re-derived, not summed: 11 + 2 = 13 headline items collapse to 12**, because `-163`'s
gate is absorbed by D0 rather than carried. That is exactly at the epic's operator-set ceiling of 12, so
⛔ **no further absorption into this spec** without a split.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.

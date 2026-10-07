# PLAN-TRUTH-148: The finalize step contract: declared surfaces, the dispatch seam, and a self-review that decides its own close

## Objective

The finalize step contract declares what each step reads and mutates, and several of those declarations are
wrong in a way no gate can see: fields that violate the mandatory-declaration rule, doc-echoes describing a
step that no longer exists, and a `mutates_source` claim that does not hold. Sitting inside the same contract,
the pre-submission self-review both authors the work and decides whether it is done — so its stop question is
answered by the party with an interest in the answer, and the property that distinguishes it is invisible in
the summary. Merged because both are the same contract surface and are verified by the same tests.

## Deliverables

11 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive the dispatch-site population and the declaration surfaces, and settle whether verifier independence is achievable here at all.** PLAN-TRUTH-108's D0 is a genuine fork with a cost: independence may not be reachable in this harness, and the answer decides D7 and D8 entirely. ⛔ Publish both populations and their sizes. (PLAN-TRUTH-097 D0 + PLAN-TRUTH-108 D0.)
2. **D1 — The declared surface is the read surface.** (PLAN-TRUTH-097 D1.)
3. **D2 — Retire the three fields that violate the mandatory-declaration rule.** (PLAN-TRUTH-097 D2.)
4. **D3 — Complete the `[DISPATCH]` seam rollout and retire the forbidden shape.** (PLAN-TRUTH-097 D3.)
5. **D4 — The two finalize doc-echoes describe a step that no longer exists.** (PLAN-TRUTH-097 D4.)
6. **D5 — A degraded module-tests run gets a DEGRADED display detail.** A degraded run reported as a clean one is this epic's whole theme. (PLAN-TRUTH-097 D5.)
7. **D6 — `push.md` stops naming `lessons-capture` as `mutates_source: true`.** (PLAN-TRUTH-097 D6.)
8. **D7 — Verifier independence, per D0.** (PLAN-TRUTH-108 D1.)
9. **D8 — The stop question is asked of the verifier, not evaluated by the author.** (PLAN-TRUTH-108 D2.)
10. **D9 — LOCAL GATE: open the two measurement gates, and the concept summary characterises the step in ONE clause.** (PLAN-TRUTH-097 D7 + PLAN-TRUTH-108 D3.)
11. **D10 — retire `_foreign_paths_by_deliverable`, a test-only shim.** Carried in from epic
    `review-apparatus` (inbox `review-apparatus-037.md`), routed here at its sender's own request
    because it is `phase-6-finalize` code cleanup and fails the PR/review test. After PR #1473
    (`38af136ed`) the function in
    `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py` is a pure
    delegation — `return _partition_foreign_paths(deliverables).by_deliverable` — with **zero
    production callers**, since `check()` calls `_partition_foreign_paths` directly for both tuple
    fields. Delete it and repoint the test call sites at `_partition_foreign_paths(...).by_deliverable`.
    ⛔ **Re-derive the call-site count before acting** — the sending plan reported 5 in
    `test_foreign_pr_gate.py` plus 1 in
    `test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py`, first-party to its
    own run but NOT re-derived in this checkout, and #1473's own tests moved that file.
    ⭐ **The transferable half generalises past this wrapper:** the residue was created by the PROOF,
    not by carelessness — `test_survey_scope_declaration.py` was declared read-only and had to pass
    UNCHANGED as the refactor's behaviour-preservation criterion, so deleting what those tests call
    would have falsified the very criterion the refactor rested on. **A refactor whose proof is "these
    tests pass unchanged" cannot also delete what those tests call.** That is predictable, and worth
    stating in the finalize contract rather than re-discovering each time.

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-097 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-097-dispatch-contract-and-measurement-residue.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-108 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-108-the-self-review-decides-its-own-close-and-its-distinguishing-property-is-invisible.md` § `## Claim Labels` (verify-at-outline)

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_gate_coverage.py` — carried from PLAN-TRUTH-097
- `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` — carried from PLAN-TRUTH-097
- `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_finalize_steps.py` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_lanes.py` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md` — carried from PLAN-TRUTH-097
- `test/plan-marshall/phase-6-finalize/test_verdict_currency.py` — carried from PLAN-TRUTH-097
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — carried from PLAN-TRUTH-108
- `doc/concepts/automatic-reviews.adoc` — carried from PLAN-TRUTH-108
- `test/plan-marshall/phase-6-finalize/` — carried from PLAN-TRUTH-108
- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**` — carried from PLAN-TRUTH-108

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-097-dispatch-contract-and-measurement-residue.md` (PLAN-TRUTH-097)
- `PLAN-TRUTH-108-the-self-review-decides-its-own-close-and-its-distinguishing-property-is-invisible.md` (PLAN-TRUTH-108)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-148-the-finalize-step-contract-declared-surfaces-the-dispatch-seam-and-a-self-review-that-decides-its-own-close.md"
```

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.

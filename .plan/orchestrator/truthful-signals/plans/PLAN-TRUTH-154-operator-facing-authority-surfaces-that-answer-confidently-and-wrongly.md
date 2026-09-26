# PLAN-TRUTH-154: Operator-facing authority surfaces that answer confidently and wrongly

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

## Objective

Three surfaces the operator reads as authoritative, each answering confidently and wrongly. An invocation
rejection suggests a notation it has not validated, so the remediation is itself unverified; the commit
trailer's authority is open in three carriers and checked in none, so a fleet-wide rename invalidates every
consumer with no propagation mechanism; and the plugin re-pin is excluded from the automated sync by a
principle we already violate by hand, roughly daily, leaving an operator-only repair script as the real
mechanism. Merged because all three are operator-facing authority claims, and the remedy in each case is to
make the machine assert what the prose currently only states.

## Deliverables

10 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive the rejection and carrier populations, and re-decide the `-059` § Scope exclusion in writing.** The invocation-rejection population (PLAN-TRUTH-129 D0), the trailer-carrier population (PLAN-TRUTH-140 D0), and PLAN-TRUTH-115 D0's re-decision of the `-059` § Scope exclusion — recorded either way, because an unrecorded re-decision is how the exclusion survived the first time. ⛔ Publish each population and its size.
2. **D1 — The unknown-notation diagnostic must not suggest a notation it has not validated.** (PLAN-TRUTH-129 D1.)
3. **D2 — Make the position-aware remediation note uniform across the `--plan-id` family.** (PLAN-TRUTH-129 D2.)
4. **D3 — Correct `branch-cleanup.md` § Predicate 2's scalar carve-out.** (PLAN-TRUTH-129 D3.)
5. **D4 — Close the trailer override set at the agent-facing carrier.** (PLAN-TRUTH-140 D1.)
6. **D5 — Say it at the operator-facing carrier too.** (PLAN-TRUTH-140 D2.)
7. **D6 — Extend the source vocabulary rather than inventing one.** (PLAN-TRUTH-140 D3.)
8. **D7 — Fold the re-pin into the sync step, at the same trigger as the executor regeneration.** The pin is LEFT BEHIND by every sync, not drifting — which is why the trigger must be the same one. (PLAN-TRUTH-115 D1.)
9. **D8 — Retire `.plan/temp/repair-plugin-pin.py` as the operator path, or state why it survives — and give `restart-check`'s signal vocabulary an honest not-applicable.** Starting with `registry_parity`, which is excluded from the readiness floor and therefore blind to exactly the gap this plan closes. (PLAN-TRUTH-115 D2 + D3.)
10. **D9 — Assert at the machine and report at the steward — plus matched controls, one per member.** (PLAN-TRUTH-140 D4 + PLAN-TRUTH-129 D4.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-129 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-129-an-invocation-rejection-answers-confidently-and-wrongly.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-129 Claim Labels: 8 verdicts, 6 corroborated + 2 unverifiable.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-140 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-140-the-trailer-authority-is-open-in-three-carriers-and-checked-in-none.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-140 Claim Labels: 9 top-level bullets, ZERO persisted verdicts - never re-grounded.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-115 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-115-the-repin-is-excluded-by-a-principle-we-already-violate-by-hand.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-115 Claim Labels: 16 verdicts, 6 corroborated + 9 unverifiable + 1 non-standard token (ready).

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/tools-script-executor/**` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — carried from PLAN-TRUTH-129
- `test/plan-marshall/tools-script-executor/**` — carried from PLAN-TRUTH-129
- `test/plan-marshall/automatic-review/**` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/manage-build-server/**` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/build-server-client/**` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/` — carried from PLAN-TRUTH-129
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/` — carried from PLAN-TRUTH-129
- `CLAUDE.md` — carried from PLAN-TRUTH-140
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-commit-trailer.md` — carried from PLAN-TRUTH-140
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-healthcheck.md` — carried from PLAN-TRUTH-140
- `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py` — carried from PLAN-TRUTH-140
- `marketplace/bundles/plan-marshall/skills/manage-run-config/SKILL.md` — carried from PLAN-TRUTH-140
- `marketplace/bundles/plan-marshall/skills/manage-run-config/standards/run-config-standard.md` — carried from PLAN-TRUTH-140
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — carried from PLAN-TRUTH-140
- `AGENTS.md` — carried from PLAN-TRUTH-140
- `test/plan-marshall/manage-run-config/**` — carried from PLAN-TRUTH-140
- `test/plan-marshall/workflow-integration-git/**` — carried from PLAN-TRUTH-140
- `.claude/skills/sync-plugin-cache/scripts/sync.py` — carried from PLAN-TRUTH-115
- `.claude/skills/sync-plugin-cache/SKILL.md` — carried from PLAN-TRUTH-115
- `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md` — carried from PLAN-TRUTH-115
- `.plan/temp/repair-plugin-pin.py` — carried from PLAN-TRUTH-115
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — carried from PLAN-TRUTH-115
- `marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/**` — carried from PLAN-TRUTH-115
- `doc/developer/marketplace-build.adoc` — carried from PLAN-TRUTH-115
- `doc/developer/manual-sync-recovery.adoc` — carried from PLAN-TRUTH-115
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/**` — added 2026-09-14, folded from `truthful-signals-010.md` finding 2 (the un-enumerated advance-vs-absence-of-objection population)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/**` — added 2026-09-14, same fold

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-129-an-invocation-rejection-answers-confidently-and-wrongly.md` (PLAN-TRUTH-129)
- `PLAN-TRUTH-140-the-trailer-authority-is-open-in-three-carriers-and-checked-in-none.md` (PLAN-TRUTH-140)
- `PLAN-TRUTH-115-the-repin-is-excluded-by-a-principle-we-already-violate-by-hand.md` (PLAN-TRUTH-115)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-154-operator-facing-authority-surfaces-that-answer-confidently-and-wrongly.md"
```

## ⭐ FOLDED 2026-09-14 — APPROVAL INFERRED FROM ABSENCE OF OBJECTION, POPULATION UN-ENUMERATED

Forwarded via `truthful-signals-010.md` finding 2 (revision 3). Expected Surface EXTENDED in the same act
(see above) — this is a population-derivation deliverable across `phase-6-finalize/standards/**` (23
files) and `workflow/**` (5 files), not yet declared before this fold.

PLAN-PR-046 (#1477, `77cb2e251`) fixed ONE instance of this shape: it gated CodeRabbit clean-review credit
behind a marker, closing the case where `count_stored: 0` was read as "reviewed and clean" (the defect
PLAN-PR-025B shipped and was caught only post-merge). The general shape, independently corroborated by an
external source: an **advance** token is a separate artifact from a **review** token, produced by a
different actor, and a workflow must proceed only on the token's PRESENCE — never on the absence of an
objection. Whether any OTHER gate in the finalize chain still infers advance from absence-of-objection has
**not been enumerated** — that enumeration, over all 23 standards and 5 workflow docs, is the actual
deliverable, per this epic's own derive-completeness rule. No causal or population claim beyond the one
confirmed instance is established by the source finding.

## ⭐ FOLDED 2026-09-15 — A GENERATED EXECUTOR REJECTING A SCRIPT'S OWN DECLARED FLAG, AND ALL-FALSE LINT FINDINGS

Forwarded from `review-apparatus-041.md` § A-014 and § C-015. Expected Surface presumed unchanged
(`plan-orchestrator/scripts/orchestrator.py`'s neighbouring executor-generation machinery and
`manage-tasks/scripts/` already broadly covered); not independently re-verified in this checkout.

**§ A-014 — a real tooling defect, not an agent-invocation mistake:** the generated executor rejected a
flag the dispatched script itself declares, and TWO full executor regenerations did not clear it. Named
apart from every other invocation-discipline item in the same transfer (folded elsewhere into
PLAN-TRUTH-162) because reading the registered set does not help when the executor's own registration is
wrong — the one case in that population where the calling-convention fix has nothing to catch.

**§ C-015 — ten lint findings against five files in four bundles, ALL FALSE.** The rule read an
unconfident parser surface as a confident one — a detector treating an uncertain reading as settled,
squarely this deliverable's own theme (a machine asserting what the prose only states).

## ⭐ FOLDED 2026-09-17 — AN ESCALATION BUILT ON A RECALLED DEFAULT, WHERE THE RESOLVED VALUE WAS ONE CALL AWAY

Forwarded from `truth-166-architecture-refresh-migration-churn-008.md` (PR #1501, first-party). Expected
Surface unchanged — `phase-6-finalize/standards/**` and `phase-6-finalize/workflow/**` already cover the
escalation-authoring surface.

An operator escalation during finalize stated *"The loop-back limit of 3 is spent on the self-review
rounds, so the gate will refuse this one."* The resolved ceiling was **14** (`manage-config plan
phase-6-finalize get`), `.plan/marshal.json` was byte-identical between the plan's `4-plan` baseline and
HEAD, and the plan finished at `loop_back_iteration: 6` — well inside it. **`3` is the documented DEFAULT**,
which is where the figure came from; the operator's "raise the limit" answer changed no configuration,
because nothing needed raising. The run's own decision log carries the later correction (*"iteration 5 of
`max_iterations=14` per correction `4f3cdd`"*), so the value was available throughout.

This is this plan's theme aimed at the escalation itself rather than at a tool's output: a confident
premise sourced from documentation instead of from the resolver. **Remedy: require an escalation whose
premise is a configured limit to quote both the resolved value AND the call that produced it** (e.g.
"max_iterations=14 per `manage-config plan phase-6-finalize get`"). That makes a recalled default visible
inside the escalation text, so a premise with no source call is refusable on sight — by the author as much
as by the operator. ⛔ Note the second-order cost: the operator was asked to decide something that was not
true, so the decision record now contains an authorization that governs nothing.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.

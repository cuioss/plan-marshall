# PLAN-TRUTH-145: Declarations that cannot learn a path, and params that cannot go stale

## Objective

Three defects with one shape: a declaration is written once and then treated as authoritative forever, with
no path by which it can learn what actually happened and no detector for the moment it stops being true. The
declared footprint cannot learn a path the outline did not predict; the scope-creep guard declares a field
that has no producer and has therefore never measured anything; and a frozen manifest param has no staleness
detector at all. Merged because the remedy in every case is the same pair — a provenance field, and an
honest INDETERMINATE where a clean zero is currently published.

## Deliverables

9 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive all three populations before changing anything.** Enumerate every consumer that derives scope from `affected_files` and classify each by whether it cross-checks (PLAN-TRUTH-136 D0); re-ground the scope-creep writer question at HEAD (PLAN-TRUTH-138 D0); derive the exposed manifest param population (PLAN-TRUTH-132 D0). ⛔ Publish each population and its size.
2. **D1 — Close the learning gap at the loop-back refresh.** (PLAN-TRUTH-136 D1.)
3. **D2 — Publish a PROVENANCE field on the `affected_files` reader.** So a consumer can tell a predicted path from an observed one. (PLAN-TRUTH-136 D2.)
4. **D3 — A skip-clean exit over an unprovenanced declaration is INDETERMINATE, not clean.** ADR-019 applied at the footprint reader: an unevaluated population is never reported as a checked negative. (PLAN-TRUTH-136 D3.)
5. **D4 — Declare the scope-creep field in the schema.** (PLAN-TRUTH-138 D1.)
6. **D5 — Build the scope-creep PRODUCER.** The field has never had one, so every reading of it to date was of an unwritten value. (PLAN-TRUTH-138 D2.)
7. **D6 — Extend `reconcile`'s comparison domain to the checkable manifest params.** (PLAN-TRUTH-132 D1.)
8. **D7 — An unchecked param is DISCLOSED, never silently omitted.** The same which-zero-is-this rule, one tier down. (PLAN-TRUTH-132 D2.)
9. **D8 — Matched controls, including the one that has never been exercised.** (PLAN-TRUTH-136 D4 + PLAN-TRUTH-138 D3 + PLAN-TRUTH-132 D3.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-136 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-136-the-declared-footprint-cannot-learn-a-path-the-outline-did-not-predict.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-138 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-138-the-scope-creep-guard-has-no-producer-and-has-never-measured-anything.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-132 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-132-a-frozen-manifest-param-has-no-staleness-detector.md` § `## Claim Labels` (verify-at-outline)

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md` — carried from PLAN-TRUTH-136
- `marketplace/bundles/plan-marshall/skills/manage-references/scripts/` — carried from PLAN-TRUTH-136
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — carried from PLAN-TRUTH-136
- `test/plan-marshall/manage-references/` — carried from PLAN-TRUTH-136
- `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` — carried from PLAN-TRUTH-138
- `marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage_references.py` — carried from PLAN-TRUTH-138
- `marketplace/bundles/plan-marshall/skills/phase-1-init/**` — carried from PLAN-TRUTH-138
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — carried from PLAN-TRUTH-138
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — carried from PLAN-TRUTH-138
- `test/plan-marshall/manage-references/**` — carried from PLAN-TRUTH-138
- `test/plan-marshall/phase-5-execute/**` — carried from PLAN-TRUTH-138
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — carried from PLAN-TRUTH-132
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` — carried from PLAN-TRUTH-132
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py` — carried from PLAN-TRUTH-132
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` — carried from PLAN-TRUTH-132
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md` — carried from PLAN-TRUTH-132
- `test/plan-marshall/manage-execution-manifest/**` — carried from PLAN-TRUTH-132

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-136-the-declared-footprint-cannot-learn-a-path-the-outline-did-not-predict.md` (PLAN-TRUTH-136)
- `PLAN-TRUTH-138-the-scope-creep-guard-has-no-producer-and-has-never-measured-anything.md` (PLAN-TRUTH-138)
- `PLAN-TRUTH-132-a-frozen-manifest-param-has-no-staleness-detector.md` (PLAN-TRUTH-132)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-145-declarations-that-cannot-learn-and-cannot-go-stale.md"
```

## ⭐ FOLDED 2026-09-13 — FINALIZE NEVER CALLS THE SCOPE-DRIFT DETECTOR IT ALREADY HAS

Forwarded via `review-apparatus` (`inbox/review-apparatus-038.md`), from `plan-pr-046`'s own finalize (PR
#1477). Expected Surface presumed unchanged — the `phase-6-finalize/` directory entry above should already
cover the missing call site; NOT independently re-derived in this checkout (leads, not instructions).

10 undeclared files were modified on PR #1477 (threshold 5), all during finalize as self-review rounds
reached contract docs and build files. `reconcile-scope` already detects this drift, but nothing in
finalize calls it — every `affected_files`-derived finalize step under-scopes whenever scope moves during
execute. Per the forwarding message this is the THIRD consecutive `review-apparatus` landing whose
realized footprint exceeded its declaration, and on PR #1473 the undeclared half silently discharged
another plan's staged deliverable — recurrence evidence, not a one-off.

## ⭐ FOLDED 2026-09-15 — NO FOOTPRINT MECHANISM FOR A TWO-REPOSITORY PLAN'S FOREIGN HALF, PLUS A 4TH CONSECUTIVE DRIFT SIGHTING

Forwarded from `review-apparatus-041.md` § B-001 and § B-004. Expected Surface unchanged —
`manage-references/**` and `phase-6-finalize/` already cover both.

**Genuinely open, and a gap rather than a drift** (§ B-001): a plan whose work lands in ANOTHER repository
has no footprint mechanism for that half at all — not a staleness case (the existing D0-D2 shape), but an
absence of the mechanism entirely for the foreign-checkout side of a two-repository plan.

**§ B-004 — a fourth consecutive `review-apparatus` landing shows the same `affected_files`
under/over-declaration drift already folded here**, now with exact figures: 19 declared vs. 13 realized,
not nested — 5 realized-but-never-declared (including two files that were the targets of fix tasks
appended mid-execute) and 4 declared-but-never-realized (an entire GitLab-contract half the plan declared
and never touched). The divergence runs in BOTH directions on this instance; `reconcile-scope` already
detects it and nothing in finalize calls it — the same remedy already carried here stands, now with a
fourth independent measurement behind it.

## ⭐ FOLDED 2026-09-15 (c) — THE SCOPE-CREEP FENCE WITNESSED UNMEASURED IN A CONSUMER, AND A COMPOSE DECISION BLIND TO WHAT CHANGED

Forwarded from `api-sheriff-deployment-configurability-012.md` and `lessons-handling-26-09-04-01-062.md`.
Expected Surface unchanged — `phase-5-execute/scripts/scope_creep_check.py`,
`manage-execution-manifest/scripts/manage-execution-manifest.py` and
`manage-execution-manifest/standards/decision-rules.md` are already declared above.

**§ -012 — D4/D5 recurrence, no new work.** Two API-Sheriff plans (PLAN-07, PLAN-10) shipped with
`references.json` carrying no `plan_creation_sha`, so `scope_creep_check` returned `could_not_look` /
`no_baseline_sha` on both. Re-grounded at `7a028157e`: `plan_creation_sha` still appears only in
`scope_creep_check.py` among marketplace Python — there is still no writer. Independent confirmation from
outside the meta-project that the fence has never measured anything; it raises this spec's priority and
changes none of D4/D5.

**§ -062 — `verify:coverage` composed for a change that cannot move coverage.** Token-Sheriff PR #744: the
manifest composed `verify:coverage` per task for a plan whose only change in `benchmarking-common` was
deleting an unreferenced `.log` test resource. The inherited JaCoCo gate failed on standing debt (0.70
instructions / 0.57 branches vs 0.80), triggering a triage round-trip that ended "accepted, no fix task" —
the same debt accepted on an earlier plan, so every plan that composes the step pays it again. Lead for the
composer: a compose decision for a coverage verification should consider whether the plan changed MAIN
code in the modules the gate would fail on, or recognize a recorded accepted baseline and report
"unchanged from accepted baseline". ⚠ HYPOTHESIS: the composer has no main-vs-test-resource discriminator
for `verify:coverage` — confirm/refute at `manage-execution-manifest/scripts/_manifest_core.py` § the
`coverage` build-class mapping (line 435 at `7a028157e`) and its caller (verify-at-outline). The same
message's fan-out half (one failed `jacoco:check` → 2 Q-Gate + 3 build-error findings) is a findings-ledger
dedup question; it rides here as a lead for `PLAN-TRUTH-146` rather than as a second record there.

## ⭐ FOLDED 2026-09-17 — D4/D5 MEASURED FIRST-PARTY: THE GUARD RETURNED `could_not_look` ON ALL 16 TASKS OF A LANDED PLAN

Forwarded from `truth-166-architecture-refresh-migration-churn-001.md` (PR #1501, first-party, ranked #1 by
its own retrospective). Expected Surface unchanged — `phase-5-execute/scripts/scope_creep_check.py` is
already declared. Third independent sighting after `-012` (two API-Sheriff plans) and the original.

A content sweep over **2,911 inventoried files with clean coverage** (no unreadable files, no truncation,
no elided buckets) found `plan_creation_sha` in exactly five files: the consumer script (4 matches), its
own `phase-5-execute/SKILL.md` (2), and three test files. **No writer.** The landed plan's
`references.json` carries nine keys and not that one, so the guard returned `could_not_look` /
`no_baseline_sha` on **all 16 of its tasks**, on a plan whose realized footprint grew to 26 paths against
22 declared — precisely the run where a scope-creep signal would have been worth having.

⭐ **The generalization, which is the reusable half:** a `could_not_look` state that fires on EVERY
invocation is an INERT guard, not an honest one — and the honesty machinery around it reads as diligence
while buying zero coverage. `_emit_could_not_look`'s docstring is meticulous about omitting
`residual_count` so an unmeasured run cannot render as a measured clean one; that care is wasted while the
branch reaching it is unconditional. D5 (build the producer) is the fix; D4 declares the field. The
sender's preferred producer is `manage-references` at init, stamping the main SHA the plan was created
against.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.

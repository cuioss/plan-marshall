# PLAN-LB-01: The push freshness gate accepts the pre-push gate's own green builds

epic: live-blockers
workstream: WS-01

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-23 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-01-push-freshness-gate.md` and is queued as one row file, `queue/PLAN-LB-01.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The `pre-push-quality-gate` finalize step runs `quality-gate`, `test-compile` and `module-tests` green on the
settled tree, and its own document says those builds are what satisfy the freshness precondition of the
`default:push` step that follows. They cannot: `pre-commit-verify-freshness` credits only a single ledger row
whose canonical performs every required analysis, so each of the gate's rows is refused as
`canonical_performs_too_few_analyses` and the verdict is `stale: build_scope_narrow`. Every finalize of a
Python-touching plan therefore either pays a second full `verify` (about 40 minutes) or halts at push and asks
for an override that the operator has been told never to give. Make the freshness check credit the union of
green build rows at the current worktree SHA when together they cover every required analysis at an adequate
scope, so the gate's own runs are sufficient. Carries forward truthful-signals PLAN-TRUTH-186 (all
deliverables) and process-compliance PLAN-23 deliverable D3.

## Deliverables

1. **Union coverage at one SHA.** When no single candidate row covers the change, the coverage dimension
   combines the candidate rows (already restricted to `kind=build`, `status == success`, current
   `worktree_sha`) and reports `covered` when, for EVERY required analysis, at least one row performs that
   analysis at a scope adequate for the change: whole-tree when `RequiredCoverage.whole_tree` is true,
   otherwise a scope containing `RequiredCoverage.modules`. Scope is judged per analysis, never pooled — a
   module-scoped `quality-gate` row does not lend its scope to a whole-tree `module-tests` row or the reverse.
   A row that measured zero tests contributes no `test` coverage; a row whose `args` are unreadable or whose
   canonical is outside the vocabulary contributes nothing. The joint verdict with the attribution dimension
   holds per contributing row: a row the architecture cannot attribute does not contribute. The `fresh`
   record names every contributing row (ledger index, canonical, scope), not one "chosen" row.
   Done when: a test builds a ledger holding green whole-tree `quality-gate`, `test-compile` and
   `module-tests` rows at SHA X with the worktree at X and a `.py` footprint, and
   `pre-commit-verify-freshness` returns `status: fresh` with `scope_cross_check: covered` and all
   contributing rows listed. The same test fails today with `stale` / `build_scope_narrow`.
2. **A refusal names what is missing.** When the union still falls short, the `stale` record carries the
   uncovered analyses as a field (for example `missing_analyses: [test]`) beside the existing per-row
   `row_scopes`, and the message says which analysis no row covered at an adequate scope. The `reason` token
   stays `build_scope_narrow` unless the outline finds no consumer branching on it; `push.md` and
   `manage-tasks/SKILL.md` both key on it today.
   Done when: a ledger with only green `quality-gate` and `test-compile` rows at the current SHA returns
   `stale` naming `test` as missing; a ledger whose only `quality-gate` rows are module-scoped while the
   change requires whole-tree returns `stale` naming `lint`.
3. **Documents match the behaviour.** `pre-push-quality-gate.md` § "Settle-band position" (the sentence that
   says only this gate's just-completed builds can have written the admitting row) becomes true as written;
   `push.md` § "Freshness precondition" stops describing freshness as "the most recent `verify` run" and
   describes the union basis, including how the step's `--display-detail` renders a multi-row basis;
   `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness" documents the union rule in its coverage table
   and its `build_scope_narrow` remedy row (the remedy is "run the missing analysis", not "re-run verify").
   Done when: the three documents state the union rule once (`manage-tasks/SKILL.md` owns it, the other two
   point at it) and the existing document-contract tests for these files pass.
4. **Controls that keep the gate closed where it must be.** Pinned as tests beside the existing
   `test_pre_commit_verify_freshness*.py` modules: (a) the Deliverable 1 row set at SHA X with the worktree
   at Y returns `stale`; (b) a covering set in which the only `module-tests` row has `status: killed` or
   `timeout` returns `stale` (that row is never a candidate); (c) a covering set whose `module-tests` row
   measured zero tests returns `stale`; (d) a single green whole-tree `verify` row still returns `fresh`
   with the same record shape as before, plus the new contributing-rows field holding that one row; (e) a
   covering set in which one needed row carries a notation the architecture does not resolve returns
   `stale`.

## Claim Labels

- OBSERVED: each candidate row is judged alone and must perform every required analysis — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` § `_row_refusal` (:504-539, the test is `if not required.analyses <= performed: return ROW_CANONICAL_TOO_WEAK` at :530-531).
- OBSERVED: no cross-row aggregation exists — `_freshness_crosscheck.py` § `scope_check_candidates` (:548-629) loops `_row_refusal` per row (:595-603), returns `COVERED` only when some single row passed (:605), and otherwise returns `NARROW` / `REASON_SCOPE_NARROW` (:624-628).
- OBSERVED: the refusal tokens are `REASON_SCOPE_NARROW = 'build_scope_narrow'` (:257) and `ROW_CANONICAL_TOO_WEAK = 'canonical_performs_too_few_analyses'` (:272) in the same file.
- OBSERVED: a `.py` footprint requires compile, lint and test; any non-empty footprint requires test — `_freshness_crosscheck.py` § `required_coverage` (:375-427).
- OBSERVED: no gate arm's canonical performs all three analyses — `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_examined.py` § `CANONICAL_ANALYSES` (:97-106) maps `quality-gate` to compile+lint, `test-compile` to compile, `module-tests` to test, and only `verify` to all three.
- OBSERVED: the gate runs those three canonicals and never `verify` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` §§ "Run quality-gate per bundle", "Whole-tree quality-gate arm", "Whole-tree test-compile gate", "Whole-tree module-tests divergence gate".
- OBSERVED: the gate document claims its own rows admit the push — `pre-push-quality-gate.md:54` ("it permits on a `kind=build` ledger entry carrying the current worktree SHA, which only this gate's just-completed builds can have written for the settled tree").
- OBSERVED: `push.md:62` describes freshness as verifying "that the most recent `verify` run actually observed this version of the code" — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md`.
- OBSERVED: candidates are pre-filtered to `kind == build`, `status == 'success'` and the current `worktree_sha` before the cross-check runs, so red, killed and timed-out rows are never candidates — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` § `cmd_pre_commit_verify_freshness` (the `candidates = [...]` comprehension).
- OBSERVED: the `fresh` record cites exactly one row through `_evidence_fields(ledger_indices[chosen], ...)` — `_cmd_pre_commit_verify_freshness.py` § `_verdict_for_candidates` (:458-469); the joint selection is `chosen = admissible[0]` at `_freshness_crosscheck.py` § `cross_check_candidates` (:812-815).
- OBSERVED: the documented coverage contract states the single-row rule — `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md:327-328` (`covered`: "At least one row's canonical performs every required analysis") and `:433` (`build_scope_narrow` remedy).
- HYPOTHESIS: in real finalize runs all four gate arms were green on the exact tree (28,128 and 28,166 tests) and push still refused `build_scope_narrow` with every row `canonical_performs_too_few_analyses` — reported by two plan runs, not reproduced here; confirm by building that row set against `_freshness_crosscheck.py` § `scope_check_candidates` (verify-at-outline).
- HYPOTHESIS: every green arm of one gate pass stamps the same `worktree_sha` as the settled tree — `quality-gate` rewrites tracked files in place (`ruff check --fix`, `ruff format`), so a row stamped before an auto-fix would carry a different SHA than the rows after it and could not join the union; confirm/refute at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/worktree_sha.py` § `compute_worktree_sha` and the build wrapper's ledger-stamping site (when the SHA is computed relative to the build) (verify-at-outline).
- HYPOTHESIS: the per-bundle `quality-gate` rows and the module-scoped `module-tests` row carry their scope as bare tokens after the canonical in `--command-args`, which is what `parse_row_scope` reads — confirm at `_freshness_crosscheck.py` § `parse_row_scope` against a real ledger row written by a module-scoped run (verify-at-outline).
- Verify-first clause: reproduce the refusal from the Deliverable 1 fixture against HEAD before changing anything; if HEAD already admits a union, shrink the plan to Deliverables 2 and 3.
- Verify-first clause: if the `worktree_sha` hypothesis is refuted (an auto-fixing `quality-gate` leaves earlier rows at another SHA), settle at outline whether the gate re-runs the affected arm or the plan stops at "union only when all rows share the SHA" and reports the remaining case; do not widen the union across SHAs.
- Verify-first clause: decide the shape of the multi-row evidence fields once and check every reader of the `fresh` record (`push.md` display-detail basis, phase-5 Step 12a, tests) before changing `_evidence_fields`.

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — union rule in `scope_check_candidates` / `cross_check_candidates`, missing-analysis reporting
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — `fresh` / `stale` record rendering for a multi-row basis
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — § "Pre-Commit Verify Freshness" coverage table and remedy rows
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — § "Settle-band position" claim
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` — § "Freshness precondition" wording and display-detail basis
- OBSERVED: `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py` — existing single-row cases that must keep passing
- OBSERVED: `test/plan-marshall/manage-tasks/_pre_commit_verify_freshness_fixtures.py` — ledger-row fixtures the new cases extend
- HYPOTHESIS: `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness_union_coverage.py` — new module for Deliverables 1, 2 and 4 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none. No other `live-blockers` plan edits these files. PLAN-LB-06 (`PLAN-LB-06-triage-fix-task-loop.md`) edits other scripts in the same `manage-tasks/scripts/` directory (`_tasks_core.py`, `_tasks_crud.py`, `_cmd_step.py`) and adds tests under `test/plan-marshall/manage-tasks/`; the files are disjoint, so the two may run together.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_examined.py` — the union reads `CANONICAL_ANALYSES` and does not change it; PLAN-LB-12 edits neighbouring files in that directory.
- Adjacent to: the gate's own arm selection in `pre-push-quality-gate.md` — untouched; the fix is on the crediting side. Making the gate run `verify` instead was the alternative and is rejected because it would discard the gate's per-arm scoping.
- Left out on purpose: the phase-5 pair from process-compliance PLAN-23 D3 (Step 11c runs one `verify` per affected bundle and Step 12a refuses those rows as `scope_narrower_than_change`). That refusal is on the scope side — per-bundle rows against a change that requires whole-tree — and pooling module scopes would contradict the divergence authority (`resolve_test_scope`). It needs its own decision on what Step 11c should run. The analysis union shipped here applies at Step 12a as well, because both call the same check.
- Left out on purpose: process-compliance PLAN-23 D3 asked that the union be taken only once green evidence is guaranteed to describe a clean checkout (its D1, generated `target/` state feeding tests). That guarantee is not part of this plan. The union does not widen the exposure: a single `verify` row is credited today on the same tree.
- Left out on purpose: a later non-success row at the same SHA for a canonical that also has a green row does not void the green row, today or after this plan. Same behaviour as the single-row rule; not changed here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-01-push-freshness-gate.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

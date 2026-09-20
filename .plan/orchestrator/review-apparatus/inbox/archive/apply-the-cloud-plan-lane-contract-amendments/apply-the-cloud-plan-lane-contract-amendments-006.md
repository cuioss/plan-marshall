envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:17:51Z

component=plan-marshall:phase-6-finalize
category=improvement
status=active

# The freshness gate refuses build_scope_narrow without naming the canonical that satisfies it

## Context

At the push step, the freshness gate returned `stale` with `reason=build_scope_narrow` (explicitly NOT `worktree_mutated`, so the finalize-internal reconciliation route did not apply). The cross-checks reported `notation_cross_check=corroborated`, `scope_cross_check=narrow`, and **all 26 matching ledger rows recorded `canonical_performs_too_few_analyses`**.

The separately-run `quality-gate`, `test-compile` and `module-tests` canonicals each cover too few analyses to be cited, so only a full `verify` — which chains compile, lint and test in one canonical — satisfies the gate. The caller had to reason that out in prose before spending roughly 25-30 minutes on the correct build.

## Root cause

The gate knows the analysis set each canonical covers — that is what `canonical_performs_too_few_analyses` is computed from — but it reports only the refusal, never the satisfying command. The caller is left to infer which canonical to run from a negative verdict, and the plausible cheap guess (`module-tests`, the thing the plan's own verification step ran) is exactly the one that cannot satisfy it.

## Proposed action

Have the gate emit the satisfying canonical alongside the refusal: `reason=build_scope_narrow, satisfied_by=verify`. It is a projection of data the gate already holds, it costs nothing, and it removes the one inference where a wrong guess costs another full build cycle.

## Evidence

- decision.log 2026-09-04T16:23:25Z — "Freshness gate returned stale reason=build_scope_narrow (NOT worktree_mutated ...). notation_cross_check=corroborated, scope_cross_check=narrow: all 26 matching rows recorded canonical_performs_too_few_analyses. The separately-run quality-gate / test-compile / module-tests canonicals each cover too few analyses to be cited. Running a full verify ... NOT using --force."
- decision.log 2026-09-04T18:13:00Z — "verify chains quality-gate to test-compile to module-tests, so it IS the three whole-tree arms in one canonical, and it is also the only canonical that satisfies the push freshness gate (build_scope_narrow otherwise)"
- Recurrence signal: a prior plan reached for `module-tests` as the remedy for this same refusal, which cannot satisfy it — so the missing hint has already cost a wrong guess once.
- aspect: llm_to_script_opportunities — candidate 3

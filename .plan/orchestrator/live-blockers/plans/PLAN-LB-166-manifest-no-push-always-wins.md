# PLAN-LB-166: A local-only run is never given push-only steps back — "no push" always wins in the execution manifest

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Plan E of the module regrouping of 2026-11-18: everything here lives in `manage-execution-manifest`, a module none of the other plans of the regrouping covers, so the plan runs in parallel with all of them.

## Objective

The execution manifest composes the finalize step list of a plan. When a plan's `commit_and_push` is false, `_apply_commit_push_disabled` drops `push`, `pre-push-quality-gate`, `functional-review` and `code-review`, "each gate goes because it is only meaningful when a downstream push exists". The ceremony selection that runs after it, `_apply_ceremony_finalize_selection`, takes only the step list and the gate map, has no `commit_and_push` parameter, and inserts the canonical step of any gate forced `always` whenever it is absent. A gate forced `always` can therefore put back a step the first function removed, so a local-only run is handed a push-only step it cannot run.

The operator decided on 2026-11-18: the ceremony selection never adds `push`, `pre-push-quality-gate`, `functional-review` or `code-review` to a plan whose `commit_and_push` is false ("no push always wins"), with a test.

## Deliverables

1. The ceremony selection honours `commit_and_push`. `_apply_ceremony_finalize_selection` in `_manifest_rules.py` receives the plan's `commit_and_push` setting (or the equivalent already available to its caller) and, when it is false, never inserts `push`, `pre-push-quality-gate`, `functional-review` or `code-review`, whatever a gate forced `always` says; every other step the selection adds today is added exactly as before, and a plan whose `commit_and_push` is true is unchanged. The outline reads the order of the two functions in the composition and the call site in `manage-execution-manifest.py`, and records which gate values a `minimal` lane yields and which of the four steps the ceremony map covers, so the guard covers exactly the steps the selection can add and no step is left uncovered or guarded needlessly.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-execution-manifest
   - Persona: implementer
2. A test pins it, written against the unfixed tree first: a plan with `commit_and_push` false and a gate forced `always` for each of the four steps (one case per step) composes a manifest without that step; the same gate on a plan with `commit_and_push` true still inserts it; the steps the first function already drops stay dropped; and a step outside the four that a forced gate adds is still added on a local-only plan. It extends `test_ceremony_finalize_selection.py` or `test_ceremony_finalize_selection_ceremony_finalize_never.py` in the existing fixture style, whichever already holds the forced-`always` cases (the outline names it).
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- "No push" wins over any gate value: no gate setting, forced or default, re-adds a push-only step to a local-only plan, and the existing drop in `_apply_commit_push_disabled` is not weakened.
- A plan that pushes is unchanged: the guard is keyed on `commit_and_push` being false and nothing else.
- Order inside the plan: deliverable 1, then deliverable 2 written against the unfixed tree.
- No file outside `manage-execution-manifest` and its tests is touched.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: two deliverables, well under the presumptive-split guard.

## Claim Labels

- OBSERVED (re-read at `main` on 2026-11-18): `_manifest_rules.py` lines 286-319 (`_apply_commit_push_disabled`) drop the four steps when `commit_and_push` is false, and lines 784-826 (`_apply_ceremony_finalize_selection`) take only the step list and the gate map and insert the canonical step of a gate forced `always` whenever it is absent (confidence 85 that the gap exists).
- HYPOTHESIS: the order in which the two functions run lets the second re-add what the first removed; confirm at the composition call site (verify-at-outline).
- HYPOTHESIS: a `minimal` lane can yield a gate forced `always` for one of the four steps; confirm which of them, if any, so the test cases are the reachable ones (verify-at-outline).
- Verify-first clause: the outline settles (a) the order of the two functions; (b) how `commit_and_push` reaches the second function without widening unrelated signatures; (c) which of the four steps the ceremony map covers; (d) which existing test file holds the forced-`always` cases.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_rules.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`
- OBSERVED: `test/plan-marshall/manage-execution-manifest/test_ceremony_finalize_selection.py`
- OBSERVED: `test/plan-marshall/manage-execution-manifest/test_ceremony_finalize_selection_ceremony_finalize_never.py`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none staged or running; PLAN-LB-162 edits the runbook lane and the review gate, and the other plans of the 2026-11-18 regrouping touch the functional review, the build server and the project-hygiene surfaces.
- Adjacent to: `test_manage_execution_manifest_compose_commit.py`, which already exercises `commit_and_push` composition and is read, not edited, unless the new test belongs there.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-166-manifest-no-push-always-wins.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

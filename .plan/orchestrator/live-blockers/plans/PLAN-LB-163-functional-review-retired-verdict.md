# PLAN-LB-163: A deliverable the operator retired with no successor closes through a `retired` functional-review verdict

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Plan B of the module regrouping of 2026-11-18: everything here lives in the functional-review gate (`phase-6-finalize`) and the criteria snapshot (`manage-solution-outline`), so the plan runs in parallel with plans in other modules.

## Objective

A deliverable of a frozen orchestrator spec can be retired by operator decision with no successor. Today no verdict closes it. The functional review offers `met`, `not_met` and `superseded`; the one route the review documents name for such a deliverable, `criteria-authorize`, closes the completion gate's criteria but leaves the deliverable's own blocking `deliverable_not_met` row, and a `superseded` row that names the deliverable itself is refused. The option the operator chose on 2026-11-12 (remove the deliverable from the outline) does not hold for an orchestrator spec, because a frozen spec clause has no drop route.

The operator decided on 2026-11-18: add a `retired` verdict, valid only when every criterion of the deliverable is authorized through `criteria-authorize`, that closes both the deliverable and its criteria, with the two review documents and the tests brought in line.

## Deliverables

1. The functional-review validator accepts a `retired` verdict. In `_review_support_validate.py` a deliverable row with verdict `retired` is accepted only when every criterion of that deliverable is already authorized through `criteria-authorize`; a `retired` row with one unauthorized criterion, or a deliverable with no criteria to authorize, is refused with a reason that names the unauthorized criteria, and a `retired` row files no blocking `deliverable_not_met` row. The refusals that exist today (a `superseded` row whose `superseded_by` cites the deliverable itself, a `not_met` row filing a blocking `deliverable_not_met`) are unchanged.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-solution-outline
   - Persona: implementer
2. The criteria side closes with the verdict. In `_criteria_snapshot.py` an authorized criterion is skipped by the completion gate today; the plan makes a deliverable closed by `retired` count as closed in the same gate, so the plan neither blocks on the deliverable row nor re-opens its criteria, and a criterion authorized after the verdict was filed is read the same way as one authorized before it. Where the verdict is persisted and how the gate reads it, the outline chooses and records, naming the order of the two writes.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-solution-outline
   - Persona: implementer
3. The two review documents state the verdict. `review-rubric.md` (the line that says a deliverable closed by operator decision goes "through `criteria-authorize`", and the line that says a frozen spec clause has no drop route) and `functional-review.md` (the line that routes such a deliverable through `criteria-authorize`) describe `retired` as the route for a deliverable retired by operator decision with no successor, state its precondition (every criterion authorized), and no longer imply that authorization alone closes the deliverable.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: documenter
4. Tests pin deliverables 1 to 3, each written against the unfixed tree first: a `retired` row with every criterion authorized is accepted and closes the deliverable and its criteria; a `retired` row with one unauthorized criterion is refused naming it; a `retired` row on a deliverable with no criteria is refused; a `not_met` row still files its blocking row and a `superseded` row naming the deliverable itself is still refused; the completion gate reads a retired deliverable as closed. They extend `test_superseded_by_names_deliverable_d3.py` and `test_criteria_gate_completion_d1.py` in their existing fixture style.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- The gate stays fail-closed: `retired` is accepted only on the precondition of deliverable 1, and no path makes an unauthorized deliverable close.
- The verdict is an operator route, not a model shortcut: the authorization step (`criteria-authorize`) stays the operator's act and is not widened.
- Order inside the plan: deliverable 1 and 2 first (the verdict and the gate), then 3, then 4 written against the unfixed tree.
- No file outside `phase-6-finalize` (functional review) and `manage-solution-outline` (criteria snapshot) and their tests is touched. The runbook lane and its review-gate parser belong to another plan.
- Recorded and not changed by this plan: whether an operator close of a `deliverable_not_met` row exists as a separate route (the documentation-only alternative would have needed it; this plan takes the verdict route instead).
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: four deliverables, under the presumptive-split guard.

## Claim Labels

- OBSERVED (re-read at `main` on 2026-11-18): `_review_support_validate.py` lines 474-482 refuse a `superseded` row whose `superseded_by` cites the deliverable itself, whatever has been authorized, and lines 484-486 file a blocking `deliverable_not_met` row for a `not_met` one.
- OBSERVED (re-read at `main` on 2026-11-18): `_criteria_snapshot.py` line 2077 skips an authorized criterion, which closes the completion gate's criteria but leaves the `deliverable_not_met` row.
- OBSERVED (re-read at `main` on 2026-11-18): `review-rubric.md` line 32 and `functional-review.md` line 279 say to close such a deliverable "through `criteria-authorize`", and `review-rubric.md` line 43 says a frozen spec clause has no drop route.
- HYPOTHESIS: the line numbers above are still current at the commit the run starts from (the file may have moved); the outline re-reads them (verify-at-outline).
- HYPOTHESIS: a deliverable with no criteria cannot be retired through this route because there is nothing to authorize; confirm that a retired orchestrator deliverable always carries at least one criterion, and if it can carry none, state how it closes (verify-at-outline).
- Verify-first clause: the outline settles (a) where the `retired` verdict is persisted and how the completion gate reads it; (b) the exact refusal text and reason code for an unauthorized criterion; (c) whether other readers of the verdict vocabulary (a retrospective, a landing analysis, the verdict enumerations in documents) must learn the new value, and records any it finds as in-scope or as a follow-up.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_superseded_by_names_deliverable_d3.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_criteria_gate_completion_d1.py`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none staged or running; PLAN-LB-162 edits the runbook lane and the review gate only, and the other plans of the 2026-11-18 regrouping (build-server logs, project hygiene, execution manifest) touch other modules.
- Adjacent to: `plan-marshall:phase-6-finalize` standards other than the two named, which this plan does not edit.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-163-functional-review-retired-verdict.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

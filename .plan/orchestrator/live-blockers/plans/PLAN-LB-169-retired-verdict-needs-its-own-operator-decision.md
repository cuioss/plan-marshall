# PLAN-LB-169: A `retired` functional-review verdict closes a deliverable only on the operator's own decision to retire it, not on a rewrite approval

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Staged on the operator's word. Source: `landings/PLAN-LB-163.md`, layer-3 finding L3-1 and layer-1 finding L1-1 (one major, re-read by the orchestrator at the merge commit `46d3308ea`), and the Open Defect "A `retired` functional-review verdict is accepted on any `criteria-authorize` entry (PLAN-LB-163)" in `epic.md`.
> Disjoint from every other staged or running plan: it lives in `manage-solution-outline` and `phase-6-finalize`.

## Objective

PLAN-LB-163 added a `retired` functional-review verdict: a deliverable the operator retired with no successor closes through it, provided every frozen criterion of the deliverable is authorized through `criteria-authorize`. The authorization is keyed on the deliverable and the frozen criterion text and carries a free-text `decision`, so an authorization the operator recorded to approve a REWRITE of a criterion is indistinguishable from one recorded to retire it.

With D1 frozen as `[a, b]`, the rewrites `a→a'` and `b→b'` authorized and a reviewer writing `{number: 1, verdict: retired}`, the validator branch returns before `_grade_criteria`: `a'` and `b'` are never graded, no `deliverable_not_met` row is filed and the gate closes the deliverable. Before the change `met` and `not_met` forced grading of the current criteria. That breaks the spec's own Standing Constraint that the verdict is "an operator route, not a model shortcut", and the spec's precondition ("every criterion authorized") admits it by construction.

This plan gives a retirement its own recorded operator decision, so a rewrite approval can never close a deliverable and the current criteria of a rewritten deliverable are always graded.

## Deliverables

1. A retirement is its own operator decision. The authorization record carries what the operator decided (a rewrite of the criterion, or the retirement of the deliverable), and `retirement_state` reports `closed` only when every frozen criterion of the deliverable carries a retirement decision. A rewrite approval, and every authorization recorded before this change, no longer satisfies it, so an existing record fails closed. The outline settles the mechanism (see the verify-first clause): a typed field on the authorization entry written by `criteria-authorize`, or a refusal of a retirement whose authorized criterion text still appears in the current outline, or both. The one predicate stays the one rule shared by the validator and the completion gate.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-solution-outline
   - Persona: implementer
2. The validator and the completion gate refuse a retirement on a rewrite approval with a message that names the cause. A `retired` verdict whose criteria are authorized only as rewrites is refused as such, grading continues for the current criteria, and no deliverable is closed. The refusal text names which criteria lack a retirement decision, in the shape the existing `unauthorized` refusal uses.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:phase-6-finalize
   - Persona: implementer
3. The two review documents and the rubric state how a retirement is recorded: the rubric's `retired` paragraph and the functional-review workflow say that a retirement needs the operator's retirement decision per criterion, not any authorization, and name the route that records it.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation
   - Persona: documenter
4. Tests pin D1 to D3, written against the unfixed tree first: a deliverable whose criteria are authorized as rewrites and carry a `retired` verdict is refused by the validator and closes nothing in the gate, and its current criteria are graded; a deliverable whose every criterion carries a retirement decision closes, as before; a mixed deliverable (one retirement, one rewrite) is refused; and a record written before this change, with no decision type, does not close a deliverable. The controls hold at `main` `46d3308ea`: the `met` and `not_met` paths, the two existing refusals and the no-criteria refusal are unchanged.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- Fail closed. Any authorization that does not positively carry a retirement decision, including every record that predates this change, closes nothing for a `retired` verdict.
- A rewrite approval keeps its present meaning for the criteria drift check: a criterion whose rewrite the operator authorized still passes `criteria_drift` as it does at `main` `46d3308ea`. Only the `retired` verdict stops accepting it.
- `criteria-authorize` stays an operator route: the decision text stays required, the decision is still written to the plan's decision log, and a retirement decision is recorded through the same guarded commit, rollback and tamper rules as a rewrite decision.
- The completion gate and the validator keep reading ONE predicate; no second reading of the retirement rule is added.
- The existing `criteria_drift`, `deleted` and `spec_criterion_missing` behaviours are unchanged.
- Order inside the plan: deliverables 1 to 3, then deliverable 4 written against the unfixed tree.
- No file outside `manage-solution-outline`, `phase-6-finalize` and their tests is touched. No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: four deliverables, under the presumptive-split guard.

## Claim Labels

- OBSERVED (re-read at `main` `46d3308ea` on 2026-11-19): `manage-solution-outline/scripts/_criteria_snapshot.py` § `_authorization` (lines 1418-1426) matches an entry on `(deliverable, normalized criterion text)` alone; § `retirement_state` (lines 1429-1468) reports `closed` when every frozen criterion is authorized; § `authorize_change` and `_commit_authorization` (lines 1652-1771) write an entry `{deliverable, criterion, decision, phase}` with a free-text `decision` and no type.
- OBSERVED (re-read at the merge commit): `phase-6-finalize/scripts/_review_support_validate.py` lines 489-503 handle `verdict == RETIRED` by calling `retirement_state(read_snapshot(plan_id), number)` and returning before `_grade_criteria` and before the `not_met` row.
- OBSERVED: the defect is hand-traced from the code and its input is constructed (landing, layer 3, L3-1); it has not been run.
- HYPOTHESIS: `manage-solution-outline.py` defines the `criteria-authorize` verb's argument surface, so a typed decision needs a new argument or value there; confirm at `manage-solution-outline.py` § the `criteria-authorize` parser and `review_support.py` § its `criteria-authorize` mention (verify-at-outline).
- HYPOTHESIS: no consumer other than `_authorization`, `retirement_state` and `open_criteria` reads `authorized_changes` entries by shape, so adding an optional field breaks none; confirm by sweeping `authorized_changes` over the inventory and reading each reader (verify-at-outline).
- Verify-first clause: the outline settles (a) the mechanism, between a typed decision on the authorization entry and a refusal when the authorized text still stands in the current outline, and whether both are needed (the first fixes the indistinguishability, the second also catches an operator who typed the wrong decision); (b) how a pre-existing entry with no type reads, which must fail closed for `retired` and keep its meaning for drift; (c) every reader of `authorized_changes` and every document that describes the entry shape; (d) whether `review_support.py` and the two landing-payload documents need to change with it. A refutation of (a) loops back to re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_criteria_gate_completion_d1.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_superseded_by_names_deliverable_d3.py`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none staged or running; PLAN-LB-167 and PLAN-LB-168 touch the runbook lane and the Sonar skill, PLAN-LB-164 the build server and PLAN-LB-165 the project-hygiene surfaces.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md` and the two landing-payload documents under `plan-orchestrator/standards/`, which describe the authorization entry or the retired counters; the outline reads them and edits one only if the entry shape it documents changes.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-169-retired-verdict-needs-its-own-operator-decision.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox message.

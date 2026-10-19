# PLAN-LB-75: The criteria gate's mechanisms are reachable, consistent and honestly documented

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-75-lb-70-reach.md` and is queued as one row file, `queue/PLAN-LB-75.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-70 (#1815, `a297ea762`),
> `landings/PLAN-LB-70.md` § Deliverable Fidelity. Priority is **medium**; PLAN-LB-74 (high) comes
> first. **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion. Do not merge them.** A Done-when says "fails at `a297ea762`" only where the behaviour is
> new at that sha; a clause that already holds says "holds at `a297ea762`". Grade each deliverable
> against THIS spec's Done-when text; an outline that rewrites a Done-when must say so and why.

## Objective

PLAN-LB-70's tests are real, but several of its mechanisms never reach production: the finalize
triage source still turns every ungraded criterion into a blocking finding after the completion gate
exempted it, `criteria_gate` is never persisted, the `criteria-refreeze-authorize` verb is wired into
no workflow and a q-gate re-dispatch now halts without a documented way forward, and the
test-integrity check is silent for every plan without a worktree and blind to class methods, `async`
tests and delete-and-compensate moves. Two standards (`triage.md`, `review-rubric.md`) now contradict
the code. This plan makes the mechanisms reachable and the documents true, each against a fixture that
fails at `a297ea762`.

## Deliverables

1. **The triage source honours the same exemptions as the completion gate, and `criteria_gate` is recorded.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc
   - Persona: plan-marshall:persona-implementer
   - `run_open_criteria` (`review_support.py:358-361`) applies the review-dropped, authorized,
     superseded and operator-closed exemptions of `open_criteria`, so a surgical plan's ungraded
     criteria no longer become blocking findings in finalize triage.
   - `criteria_gate` (`_cmd_lifecycle.py:1398-1405`) is persisted in the plan's status record and
     shown by the finalize output, not only returned by the transition.
   - `triage.md` L62 and L64 ("the finalize completion gate refuses that exit independently";
     "a criterion is open until the sealed verdict grades it met") are corrected to the exemptions;
     the duplicated sentence flagged in the PLAN-LB-52 audit is removed.
   - `functional_review_drop_reason` (`_cmd_lifecycle.py:977`) gets a producer or is removed.

   *Done when:* each of these fails at `a297ea762`:
   - a fixture surgical plan whose manifest dropped functional review yields no
     `open_done_when_criterion` finding from the triage source;
   - a fixture plan with an operator-authorized deleted criterion yields none either;
   - the transition's `criteria_gate` value is readable from the status record afterwards;
   - a doc test asserts `triage.md` states the exemptions and carries the sentence once.

2. **A q-gate re-dispatch has a documented path through the re-freeze decision.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc
   - Persona: plan-marshall:persona-implementer
   - `phase-3-outline/SKILL.md` (L677) and the light-lane step route a `refreeze_requires_decision`
     result to `criteria-refreeze-authorize` and to the operator question that must precede it,
     instead of reading every non-success `snapshot-criteria` as "outline could not be read".
   - The D3e decision of PLAN-LB-70 (`criteria-authorize` wired, `verify-first` removed) is recorded in
     `functional-review.md` beside the D4c record at L93.

   *Done when:* each of these fails at `a297ea762`:
   - a doc test asserts the outline skill and the light-lane step name `refreeze_requires_decision`,
     the verb and the operator question;
   - a doc test asserts `functional-review.md` records the D3e decision.

3. **The test-integrity check reaches plans without a worktree and the weakened-test rules agree.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc
   - Persona: plan-marshall:persona-implementer
   - A plan with `use_worktree: false` is graded against the main checkout's diff to the base, not
     skipped; the choice of evidence root is recorded at outline.
   - Per-function matching is keyed by a qualified name, so class methods (indented `def`),
     `async def` tests and same-name tests in different classes are matched; a deleted test whose
     assertions are added elsewhere in the same file is reported.
   - The docstring of `_review_support_integrity.py` and `functional-review.md` L309 state exactly
     which evasions are caught and which are not (a weaker replacing assertion; a Java test method),
     and `review-rubric.md` and `functional-review.md` L309 agree on whether a deliverable that asks for
     the change retires a `weakened_test` finding.

   *Done when:* each of these fails at `a297ea762`:
   - an assertion moved between two methods of one class is reported;
   - an `async def` test that loses an assertion is reported;
   - a deleted test with an equal number of assertions added to another test in the same file is
     reported;
   - a `use_worktree: false` fixture plan that removes an assertion yields a `weakened_test` finding;
   - a doc test asserts the two documents give one answer on the "asks for the change" case.

   And these **hold at** `a297ea762` and are kept as controls: an assertion moved to a NEW test
   function is reported; a wholly deleted test is reported.

4. **A closed review does not close later criteria.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `functional_review_override_heads` (sticky in `_review_closed_reason`, `_criteria_snapshot.py:287-311`
     and `:887-889`) closes criteria only for the head it names; a later delta round that finds an
     unmet criterion on a newer head keeps that criterion open. PLAN-LB-70 tried a head-aware variant
     and reverted it for the override-with-sealed-verdict case; both cases are fixtures here.
   - `superseded` needs a non-empty `superseded_by` that names an existing deliverable.

   *Done when:* each of these fails at `a297ea762`:
   - after an override of head A, a verdict for head B with a `not_met` criterion leaves that criterion
     open;
   - a deliverable with `superseded_by: "x"` that names no deliverable does not close its criteria.

   And this **holds at** `a297ea762`: an override with a sealed verdict on the same head closes the
   criteria.

## Claim Labels

- OBSERVED: `run_open_criteria` / `open_criteria` has no drop logic at the triage source, and `triage.md` L42-58 still ingests every open row as a severity-error finding; L62 and L64 still say the completion gate "refuses that exit independently" — `phase-6-finalize/scripts/review_support.py` L358-361 and `phase-6-finalize/standards/plan-marshall/workflow/triage.md` (audit of PLAN-LB-70).
- OBSERVED: `criteria_gate` is set only on the transition output; `functional_review_drop_reason` is read and never written — `manage-status/scripts/_cmd_lifecycle.py` L977, L1398-1405.
- OBSERVED: `criteria-refreeze-authorize` is invoked by no workflow, and `phase-3-outline/SKILL.md` L677 reads any non-success `snapshot-criteria` as "outline could not be read" — `manage-solution-outline/scripts/manage-solution-outline.py` L1290-1305, L1712-1729.
- OBSERVED: `worktree_unresolved` is skipped silently for every `use_worktree: false` plan — `review_support.py` L213-214; `_references_core.py` L294-296.
- OBSERVED: per-function matching covers column-0 Python `def` and JS `it/test/describe` only, and excludes a deleted function from the per-function leg — `phase-6-finalize/scripts/_review_support_integrity.py` L105-121, L169-182.
- OBSERVED: `weakened_test` is blocking until restored or overridden, while `review-rubric.md` still says a deliverable that asks for the change justifies it — `functional-review.md` L309 against the unchanged rubric.
- HYPOTHESIS: the main checkout's diff to `origin/main` is the right evidence root for a plan without a worktree — confirm at `review_support.py` § evidence root and `_references_core.py` § `resolve_live_worktree` (verify-at-outline).
- Verify-first clause: decide the qualified-name scheme for per-function matching (module path plus class plus function) before D3 is scoped, and record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py` — `run_open_criteria`, evidence root (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_integrity.py` — per-function matching and docstring (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — `criteria_gate`, the drop reason (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — override heads, `superseded` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/plan-marshall/workflow/triage.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — L93, L309 (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` and `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` (verify-at-outline) (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` and `test/plan-marshall/manage-status/` — the fixtures of D1 to D4

## Dependencies and Sequencing

- Depends on: PLAN-LB-70 (shipped). Emit **after** PLAN-LB-74, which edits the same files.
- Overlaps with: the staged PLAN-LB-53 and PLAN-LB-55 on `manage-status/scripts/` and
  `phase-6-finalize/`. The emit gate decides.
- Adjacent to: `phase-3-outline` is touched only for the documented routing of one result code.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-75-lb-70-reach.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

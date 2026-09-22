# PLAN-177: Close the Leftover Gate Gaps

epic: test-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-177-close-the-leftover-gate-gaps.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
>
> ⛔ **Scope is exactly the two gate-adjacent leftovers below.** This is the "leftovers"
> half of the PLAN-140 redesign (the campaign half is PLAN-176). Deliberately excluded,
> with reasons: the deferred CodeRabbit nitpicks (production files unanchored — stage
> when anchored); the per-slice reduction residue (each a plan-sized re-entry into a
> landed slice — stays stage-on-demand); the harness-scope tail (outside this epic);
> the flip and PR-carving items (operator decisions, not plan work); the
> declaration-form question (ledger narrative, not a deliverable).

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode): process compliance is mandatory, not advisory.

## Objective

Close the two leftover gaps that keep the epic's gates from meaning what they say:
teach the `subprocess-pythonpath` rule to distinguish its five known false-positive
shapes so the tree-wide gate goes green for the first time, and give the `_run_python`
isolation a regression test that discriminates the old regime from the new. Done when
the gate reports green with zero error-severity findings and the isolation test fails
against the pre-fix code and passes after.

## Deliverables

1. **D1 — Fix the rule's five false-positive shapes.** The rule matches a call SHAPE
   and cannot see a deliberate env scrub, a helper-supplied `PYTHONPATH`, or a `-m`
   stdlib invocation — the five confirmed instances (`462a76`, `c0f4ef`, `02c9ea`,
   `79bf95`, `24970a` per the PLAN-135 landing record). Teach the detector to
   distinguish them without weakening it against genuine violations: each fixed shape
   carries a negative control (the false-positive form, must stay clean) and the
   neighboring genuine-violation form (must still fire).
   *Done when:* `rules_run` reports zero `subprocess-pythonpath` findings, the gate
   reports green, and every fixed shape has its matched control pair observed.
2. **D2 — Discriminate the `_run_python` isolation.** The code is correct and the prose
   accurate, but both consuming assertions pass under the old and new regimes, so a
   regression would keep them green. Write the missing regression protection: a test
   that fails against the pre-fix isolation and passes after.
   *Done when:* the new test is observed failing on the old regime and passing on the
   new, and both existing consuming assertions still pass.

## Claim Labels

- OBSERVED: the tree-wide gate is red solely on 5 error-severity
  `subprocess-pythonpath` findings — read at `landings/PLAN-135.md` (Added by
  PLAN-135's landing: all 5 verified false positives, every other finding a warning).
- HYPOTHESIS: the five instances and their shapes at dispatch — confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` § `analyze_subprocess_pythonpath` (verify-at-outline; landings have moved the tree since, so D1 re-derives the instance list before scoping).
  - verdict: corroborated | checked_at: 5feeff9429e5bb12157f8e6571de54174d827c35 | by: test-quality/analyze | rescoped: n/a | evidence: a5977d953 fixes the five filed shapes with matched control pairs; narrowed to literal -m py_compile per review, neighboring violations still fire
- OBSERVED: no test discriminates the `_run_python` isolation — read at
  `test/sync-plugin-cache/test_staleness_guard.py` § `_run_python` (the helper under
  test; both consumers pass either way, so the gap is missing protection, not a live
  defect).

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — the rule fix (verify-at-outline)
- HYPOTHESIS: `test/pm-plugin-development/plugin-doctor/` — rule regression tests (verify-at-outline)
- HYPOTHESIS: `test/sync-plugin-cache/test_staleness_guard.py` — the isolation discrimination test (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-135 (landed — the false-positive record it filed is this plan's
  input), PLAN-105 (landed — instruments).
- Overlaps with: none live (flight line empty at stage time; N=1 sequential).
- Adjacent to: PLAN-176's slice (`040` delivery pipeline) — nearby test surface this
  plan does not touch; the rule file both plans' gates read is shared infrastructure,
  not a collision.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-177-close-the-leftover-gate-gaps.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

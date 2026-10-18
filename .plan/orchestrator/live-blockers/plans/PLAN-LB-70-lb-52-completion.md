# PLAN-LB-70: The criteria gate refuses only real gaps, reads specs correctly, and is sealed outside the file it guards

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-70-lb-52-completion.md` and is queued as one row file,
> `queue/PLAN-LB-70.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-18 from the PLAN-LB-52 landing (`landings/PLAN-LB-52.md`). Fix-forward:
> PLAN-LB-52 (`6286484d8`) is kept.
> - **Each deliverable is its own outline deliverable, and each Done-when is its own success
>   criterion. Do not merge them.**
> - Every Done-when test is **written first and run before any production edit, and seen failing
>   at `6286484d8` on its own assertion** — not as a collection error. Log the red run, then the
>   green.

## Objective

PLAN-LB-52 froze the success criteria and gated the finalize exit on them, but the gate refuses
legitimate work:

- every plan whose functional review is dropped can never finalize;
- every orchestrator-staged plan gets a false "spec criterion missing";
- several ordinary states read as open criteria.

Its tamper protection is a digest stored inside the file it protects.

## Deliverables

1. **The finalize gate refuses only genuinely open criteria.**
   - A plan whose manifest dropped functional review is not refused for `ungraded` criteria. That
     covers surgical scope, commit-push disabled, and `functional_review` off. Instead:
     - the gate reports `criteria_gate: not_applicable (review dropped: {reason})`;
     - the finalize output records it.
   - `open_criteria` honours:
     - `authorized_changes`: a deleted or rewritten criterion authorized by a logged operator
       decision is closed;
     - superseded deliverables;
     - a review closed by the operator past its round cap.
   - A verdict row matches its criterion by a stable id, not by exact text, so a paraphrase does
     not orphan it. The validator refuses a verdict whose text diverges from the outline only if
     the rubric requires that, and says so.

   *Done when:* each of these fails at `6286484d8`:
   - a surgical light-lane fixture plan with a snapshot and no functional-review verdict
     completes `transition --completed 6-finalize`;
   - a plan with an operator-authorized deleted criterion completes;
   - a superseded deliverable's criteria do not block;
   - a paraphrased verdict row grades its criterion.

   A plan with one genuinely unmet criterion is still refused: that is the negative control.

2. **Spec and citation parsing match real documents.**
   - `_SPEC_DONE_WHEN_RE` extraction reads the whole Done-when, including its wrapped lines and
     bullet list, up to the next deliverable or section.
   - `PRE_FIX_CRITERION_RE` no longer matches "prefix" or other words merely containing "prefix".
   - Citation parsing accepts:
     - a backticked `` `test/x.py::t` ``;
     - a build-log citation under `.plan/local/plans/*/build-results/`, checked against that
       directory rather than the worktree;
     - existence judged at the graded head commit, not the working tree.
   - `evidence_check: not_run` is surfaced by the functional-review workflow as a finding, never
     silently accepted, as rubric §4 says.

   *Done when:* each of these fails at `6286484d8`:
   - the PLAN-LB-52 spec itself (a fixture copy) yields its full D1 Done-when text;
   - a criterion "uses the canonical prefix set" graded `met` stays `met`;
   - a backticked citation and a build-log citation are accepted;
   - an uncommitted test file cited in a verdict is refused;
   - a `not_run` evidence check produces a finding.

3. **The seal and the snapshot are bound outside the files they protect.**
   - The verdict digest and the snapshot digest are recorded through `manage-status`, in the
     plan's status record, by the verb that writes the file. The checks compare against that
     record.
   - A snapshot that existed and was deleted is detected: the status record says one was frozen.
     Every check then refuses instead of falling back to the legacy path.
   - Re-freezing requires an operator decision logged through the same path as
     `criteria-authorize`. A phase rollback alone does not permit it.
   - The freeze becomes a transition requirement: `3-outline → 4-plan` refuses without a snapshot
     on a plan created after this change, while legacy plans are exempt by creation date.
   - Wire `criteria-authorize` and `verify-first --record` into the workflows that need them, or
     remove `verify-first` and its doc claims. Choose at outline and record the choice.

   *Done when:* each of these fails at `6286484d8`:
   - a verdict edited and re-sealed by recomputing its in-file digest is refused;
   - a deleted snapshot on a plan whose status says "frozen" is refused;
   - a re-freeze after `set-phase` without a logged decision is refused;
   - a new plan cannot leave `3-outline` without a snapshot.

4. **The deleted-assertion rows reach the validator.**
   - `test-integrity` rows are consumed by `run_validate` (and by code review, if in scope at
     outline) as findings.
   - Net-count evasion is closed: an assertion removed from one test and added to another is
     still reported, by matching per test function.
   - "Fixture changed together with the rule it pins" is implemented, or explicitly dropped with
     an operator decision.

   *Done when:* each of these fails at `6286484d8`:
   - a branch that removes an assertion produces a validator finding with no prose step;
   - removing one assertion and adding one elsewhere in the same file is still reported.

Split guard: four deliverables, one surface (the criteria snapshot, review support and the
finalize refusal).

## Claim Labels

- OBSERVED: `_manifest_rules.py:476` `_SCOPE_GATED_SURGICAL_DROP` contains `functional-review` and
  `code-review`.
- OBSERVED: `_cmd_lifecycle.py:972-992` refuses `open_done_when_criteria` from
  `open_criteria(plan_id)`.
- OBSERVED: `_criteria_snapshot.py:69` `_SPEC_DONE_WHEN_RE = …\s*(.+)`, one line.
- OBSERVED: `_review_support_validate.py:50` `PRE_FIX_CRITERION_RE` contains `pre-?fix`.
- OBSERVED: the seal digest lives inside the verdict JSON (`_criteria_snapshot.py:88-128`, per
  the delegated audit).
- HYPOTHESIS: verdict rows carry a criterion id usable for stable matching (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py`,
  `manage-solution-outline.py` (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py`,
  `_status_core.py` (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py`,
  `_review_support_validate.py`, `_review_support_integrity.py`, `_review_support_attribution.py`
  (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md`,
  `workflow/functional-review.md`, `plan-marshall/workflow/triage.md` (D2, D4)
- HYPOTHESIS: `phase-3-outline/SKILL.md` and the light-lane step, for the transition requirement
  (verify-at-outline) (D3)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_criteria_integrity_d1.py`, `_d2.py`, and the
  `manage-status` lifecycle tests (D1–D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-52 (shipped).
- Overlaps: PLAN-LB-55 (gate-head truth; its surface touches finalize and the gates) and
  PLAN-LB-53 (after PLAN-LB-55). The emit gate decides. Recommended: emit before PLAN-LB-55, because
  regression 1 blocks plan-marshall-lane finalizes.
- Emitted after the drain, in the PLAN-LB-66 structure.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-70-lb-52-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

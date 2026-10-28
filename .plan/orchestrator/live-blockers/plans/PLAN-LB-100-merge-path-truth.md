# PLAN-LB-100: The merge path tells the truth — `pre_merge_gate merge` checks that every required review bot saw the head, a merge under an authorization is recorded as one, and the merge question says what follows

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-100-merge-path-truth.md` and is queued as one row file, `queue/PLAN-LB-100.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the operator's instruction to implement the open HIGH item "the gate-truth half of PLAN-LB-55", which
> PLAN-LB-55 and then PLAN-LB-93 deferred. This plan is the **merge-path half** of that item (the participation check inside
> `pre_merge_gate merge`, the merged-under-authorization record, and the truthfulness of the merge question). The
> **review-policy half** (roster read, stale-bot trigger, demotion remedies, quota loop) is PLAN-LB-101. The two overlap on
> `branch-cleanup.md` and `pre_merge_gate.py`; run PLAN-LB-100 first.

## Objective

A merge can still go out on a head that one required review bot never saw, because `pre_merge_gate merge` runs no required-bot
participation check; the only net is the prose barrier in `branch-cleanup.md`, which a run that skips the barrier step also skips.
A merge that proceeded under an authorization is described in clean-merge wording unless a document branch is followed by hand.
And the merge question does not say that, with `final_merge_without_asking` set, no second question follows. This plan moves each
of the three into script-enforced behaviour.

## Deliverables

1. **`pre_merge_gate merge` runs the required-bot participation check against the merge candidate.**
   - `merge` calls the same predicate the barrier uses (`review_completeness check`, with the configured roster) against the
     candidate head and refuses unless every required bot participated on that head, or a recorded HEAD-bound grant covers the
     gap, or the standing authorization applies (see Verify-first).
   - The refusal is a new, named error code beside `merge_candidate_not_gated`, and carries the unproven bots and their states.
   - A run that skips the barrier step no longer merges unchecked.

   *Done when:* tests in `test_pre_merge_gate.py`: a candidate a required bot did not review is refused without a covering grant
   and merges with one; a quota-limited required bot that has a qualifying review and handled findings is admitted; an unreviewed
   required bot that never reviewed any head is refused; an EMPTY roster is not read as a pass (see PLAN-LB-101 D1) — the check
   states whether the roster was read. Each refusal case fails at HEAD.

2. **A merge under an authorization is recorded as one, by script.**
   - When the merge proceeds past a reported gap, a script writes the step record `merged under {kind}, gap recorded` (the
     bounded form, ≤80 characters, ASCII), with the full expansion in the unbounded decision-log line.
   - A clean merge never carries it, and an authorized merge never carries the clean-merge wording.
   - `branch-cleanup.md` Branch E stays the specification of the wording; the script is what makes it happen.

   *Done when:* tests: a granted merge's step record carries `merged under barrier-ask-override, gap recorded`; a clean merge's
   does not; the longest admissible `{kind}` still fits the 80-character bound. Fails at HEAD, where no `.py` file under
   `marketplace/bundles/` contains the wording.

3. **Every merge-path question tells the truth about what follows.**
   - When `final_merge_without_asking` is `true`, the pre-enqueue option text says the PR will be merged without a second question.
   - When it is `false`, the text says a confirmation follows.
   - The text is generated from the knob's value, not authored per call site.

   *Done when:* tests assert the option text for both values at each site that renders a pre-enqueue merge option, and that no
   site renders a text the other value would contradict.

Split guard: three deliverables, one theme (the merge dispatch), one surface. The review-policy half is PLAN-LB-101 and shares no
deliverable with this plan.

## Standing Constraints

- The operator's ruling stands: with at least one valid CodeRabbit review and the quota refusing the re-review, the merge proceeds
  without a question. The participation check must admit that case and refuse only an unreviewed required bot.
- A required reviewer is mandatory and is never demoted to `optional_bots`; the only ruling that covers its silence is a recorded
  HEAD-bound merge authorization.
- Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none as landing evidence.
- Every new refusal fails closed: a roster that could not be read is not an empty roster, and an unreadable participation state is
  not a pass.

## Claim Labels

- OBSERVED: `pre_merge_gate.py` defines `MERGE_HEAD_NOT_GATED = 'merge_candidate_not_gated'` and `cmd_merge`, and contains no
  reference to `review_completeness`, participation or a grant — read by grep at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` (L97, L449; zero hits for `review_completeness`, `participat`, `grant`) at HEAD `3aad286fb`.
- OBSERVED: no Python file under `marketplace/bundles/` contains the string `gap recorded`; Branch E's wording is documented only in `branch-cleanup.md` L2216-2231 (`--display-detail "merged under {kind}, gap recorded"` at L2231).
- OBSERVED: the barrier reads the roster from `step-params get` and forwards it to `review_completeness check` — `branch-cleanup.md` L843-859 and L994.
- OBSERVED: `branch-cleanup.md` documents the "Merge anyway (record reason)" resume as re-acquiring the mutex and re-validating (L1401, L1437), so that LB-93 D6 bullet is already documentation, not a gap.
- HYPOTHESIS: the pre-enqueue option text that mentions `final_merge_without_asking` is authored at more than one site — confirm at `branch-cleanup.md` L573-614 and L719 and at every other site that renders a pre-enqueue merge option (verify-at-outline).
- HYPOTHESIS: a script that writes step records (`manage-status mark-step-done` or the finalize record helpers) is the right home for D2 — confirm at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` and `phase-6-finalize/scripts/` (verify-at-outline).
- Verify-first clause (D1): record how the check tells a quota-limited required bot with a qualifying review apart from an unreviewed one, and which `review_completeness` state members it maps to each side; refutation of the mapping loops back to re-scope.
- Verify-first clause (D2): run the full finalize path for a granted merge and confirm the wording is produced by the script and not by an agent following Branch E by hand.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — `cmd_merge` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — barrier, Branch E, pre-merge confirmation gate (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the predicate D1 reuses (D1)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` (D1, D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` and `test/plan-marshall/manage-status/` — the step-record writer for D2 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-101 on `branch-cleanup.md` and the `automatic-review` skill. Run PLAN-LB-100 first.
- Adjacent to: `_push_gate.py` and the push verb (the armed-merge refusal PLAN-LB-93 shipped), which stay untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-100-merge-path-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

# PLAN-LB-123: The delta has a workable source, the manifest records the command it decided on, and a prescribed hand-back is not reclassified

epic: live-blockers
workstream: WS-01

> Plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-123-execute-handback-and-manifest-gaps.md`. This spec is NOT queued: the operator asked for the follow-up
> plans to be specced and not staged, so no row file exists. The orchestrator EMITS the command below; it never launches the plan
> inline, and a row is added when the operator launches it.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Specced on the operator's word (decision 14): the fix plan for the PLAN-LB-117 findings (PR 1918, merge `c394a95fb`; report
> `landings/PLAN-LB-117.md`). Every finding id below (L1-n, L2-n, L3-n) is that report's. The points the orchestrator re-read at their
> lines are OBSERVED; the points the analysis leaf read and the orchestrator did not re-read, and every claim about reach, are
> HYPOTHESIS and are settled first. D3 opens with the precondition the report left unsettled.
>
> Ruling check. D1 (the delta's source can only be followed by an invented value) and D2 (a re-compose is not idempotent) are graded
> high; D3 is a major lead on whether a prescribed yield is now classified `error`. D4 and D5 are minor and separable. No token or
> measurement work: `total_tokens` stays as it is. No Sonar.

## Objective

PLAN-LB-117 made a stall beside a hand-back decidable, gave `completed_tasks_delta` a named source and defined the owed rung. Reading
the merged code found that the documented sequence for the delta cannot be followed, that the manifest records a different command from
the one its decision rested on, and that the new order may classify a prescribed hand-back as an error.

After this plan the orchestrator text states a sequence that yields the delta without inventing it, the manifest records the command
the deferral was decided on and a re-compose is idempotent, a hand-back whose task is not owed is either shown safe or classified by
a stated rule, and the minor edges and the contradicting lines are closed.

## Deliverables

1. **The B7 text yields the delta by a sequence the orchestrator can follow.** *(L3-1; high)*
   - `execution.md:239,247-254` says both done counts come from "the loop-exit-guard call below", but that call takes
     `--completed-tasks-delta` as input. The code is fine: a plain `loop-exit-guard` call reports `done_count`
     (`_tasks_query.py:396,406`) and the pre-dispatch peek is a plain call (`:270-275`). The text states the sequence: a plain call
     before the dispatch records the done count, a plain call after it records the second, and the delta is their difference passed to
     the evaluating call.
   - The snapshot lives in orchestrator context and a resume loses it. The text says where it is written (a field the row
     `record-dispatch-boundary` writes, or a stated re-derivation on resume) so a resumed session cannot invent a zero. The choice is
     recorded at outline.

   *Done when:* a doc test asserts the text names the before-and-after plain calls and the subtraction and no longer reads both counts
   from the evaluating call (red at `c394a95fb`); if the row is extended, a fixture shows the done count written and read back; a
   fixture shows the evaluation of a first dispatch refused as `no_progress_not_decidable` when no snapshot exists.

2. **The manifest records the command the deferral was decided on, and a re-compose is idempotent.** *(L3-2; high)*
   - The decision pass admits a command when its tier is `orchestrator` and `exceeds_bash_ceiling` is true
     (`manage-execution-manifest.py:1343-1362`), and the routing pass records the first module-tests command whose tier is
     `orchestrator`, qualifying or not (`:1517-1551`). For one task listing an unmeasured command B first and a measured over-ceiling
     command A second, A decides and B is recorded; a re-compose re-measures B, which does not qualify, and the stamps move.
   - The routing pass records the qualifying command, so the recorded `owed_rung_command` is the one the decision rested on. A second
     compose over the same input produces the same manifest.
   - `manage-execution-manifest/SKILL.md:779` describes the qualifying-command rule the code then implements.

   *Done when:* a fixture with an unmeasured command first and a measured over-ceiling command second records the second (red at
   `c394a95fb`); composing twice yields identical manifests (red); a single-command task is unchanged (control).

3. **A hand-back whose task is not owed is shown safe, or classified by a stated rule.** *(L3-3; major lead — settle first)*
   - Settle first: whether a task handed back by a `running` return or the Step 11b/11c hand-backs is `in_progress` without
     `verification_owed` at the return (`phase-5-execute/SKILL.md:1104`; the Step 11b and 11c texts), and whether such a dispatch can burn
     more than the token threshold with a delta of 0. The predicate now decides before the hand-back and subtracts only tasks held open
     with `verification_owed` (`_tasks_query.py:613-631`), so a not-owed hand-back counts as in progress and the dispatch is `error`.
   - If it is reachable: the prescribed hand-back is exempt by a stated rule (the return's own marker, or every hand-back task
     carrying the owed hold at the return), the text in `execution.md:242` and `phase-5-execute/SKILL.md:1104` states which, and a
     fixture pins it. If it is not reachable: the lead is refuted, the PR says so, and the assumption "every hand-back's task is owed" is
     written into `execution.md:242` as an invariant with its source.

   *Done when:* a fixture with a `running` hand-back on a task without the owed hold, delta 0 and more than the threshold is classified
   by the stated rule (red at `c394a95fb` if the lead stands); the matched control, a hand-back alone on an owed task, stays the
   hand-back cause; or the PR shows the refutation and the invariant sentence.

4. **The minor edges of the evaluation and the stamp.** *(separable; L3-4, L3-5, L3-6, L2-1, L2-2)*
   - A negative `--completed-tasks-delta` (a done task reopened) and a negative token figure are refused as not decidable, not read
     as progress (`_tasks_query.py:478-487,615`).
   - The reason `no_progress_predicate_holds_beside_handback` is chosen only for a valid hand-back, not on the bare flag
     (`:625-627`).
   - `_bounded_tier_fields` passes `measured` from the stamp it holds, so a default stamp does not report `exceeds_bash_ceiling` true
     (`_cmd_client_build.py:486,533,538`); `_narrow_default_stamp` is read first to see whether a default can exceed a ceiling.
   - The D3 leaf-side test drives the leaf's choice to pass `--verification-owed`, or the PR states the leaf side is pinned by text
     only (`test_unmeasured_rung_owed_hold.py:87,111,118`); the untested branches (a hand-back naming a mix of valid and unknown ids, a
     missing or unreadable manifest, a non-empty unknown-step list) have a fixture each.
   - The `== 14` and `== 8` hand counts in two tests are replaced by the constant they count.

   *Done when:* each shape above is a fixture red at `c394a95fb`; the leaf-side test fails against a stub that puts the hold on a single
   task.

5. **The contradicting and transitional lines agree.** *(separable; L3-7)*
   - The module docstring of `_cmd_client_build.py` no longer labels the unmeasured hint "within ceiling"; `phase-5-execute/SKILL.md:662-665`
     no longer says "its deliverable's rung" after the grouping moved to (deliverable, command); `:1394` names the cause of a stall that
     reclassifies a hand-back; the line "the handed-back task never counts toward the predicate" states the owed-task limit it has;
     `phase-6-finalize/SKILL.md:929` and `manage-metrics/standards/data-format.md:1053` read the same two logs the code writes.

   *Done when:* a read of each cited line shows the contradiction gone; the PR names the lines read.

Split guard: five deliverables. D1 to D3 are the core and share `execution.md`, `_tasks_query.py` and the manifest script; D4 and D5 are
separable and are the first to split off, D5 first. A split runs in sequence, since all five touch `execution.md`, the manifest text
or the same script. D3 is settled first because its answer changes D1's text.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **Do not weaken the no-progress rule for a genuine stall.** A stall on a not-owed task beside a hand-back is still `error`.
- **The owed hold stays.** `loop-exit-guard` still refuses a clean exit while an owed task is open.
- **Fail closed.** An absent or invalid input to the evaluation is a named stop, never a zero.
- **Counts come from an enumeration, not a hand list.**
- **No token or measurement work.** `total_tokens` stays as it is.
- **Documentation states the current behaviour.** No comment or doc describes a change or the pre-fix behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so.
- **No Sonar.**

## Claim Labels

- OBSERVED: `execution.md` L239 and L247-254 read both done counts from "the loop-exit-guard call below", which takes the delta as
  input; the first dispatch has no previous snapshot — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md`.
- OBSERVED: a plain `loop-exit-guard` call reports `done_count` and the pre-dispatch peek is a plain call —
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` L396, L406, L270-275.
- OBSERVED: the decision pass admits a command only when its tier is `orchestrator` and `exceeds_bash_ceiling` is true, the routing
  pass records the first orchestrator-tier module-tests command, qualifying or not, and a re-compose re-measures the recorded command —
  `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` L1343-1362, L1517-1551.
- OBSERVED: the predicate decides before the hand-back and subtracts only tasks held open with `verification_owed` —
  `_tasks_query.py` L613-631 (code re-read; the precondition is not settled).
- OBSERVED: `type(value) is int` accepts any integer and `predicate_holds` needs `delta == 0`, so a negative delta reads as progress;
  the reason string is chosen on the bare flag — `_tasks_query.py` L478-487, L615, L625-627.
- OBSERVED: `_bounded_tier_fields` passes `measured=True` — `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py`
  L486, L533, L538 (code re-read; whether a default can exceed a ceiling is not).
- OBSERVED: the D3 leaf-side tests call `cmd_finalize_step` with `owed=True` for every task themselves —
  `test/plan-marshall/execute-task/test_unmeasured_rung_owed_hold.py` L87, L111, L118.
- HYPOTHESIS: a `running` return or a Step 11b/11c hand-back leaves its task `in_progress` without `verification_owed`, and such a
  dispatch can consume more than 50,000 tokens with a delta of 0 — confirm/refute at `phase-5-execute/SKILL.md` L1104 and the Step
  11b/11c text (verify-at-outline). It decides D3.
- HYPOTHESIS: the row `record-dispatch-boundary` writes carries no done count — confirm/refute at `manage-tasks/scripts/manage-tasks.py`
  (verify-at-outline). It decides D1's snapshot location.
- HYPOTHESIS: a mixed valid and unknown id list is wholly invalid and a missing or unreadable manifest fails closed
  (`_tasks_query.py:531-551`), with no test for either — confirm/refute at outline (D4).
- HYPOTHESIS: `_narrow_default_stamp` can produce a stamp above a ceiling, and the deferral does not use narrow-unit resolves
  (`manage-execution-manifest.py:1179-1189`) — confirm/refute at outline (D4). If neither, the third bullet is dropped.
- HYPOTHESIS: the lines of D5 read as the report says (`phase-5-execute/SKILL.md:662-665,1394`, `phase-6-finalize/SKILL.md:929`,
  `manage-metrics/standards/data-format.md:1053`, `_cmd_client_build.py:58-67`) — confirm/refute at outline.
- Verify-first clause (D1, D2): reproduce each shape as a fixture red at `c394a95fb` before changing the code.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — L239, L242, L247-254 (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` — `evaluate_no_progress`, the hand-back, the inputs (D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — the routing pass, L1343-1362, L1517-1551 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` — L779 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py` — `_bounded_tier_fields` (D4, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — L662-665, L1104, L1394 (D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — L929 (D5)
- OBSERVED: `test/plan-marshall/execute-task/test_unmeasured_rung_owed_hold.py` — the leaf-side fixtures (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/manage-tasks.py` — the dispatch-boundary row, only if D1 extends it (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — L1053 (D5; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-tasks/` — the evaluation and loop-exit-guard fixtures (D1, D3, D4; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-execution-manifest/` — the compose fixtures (D2; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-metrics/test_manage_metrics_dispatch_termination_causes.py` and `test_qgate_doc_contract.py` — the hand-count tests (D4; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the merge of PLAN-LB-117 (`c394a95fb`), which is on the base branch.
- **Overlaps with** no running plan by the surfaces above; `execute-task/SKILL.md` is read, not edited. The disjointness gate decides
  the pairing at emit.
- **Adjacent to** (left untouched): the lane skill (PLAN-LB-106, 108, 116), the finalize review gate (PLAN-LB-105, 119), the merge and
  push gates (PLAN-LB-120).
- **Owed outside this plan, operator-run:** a harness sync after merge. Executor regeneration is owed only if a verb or flag is
  added; the landing says so.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-123-execute-handback-and-manifest-gaps.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

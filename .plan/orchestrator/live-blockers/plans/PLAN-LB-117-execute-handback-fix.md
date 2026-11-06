# PLAN-LB-117: The hand-back classification decides a stall beside a hand-back, its inputs have a stated source, and the owed-rung bookkeeping holds

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-117-execute-handback-fix.md` and is queued as one row file, `queue/PLAN-LB-117.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word ("emit the fix plan") after the three-layer analysis of the landing of PLAN-LB-109 (PR 1911, merge
> `051fda6a0`). The report is `landings/PLAN-LB-109.md`; every finding id below (L1-n, L2-n, L3-n) is that report's. The points the
> orchestrator re-read at their lines are labelled OBSERVED; the points the analysis leaf read and the orchestrator did not re-read are
> labelled HYPOTHESIS and are settled first.
>
> Ruling check. D1 and D2 are graded blocking under the epic's focus rule: they sit on the mechanism that decides whether a dispatch is
> an `error`, and a wrong decision feeds lessons capture (Signal 3) and the no-progress rule. D3 settles the spec ambiguity that left a
> deliverable's Done-when disputed. D4 and D5 are minor and are separable. No token or measurement work: `total_tokens` stays as it is.

## Objective

The prescribed-yield classification shipped by PLAN-LB-109 has two defects in its decision, one defect in how its input is sourced, an
undefined term that left one Done-when disputed, bookkeeping that can break its own invariant, and a set of contradicting documentation
lines.

After this plan, a stall on a task that is not owed a rung is still decided by the no-progress rule when a hand-back sits beside it,
`completed_tasks_delta` has a stated, reachable source and an absent input is not read as zero, the owed rung is defined once and the
unmeasured arm is tested on the leaf side, the manifest keeps one tail command per deliverable, and the documentation lines that
contradict each other agree.

## Deliverables

1. **A stall beside a hand-back is still decided, and the hand-back's step ids are checked.**
   - `evaluate_no_progress` (`_tasks_query.py`, L456-524) checks the hand-back against the owed tasks before it classifies the
     dispatch, so a return that carries `verification_handback true` exempts only the owed task(s) it names. A non-owed task that is
     in progress and consumed more than the threshold in the same dispatch is classified by the predicate, `error`, and the decision
     line is written.
   - The step ids on a hand-back are checked against the manifest's `phase_5.verification_steps` for the deliverable; an id that is not
     in it does not exempt (L3-7).
   - The spec's two statements are reconciled in the code's order and in `execution.md:242`: "never reaches the predicate" applies to
     the owed task alone.

   *Done when:* a fixture with one hand-back on an owed task and one stalled non-owed task in the same dispatch is classified `error`
   with the decision line written (red against the code at `051fda6a0`); a fixture with the hand-back alone stays
   `verification_handback`; a hand-back naming a step id outside the manifest's list does not exempt (red at base).

2. **`completed_tasks_delta` has a source, and an absent input is not zero.**
   - `execution.md:239` names where the orchestrator reads `completed_tasks_delta` from, and the named source carries it. The row
     `record-dispatch-boundary` writes is extended to carry the done count if that is the only source; otherwise the text names the
     existing one. The choice is recorded at outline.
   - `evaluate_no_progress` treats `--consumed-tokens` without `--completed-tasks-delta` as not decidable (a named error), not as a
     delta of 0 (L3-6, `_tasks_query.py:424-427,438-453`); the mode turns on only when both inputs are present.

   *Done when:* a fixture shows a dispatch that completed tasks and consumed more than 50,000 tokens beside a non-owed in-progress
   task is not `error` when the delta is supplied (red at base for the unsourced `0`); `--consumed-tokens` alone returns the named
   error; the `execution.md` line names a source that exists in the row or the call.

3. **The owed rung is defined once, and the unmeasured arm is tested on the leaf side.**
   - One definition of "owed rung" in `manage-execution-manifest/SKILL.md`: the compose-time command, the per-task owed hold, and
     which of them the unmeasured arm puts on which tasks (L1-2). `execute-task/SKILL.md:314-316` and the manifest text agree with it
     (L3-8).
   - A leaf-side test covers the unmeasured arm: a configured command without a measurement, with a live tier of `orchestrator`,
     leaves the owed hold on every task of the group, and a measured over-ceiling command defers to the chain tail (L2-1).
   - Whether an unmeasured command above the ceiling may defer (`_cmd_client_build.py:400`, L3-14) is read first; it must not, since
     the stamp is the only source of `exceeds_bash_ceiling` and bullet 3 of the shipped spec keeps today's behaviour.

   *Done when:* the definition appears once and the other texts point at it; the leaf-side fixture fails against a stub that puts the
   hold on a single task; the unmeasured-key read is shown in the PR as confirmed or refuted, and a refutation drops the third
   bullet.

4. **The manifest keeps one tail command per deliverable.** *(separable)*
   - `owed_rung_command` is not overwritten by a later orchestrator-tier command of the same task (`manage-execution-manifest.py:1494-1508`,
     L3-2).
   - Stale stamps are cleared per (deliverable, command), not per deliverable (`:1458-1460`, L3-3; `manage-execution-manifest/SKILL.md:772`).
   - The chain order respects dependencies through a task outside the group (`:1250`, L3-4).
   - `finalize-step` reads a record with `verification: null` without raising (`_cmd_step.py:145`, L3-5), if such a record occurs.

   *Done when:* a two-module deliverable fixture keeps the first command in `owed_rung_command` and exactly one `chain_tail`; a
   re-measured module B does not clear module A's stamps; a group whose task depends on an outside task puts the tail after it; a
   record with `verification: null` is read without error. Each is red at base.

5. **The documentation lines that contradict each other agree.** *(separable)*
   - `execution.md:207-208` no longer has a row that matches nothing (L3-9); `phase-5-execute/SKILL.md:1394` does not say "the ONLY
     yields" against `:136` and `:1373` (L3-10); the claim at `phase-6-finalize/SKILL.md:929` is supported or removed (L3-11); the
     transitional wording at `phase-6-finalize/SKILL.md:925`, `_signal_scan.py:15` and `manage-metrics.py:126` is rewritten as current
     state (L3-15).

   *Done when:* a read of each cited line shows the contradiction gone; the PR names the lines read.

Split guard: five deliverables. D1 and D2 are the core and edit one function; D3 depends on neither. D4 and D5 are separable and are
the first to split off if the PR grows; any split runs in sequence, since all five touch `execution.md`, the manifest text or the same
script.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around.
- **Do not weaken the no-progress rule for a genuine stall.** D1 exists to restore this.
- **The owed hold stays.** `loop-exit-guard` still refuses a clean exit while an owed task is open.
- **Counts come from an enumeration, not a hand list.** The `== 14` and `== 8` hand counts in two tests of the shipped plan are replaced by
  the constant they count.
- **No token or measurement work.** `total_tokens` stays as it is.
- **Documentation states the current behaviour.** No comment or doc describes a change or the pre-fix behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so.
- **Executor regeneration is owed after merge** only if a verb or flag is added; the landing says so.

## Claim Labels

- OBSERVED: the hand-back is checked before the predicate — `_tasks_query.py:509-512`; the decision line is written only on `error`
  — `execution.md:254-260`; the shipped spec states both "never reaches the predicate" and "do not weaken the no-progress rule"
  (`plans/PLAN-LB-109-…md:69-70,118-120`).
- OBSERVED: `completed_tasks_delta` is "read from the prior `record-dispatch-boundary` row" — `execution.md:239`; `_int_arg` turns an
  absent integer into `0` — `_tasks_query.py:424-427`; one input turns the mode on — `:438-453`.
- OBSERVED: `owed_rung_command` is overwritten by the last orchestrator-tier command — `manage-execution-manifest.py:1494-1508`;
  staleness is decided by deliverable — `:1458-1460`.
- OBSERVED: step ids are not validated — `_tasks_query.py:505`; `finalize-step` reads `.get('verification', {})` — `_cmd_step.py:145`.
- OBSERVED: the heading at `execute-task/SKILL.md:314` and the line at `:316` disagree; `execution.md:207-208` and
  `phase-6-finalize/SKILL.md:925` read as described in the report.
- HYPOTHESIS: the row `record-dispatch-boundary` writes carries no done count (the lane's report and the leaf's fixture headers; not
  re-read) — confirm/refute at outline; it decides D2's source.
- HYPOTHESIS: a configured, unmeasured key can reach `exceeds_bash_ceiling` above the ceiling (`_cmd_client_build.py:400-401`; the
  leaf's reading, not re-read) — confirm/refute at outline (D3).
- HYPOTHESIS: the chain order ignores dependencies through outside tasks (`manage-execution-manifest.py:1250`; leaf only) and a
  `verification: null` record occurs (L3-5; occurrence unknown) — confirm/refute at outline (D4).
- HYPOTHESIS: `phase-5-execute/SKILL.md:136,1373` and `phase-6-finalize/SKILL.md:929` read as the report says (partly re-read) —
  confirm/refute at outline (D5).
- Verify-first clause (D1, D2): reproduce each shape as a fixture red at `051fda6a0` before changing the code.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` — `evaluate_no_progress`, `_int_arg` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — L207-208, L239, L242, L254 (D1, D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — L1250, L1458-1510 (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` — the owed-rung definition, L772 (D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — L314-316 (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py` — L145 (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — L136, L1373, L1394 (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — L925, L929 (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-logging/scripts/_signal_scan.py` and `manage-metrics.py` — the transitional wording (D5; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/manage-tasks.py` — the row the done count is written on, if D2 extends it (verify-at-outline)
- HYPOTHESIS: `_cmd_client_build.py` under `manage-architecture` — only if the unmeasured read needs a change (D3; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-tasks/` — the loop-exit-guard and finalize-step fixtures (D1, D2, D4; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-execution-manifest/` — the compose fixtures (D3, D4; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/execute-task/` — the leaf-side unmeasured-arm fixture (D3; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-logging/` — the signal-scan fixtures, only if D5 touches `_signal_scan.py` (verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the landing of PLAN-LB-109, which is on the base branch.
- **Overlap check at emit.** The gate decides the pairing. `execute-task/SKILL.md` is also on the surface of PLAN-LB-110 (staged); if
  the gate reports 2 or more shared files with in-flight work, an overlap prompt is required, and this plan runs after the other.
- **Adjacent to** (left untouched): the lane skill (PLAN-LB-106, 108, 116), the finalize review gate (PLAN-LB-105).
- **Owed outside this plan, operator-run:** a harness sync after merge.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-117-execute-handback-fix.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

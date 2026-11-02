# PLAN-LB-109: A hand-back the execute workflow prescribes is recorded as a hand-back, not as an error

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-109-execute-prescribed-yield-not-error.md` and is queued as one row file,
> `queue/PLAN-LB-109.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's instruction of 2026-11-02 ("stage the corresponding plans, aggregate where sensible") from finding
> `lessons-routing-059`, graded high by operator ruling in the 2026-11-01 sweep. Its sources are two API-Sheriff lessons:
> `2026-10-12-16-007` (plan-24, PR #430) and `2026-10-12-07-007` (plan-25, PR #408). Every OBSERVED claim below was read at
> `0fb6a79b1`. **Each deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do not merge,
> narrow or rewrite them.** A claim that something fails at `0fb6a79b1` counts as evidenced only by a run against that tree.

## Objective

A phase-5 leaf sometimes reaches a build it must not run, because the build resolves to the orchestrator tier and exceeds the
per-task limit. The workflow tells the leaf to stop and hand the build back to the main context. The orchestrator then records
that prescribed hand-back as `error`, for three reasons that combine:

- the return is classified `voluntary_checkpoint`;
- the deterministic no-progress rule (B7) turns any `voluntary_checkpoint` into `error` when a task is in progress, no task was
  newly completed and more than 50,000 tokens were consumed;
- a task whose verification is owed to the orchestrator tier is held `in_progress` by design, so every such hand-back meets the
  rule.

Those false errors also feed the script-failure signal that decides whether lessons capture runs.

This plan gives the hand-back a declared signal of its own, and makes the no-progress rule exempt it deterministically. It keeps
the lessons signal to genuine stalls. It also lets planning detect a module whose test build always exceeds the per-task limit,
so that module builds once per deliverable instead of once per task.

## Deliverables

1. **The prescribed hand-back carries a declared signal and a termination cause of its own.**
   - Every phase-5 leaf return that hands a build to the orchestrator carries one explicit discriminator (working name
     `verification_handback: true`), next to a non-empty `pending_verify_steps[]`. This covers four returns: Step 11b, Step 11c,
     the leaf `running` hand-back, and a per-task verification that resolved to the orchestrator tier and was closed with
     `--verification-owed`. The discriminator is stated in the `phase-5-execute/SKILL.md` § Output contract.
   - `execution.md` § "Termination-cause classification" gains a row for this cause. A return carrying the discriminator is
     classified as that cause, never as `voluntary_checkpoint`. `DISPATCH_TERMINATION_CAUSES` in `manage-metrics.py` gains the
     member, so `record-dispatch-boundary` accepts it instead of rejecting it at argparse.
   - `phase-5-execute/SKILL.md` § "Forbidden: agent-initiated checkpoints" currently names `budget_yield` as "the one legitimate
     yield". That contradicts the orchestrator-tier yield the same file prescribes at § "Per-step `execution_tier`". The section
     names both yields, with the observable signals that set each apart from a forbidden checkpoint.
   - **Consumers of the boundary row stay unchanged.** The field they see is the `termination_cause` column of
     `work/metrics-dispatch-boundaries-5-execute.toon`. Its readers are `plan-retrospective/scripts/analyze-logs.py` (the
     voluntary-checkpoint polling detector and the dispatch-boundary columns) and `manage-metrics reconcile-ledgers`. One check
     per edge:
     - a file whose only rows carry the new cause;
     - a file that mixes the new cause with `voluntary_checkpoint`;
     - a file that carries neither;
     - two consecutive hand-back rows for the same task (a re-attach).

   *Done when:* `record-dispatch-boundary --termination-cause {new member}` succeeds; it fails at `0fb6a79b1`. A doc test finds
   the new cause in the termination-table rows of `execution.md` and in the `phase-5-execute/SKILL.md` return contract. The
   analyzer's polling detector does not count a run of hand-back rows as voluntary-checkpoint polling, and on the mixed fixture it
   counts exactly what it counts for the `voluntary_checkpoint` rows alone.

2. **The no-progress rule cannot reclassify a prescribed hand-back, and a script decides it, not prose.**
   - A deterministic verb evaluates the B7 predicate (`in_progress_count > 0 AND completed_tasks_delta == 0 AND consumed_tokens >
     50000`), instead of the orchestrator reading prose. The outline decides which verb owns it, either a mode of
     `loop-exit-guard` or a classification verb next to `record-dispatch-boundary`, and records why.
   - A return classified as the D1 cause never reaches the predicate. Independently of that, a task carrying
     `verification_owed: true` does not count toward the predicate's `in_progress_count`. `loop-exit-guard` reports owed tasks
     separately (count and ids). Its `continue`/`success` verdict is unchanged, because an owed task still blocks the clean exit.
   - The 50,000-token threshold stays, as do the `error` routing of a genuine stall and the decision-log line that carries all
     three predicate values. The rule is stated once: the restatement in `phase-5-execute/SKILL.md` § "B7" becomes a pointer, or
     the two texts are pinned equal by a test.
   - B7 in `execution.md` cites `§ "Other Errors" downstream`, a section that does not exist in that file. The citation is changed
     to name the section that actually holds the `error` retry and escalation path.

   *Done when:*
   - The plan-25 shape is classified as the D1 cause, not `error`; this fails at `0fb6a79b1`. That shape is one owed task
     `in_progress`, `completed_delta=0`, 536,031 tokens and `pending_verify_steps=[verify:module-tests]`.
   - An `in_progress` task with no owed marker and no `pending_verify_steps`, at the same delta and token count, is still `error`.
   - `loop-exit-guard`, on a plan whose only open task is owed, returns `continue` and reports the owed id separately.

3. **The lessons script-failure signal counts genuine stalls only.**
   - `phase-6-finalize/SKILL.md` item 4b, Signal 3, scans the work log for "`voluntary_checkpoint → error` reclassifications".
     B7 writes its reclassification to the decision log instead, as
     `(plan-marshall:phase-5-execute:no-progress) reclassified voluntary_checkpoint as error …`. The writer and the scanner are
     made to use one string in one log type, stated once and cited from `lessons-capture.md`.
   - A D1 hand-back is named as not lesson-bearing and never enters the count.
   - Signal 3 says it is "kept consistent with" the retrospective analyzer's failure-marker set. If that analyzer carries its own
     copy of the markers, the copy changes in the same commit.

   *Done when:* a fixture plan whose only phase-5 boundary rows are D1 hand-backs yields `signal_3_count == 0`. A fixture with one
   genuine B7 reclassification yields `signal_3_count == 1`. A doc test asserts that the marker B7 writes is the marker Signal 3
   scans for. The first and third fail at `0fb6a79b1`.

4. **A module whose test build always exceeds the per-task limit builds once per deliverable.**
   - The operator ruled on plan-25: one full module build per deliverable. Sometimes planning finds that a deliverable's per-task
     `module-tests` rung resolves to the orchestrator tier from a *measured* learned duration, not from the stamp used when nothing
     is measured. In that case only the deliverable's last task in its chain carries the owed rung, and the deliverable's other
     tasks close without the owed hold. Narrow units that resolve `per_task` still run inline per task, as `execute-task` Step 5
     (b) states.
   - The decision is recorded where the plan can read it, in a manifest field or a task-ladder stamp; the outline decides which.
     The leaf honours the recorded decision without re-deriving it.
   - A command key with no measurement keeps today's behaviour. The stamp is advisory and the live re-resolve still routes
     (`phase-5-execute/SKILL.md` § "Per-step `execution_tier`"), so a run that later measures below the limit is not forced to
     defer.

   *Done when:* a compose fixture with a module whose learned `module-tests` duration is above the ceiling, and a three-task
   deliverable, puts the owed rung on exactly one task: the last in the chain. The same fixture below the ceiling, or unmeasured,
   puts it on all three. Both fail at `0fb6a79b1`.

Split guard: D1–D3 ship together, because D1's cause is what D2 exempts and D3 discounts. D4 can be separated: if the outline
finds it needs phase-4 packing changes beyond a stamp, D4 splits into its own plan and D1–D3 proceed.

## Standing Constraints

- **Do not weaken the no-progress rule for a genuine stall.** The 50,000-token threshold, the three predicate values in the
  decision log and the `error` routing all stay. Only a declared, observable hand-back is exempt; free text such as "Returning
  control …" never is.
- **The leaf never runs, backgrounds or polls an orchestrator-tier build.** The `await-long-running` seam stays its only owner.
  Nothing here changes how `execution_tier` is resolved or the per-call ceiling.
- **The owed-verification hold stays** (PLAN-LB-47 D1). An owed task is not `done` before its build reports, and
  `loop-exit-guard` still refuses a clean exit while one is open.
- **Every count or set the plan asserts comes from an enumeration of the code, not a hand list.** This covers the causes, the
  readers of the boundary row and the marker classes. A test parametrized over `DISPATCH_TERMINATION_CAUSES` derives its values
  from the constant.
- **The run cannot exercise its own fix.** This plan runs in the runbook lane, which drives no phase-5 dispatch. Evidence is
  fixtures and tests run against `0fb6a79b1` and the head, never the run's own boundary rows.
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: the classification table defines the build hand-back as a `voluntary_checkpoint` — `execution.md` L207 (the
  `voluntary_checkpoint` row: "step ids when the return hands back an orchestrator-tier build") and L394 (trigger: "`status:
  blocked` / `voluntary_checkpoint` terminal payload carrying the owed steps in `pending_verify_steps[]`"). The leaf side
  prescribes the same yield — `phase-5-execute/SKILL.md` L224, L1145, L1190, L1097.
- OBSERVED: B7 fires on any provisional `voluntary_checkpoint` and reads only `in_progress_count`, `completed_tasks_delta` and
  `consumed_tokens`, never `pending_verify_steps` — `execution.md` L229-251 § "B7 — voluntary_checkpoint no-progress
  reclassification"; restated at `phase-5-execute/SKILL.md` L1360-1368.
- OBSERVED: an owed task is held `in_progress` with `verification_owed: True` — `manage-tasks/scripts/_cmd_step.py` L137-143 §
  `cmd_finalize_step`. The leaf passes `--verification-owed` exactly when task verification resolved to the orchestrator tier —
  `phase-5-execute/SKILL.md` L653-658 (Step 7). So `in_progress_count > 0` and `completed_delta == 0` hold by construction on
  every owed hand-back.
- OBSERVED: `loop-exit-guard` counts every `in_progress` task, owed or not, and reports no owed count —
  `manage-tasks/scripts/_tasks_query.py` L338-370 (the loop-exit-guard handler).
- OBSERVED: `phase-5-execute/SKILL.md` L1387 calls `budget_yield` "the one legitimate yield", while L224 prescribes the
  orchestrator-tier yield.
- OBSERVED: `DISPATCH_TERMINATION_CAUSES` has 13 members and none for a build hand-back —
  `manage-metrics/scripts/manage-metrics.py` L86-121.
- OBSERVED: Signal 3 counts "`voluntary_checkpoint → error` reclassifications" from the **work** log —
  `phase-6-finalize/SKILL.md` L916-927 (item 4b). B7 logs its reclassification to the **decision** log with the text "reclassified
  voluntary_checkpoint as error" — `execution.md` L243-247. The content sweep finds that text in `execution.md` only.
- OBSERVED: `execution.md` has no "Other Errors" section, although B7 cites one (L241) — the whole file was read.
- OBSERVED: none of PLAN-LB-26, PLAN-LB-47 and PLAN-LB-61 touched B7 or Signal 3 — their corpus specs were read. PLAN-LB-26 added
  the `pending_verify_steps` field (D4) and the owed hold (D5). PLAN-LB-47 made the owed hold flag-only (D1) and defined the
  `running` contract (D3). PLAN-LB-61 covered the triage store, the wait bound, the Intent renderer and the all-owned guard. This
  plan builds on their fields and does not redo them.
- HYPOTHESIS: the per-task verification hand-back (`execute-task` Step 5 (b), closed with `--verification-owed`) carries a
  `verify:module-tests` id in `pending_verify_steps[]`, since the field is defined over `phase_5.verification_steps` ids. Confirm
  at `execute-task/SKILL.md` Step 5 (b) and `phase-5-execute/SKILL.md` § Output (verify-at-outline). If it carries none, D1 must
  add it, or the owed marker alone keys D2.
- HYPOTHESIS: `completed_tasks_delta` is described as "read from the prior `record-dispatch-boundary` row", but that row may carry
  no done count. Confirm at `manage-metrics/standards/data-format.md` (the dispatch-boundary columns) and the row builder in
  `manage-metrics.py` (verify-at-outline).
- HYPOTHESIS: the `error` retry and escalation path that B7 means lives in `plan-marshall/standards/execution-recovery.md`
  (verify-at-outline).
- HYPOTHESIS: `analyze-logs.py` carries its own failure-marker set, which Signal 3 claims to mirror; the content sweep found no
  "reclassif" text in it. Confirm at `plan-retrospective/scripts/analyze-logs.py` and
  `plan-retrospective/references/logging-gap-analysis.md` (verify-at-outline).
- HYPOTHESIS: `architecture derive-verification` stamps the per-task verification ladder (its handler is in
  `manage-architecture/scripts/_cmd_client_handlers.py`), and `_stamp_phase_5_step_execution_tier` in
  `manage-execution-manifest` (`_manifest_validation.py` or `manage-execution-manifest.py`) stamps the compose-time tier. Confirm
  which of them owns D4's stamp (verify-at-outline).
- HYPOTHESIS: the API-Sheriff `integration-tests` build (~1140-1160 s) resolved to the orchestrator tier from a measured duration,
  not from the unmeasured default. This comes from the lesson and was not re-verified here (verify-at-outline if a fixture depends
  on it).
- Verify-first clause (D2): settle the per-task HYPOTHESIS above before choosing D2's key. If a per-task owed hand-back carries no
  step id, the exemption keys on the owed marker and D1 adds the id.
- Verify-first clause (D4): read where `execute-task` takes its per-task ladder before scoping. If deferring the rung needs
  packing or `depends_on` changes, split D4 out (see the Split guard).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — termination table L203-211, boundary template cause list L221, B7 L229-251, orchestrator-tier section L392-415 (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — return contract, § Forbidden checkpoints L1370-1387, B7 restatement L1360-1368, Step 7 (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — `DISPATCH_TERMINATION_CAUSES` L86-121 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` — loop-exit-guard owed count (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — § "Loop-Exit Guard" (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — item 4b Signal 3 L916-927 (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md` — Signal 3 description L58, L94 (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` — polling detector and marker set (verify-at-outline) (D1, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — cause list (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py` — tier stamp (verify-at-outline) (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` — derive-verification ladder (verify-at-outline) (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — Step 5 (b) hand-back (verify-at-outline) (D1, D4)
- OBSERVED: `test/plan-marshall/manage-metrics/test_manage_metrics_dispatch_termination_causes.py` (D1)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_dispatch_envelope_contracts.py` (D1, D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_loop_exit_guard.py` (D2)
- OBSERVED: `test/plan-marshall/test_lessons_capture_workflow.py` (D3)
- OBSERVED: `test/plan-marshall/plan-retrospective/test_analyze_logs_detect_voluntary_checkpoint_polling.py` (D1)
- OBSERVED: `test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py` (D4)

## Dependencies and Sequencing

- **Depends on:** none. This plan builds on PLAN-LB-26 (#1769), PLAN-LB-47 (#1778) and PLAN-LB-61 (shipped), and uses their
  `pending_verify_steps` field and owed hold unchanged.
- **Overlaps with PLAN-LB-87 (parked)** on four surfaces. If PLAN-LB-87 is un-parked, **sequence the two plans; never run them
  concurrently.**
  - `plan-marshall/workflow/execution.md`: LB-87 adds `--step-id` and drops literal zeros in the `record-dispatch-boundary`
    templates at L220-222 and L265-267. This plan edits the cause list in the same template at L221, and the rows and B7 next to
    it, so the edits collide in the text.
  - `manage-metrics.py`: LB-87 edits `record-dispatch-boundary`, `reconcile-ledgers` and `accumulate-agent-usage`. This plan
    edits the `DISPATCH_TERMINATION_CAUSES` constant, a different symbol in the same file.
  - `phase-6-finalize/SKILL.md`: LB-87 edits the boundary call site near L1196; this plan edits item 4b near L916.
  - `manage-execution-manifest/`: LB-87 D3 changes the finalize order; this plan's D4 changes the phase-5 tier stamp.

  Whichever plan runs second re-grounds its line references.
- **Overlaps with PLAN-LB-107** (staged on 2026-11-02 in the same act) on `phase-6-finalize/SKILL.md`, possibly. The gate decides
  the pairing.
- **Not touched:** PLAN-LB-86's `manage-metrics.py` reader functions. The gate will still ask about the shared file.
- **Adjacent to:**
  - `runbook-lane/SKILL.md`, which mentions no-progress once. It is not edited unless the outline finds that it restates B7.
  - The `await-long-running` seam and the resolution of `execution_tier`; both are left untouched.
  - The `running` hand-back contract (PLAN-LB-47 D3), which this plan consumes and does not change.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-109-execute-prescribed-yield-not-error.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

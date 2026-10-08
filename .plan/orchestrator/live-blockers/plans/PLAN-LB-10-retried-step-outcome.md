# PLAN-LB-10: A retried finalize step can record its outcome

epic: live-blockers
workstream: WS-01

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-22 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-10-retried-step-outcome.md` and is queued as one row file, `queue/PLAN-LB-10.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`manage-status mark-step-done` refuses every write whose outcome differs from the stored one unless the caller passes `--force`. A finalize step reaches that state on its ordinary path: it records `failed` or `loop_back`, is retried, succeeds, and its `done` is refused with `error: conflict`; nothing is written, the dispatcher's completion guard then halts the phase, and the run only continues when someone adds an undocumented `--force`. The mirror case is worse: a gate that was `done` and comes back red on a re-fire cannot record `failed`, so the stale `done` stays and the pipeline carries on past a red gate. One finalize needed the override three times (sync-baseline, push, automatic-review). `ci_verify` adds a false report on top: on green it issues the mark without `--force`, ignores the answer, and returns `step_marked_done: true` while the record still says `loop_back`. This plan makes the retry and re-fire transitions legal in the tool, makes `ci_verify` report what was written, and brings the step documents and the contract text in line. Carries forward process-compliance PLAN-21 deliverable D2 including its later widening to step-record transitions, and truthful-signals PLAN-TRUTH-170's `ci_verify` fold and the missing-`--force` sweep of its D1.

## Deliverables

1. **Retry and re-fire transitions are legal without `--force`.** In `cmd_mark_step_done`, replace the blanket "different outcome ⇒ `conflict`" rule with an explicit transition table. Legal without `--force`: from `failed` or `loop_back` to any outcome (a retry or a later round reporting its own result), and from `done` to `failed` or `loop_back` (a re-fired gate that is now red or has new findings). Every legal transition goes through the existing `_extend_firing_history` path, so the superseded firing stays in `prior_firings` and `firing_count` rises; nothing is lost by dropping the flag. All existing refusals that are about well-formedness stay exactly as they are and are evaluated first (`missing_head_at_completion`, `unknown_head_at_completion`, `unknown_yield_name`, the `--loop-back-target` pairing, the display-detail checks). `--force` keeps working for every transition, so callers that still pass it see no change. The transitions that remain refused without `--force` are settled by the verify-first clause below. *Done when:* a test walks `failed → done` through the documented call with no `--force` and asserts `status: success`, `changed: true`, `previous_outcome: failed`, `firing_count: 2` (red before the change: `error: conflict`); companion tests cover `loop_back → done`, `failed → skipped`, `failed → loop_back`, `done → failed` and `done → loop_back`; a test asserts that a transition left outside the table still returns `conflict` and writes nothing.

2. **`ci_verify` reports the write, not the path taken.** `_run_mark_step_done` returns the proxy result and the green branch of `verify` reads it: `step_marked_done` is `true` only when the mark returned `status: success`; otherwise it is `false`, the result carries the mark's `error` and `message` (for example `step_mark_error: conflict`), and the top-level result is not a clean green — the caller must be able to tell "CI is green and the step is recorded" from "CI is green and the record was refused". After D1 the green mark over a stored `loop_back` or `failed` succeeds by itself; this deliverable covers every other refusal (`missing_head_at_completion` when HEAD could not be resolved, `unknown_yield_name`, an unreachable executor). *Done when:* a test injects a `mark_done_runner` that returns `{status: error, error: conflict}` and asserts `step_marked_done is False` and the error is surfaced (red before the change: `True`); the existing green-path tests still assert `True` with a succeeding stub; an end-to-end test over a real status file with a stored `loop_back` record shows the record reads `done` after a green `ci_verify` run.

3. **The dispatcher's own `failed` records land.** The finalize dispatcher writes `--outcome failed` itself in three places (per-agent timeout, the missing-terminal-record guard, the `wait_failed` precondition). Each can land on a record that already says `done` or `loop_back` from an earlier firing. With D1 these writes succeed; this deliverable adds the missing instruction to parse the result of each such call and to stop with the tool's message when it is still refused, instead of continuing as if the failure had been recorded. *Done when:* each dispatcher-side `mark-step-done … --outcome failed` block in `phase-6-finalize/SKILL.md` is followed by a `status` parse, and a doc-contract test pins that.

4. **The contract text and the step documents match the tool.** Rewrite the `--force` paragraphs in `phase-6-finalize/standards/external-step-contract.md` (today: "`--force` is REQUIRED whenever the outcome being written DIFFERS from the one already stored") and the `conflict` / `--force` text in `manage-status/SKILL.md` and the module docstring of `_cmd_mark_step.py` to state the transition table. Then sweep every finalize step document's terminal `mark-step-done` calls and publish the population in the PR body: for each re-fireable step, each terminal branch, whether it carries `--force`, and whether it still needs it after D1. Flags that are now redundant may stay; a branch that performs a transition the table does not allow without `--force` and lacks the flag is fixed. *Done when:* a derived test enumerates the terminal `mark-step-done` invocations in the step documents the finalize registry discovers and asserts that none performs a transition outside the unforced table without `--force`; the population table is in the PR body with its size.

## Claim Labels

- OBSERVED: any write whose outcome differs from the stored one returns `{status: error, error: conflict, existing_outcome, requested_outcome}` and writes nothing unless `args.force` is set; there is no per-transition distinction — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` § `cmd_mark_step_done` lines 655-668, at HEAD `6edefac32`
- OBSERVED: the comment directly below that check describes "the outcome-changing re-fire path (loop_back → done, and the --force overwrite)" as if `loop_back → done` reached it unforced; it does not, the conflict return above it fires first — read at `_cmd_mark_step.py` lines 684-686
- OBSERVED: an outcome-changing write already preserves the superseded firing (`prior_firings`, `firing_count`), so allowing a transition without `--force` discards no history — read at `_cmd_mark_step.py` § `_extend_firing_history` (lines 742-791) and its call at line 687
- OBSERVED: `_run_mark_step_done` issues `mark-step-done --outcome done --display-detail … --head-at-completion …` with no `--force` — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` lines 389-417
- OBSERVED: the green branch calls `mark_done_fn(...)`, discards its return value, and returns `'step_marked_done': True` unconditionally — read at `ci_verify.py` § `verify` lines 629-648
- OBSERVED: the contract document tells every external step that `--force` is required whenever the written outcome differs from the stored one, and names "a re-fireable step's clean branch overwriting the `loop_back` its own previous round stored" as the canonical case — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md` lines 37-45 and 59
- OBSERVED: most step documents do not follow that instruction. Counting lines that contain `--outcome done` against lines that contain `--force` per document: `workflow/sonar-roundtrip.md` 6/0, `workflow/lessons-capture.md` 6/0, `automatic-review/SKILL.md` 5/0, `workflow/create-pr.md` 4/0, `standards/finalize-step-sync-baseline.md` 3/0, `workflow/adr-propose.md` 3/0, `standards/record-metrics.md` 3/0, `.claude/skills/finalize-step-plugin-doctor/SKILL.md` 6/0, `.claude/skills/finalize-step-review-retrospective/SKILL.md` 6/0; `standards/branch-cleanup.md` 10/11 and `workflow/pre-submission-self-review.md` 6/12 do carry it — counted by text search at HEAD; a line count, not a per-branch reading
- OBSERVED: the dispatcher writes `--outcome failed` without `--force` at the per-agent timeout, at the missing-terminal-record guard and at the `wait_failed` precondition — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` lines 995-998, 1159-1162 and 502
- OBSERVED: the existing `ci_verify` tests assert `step_marked_done is True` with a stub runner that cannot refuse — read at `test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py` lines 264-270
- HYPOTHESIS: `sync-baseline`, `push` and `automatic-review` are the steps whose `failed → done` retry was refused in one finalize, forcing `--force` three times — reported by a run, not reproduced; confirm/refute by driving `cmd_mark_step_done` over a stored `failed` record with each step's documented terminal call from `standards/finalize-step-sync-baseline.md`, `standards/push.md` and `automatic-review/SKILL.md` (verify-at-outline)
- HYPOTHESIS: a `ci_verify` green run left a `loop_back` record unchanged across two invocations while returning `step_marked_done: true` — observed in a consumer repository run, consistent with the two OBSERVED code facts above; confirm/refute with the end-to-end test of D2 (verify-at-outline)
- HYPOTHESIS: no reader of `status.metadata.phase_steps` depends on a `conflict` refusal to detect a re-fire — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_assert_step_recorded.py` and the item-1 re-entry check in `phase-6-finalize/SKILL.md` (verify-at-outline)
- Verify-first clause: before scoping D1, settle the residual refusals. Proposed table: `failed → *` and `loop_back → *` legal; `done → failed` and `done → loop_back` legal; `done → skipped`, `skipped → *` and the legacy bare-string entry stay refused without `--force`. Check each proposed-legal transition against the readers of the record (`_cmd_assert_step_recorded.py`, `plan-marshall/scripts/_invariants.py` § `_capture_phase_steps_complete`, `phase-6-finalize/scripts/verdict_currency.py`) for one that would mis-read a now-silent overwrite; a transition a reader cannot tolerate stays refused and the plan records why
- Verify-first clause: before scoping D4's sweep, derive the re-fireable population from the finalize step registry (the discovery path `_cmd_mark_step.py` § `_derive_phase_roster` uses) rather than from the file list above, so project-local steps under `.claude/skills/finalize-step-*` and bundle steps are both covered

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — transition table in `cmd_mark_step_done`, module docstring (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — `mark-step-done --force` help text (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — § mark-step-done: conflict rule, `--force`, error table (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — `_run_mark_step_done` result read, `step_marked_done` derivation, module docstring (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — dispatcher-side `--outcome failed` blocks get a result parse (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md` — `--force` paragraphs (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md` — how the step reads `step_marked_done` and the new error field (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/` — step documents whose terminal branch the sweep finds outside the unforced table; expected to be few or none after D1 (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/` — same sweep, workflow-form step documents (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — same sweep, the review step's terminal branches (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — same sweep, project-local step (six `--outcome done` lines, no `--force`) (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-review-retrospective/SKILL.md` — same sweep, project-local step (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — same sweep, project-local step (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — only if it restates the `--force` rule (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-status/test_mark_step_done_mark_step_force.py` — existing forced-overwrite tests stay green; conflict-residue test added here or beside it (D1)
- HYPOTHESIS: `test/plan-marshall/manage-status/test_mark_step_done_retry_transitions.py` — new transition-table tests (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_core.py` — refused-mark test and end-to-end record test (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py` — `step_marked_done` assertions follow the derived value (D2)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_step_terminal_mark_transitions.py` — new derived sweep test over the registry's step documents (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-09 (`manage-status/scripts/`, `phase-6-finalize/standards/archive-plan.md` via the sweep, `phase-6-finalize/SKILL.md`; if this plan lands first, LB-09 can record `failed` over `done` on a refused archive without `--force`); PLAN-LB-02 (`phase-6-finalize/SKILL.md`, `workflow/pre-submission-self-review.md` if the sweep touches it, `.claude/skills/finalize-step-*`); PLAN-LB-05 (`standards/ci-verify.md`, `standards/branch-cleanup.md`, `automatic-review/SKILL.md`); PLAN-LB-11 (`phase-6-finalize/SKILL.md`, a different item); PLAN-LB-18 (`automatic-review/SKILL.md`). All are document-section overlaps except LB-09's; sequence with LB-09 and LB-02, and re-run the sweep after whichever lands second.
- Adjacent to: `manage-status/scripts/_cmd_assert_step_recorded.py` is read for the verify-first clause and not edited; the firing-history shape (`prior_firings`, `firing_count`) is reused unchanged.
- Left out on purpose (the rest of the two source specs): process-compliance PLAN-21 D1 (dispatch roster), the re-stamp firing-count part of D2, D3 (`verdict_inputs`), D4 (plugin-doctor realized footprint), D5 (dispatch-boundary records); truthful-signals PLAN-TRUTH-170 D0, D2 (`[OUTCOME]` emission), D3 (`display_detail` ceiling), D4a (derived `head_at_completion`), D4b (`assert-step-recorded --require-terminal` on a stale record), D5 (staging allowlist — that is PLAN-LB-11) and the `pr_number` fold.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-10-retried-step-outcome.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

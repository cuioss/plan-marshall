# WS-01: Finalize and Phase Gates

epic: live-blockers

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-finalize-gates.md` and is tracked in the
> `workstreams[]` field of the epic header, `status.json`. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Gates and steps in the plan lifecycle that block a correct run, report a false result or cannot proceed without an operator override. The workstream closes when a plan can pass refine, execute and finalize without `--force`, `--override` or a hand-set field.

## Scope

- In scope: the phase handshake, the pre-push and freshness gates, pre-submission self-review, triage and fix tasks, the scope-creep guard, the findings store, archive and merge gating, finalize step records, commit staging
- Out of scope: build execution and Maven parsing (WS-02); the orchestrator launch gate (WS-03); harness sync and CI (WS-04); review-bot behaviour (WS-05)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-LB-01-push-freshness-gate | staged | The push freshness gate accepts the pre-push gate's own green builds |
| PLAN-LB-02-self-review-convergence | staged | Pre-submission self-review converges and stops re-running settled steps |
| PLAN-LB-03-self-review-consumer-repos | staged | Self-review ends cleanly on a diff no surfacer covers |
| PLAN-LB-04-light-lane-refine-boundary | staged | Light-lane plans pass the refine boundary without overrides |
| PLAN-LB-05-unrunnable-waits | staged | Wait procedures the harness can actually run; no false timeouts |
| PLAN-LB-06-triage-fix-task-loop | staged | Triage can create fix tasks and they get scheduled |
| PLAN-LB-07-scope-creep-guard | staged | The scope-creep guard records its finding and measures the plan's own changes |
| PLAN-LB-08-triage-survives-recheck | staged | Re-running a quality check keeps the triage already done |
| PLAN-LB-09-pending-findings-gate | staged | Pending findings block archive and merge for real |
| PLAN-LB-10-retried-step-outcome | staged | A retried finalize step records its true outcome |
| PLAN-LB-11-finalize-staging-allowlist | staged | Finalize commits are staged mechanically, not by prose |

## Sequencing and Surface Notes

- LB-02 and LB-03 share `pre-submission-self-review.md`; sequence them.
- LB-05 and LB-09 both edit `phase-6-finalize/standards/branch-cleanup.md` in different sections.
- LB-06 and LB-07 both sit in the execute loop; LB-06 edits `execution.md`, LB-07 does not.
- LB-10 and LB-02 both touch finalize step records (`_cmd_mark_step.py` against the loop counter in `phase-6-finalize/SKILL.md`).

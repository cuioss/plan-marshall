envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:44:02Z

# phase-5 scope-creep guard crashes: invalid finding type + pre-rebase diff base

**Observed (plan-12-tool-triage, finalize → 5-execute loop-back, TASK-12):** `phase-5-execute:scope_creep_check check --plan-id plan-12-tool-triage` exited 1 with `status: error, error: finding_persist_failed`, halting the whole fix envelope before any task completed.

1. **Invalid finding type.** The guard persists its finding as `--type scope_creep_warning`; the findings store rejects it: `Invalid finding type: scope_creep_warning. Must be one of ('bug', 'improvement', 'anti-pattern', 'triage', 'tip', 'insight', 'best-practice', 'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'arch-constraint', 'pr-comment', 'pr-comment-overflow')`. phase-5-execute SKILL Step 6.5 documents `manage-findings qgate add --type scope_creep_warning` as the persisted shape — the documented contract and the store's type vocabulary disagree, so EVERY over-threshold run crashes. The guard's `could_not_look` / `error` shape discipline is careful; the one path that actually fires is the broken one.
2. **Stale diff base.** The guard diffs `plan_creation_sha..HEAD`. After `finalize-step-sync-baseline` rebased the branch onto `origin/main`, that base predates the rebase, so the diff sweeps in upstream + `.plan/orchestrator/**` commits the plan never made: `residual_count: 738` (threshold 5). Any plan whose branch is rebased (i.e. every finalize loop-back into execute) trips the guard on files it did not touch.

**Operator decision:** treat guard errors as non-blocking for this run (logged as WARNING per task). The guard provides no signal on loop-back re-entries until both are fixed.

**Suggested fix:** register `scope_creep_warning` in the finding-type set (or map it to an existing type), and diff against the merge-base with the recorded base branch (or re-anchor the baseline on rebase) rather than the raw `plan_creation_sha`. Add a test that runs the guard after a rebase.

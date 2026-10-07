envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:17:49Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=script_failure_analysis,request_result_alignment,artifact_consistency

# Finalize steps at and after branch-cleanup lose the plan's own new script flags

## Context

This plan's D3 added a repeatable `--fact KEY=VALUE` flag to `manage-status mark-step-done`, and D4 wired `branch-cleanup.md` to emit it. At 12:01:21Z the plan's own `branch-cleanup` step ran:

```
mark-step-done --plan-id finalize-step-records-are-prose-not-facts --phase 6-finalize \
  --step branch-cleanup --outcome done \
  --fact action=noop --fact upstream_commit_count=0 --fact merge_mechanism=merge_queue \
  --fact work_performed=true --display-detail "merged via queue, main pulled, branch + worktree removed"
```

and was rejected with `manage-status.py: error: unrecognized arguments: --fact action=noop --fact ups...` (exit 2).

The earlier `finalize-step-sync-baseline` step, which ran at 09:06Z with cwd pinned to the worktree, recorded its facts successfully (`facts: {action: noop, upstream_commit_count: "0", work_performed: "true"}` is present in status.json). So the flag works — it just was not reachable from where `branch-cleanup` ran.

Verified at retrospective time: `mark-step-done --help` against the installed executor lists no `--fact`, while `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` on merged main implements `_parse_facts` and threads `facts` through `_build_entry`.

## Root cause

`branch-cleanup` removes the worktree as part of its own work, and its `mark-step-done` call fires afterwards. Once the worktree is gone, script resolution falls back to the main-checkout executor, which is bound to the plugin cache — and the cache is synced by `project:finalize-step-sync-plugin-cache`, which is ordered *after* `branch-cleanup`. So every step at or after `branch-cleanup` executes against a bundle snapshot that predates the plan's own merge.

This is the same ordering archetype as the PLAN-10 landing (#1036): a plan that changes a finalize-time component cannot have that change exercised by its own finalize. Here it is sharper, because the affected component is the one the plan exists to fix.

## Proposed action

Pick one, in preference order:

1. Move the `mark-step-done` call for `branch-cleanup` to before the worktree removal, so the step records its facts while the plan's own code is still reachable.
2. Have the finalize dispatcher detect the capability cliff explicitly: before any step at or after `branch-cleanup`, assert that the flags the step's `records_facts` declaration needs are present in the resolved script's argparse surface, and fail loudly rather than silently.
3. Reorder `project:finalize-step-sync-plugin-cache` ahead of `branch-cleanup`, so the merged bundle is live for the tail of finalize.

Option 1 is the narrowest and does not perturb the sync ordering.

## Evidence

- aspect: script_failure_analysis — `anti-pattern,invented_flag,"plan-marshall:manage-status:manage-status",mark-step-done,2,"2026-08-02T12:01:21Z"` (classified `invented_flag`; it is not invented, it is unreachable)
- aspect: request_result_alignment — D4 `fulfilled_in_source_not_in_own_run`
- `logs/script-execution.log:1304-1307` — the rejection with full argv
- `logs/script-execution.log:1308` — the facts-free retry that succeeded 13 seconds later
- `status.json` `metadata.phase_steps["6-finalize"]["branch-cleanup"]` — `display_detail` only, no `facts` key
- `status.json` `metadata.phase_steps["6-finalize"]["finalize-step-sync-baseline"]` — carries `facts`, proving the flag works pre-removal

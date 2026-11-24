envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:41Z

component=plan-marshall:phase-5-execute
category=bug
title=phase-5-execute Step 10a documents a manage-change-ledger flag that does not exist (5 recurrences)
source_lesson=2026-11-23-14-010
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# phase-5-execute Step 10a documents a manage-change-ledger flag that does not exist (5 recurrences)

# Candidate lesson: phase-5-execute Step 10a documents a manage-change-ledger flag that does not exist (5 recurrences)

Source: [ERROR] work-log lines from plan-marshall:phase-5-execute, `manage-change-ledger append` exit_code=2, at 08:02:17Z, 10:35:32Z, 11:09:30Z, 11:40:37Z and 14:01:00Z on 2026-11-23. Every time the cause was `--changed-paths-file` not declared, and every time a retry with `--changed-paths` succeeded. One entry names the cause directly: "--changed-paths-file documented in phase-5-execute Step 10a is not declared". These lines use the per-phase [ERROR] form rather than the execute-script `script_failure` marker, so they are not counted in signal_script_failure_clusters_count, but they are the most frequent failure of the run.

Component: plan-marshall:phase-5-execute (Step 10a, change-ledger append after a per-deliverable commit); plan-marshall:manage-change-ledger

## What happened

The workflow prose tells the agent to pass the changed-path list through a file (`--changed-paths-file`). The script's argparse declares only `--changed-paths`. Each per-deliverable commit therefore cost one rejected call and one retry, and every rejection wrote an ERROR line.

## Candidate rule

Align the doc and the script in one change: either add `--changed-paths-file` to `manage-change-ledger append`, which is preferable because a path list in a file keeps long lists out of the shell, or correct Step 10a to the declared `--changed-paths`. Add the call to the plugin-doctor `manage-invocation-invalid` coverage so that this drift fails at edit time.

## Recurrence folded in (candidate message 013 of the same plan)

The same defect was reported a second time by the plan's own retrospective: at least six phase-5-execute dispatches (envelopes 1 and 2, fix rounds TASK-10..13, TASK-14, TASK-15, TASK-16/17) called `manage-change-ledger append --changed-paths-file` as Step 10a documents, got exit 2, and retried with a hand-built comma-separated `--changed-paths`. The retrospective counted 12 work-log errors and 5 script errors. A third option: a `--from-commit SHA` mode that derives the paths from `git diff-tree` would remove the hand-built list entirely.


## Recurrence in a later plan (plan-20-leftover-fixes-2 and plan-11-store-anchoring-signed, inbox plan-20-leftover-fixes-2-012, plan-11-store-anchoring-signed-007)

Seen again in both plans that ran after the lesson was filed. plan-20: three work-log errors (2026-11-23T18:26:50Z, 18:54:33Z, 19:11:53Z), each per-deliverable ledger append rejected `--changed-paths-file` as undeclared and was retried with `--changed-paths`; the agent itself named the drift between the workflow document and the installed script (plan-marshall 0.1.2184). plan-11: the same flag was rejected at 2026-11-23T17:37:46Z. Total since this lesson was written: nine rejections across three plans, still unfixed in either direction.

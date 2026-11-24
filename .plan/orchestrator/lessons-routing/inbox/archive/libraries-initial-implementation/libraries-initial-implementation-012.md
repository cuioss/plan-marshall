envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:07Z

component=plan-marshall:manage-change-ledger
category=bug
title=Docs prescribe manage-change-ledger append --changed-paths-file; the script accepts only --changed-paths
source_lesson=2026-11-18-13-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Docs prescribe manage-change-ledger append --changed-paths-file; the script accepts only --changed-paths

# Candidate lesson: workflow docs prescribe `manage-change-ledger append --changed-paths-file`; the script accepts only `--changed-paths`

- Source signal: plans git-core-import (inbox git-core-import-004) and plan-18-leftover-fixes (inbox plan-18-leftover-fixes-013). Doc/script drift in the plan-marshall bundle, not a project defect. Four execute dispatches of the second plan hit the same argparse rejection.

## What happened

The phase-5 workflow (Step 10a) tells the leaf to record changed paths through `manage-change-ledger append --changed-paths-file <file>`. The installed script has no such flag and accepts only `--changed-paths` with a comma-separated list. Each leaf hit the rejection and retried with the comma-joined form (four hand-joined path lists in one plan).

## Why it matters

The file form exists so that a long path list never goes through the shell argument vector. The inline fallback defeats that purpose for any large footprint (the first plan changed 26+ paths).

## Candidate rule

- Preferred: add `--changed-paths-file PATH` to `append`, which matches the Write-then-pass-file pattern used elsewhere. Otherwise correct every doc reference to `--changed-paths`.
- Add the `append` canonical-invocation block to the plugin-doctor `manage-invocation-invalid` scan so the drift is caught at edit time.


## Recurrence in the third plan (git-worktrees-import, inbox plan-03-git-worktrees-import-016)

- Source signal: two work-log ERROR lines (phase 5-execute) that do not use the `script_failure notation=` marker, so the signal scan did not count them.
- Both per-deliverable ledger appends of the plan failed with exit code 2 because `--changed-paths-file` is documented in phase-5-execute Step 10a but not declared by the parser; each was retried with `--changed-paths` and succeeded.

Same root cause and same corrective rule as above: the third plan in a row hit the documented-flag-not-declared rejection. Align Step 10a with the argparse surface, or add the file flag.


## Recurrence in the fourth plan (git-worktrees-hardening, inbox plan-19-git-worktrees-hardening-008)

- Source signal: two work-log ERROR lines (phase 5-execute, after the TASK-2 and the TASK-11 commit), again not counted as `script_failure`: `manage-change-ledger append` exit_code 2, `--changed-paths-file` undeclared; documented in phase-5 Step 10a; each retried with `--changed-paths`. Installed plan-marshall 0.1.2157/0.1.2159.

Same root cause and same corrective rule: the fourth plan in a row hit the documented-flag-not-declared rejection. Align Step 10a with the argparse surface, or add the file flag; cover the call with a canonical-invocation check that walks `--help`.


## Recurrence in the fifth plan (git-core-incore-write-cas, inbox git-core-incore-write-cas-016)

- Source signal: plan-retrospective (chat-history-analysis, log-analysis), component `plan-marshall:phase-5-execute`, confidence high.
- Two separate phase-5 execute envelopes of the plan (the envelope-1 resume running TASK-2 to TASK-5, and the review-fix envelope running TASK-010/011) each reported that the Step 10a `manage-change-ledger append --changed-paths-file` call was rejected as an unknown flag, retried with the comma-separated `--changed-paths`, and logged the rejection. `errors_work` was 5 against 3 classified script failures: the plan's script-failure analysis did not list this rejection, so the lessons-capture step did not carry it either.
- Every deliverable commit pays one failed call plus a retry.

Same root cause and same corrective rule: align the Step 10a invocation with the `append` parser (document `--changed-paths`, or add `--changed-paths-file` to the parser) and add the invocation to the canonical-invocations guard so the drift fails a test. New point: also check why script-failure-analysis did not classify this rejection.


## Recurrence in the sixth plan (plan-05-git-core-merge-read-notes, inbox plan-05-git-core-merge-read-notes-007)

- Source signal: work-log `[ERROR]` line in 5-execute (2026-11-19T17:02:06Z), after the TASK-11 per-deliverable commit: `Script plan-marshall:manage-change-ledger:manage-change-ledger append failed: exit_code=2, args=--changed-paths-file rejected (installed verb declares --changed-paths)`.
- The line was logged in the plain `failed:` form, not the `script_failure` marker, so the dispatcher's script-failure cluster count and the signal scan do not see it (the same gap lesson message 016 of the previous plan named).

Same root cause and same corrective rule: make the workflow docs and the verb agree (add `--changed-paths-file` to `append`, which also fits a long path list and the project's no-multi-line-shell rule, or fix every doc reference to `--changed-paths`), and check that this error line form is counted by `signal-scan`.


## Recurrence in the seventh plan (implement-plan-06-build-guards, inbox implement-plan-06-build-guards-011)

- Source signal: work-log rejections in 5-execute, not counted by the script-failure scan (plain `failed:` form): `manage-change-ledger append --changed-paths-file` rejected by the worktree executor (exit 2, unknown flag) at 2026-11-19T22:01:51Z and 2026-11-20T06:39:14Z, retried with `--changed-paths` both times.
- The message adds a version-skew hypothesis: two bundle versions (0.1.2167 and 0.1.2171) were both present in the run, so the worktree executor may resolve a different bundle than the main checkout. The same message lists a third flag rejection of the same class: `architecture search --content ... --module git-worktrees` (unknown flag `--module`), retried without it.

Same root cause and same corrective rule as above (documents and the verb disagree about `--changed-paths-file`). New point to check: whether the worktree resolves an older plan-marshall bundle than the one the workflow docs describe, and quote flags from the live `--help` of the executor in use.


## Recurrence in the eighth plan (plan-07-store-module-registry-spi, inbox plan-07-store-module-registry-spi-006 and -007)

- Source signal: three phase-level `[ERROR]` lines in the work log (2026-11-20T08:50:59Z, 09:15:07Z, 11:20:47Z): `manage-change-ledger append failed: exit_code=2, args=--changed-paths-file (unknown flag; use --changed-paths)`. Every per-deliverable commit of the plan hit the rejection and was retried with `--changed-paths`. The lines carry the phase-level form, so signal-scan counted no script_failure cluster for them (the gap this lesson already names).
- The leaf followed the documentation (phase-5-execute Step 10a and the execution.md recovery text), so this is drift between documents and verb, not an agent mistake. Message -007 generalises it: dispatched leaves hit documented-versus-installed executor mismatches more than once per run, and each leaf rediscovers the same one because it has no memory of the previous leaf's retry.

Same root cause and same corrective rule. New rule to add: a leaf that finds a documented call the installed executor rejects records the drift once (a finding or an inbox candidate), so the next leaf of the same plan does not repeat the failed call and the documentation is corrected at the source. Eighth plan in a row without the correction.


## Recurrence in the ninth plan (plan-21-merge-worktrees-into-core, inbox plan-21-merge-worktrees-into-core-005)

- Source signal: two phase-5-execute work-log `[ERROR]` lines (2026-11-20T15:57:45Z and 16:40:28Z), again in the plain `failed:` form that the script-failure scan does not count: `manage-change-ledger append` exit 2 on the undeclared `--changed-paths-file`, retried with `--changed-paths`. Ninth plan in a row without the correction.

Same root cause and same corrective rule (the documents and the verb disagree). The same message also reports `manage-findings qgate query` (a verb that is not registered) and `qgate list` without its required `--phase`: see lesson 2026-11-18-13-003.


## Recurrence in the tenth plan (plan-08-store-drafts-save, inbox plan-08-store-drafts-save-002)

- Source signal: two phase-5-execute `[ERROR]` lines (2026-11-20T19:15:27Z and 19:38:23Z) attributed to the phase notation, not to the change-ledger notation: `manage-change-ledger append` exit 2, `--changed-paths-file` unknown flag, "documented in phase-5 SKILL Step 10a, not declared by verb". Three separate execute leaves hit it, and the finalize workflow documents the same flag.

Same root cause and same corrective rule (the documents and the verb disagree). Tenth plan in a row without the correction; add a doc-versus-`--help` check (the `manage-invocation-invalid` class) over the Step 10a block and the finalize doc so the next drift is caught before a leaf runs it.


## Recurrence in the eleventh plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-005)

- Source signal: two phase-5-execute `[ERROR]` lines (2026-11-21T13:59:19Z after the TASK-2 commit, 2026-11-21T14:50:39Z after the TASK-9 commit): `manage-change-ledger append --changed-paths-file` rejected, exit 2, as phase-5-execute 0.1.2181 documents it. The lines use the plain `Script ... failed` form, so `signal-scan` did not count them.
- New point: one TASK-4 ledger row was first written with `commit_sha=HEAD` instead of the resolved SHA and a corrected row followed it. `append` should reject a non-hex `commit_sha`.

Same root cause and rule (the documents and the verb disagree); add the doc-versus-`--help` check before a plan starts, and validate `commit_sha` in `append`.


## Recurrence in the twelfth plan (plan-23-forms-hardening, inbox plan-23-forms-hardening-005)

- Source signal: script failure, notation `plan-marshall:manage-change-ledger:manage-change-ledger` (work log 08:43:09, 09:16:17, 11:05:23 for `--changed-paths-file`; script log 09:43:34 for space-separated paths after `--changed-paths`). The installed `append` (plan-marshall 0.1.2184, checked with `append --help`) declares only `--changed-paths CHANGED_PATHS`, "comma-separated git-sourced changed paths"; once the paths were passed space-separated and argparse rejected the extra positional.
- Same root cause and rule (the documents and the verb disagree; the capture did not trace which document names the flag): align the doc with the installed surface, or ship the flag, which suits long path lists and keeps them out of the shell. Twelfth plan in a row; every deliverable commit pays one rejection until then.

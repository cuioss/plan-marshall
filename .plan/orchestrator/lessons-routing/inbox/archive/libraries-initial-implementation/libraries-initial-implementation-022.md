envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:14Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
title=manage-solution-outline get-deliverable: the typed-ID flag is --deliverable-number, not --number
source_lesson=2026-11-19-06-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# manage-solution-outline get-deliverable: the typed-ID flag is --deliverable-number, not --number

# Candidate lesson: `manage-solution-outline get-deliverable --number` instead of `--deliverable-number`

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-006), script_failure cluster `plan-marshall:manage-solution-outline:manage-solution-outline` (phase 5-execute, first entry).

## What happened

```
script_failure notation=plan-marshall:manage-solution-outline:manage-solution-outline exit_code=2 failure_kind=argparse_rejection
detail=`--number` is not declared for `... get-deliverable`: ['deliverable-number', 'plan-id']
```

The execute agent shortened the typed-ID flag `--deliverable-number` to `--number`.

## Candidate rule

Find where phase-5-execute / execute-task tells the agent to read a deliverable and quote the canonical `get-deliverable --plan-id ... --deliverable-number N` form verbatim there; the typed-ID flag naming rule (argument-naming.md) is the guard this call missed. Same family as the invented-verb and rejected-flag lessons (`qgate query`, `manage-findings list --limit`): the agent paraphrases a surface it has not read.


## Recurrence in the next plan (git-core-incore-write-cas, inbox git-core-incore-write-cas-011)

- Source signal: script_failure cluster `plan-marshall:manage-solution-outline:manage-solution-outline` (work-log line 6a94f5, 2026-11-18T16:01:12Z, first phase-5-execute dispatch, before TASK-001 step 1, exit 2, argparse rejection).
- `manage-solution-outline get-deliverable --number N` was called again; the declared flags are `--plan-id` and `--deliverable-number`.

Same root cause and same corrective rule: the reading step in phase-5-execute / execute-task should quote `get-deliverable --plan-id {plan_id} --deliverable-number {N}` verbatim from the canonical invocations. Second plan in a row.


## Recurrence in the third plan (plan-07-store-module-registry-spi, inbox plan-07-store-module-registry-spi-004)

- Source signal: script_failure marker (work log, 2026-11-20T09:39:13Z, phase 5-execute re-entry), notation `plan-marshall:manage-solution-outline:manage-solution-outline`, argparse_rejection, exit 2: a phase-5 leaf called `get-deliverable --number N`; the verb declares only `--plan-id` and `--deliverable-number`. The call was retried.

Same root cause and same corrective rule: quote the flag from the canonical invocation block at the point where phase-5-execute / execute-task reads a deliverable. Third plan in a row, so the correction belongs in the shared text the leaf is given and not in a per-run reminder.


## Recurrence in a later plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-004)

- Source signal: script-failure cluster `plan-marshall:manage-solution-outline:manage-solution-outline` (1 `script_failure` row, 2026-11-21T14:15:19Z, `argparse_rejection`): at phase 5-execute re-entry `get-deliverable --number N` was rejected; the declared flags are `--plan-id` and `--deliverable-number`.

Same rule: typed-ID flags carry the entity name (`--deliverable-number`, `--task-number`, `--lesson-id`); a bare `--number` or `--id` is never declared on a manage-* script.


## Recurrence in a third plan (plan-23-forms-hardening, inbox plan-23-forms-hardening-004)

- Source signal: script failure, notation `plan-marshall:manage-solution-outline:manage-solution-outline` (script log 08:29:53, 08:47:37, 09:33:12; `argparse_rejection`, exit 2): three separate phase-5 envelopes called `get-deliverable --plan-id P --number N`; the verb declares `--deliverable-number` and `--plan-id` only. Each time the leaf retried correctly within seconds, but the same wrong flag came back in every new envelope, so the lesson does not carry over from one envelope to the next.
- Preferred fix: the phase-5 workflow text that leads to this call quotes the canonical `get-deliverable --plan-id P --deliverable-number N` form verbatim (an alias `--number` would conflict with the typed-ID flag naming standard).


## Recurrence in a later plan (plan-20-leftover-fixes-2, inbox plan-20-leftover-fixes-2-010)

`--number` passed to `manage-solution-outline get-deliverable` again (2026-11-23T18:29:07Z, at phase-5 re-entry); declared flags are `deliverable-number` and `plan-id`. The typed-ID convention names the entity in the flag.

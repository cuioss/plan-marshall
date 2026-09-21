envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:20Z

component=plan-marshall:plan-marshall
category=bug
confidence=high

# Stop documenting deliverable 0 for triage fix tasks the validator rejects

## Context

`plan-marshall/workflow/triage.md` line 191 instructs the caller to write a triage fix task with `deliverable: 0`:

> Write the task YAML to the returned scratch path (title, deliverable: 0, domain matching the finding, profile: implementation, ...)

`manage-tasks/scripts/_tasks_core.py` line 759 rejects exactly that:

```python
if deliverable == 0 and origin_raw != 'holistic':
    raise ValueError('Missing required field: deliverable')
```

Triage-added fix tasks carry `origin: pr`, not `origin: holistic`, so a caller following triage.md verbatim gets a hard rejection. The error message compounds it: the field was PRESENT and explicitly `0`, but the message says "Missing required field".

This run never hit the failure, because its six triage tasks (TASK-6 through TASK-11) were written with real deliverable numbers (1, 2, 3, 1, 2, 3) rather than the documented `0`. The doc was silently ignored and the run succeeded because of it.

## Root cause

`0` is used as the absent-sentinel inside the validator (line 755-757 maps `None` and blank to `0`), and is then rejected under a message describing absence. The documentation, meanwhile, treats `0` as a meaningful "no deliverable" value. The two readings of `0` were never reconciled.

## Proposed action

Pick one. Either accept `deliverable: 0` for pr-origin triage tasks the way it is accepted for `holistic`, or correct triage.md to instruct writing the finding's owning deliverable number. In either case fix the message: a present-but-rejected value must not be reported as missing, because that sends the caller looking for an omission that is not there.

## Evidence

- marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md line 191, verified against HEAD.
- marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py lines 755-760, verified against HEAD.
- This plan's own tasks_table: TASK-6..11 all carry non-zero deliverable numbers despite being pr-origin triage tasks, so the documented form was not the form used.

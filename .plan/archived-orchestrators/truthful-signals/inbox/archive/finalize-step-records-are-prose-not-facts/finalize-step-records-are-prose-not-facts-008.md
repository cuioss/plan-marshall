envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:17:58Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=script_failure_analysis,request_result_alignment

# A rejected --fact call retries as prose and the loss leaves no trace

## Context

At 12:01:21Z `branch-cleanup`'s `mark-step-done --fact ...` was rejected (exit 2). At 12:01:34Z the same step re-issued `mark-step-done` without any `--fact` and got `status: success`. The step's persisted record is:

```
branch-cleanup:
  outcome: done
  display_detail: "merged via queue, main pulled, branch + worktree removed"
```

That `display_detail` string is verbatim one of the two prose shapes this plan's own `request.md` quotes as the defect being fixed ("the rest say only *merged via queue, main pulled, branch + worktree removed*").

Nothing in `status.json`, in the step's `display_detail`, or in the finalize step-outcome surface records that four facts were derived, attempted, and dropped. The only trace is one ERROR line in `script-execution.log`. A consumer reading the ledger sees a clean `outcome: done` and has no way to distinguish "this step declared no facts" from "this step's facts were lost".

## Root cause

The degradation path is a caller-side retry with a narrower argv, and the narrower call is indistinguishable from a legitimate no-facts call. `_build_entry` deliberately omits the `facts` key when absent (the omit-when-absent convention that keeps the historical record shape byte-identical) — which is correct for a step that owes no facts, and is exactly what makes a *lost* fact set invisible.

The step's `records_facts` frontmatter declaration is the missing cross-check: it states which keys this step owes, so a record for a step with a non-empty `records_facts` and no `facts` key is detectably wrong.

## Proposed action

1. Do not retry a rejected `mark-step-done` with a narrower argv. Surface the rejection.
2. Add the reciprocal assertion to `assert-step-recorded` (or to the finalize completion check): a step whose `records_facts` declaration is non-empty and whose persisted record carries no `facts` key is a recorded failure, not a pass. This is the population-derived form — derive the expected key set from the step declaration, never from a hardcoded list.
3. If a degraded record must be written at all, mark it (e.g. `facts_unavailable: <reason>`) so the ledger says what it does not know.

## Evidence

- `logs/script-execution.log:1304-1308` — rejection at 12:01:21Z, facts-free success at 12:01:34Z
- `status.json` `metadata.phase_steps["6-finalize"]["branch-cleanup"]` — the prose-only record
- `request.md` § "The two defects, both measured" → defect A quotes the identical string as the defect
- `_cmd_mark_step.py::_build_entry` — `if facts: entry['facts'] = facts` (omit-when-absent, by design)

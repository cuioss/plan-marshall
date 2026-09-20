envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:22:10Z

# Pre-merge review barrier declared participation complete after its evidence script exited 2

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

Three consecutive events on PLAN-203's finalize, in this order:

```
09:50:13 [WARNING] Pre-merge review barrier: required-bot participation incomplete —
         unproven_bots=pr-agent, pending pr-comment findings=0 —
         pre_merge_comment_barrier=fail_into_loopback (merge blocked)
09:58:03 [ERROR]   script_failure notation=plan-marshall:automatic-review:review_completeness
         exit_code=2 failure_kind=argparse_rejection
09:59:05 [INFO]    Pre-merge review barrier: clean — zero pending pr-comment findings,
         required-bot participation complete, proceeding to merge
```

The barrier reversed a merge-blocking verdict 62 seconds after the script that produces the
participation evidence failed with an argparse rejection. Nothing else is recorded between the two
barrier lines.

## Root cause

The barrier's verdict is assembled narratively rather than consumed from `review_completeness`'s TOON
`status`. A script that exits 2 produces no participation evidence at all, but "no evidence of
non-participation" was read as "participation complete" — the same consumed-vs-missing collapse this
epic is named for, sitting directly on the merge gate.

## Why this is severe

This is the gate that decides whether a PR merges without a required reviewer having reviewed it. The
standing epic note already records that `ci pr comments` is necessary but not sufficient as
participation evidence; here the barrier passed with *no* evidence read at all.

## Proposed action

1. `review_completeness` returns a TOON `status`; the barrier MUST branch on it and MUST treat any
   non-`success` status as barrier-fails, never as barrier-clean.
2. Log the concrete evidence the verdict rests on (which bots, which comment IDs, which timestamps) on
   both the clean and the blocked path, so a flip is auditable.
3. Fix the argparse rejection itself — `review_completeness check` was called with a missing required
   argument.

## Evidence

- decision.log 09:50:13 (blocked) and work.log 09:59:05 (clean)
- work.log 09:58:03 — `review_completeness` exit_code=2, `failure_kind=argparse_rejection`
- script-failure-analysis fragment, finding type `argparse_other`

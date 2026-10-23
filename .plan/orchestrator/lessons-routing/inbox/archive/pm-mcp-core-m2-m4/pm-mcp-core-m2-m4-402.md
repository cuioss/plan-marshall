envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:32Z

component=plan-marshall:tools-script-executor
category=anti-pattern
created=2026-10-21
bundle=plan-marshall

# Argparse rejections recurred five times in one finalize run

One run produced five `failure_kind=argparse_rejection` events across four notations,
each costing a retry of the step that issued it:

- `manage-architecture` `--plan-id ... resolve --command quality-gate` (10:40Z)
- `manage-change-ledger append --plan-id ...` — the verb declares no `--plan-id` (12:44Z)
- `review_support validate --findings-file ...` — the flag is `--verdict-file` (15:40Z)
- `ci checks 131` / `ci checks logs --job-id` / missing `run-id` (16:34-16:45Z)
- `manage-findings list --limit ...` — not declared (17:04Z)

None was a logic failure; every one was a call site paraphrasing a declaration.

## Solution

On a rejection, stop and read the declaration (`--help`, or the skill's canonical
invocation block) instead of adjusting the flag name by intuition, and correct the
offending workflow text at authoring time so the next run does not repeat it. The
recovery is cheap, which is exactly why the drift survives: the cost is paid per
occurrence and never accumulates into a single visible failure.

## Impact

Workflow bodies and skills that call manage-* verbs. The count in one run is the signal
worth acting on: five rejections is a documentation-drift cluster, not five accidents.

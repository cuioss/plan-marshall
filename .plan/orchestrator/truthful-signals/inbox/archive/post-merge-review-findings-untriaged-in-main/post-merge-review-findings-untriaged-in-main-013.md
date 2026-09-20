envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T13:11:16Z

component=plan-marshall:manage-logging
category=bug
created=2026-07-29
bundle=plan-marshall

# Make manage-logging read --phase actually filter, or reject it

`manage-logging.py read` declares a `--phase` flag with a constrained choice list:

```
usage: manage-logging.py read [-h] --plan-id PLAN_ID
                              --type {script,work,decision} [--limit LIMIT]
                              [--phase {1-init,2-refine,3-outline,4-plan,5-execute,6-finalize}]
                              [--store {plans,orchestrator}]
```

It accepts the flag, validates the value against the choice list, returns `status: success` — and
filters nothing.

Observed twice in this run against a 330-entry work log:

- `read --type work --phase 6-finalize --limit 400` returned `total_entries: 330, showing: 330` —
  the entire log including all of 1-init through 5-execute.
- `read --type work --phase 1-init --limit 5` returned `total_entries: 330` and, as its five rows,
  the five most recent **6-finalize** lines (12:51:32 through 12:55:45). Not one entry from
  `1-init`.

So the flag is not merely a no-op on a full read: under `--limit` it returns the tail of the
unfiltered log while presenting it as a phase-scoped result.

## Root cause

A declared, choice-validated flag that is never consumed by the read path. The argparse surface
gives a caller every reason to believe the filter exists — it is documented, it rejects invalid
values, and it returns success.

## Solution

Either implement the filter (phase attribution is derivable from the `(plan-marshall:phase-N-...)`
component prefix that work-log lines already carry), or remove the flag and return an explicit
`unsupported_argument` error. A third acceptable option is to keep the flag and have it return
`status: error` with a `filter_not_implemented` code — anything except accepting it and silently
returning the unfiltered set.

Whichever is chosen, `total_entries` must describe the set actually returned, not the set before
a filter that did not run.

## Impact

This is the vacuous-guard archetype (now n=6 for the epic) sitting in the retrospective's own
primary read path. Any consumer that scopes a log read by phase — a retrospective aspect, an audit
check, an operator debugging a single phase — silently receives the whole log and, under a limit,
receives the wrong phase's tail while believing it received the right phase's entries. It is a
confident, schema-validated signal asserting a scoping that never happened.

## Evidence

- `manage-logging read --plan-id post-merge-review-findings-untriaged-in-main --type work
  --phase 6-finalize --limit 400` → `total_entries: 330, showing: 330` (the full log).
- `manage-logging read --plan-id post-merge-review-findings-untriaged-in-main --type work
  --phase 1-init --limit 5` → five 6-finalize entries timestamped 2026-07-29T12:51:32Z onward.
- `manage-logging.py read --help` — the flag and its choice list.
